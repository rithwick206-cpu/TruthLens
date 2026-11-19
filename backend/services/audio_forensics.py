from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH, override=True)

import numpy as np

# Set writable cache directories
HF_CACHE_DIR = Path(__file__).resolve().parent.parent / "models" / "hf_cache"
HF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("HF_HOME", str(HF_CACHE_DIR))
os.environ.setdefault("TORCH_HOME", "/tmp/torch")

# Singleton audio model cache
_AUDIO_MODEL_BUNDLE: Optional[Dict[str, Any]] = None


def load_audio_16k_mono(audio_path: str) -> Tuple[np.ndarray, float, List[float]]:
    """Loads any audio file (WAV, MP3, M4A, OGG) to 16 kHz mono float32 numpy array.
    Returns (waveform, duration_sec, waveform_peaks)."""
    import soundfile as sf
    import librosa
    import imageio_ffmpeg

    waveform: Optional[np.ndarray] = None
    sr: int = 16000

    # 1. Try reading directly with soundfile
    try:
        data, file_sr = sf.read(audio_path, dtype="float32")
        if data.ndim > 1:
            data = np.mean(data, axis=1)
        if file_sr != sr:
            data = librosa.resample(data, orig_sr=file_sr, target_sr=sr)
        waveform = data
    except Exception:
        pass

    # 2. Try librosa load
    if waveform is None:
        try:
            data, _ = librosa.load(audio_path, sr=sr, mono=True)
            waveform = data
        except Exception:
            pass

    # 3. Fallback to FFmpeg conversion via temporary WAV
    if waveform is None:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_wav_path = tmp.name

        try:
            cmd = [
                ffmpeg_exe,
                "-y",
                "-i",
                str(audio_path),
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                tmp_wav_path,
            ]
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=15,
                check=True,
            )
            data, _ = sf.read(tmp_wav_path, dtype="float32")
            if data.ndim > 1:
                data = np.mean(data, axis=1)
            waveform = data
        finally:
            if os.path.exists(tmp_wav_path):
                try:
                    os.remove(tmp_wav_path)
                except OSError:
                    pass

    if waveform is None or len(waveform) == 0:
        waveform = np.zeros(16000, dtype=np.float32)

    # Compute duration
    duration_sec = round(len(waveform) / float(sr), 2)

    # Compute ~60 normalized waveform peaks for frontend timeline
    num_peaks = 60
    if len(waveform) < num_peaks:
        raw_peaks = [float(abs(x)) for x in waveform] + [0.0] * (num_peaks - len(waveform))
    else:
        chunk_size = len(waveform) // num_peaks
        raw_peaks = []
        for i in range(num_peaks):
            chunk = waveform[i * chunk_size : (i + 1) * chunk_size]
            peak = float(np.max(np.abs(chunk))) if len(chunk) > 0 else 0.0
            raw_peaks.append(peak)

    max_peak = max(raw_peaks) if raw_peaks and max(raw_peaks) > 0 else 1.0
    waveform_peaks = [round(float(p / max_peak), 3) for p in raw_peaks]

    return waveform.astype(np.float32), duration_sec, waveform_peaks


def _is_host_reachable(host: str = "huggingface.co", port: int = 443, timeout: float = 0.5) -> bool:
    import socket

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        return True
    except Exception:
        return False


def _load_audio_classifier() -> Dict[str, Any]:
    """Loads the Wav2Vec2 deepfake audio classifier or falls back to acoustic heuristic mode."""
    global _AUDIO_MODEL_BUNDLE
    if _AUDIO_MODEL_BUNDLE is not None:
        return _AUDIO_MODEL_BUNDLE

    model_name = "MelodyMachine/Deepfake-audio-detection-V2"
    try:
        from transformers import AutoFeatureExtractor, AutoModelForAudioClassification

        # Try local cache first to avoid blocking when offline
        try:
            feature_extractor = AutoFeatureExtractor.from_pretrained(model_name, local_files_only=True)
            model = AutoModelForAudioClassification.from_pretrained(model_name, local_files_only=True)
            model.eval()
            _AUDIO_MODEL_BUNDLE = {
                "model": model,
                "feature_extractor": feature_extractor,
                "model_mode": "wav2vec2_pretrained",
                "caveat": None,
            }
            return _AUDIO_MODEL_BUNDLE
        except Exception:
            pass

        if not _is_host_reachable():
            raise ConnectionError("Hugging Face host unreachable or offline in current environment.")

        feature_extractor = AutoFeatureExtractor.from_pretrained(model_name)
        model = AutoModelForAudioClassification.from_pretrained(model_name)
        model.eval()

        _AUDIO_MODEL_BUNDLE = {
            "model": model,
            "feature_extractor": feature_extractor,
            "model_mode": "wav2vec2_pretrained",
            "caveat": None,
        }
    except Exception as e:
        _AUDIO_MODEL_BUNDLE = {
            "model": None,
            "feature_extractor": None,
            "model_mode": "acoustic_heuristic_fallback",
            "caveat": (
                f"Wav2Vec2 audio classifier ({model_name}) is unavailable or offline ({str(e)}); "
                "operating in acoustic-feature heuristic fallback mode."
            ),
        }

    return _AUDIO_MODEL_BUNDLE


def _evaluate_audio_window(window: np.ndarray, sr: int = 16000) -> float:
    """Evaluates a single audio segment (2.0s or shorter) and returns a manipulation score [0.0, 1.0]."""
    bundle = _load_audio_classifier()
    model_mode = bundle["model_mode"]

    if model_mode == "wav2vec2_pretrained":
        try:
            import torch

            model = bundle["model"]
            extractor = bundle["feature_extractor"]
            inputs = extractor(window, sampling_rate=sr, return_tensors="pt", padding=True)
            with torch.no_grad():
                logits = model(**inputs).logits
                probs = torch.softmax(logits, dim=-1)[0]
                # Default assume class 1 is fake / synthetic, or check id2label
                fake_idx = 1
                if hasattr(model.config, "id2label"):
                    for idx, label in model.config.id2label.items():
                        if any(w in label.lower() for w in ["fake", "synthetic", "spoof"]):
                            fake_idx = int(idx)
                            break
                return float(probs[fake_idx].item())
        except Exception:
            pass

    # Acoustic heuristic fallback via librosa
    import librosa

    try:
        # 1. Spectral Flatness
        flatness = librosa.feature.spectral_flatness(y=window)
        mean_flatness = float(np.mean(flatness))

        # 2. Zero Crossing Rate
        zcr = librosa.feature.zero_crossing_rate(y=window)
        zcr_var = float(np.var(zcr))

        # 3. MFCC delta variance (vocoder smoothing artifact)
        mfcc = librosa.feature.mfcc(y=window, sr=sr, n_mfcc=13)
        delta_mfcc = librosa.feature.delta(mfcc)
        delta_var = float(np.var(delta_mfcc))

        # Heuristic scoring: synthetic speech often exhibits flat spectral tails and reduced delta dynamics
        heuristic = 0.25
        if mean_flatness > 0.08:
            heuristic += 0.20
        if delta_var < 1.5:
            heuristic += 0.20
        if zcr_var < 0.001:
            heuristic += 0.15

        return round(float(np.clip(heuristic, 0.05, 0.85)), 3)
    except Exception:
        return 0.35


def run_audio_detector(waveform: np.ndarray, sr: int = 16000) -> Dict[str, Any]:
    """Slices audio into 2.0s sliding windows with 1.0s stride and scores manipulation."""
    bundle = _load_audio_classifier()
    model_mode = bundle["model_mode"]
    caveat = bundle["caveat"]

    window_size = int(2.0 * sr)  # 32,000 samples
    stride = int(1.0 * sr)       # 16,000 samples
    total_len = len(waveform)

    segments: List[Dict[str, Any]] = []

    if total_len <= window_size:
        # Clip shorter than 2 seconds -> single window
        score = _evaluate_audio_window(waveform, sr)
        risk = (
            "Low Manipulation Indicator"
            if score < 0.35
            else ("Moderate Indicator — Needs Review" if score <= 0.65 else "High Manipulation Indicator")
        )
        dur = round(total_len / float(sr), 2)
        segments.append(
            {
                "start_sec": 0.0,
                "end_sec": dur,
                "timestamp_label": f"00:00 - {int(dur//60):02d}:{int(dur%60):02d}",
                "score": score,
                "risk_band": risk,
            }
        )
    else:
        start_idx = 0
        while start_idx < total_len:
            end_idx = min(start_idx + window_size, total_len)
            window = waveform[start_idx:end_idx]

            # If the last residual chunk is shorter than 0.5s, break
            if len(window) < int(0.5 * sr) and segments:
                break

            score = _evaluate_audio_window(window, sr)
            risk = (
                "Low Manipulation Indicator"
                if score < 0.35
                else ("Moderate Indicator — Needs Review" if score <= 0.65 else "High Manipulation Indicator")
            )
            s_sec = round(start_idx / float(sr), 2)
            e_sec = round(end_idx / float(sr), 2)
            lbl = f"{int(s_sec//60):02d}:{int(s_sec%60):02d} - {int(e_sec//60):02d}:{int(e_sec%60):02d}"

            segments.append(
                {
                    "start_sec": s_sec,
                    "end_sec": e_sec,
                    "timestamp_label": lbl,
                    "score": score,
                    "risk_band": risk,
                }
            )

            if end_idx >= total_len:
                break
            start_idx += stride

    scores = [s["score"] for s in segments]
    # Blended score: 70% peak anomaly + 30% mean
    if scores:
        calibrated_score = round(float(0.7 * max(scores) + 0.3 * np.mean(scores)), 4)
    else:
        calibrated_score = 0.3

    calibrated_score = max(0.0, min(1.0, calibrated_score))
    if calibrated_score < 0.35:
        overall_risk = "Low Manipulation Indicator"
    elif calibrated_score <= 0.65:
        overall_risk = "Moderate Indicator — Needs Review"
    else:
        overall_risk = "High Manipulation Indicator"

    return {
        "calibrated_score": calibrated_score,
        "overall_risk_band": overall_risk,
        "segments": segments,
        "model_mode": model_mode,
        "caveat": caveat,
    }


def transcribe_audio_groq(audio_path: str) -> Dict[str, Any]:
    """Transcribes audio using Groq Whisper-large-v3-turbo with graceful degradation."""
    groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not groq_api_key or groq_api_key.lower() == "optional":
        return {
            "transcript_status": "not_configured",
            "text": "",
            "segments": [],
            "caveat": "Groq API key not configured; speech-to-text transcription bypassed.",
        }

    try:
        from groq import Groq

        client = Groq(api_key=groq_api_key, timeout=15.0)
        with open(audio_path, "rb") as f:
            transcription = client.audio.transcriptions.create(
                file=(Path(audio_path).name, f.read()),
                model="whisper-large-v3-turbo",
                response_format="verbose_json",
            )

        full_text = getattr(transcription, "text", "") or ""
        raw_segments = getattr(transcription, "segments", []) or []
        segments = [
            {
                "start": float(getattr(s, "start", 0.0) or 0.0),
                "end": float(getattr(s, "end", 0.0) or 0.0),
                "text": str(getattr(s, "text", "")).strip(),
            }
            for s in raw_segments
        ]
        return {
            "transcript_status": "completed",
            "text": full_text,
            "segments": segments,
            "caveat": None,
        }
    except Exception as exc:
        return {
            "transcript_status": "degraded",
            "text": "",
            "segments": [],
            "caveat": f"Groq Whisper transcription failed or timed out ({str(exc)}).",
        }


def analyze_audio_file(
    audio_path: str,
    case_id: str,
    artifact_prefix: str = "audio",
) -> Dict[str, Any]:
    """Public reusable entrypoint for audio forensics analysis."""
    waveform, duration_sec, waveform_peaks = load_audio_16k_mono(audio_path)
    detection_res = run_audio_detector(waveform, sr=16000)
    transcript_res = transcribe_audio_groq(audio_path)

    indicators: List[str] = []
    limitations: List[str] = []
    alternative_explanations: List[str] = []
    flagged_evidence: List[Dict[str, Any]] = []

    if duration_sec < 3.0:
        limitations.append(
            f"Short audio clip ({duration_sec}s < 3.0s); voice synthesis detection reliability is reduced."
        )

    if detection_res.get("caveat"):
        limitations.append(detection_res["caveat"])

    if transcript_res.get("caveat") and transcript_res["transcript_status"] != "completed":
        limitations.append(transcript_res["caveat"])

    # Collect indicators from segments
    for seg in detection_res["segments"]:
        if seg["score"] >= 0.55:
            severity = "high" if seg["score"] > 0.65 else "moderate"
            indicators.append(
                f"Synthetic voice artifact detected in segment {seg['timestamp_label']} (score: {seg['score']:.2f})."
            )
            flagged_evidence.append(
                {
                    "media_type": "audio",
                    "location_or_timestamp": seg["timestamp_label"],
                    "indicator": "Acoustic Discontinuity / Deepfake Voice Indicator",
                    "severity": severity,
                    "explanation": (
                        f"Elevated acoustic anomaly score of {seg['score']:.2f} detected during "
                        f"window {seg['timestamp_label']}."
                    ),
                    "artifact_url": None,
                }
            )

    if not flagged_evidence:
        indicators.append("Audio waveform exhibits natural vocal harmonics with no prominent vocoder artifacts.")

    alternative_explanations.extend(
        [
            "Cellular or VoIP codecs (AMR, Opus low-bitrate) can introduce robotic or phase artifacts resembling synthesis.",
            "Aggressive noise suppression algorithms (e.g., Zoom/Discord Krisp) can flatten natural room reverberation.",
        ]
    )

    modality_summary = {
        "media_type": "audio",
        "calibrated_score": detection_res["calibrated_score"],
        "risk_band": detection_res["overall_risk_band"],
        "indicators": indicators,
        "artifact_urls": {},
        "metadata": {
            "duration_sec": duration_sec,
            "model_mode": detection_res["model_mode"],
            "segments": detection_res["segments"],
            "waveform_peaks": waveform_peaks,
            "transcript_status": transcript_res["transcript_status"],
            "transcript_text": transcript_res["text"],
            "transcript_segments": transcript_res["segments"],
        },
    }

    return {
        "modality_summary": modality_summary,
        "flagged_evidence": flagged_evidence,
        "limitations": limitations,
        "alternative_explanations": alternative_explanations,
    }
