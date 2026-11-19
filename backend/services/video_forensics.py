from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import imageio_ffmpeg
import numpy as np

from .audio_forensics import analyze_audio_file
from .image_forensics import analyze_image_file

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
ARTIFACTS_DIR = STORAGE_DIR / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def sample_video_frames(
    video_path: str,
    max_frames: int = 20,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], str]:
    """Samples frames from a video at ~1 FPS (or 20 evenly spaced frames if >20s).
    Returns (sampled_frames_meta, video_meta, temp_dir)."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Unable to open video file: {video_path}")

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration_sec = round(total_frames / fps, 2) if fps > 0 else 0.0

    video_meta = {
        "fps": round(fps, 2),
        "total_frames": total_frames,
        "width": width,
        "height": height,
        "duration_sec": duration_sec,
    }

    # Decide frame indices to sample
    if total_frames <= 0:
        cap.release()
        return [], video_meta, ""

    if duration_sec <= float(max_frames):
        # 1 FPS sampling
        step = max(1, int(round(fps)))
        target_indices = list(range(0, total_frames, step))[:max_frames]
    else:
        # Evenly spaced sampling across long video
        target_indices = [
            int(i * (total_frames - 1) / max(1, max_frames - 1))
            for i in range(max_frames)
        ]

    # Remove duplicates and ensure sorted
    target_indices = sorted(list(dict.fromkeys(target_indices)))

    temp_dir = tempfile.mkdtemp(prefix="truthlens_vid_frames_")
    sampled_frames: List[Dict[str, Any]] = []

    current_idx = 0
    target_set = set(target_indices)

    while cap.isOpened() and len(sampled_frames) < len(target_indices):
        ret, frame = cap.read()
        if not ret:
            break

        if current_idx in target_set:
            t_sec = round(current_idx / fps, 2)
            t_str = f"{int(t_sec // 60):02d}:{int(t_sec % 60):02d}"
            frame_filename = f"frame_{current_idx:06d}.png"
            frame_path = os.path.join(temp_dir, frame_filename)
            cv2.imwrite(frame_path, frame)

            sampled_frames.append(
                {
                    "frame_index": current_idx,
                    "timestamp_sec": t_sec,
                    "timestamp_str": t_str,
                    "image_path": frame_path,
                }
            )

        current_idx += 1
        if current_idx > max(target_indices):
            break

    cap.release()
    return sampled_frames, video_meta, temp_dir


def extract_video_audio_track(video_path: str) -> Optional[str]:
    """Extracts the audio track from video to a 16kHz mono WAV using ffmpeg.
    Returns temporary WAV path if audio exists and is non-empty, else None."""
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio:
        tmp_wav_path = tmp_audio.name

    try:
        cmd = [
            ffmpeg_exe,
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            tmp_wav_path,
        ]
        res = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
        )
        if res.returncode == 0 and os.path.exists(tmp_wav_path) and os.path.getsize(tmp_wav_path) > 1000:
            return tmp_wav_path
    except Exception:
        pass

    if os.path.exists(tmp_wav_path):
        try:
            os.remove(tmp_wav_path)
        except OSError:
            pass
    return None


def analyze_video_file(
    video_path: str,
    case_id: str,
) -> Dict[str, Any]:
    """Public reusable entrypoint for temporal video forensics + audio track extraction."""
    indicators: List[str] = []
    limitations: List[str] = []
    alternative_explanations: List[str] = []
    flagged_evidence: List[Dict[str, Any]] = []
    artifact_urls: Dict[str, str] = {}

    # 1. Sample Video Frames
    sampled_frames, video_meta, temp_dir = sample_video_frames(video_path, max_frames=20)
    if not sampled_frames:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        return {
            "modality_summary": {
                "media_type": "video",
                "calibrated_score": 0.5,
                "risk_band": "Moderate Indicator — Needs Review",
                "indicators": ["Video stream could not be decoded or contained no readable frames."],
                "artifact_urls": {},
                "metadata": {"video_meta": video_meta, "has_audio": False},
            },
            "extracted_audio_result": None,
            "flagged_evidence": [],
            "limitations": ["Corrupted or empty video stream."],
            "alternative_explanations": [],
        }

    # 2. Fast per-frame scoring pass (no Grad-CAM / ELA on the initial scan)
    frame_timeline: List[Dict[str, Any]] = []
    for f in sampled_frames:
        res = analyze_image_file(
            image_path=f["image_path"],
            case_id=case_id,
            artifact_prefix=f"vid_temp_{f['frame_index']}",
            generate_gradcam=False,
            run_exif_ela=False,
        )
        score = res["modality_summary"]["calibrated_score"]
        frame_timeline.append(
            {
                "frame_index": f["frame_index"],
                "timestamp_sec": f["timestamp_sec"],
                "timestamp_str": f["timestamp_str"],
                "score": score,
                "image_path": f["image_path"],
            }
        )

    # 3. Compute temporal statistics
    scores = [f["score"] for f in frame_timeline]
    mean_score = float(np.mean(scores))
    max_score = float(np.max(scores))
    score_std = float(np.std(scores))

    deltas = (
        [abs(scores[i] - scores[i - 1]) for i in range(1, len(scores))]
        if len(scores) > 1
        else [0.0]
    )
    max_frame_delta = float(np.max(deltas)) if deltas else 0.0

    temporal_stats = {
        "mean_score": round(mean_score, 4),
        "max_score": round(max_score, 4),
        "score_std": round(score_std, 4),
        "max_frame_delta": round(max_frame_delta, 4),
        "total_sampled": len(frame_timeline),
    }

    if max_frame_delta >= 0.25:
        indicators.append(
            f"Temporal visual inconsistency detected: score jump of {max_frame_delta:.2f} between consecutive frames."
        )
        flagged_evidence.append(
            {
                "media_type": "video",
                "location_or_timestamp": "Temporal Frame Sequence",
                "indicator": "Temporal Consistency Jump (Inter-frame Anomaly)",
                "severity": "moderate",
                "explanation": (
                    f"Sharp jump of {max_frame_delta:.2f} in facial manipulation confidence between adjacent frames "
                    "suggests intermittent face replacement or temporal blending discontinuities."
                ),
                "artifact_url": None,
            }
        )

    # 4. Identify up to top 3 highest-risk keyframes for Grad-CAM & ELA
    sorted_frames = sorted(frame_timeline, key=lambda x: x["score"], reverse=True)
    top_keyframes = sorted_frames[: min(3, len(sorted_frames))]
    keyframe_details: List[Dict[str, Any]] = []

    for rank, kf in enumerate(top_keyframes):
        prefix = f"video_frame_{kf['frame_index']}"
        kf_res = analyze_image_file(
            image_path=kf["image_path"],
            case_id=case_id,
            artifact_prefix=prefix,
            generate_gradcam=True,
            run_exif_ela=True,
        )
        kf_mod = kf_res["modality_summary"]

        for art_key, art_url in kf_mod.get("artifact_urls", {}).items():
            artifact_urls[f"frame_{kf['frame_index']}_{art_key}"] = art_url

        # Add keyframe flagged evidence
        for fe in kf_res.get("flagged_evidence", []):
            fe["location_or_timestamp"] = f"Frame @ {kf['timestamp_str']} ({fe['location_or_timestamp']})"
            fe["media_type"] = "video"
            flagged_evidence.append(fe)

        # Also preserve original keyframe image for side-by-side visual comparison
        raw_keyframe_filename = f"{case_id}_{prefix}_raw.png"
        raw_keyframe_path = ARTIFACTS_DIR / raw_keyframe_filename
        try:
            shutil.copyfile(kf["image_path"], raw_keyframe_path)
            kf_mod.setdefault("artifact_urls", {})["raw"] = f"/storage/artifacts/{raw_keyframe_filename}"
            artifact_urls[f"frame_{kf['frame_index']}_raw"] = f"/storage/artifacts/{raw_keyframe_filename}"
        except Exception:
            pass

        keyframe_details.append(
            {
                "frame_index": kf["frame_index"],
                "timestamp_str": kf["timestamp_str"],
                "timestamp_sec": kf["timestamp_sec"],
                "score": kf["score"],
                "artifact_urls": kf_mod.get("artifact_urls", {}),
            }
        )

        limitations.extend(kf_res.get("limitations", []))
        alternative_explanations.extend(kf_res.get("alternative_explanations", []))

    # Overall video calibrated score: 70% peak frame + 30% mean
    calibrated_score = round(float(0.7 * max_score + 0.3 * mean_score), 4)
    calibrated_score = max(0.0, min(1.0, calibrated_score))

    if calibrated_score < 0.35:
        risk_band = "Low Manipulation Indicator"
        indicators.append("Temporal frame analysis demonstrates consistent visual fidelity across sampled intervals.")
    elif calibrated_score <= 0.65:
        risk_band = "Moderate Indicator — Needs Review"
        indicators.append("Sampled video frames display moderate feature ambiguity requiring human inspection.")
    else:
        risk_band = "High Manipulation Indicator"
        indicators.append("Deep learning analysis flags persistent synthetic artifacts across sampled video frames.")

    # 5. Audio track extraction & analysis
    tmp_audio_path = extract_video_audio_track(video_path)
    extracted_audio_res: Optional[Dict[str, Any]] = None
    has_audio = False

    if tmp_audio_path:
        has_audio = True
        try:
            extracted_audio_res = analyze_audio_file(
                audio_path=tmp_audio_path,
                case_id=case_id,
                artifact_prefix="video_audio",
            )
            # Tag audio flagged evidence
            for fe in extracted_audio_res.get("flagged_evidence", []):
                flagged_evidence.append(fe)
            limitations.extend(extracted_audio_res.get("limitations", []))
            alternative_explanations.extend(extracted_audio_res.get("alternative_explanations", []))
        finally:
            if os.path.exists(tmp_audio_path):
                try:
                    os.remove(tmp_audio_path)
                except OSError:
                    pass

    # Clean up temp frames directory
    if temp_dir and os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)

    alternative_explanations.extend(
        [
            "High video compression (H.264/H.265 bitrate starvation) produces blockiness and temporal flickering mimicking face swap boundaries.",
            "Motion blur during rapid camera or head movements frequently triggers elevated deepfake model activations.",
        ]
    )

    clean_timeline = [
        {
            "frame_index": f["frame_index"],
            "timestamp_sec": f["timestamp_sec"],
            "timestamp_str": f["timestamp_str"],
            "score": f["score"],
        }
        for f in frame_timeline
    ]

    modality_summary = {
        "media_type": "video",
        "calibrated_score": calibrated_score,
        "risk_band": risk_band,
        "indicators": indicators,
        "artifact_urls": artifact_urls,
        "metadata": {
            "duration_sec": video_meta["duration_sec"],
            "fps": video_meta["fps"],
            "total_frames": video_meta["total_frames"],
            "width": video_meta["width"],
            "height": video_meta["height"],
            "frame_timeline": clean_timeline,
            "temporal_stats": temporal_stats,
            "keyframes": keyframe_details,
            "has_audio": has_audio,
        },
    }

    return {
        "modality_summary": modality_summary,
        "extracted_audio_result": extracted_audio_res,
        "flagged_evidence": flagged_evidence,
        "limitations": list(dict.fromkeys(limitations)),
        "alternative_explanations": list(dict.fromkeys(alternative_explanations)),
    }
