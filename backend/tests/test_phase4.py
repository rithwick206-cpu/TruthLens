from __future__ import annotations

import hashlib
import io
import os
import wave
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.schemas import ForensicReport
from backend.services.correlator import (
    GeminiCorrelationOutput,
    VQAProbeFinding,
    compute_deterministic_correlation,
    correlate_case_findings,
)

client = TestClient(app)


def generate_png_bytes(width: int = 300, height: int = 300) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (width, height), color=(90, 140, 210))
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_wav_bytes(duration_sec: float = 2.5, sr: int = 16000) -> bytes:
    import numpy as np

    t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
    audio = 0.4 * np.sin(2 * np.pi * 350.0 * t)
    audio_int16 = (audio * 32767).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio_int16.tobytes())
    return buf.getvalue()


def test_correlator_deterministic_fallback_without_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    img_bytes = generate_png_bytes()
    wav_bytes = generate_wav_bytes()

    ingest_resp = client.post(
        "/api/cases/ingest",
        data={"caption_text": "Live broadcast clip of government press conference."},
        files={
            "image": ("press_photo.png", img_bytes, "image/png"),
            "audio": ("press_speech.wav", wav_bytes, "audio/wav"),
        },
    )
    assert ingest_resp.status_code == 201
    case_id = ingest_resp.json()["case_id"]

    analyze_resp = client.post(f"/api/analyze/{case_id}")
    assert analyze_resp.status_code == 200

    report = ForensicReport(**analyze_resp.json())
    assert report.case_id == case_id
    assert report.status == "analyzed"
    assert report.cross_modal_correlation is not None
    assert report.cross_modal_correlation.status in [
        "reinforcing",
        "contradictory",
        "inconclusive",
        "single_modality",
    ]

    # Verify caveats contain calibration disclaimer and Gemini unconfigured note
    caveats = report.limitations_and_caveats
    assert any("probabilistic indicators" in c.lower() for c in caveats)
    assert any("gemini multimodal correlator not configured" in c.lower() for c in caveats)


def test_correlator_contradictory_signals():
    # Direct test of compute_deterministic_correlation with divergent scores
    modalities = {
        "image": {
            "media_type": "image",
            "calibrated_score": 0.15,
            "risk_band": "Low Manipulation Indicator",
            "indicators": ["Natural facial lighting"],
        },
        "audio": {
            "media_type": "audio",
            "calibrated_score": 0.88,
            "risk_band": "High Manipulation Indicator",
            "indicators": ["Robotic vocal synthesis"],
        },
    }
    result = compute_deterministic_correlation(
        modalities=modalities,
        flagged_evidence=[],
        caption_text=None,
    )

    cm = result["cross_modal_correlation"]
    assert cm["status"] == "contradictory"
    assert "contradictory" in cm["summary"].lower()


def test_correlator_mocked_gemini_vqa_mismatch(monkeypatch):
    mock_gemini_output = GeminiCorrelationOutput(
        cross_modal_status="contradictory",
        cross_modal_summary="Deepfake audio detected while video background is authentic.",
        cross_modal_details=["Vocal harmonics indicate neural vocoder generation."],
        vqa_findings=[
            VQAProbeFinding(
                probe_question="Is the mouth movement synchronized with speech?",
                observation="Mouth movements fail to correspond to phoneme bursts.",
                supports_manipulation=True,
                severity="high",
            )
        ],
        caption_mismatch_detected=True,
        caption_mismatch_explanation="Caption claims official presidential address, but footage is from an unverified podcast.",
        additional_limitations=["Low light video compression."],
        additional_alternative_explanations=["Satirical dubbing by third party."],
        recommended_human_checks=["Review official White House press transcript."],
        executive_summary="High-risk forensic case: audio synthesis corroborated by caption-footage conflict.",
    )

    # Monkeypatch run_gemini_correlator to return mocked output
    monkeypatch.setattr(
        "backend.services.correlator.run_gemini_correlator",
        lambda dossier, image_paths=None: (mock_gemini_output, "success"),
    )

    img_bytes = generate_png_bytes()
    ingest_resp = client.post(
        "/api/cases/ingest",
        data={"caption_text": "Official presidential speech."},
        files={"image": ("speech_frame.png", img_bytes, "image/png")},
    )
    assert ingest_resp.status_code == 201
    case_id = ingest_resp.json()["case_id"]

    analyze_resp = client.post(f"/api/analyze/{case_id}")
    assert analyze_resp.status_code == 200

    report = ForensicReport(**analyze_resp.json())
    assert report.case_id == case_id
    assert report.cross_modal_correlation.status == "contradictory"
    assert report.summary == mock_gemini_output.executive_summary

    # Verify VQA probe and Caption mismatch evidence appear in flagged_evidence
    flagged_indicators = [f.indicator for f in report.flagged_evidence]
    assert any("Cross-Modal Context Mismatch" in ind for ind in flagged_indicators)
    assert any("VQA Anomaly" in ind for ind in flagged_indicators)

    # Verify recommended human checks include Gemini's check
    assert any("Review official White House" in chk for chk in report.recommended_human_checks)


def test_correlator_gemini_error_graceful_fallback(monkeypatch):
    # Monkeypatch run_gemini_correlator to simulate an API error
    monkeypatch.setattr(
        "backend.services.correlator.run_gemini_correlator",
        lambda dossier, image_paths=None: (None, "error: APIConnectionTimeout"),
    )

    img_bytes = generate_png_bytes()
    ingest_resp = client.post(
        "/api/cases/ingest",
        data={"caption_text": "Breaking news clip."},
        files={"image": ("news_photo.png", img_bytes, "image/png")},
    )
    assert ingest_resp.status_code == 201
    case_id = ingest_resp.json()["case_id"]

    analyze_resp = client.post(f"/api/analyze/{case_id}")
    # Must never throw HTTP 500
    assert analyze_resp.status_code == 200

    report = ForensicReport(**analyze_resp.json())
    assert report.case_id == case_id
    assert any("degraded gracefully" in c.lower() for c in report.limitations_and_caveats)


def test_analyze_caption_only_case():
    ingest_resp = client.post(
        "/api/cases/ingest",
        data={"caption_text": "Viral claim circulating without accompanying media attachments."},
    )
    assert ingest_resp.status_code == 201
    case_id = ingest_resp.json()["case_id"]

    analyze_resp = client.post(f"/api/analyze/{case_id}")
    assert analyze_resp.status_code == 200

    report = ForensicReport(**analyze_resp.json())
    assert report.case_id == case_id
    assert report.status == "analyzed"
    assert report.overall_risk_band == "Insufficient Media — Needs Review"
    assert report.calibrated_confidence == 0.25
    assert "text" in report.modalities
