from __future__ import annotations

import hashlib
import io
import os
import tempfile
import wave
from pathlib import Path
from PIL import Image
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.schemas import ForensicReport

client = TestClient(app)


def generate_synthetic_wav(duration_sec: float = 3.0, sample_rate: int = 16000) -> bytes:
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    # 440 Hz + 880 Hz harmonic
    audio = 0.5 * np.sin(2 * np.pi * 440.0 * t) + 0.2 * np.sin(2 * np.pi * 880.0 * t)
    audio_int16 = (audio * 32767).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())
    return buf.getvalue()


def generate_synthetic_mp4(num_frames: int = 30, fps: int = 10, width: int = 256, height: int = 256) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(tmp_path, fourcc, fps, (width, height))
        for i in range(num_frames):
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame[:, :, 0] = (i * 8) % 256
            frame[:, :, 1] = 120
            frame[:, :, 2] = 200
            cv2.circle(frame, (30 + i * 5, 128), 20, (0, 255, 255), -1)
            out.write(frame)
        out.release()
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def generate_synthetic_png(width: int = 300, height: int = 300) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (width, height), color=(100, 150, 200))
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_analyze_audio_end_to_end():
    wav_bytes = generate_synthetic_wav(duration_sec=3.0)
    expected_hash = hashlib.sha256(wav_bytes).hexdigest()

    ingest_resp = client.post(
        "/api/cases/ingest",
        data={"caption_text": "Sample voice note for speech synthesis check."},
        files={"audio": ("suspect_voice.wav", wav_bytes, "audio/wav")},
    )
    assert ingest_resp.status_code == 201
    case_id = ingest_resp.json()["case_id"]

    analyze_resp = client.post(f"/api/analyze/{case_id}")
    assert analyze_resp.status_code == 200

    report = ForensicReport(**analyze_resp.json())
    assert report.case_id == case_id
    assert report.status == "analyzed"
    assert 0.0 <= report.calibrated_confidence <= 1.0

    assert "audio" in report.modalities
    audio_mod = report.modalities["audio"]
    assert audio_mod.media_type == "audio"
    assert 0.0 <= audio_mod.calibrated_score <= 1.0
    assert audio_mod.risk_band in [
        "Low Manipulation Indicator",
        "Moderate Indicator — Needs Review",
        "High Manipulation Indicator",
    ]

    # Verify audio metadata fields: segments, waveform_peaks, duration_sec
    assert "segments" in audio_mod.metadata
    assert len(audio_mod.metadata["segments"]) > 0
    assert "waveform_peaks" in audio_mod.metadata
    assert len(audio_mod.metadata["waveform_peaks"]) == 60
    assert audio_mod.metadata["duration_sec"] >= 2.9

    # Verify SHA-256 match
    assert report.sha256_hashes["suspect_voice.wav"] == expected_hash


def test_analyze_video_end_to_end():
    mp4_bytes = generate_synthetic_mp4(num_frames=30, fps=10)
    expected_hash = hashlib.sha256(mp4_bytes).hexdigest()

    ingest_resp = client.post(
        "/api/cases/ingest",
        data={"caption_text": "Short clip showing potential facial deepfake."},
        files={"video": ("sample_clip.mp4", mp4_bytes, "video/mp4")},
    )
    assert ingest_resp.status_code == 201
    case_id = ingest_resp.json()["case_id"]

    analyze_resp = client.post(f"/api/analyze/{case_id}")
    assert analyze_resp.status_code == 200

    report = ForensicReport(**analyze_resp.json())
    assert report.case_id == case_id
    assert report.status == "analyzed"
    assert 0.0 <= report.calibrated_confidence <= 1.0

    assert "video" in report.modalities
    video_mod = report.modalities["video"]
    assert video_mod.media_type == "video"
    assert 0.0 <= video_mod.calibrated_score <= 1.0

    # Verify frame timeline exists in metadata
    assert "frame_timeline" in video_mod.metadata
    assert len(video_mod.metadata["frame_timeline"]) > 0
    assert "temporal_stats" in video_mod.metadata

    # Verify keyframe artifacts exist on disk and serve via static mount
    assert len(video_mod.artifact_urls) > 0
    for art_name, art_url in video_mod.artifact_urls.items():
        resp = client.get(art_url)
        assert resp.status_code == 200
        assert "image" in resp.headers.get("content-type", "")
        # Disk existence check
        art_file = Path(__file__).resolve().parent.parent / "storage" / "artifacts" / Path(art_url).name
        assert art_file.exists()

    assert report.sha256_hashes["sample_clip.mp4"] == expected_hash


def test_analyze_multimodal_bundle():
    png_bytes = generate_synthetic_png(300, 300)
    wav_bytes = generate_synthetic_wav(3.0)
    img_hash = hashlib.sha256(png_bytes).hexdigest()
    wav_hash = hashlib.sha256(wav_bytes).hexdigest()

    caption = "A viral celebrity interview clip with altered audio and image."
    ingest_resp = client.post(
        "/api/cases/ingest",
        data={"caption_text": caption},
        files={
            "image": ("interview_photo.png", png_bytes, "image/png"),
            "audio": ("interview_audio.wav", wav_bytes, "audio/wav"),
        },
    )
    assert ingest_resp.status_code == 201
    case_id = ingest_resp.json()["case_id"]

    analyze_resp = client.post(f"/api/analyze/{case_id}")
    assert analyze_resp.status_code == 200

    report = ForensicReport(**analyze_resp.json())
    assert report.case_id == case_id

    # Verify both modalities are present
    assert "image" in report.modalities
    assert "audio" in report.modalities

    # Verify sha256 hashes
    assert report.sha256_hashes["interview_photo.png"] == img_hash
    assert report.sha256_hashes["interview_audio.wav"] == wav_hash

    # Verify cross modal status acknowledges multiple modalities
    assert report.cross_modal_correlation is not None
    assert report.cross_modal_correlation.status in ["reinforcing", "contradictory", "inconclusive", "single_modality"]
