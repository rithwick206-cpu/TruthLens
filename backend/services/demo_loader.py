from __future__ import annotations

import hashlib
import io
import os
import secrets
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from PIL import Image

from ..db import create_case, update_case_result
from ..schemas import CrossModalResult, FlaggedEvidence, ForensicReport, IngestedFile, ModalitySummary

DEMO_ASSETS_DIR = Path(__file__).resolve().parent.parent / "demo_assets"
STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"
ORIGINALS_DIR = STORAGE_DIR / "originals"
ARTIFACTS_DIR = STORAGE_DIR / "artifacts"
REPORTS_DIR = STORAGE_DIR / "reports"


def ensure_demo_dirs():
    DEMO_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    ORIGINALS_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


DEMO_METADATA = [
    {
        "sample_id": "authentic_bundle",
        "title": "Authentic Field Photo + Consistent Caption",
        "description": "Clean high-res DSLR image with intact camera metadata and reinforcing contextual alignment.",
        "expected_risk_band": "Low Manipulation Indicator",
    },
    {
        "sample_id": "manipulated_multimodal",
        "title": "Manipulated Media + Cloned Audio + Misleading Caption",
        "description": "Synthetically composited image paired with cloned synthetic voice note and misleading breaking news claims.",
        "expected_risk_band": "High Manipulation Indicator",
    },
    {
        "sample_id": "compressed_real_photo",
        "title": "Heavily Compressed Social Media Photo",
        "description": "Authentic mobile capture re-saved multiple times through social messaging apps with stripped EXIF and compression artifacts.",
        "expected_risk_band": "Moderate Indicator — Needs Review",
    },
    {
        "sample_id": "cloned_executive_scam",
        "title": "Executive Voice Clone (CEO Emergency Wire Fraud)",
        "description": "Synthetic voice clone note with vocoder harmonics requesting urgent financial transaction authorization.",
        "expected_risk_band": "High Manipulation Indicator",
    },
    {
        "sample_id": "spliced_political_testimony",
        "title": "Spliced Audio Testimony (Acoustic Discontinuity)",
        "description": "Digitally stitched voice deposition featuring mid-sentence phase jumps and acoustic boundary cuts.",
        "expected_risk_band": "High Manipulation Indicator",
    },
    {
        "sample_id": "telecom_robocall_scam",
        "title": "AI Robocall Banking Scam (Bandpass Telephone Line)",
        "description": "Automated robocall audio message simulating 300Hz-3400Hz cellular compression and synthetic cadence.",
        "expected_risk_band": "High Manipulation Indicator",
    },
    {
        "sample_id": "authentic_broadcast_speech",
        "title": "Authentic Broadcast Address (Wideband Clean Speech)",
        "description": "Genuine studio microphone recording with natural breath cadence and vocal tract formant resonances.",
        "expected_risk_band": "Low Manipulation Indicator",
    },
]


def list_demo_samples() -> List[Dict[str, str]]:
    """Returns metadata for the 3 stage demo bundles."""
    return list(DEMO_METADATA)


def _generate_synthetic_image(output_path: Path, mode: str = "clean") -> bytes:
    """Generates synthetic test image assets."""
    width, height = 400, 400
    img = Image.new("RGB", (width, height), color=(180, 200, 220))

    img_np = np.array(img)
    if mode == "clean":
        # Smooth subtle gradients
        for y in range(height):
            img_np[y, :, 0] = int(120 + 80 * (y / height))
            img_np[y, :, 1] = int(150 + 60 * (y / height))
            img_np[y, :, 2] = 200
        cv2.circle(img_np, (200, 200), 70, (230, 210, 180), -1)
        res_pil = Image.fromarray(img_np)
        res_pil.save(str(output_path), format="PNG")
    elif mode == "manipulated":
        # High contrast boundary patch (face swap boundary anomaly)
        for y in range(height):
            img_np[y, :, 0] = int(80 + 100 * (y / height))
            img_np[y, :, 1] = 130
            img_np[y, :, 2] = 160
        # Discontinuous harsh patch
        img_np[120:280, 120:280] = (245, 170, 130)
        cv2.rectangle(img_np, (120, 120), (280, 280), (255, 200, 150), 2)
        res_pil = Image.fromarray(img_np)
        res_pil.save(str(output_path), format="PNG")
    elif mode == "compressed":
        # Low quality JPEG compression simulation
        for y in range(height):
            img_np[y, :, 0] = (y * 2) % 256
            img_np[y, :, 1] = 140
            img_np[y, :, 2] = 180
        cv2.circle(img_np, (200, 200), 80, (220, 190, 160), -1)
        temp_buf = io.BytesIO()
        temp_pil = Image.fromarray(img_np).resize((180, 180))
        temp_pil.save(temp_buf, format="JPEG", quality=25)
        temp_buf.seek(0)
        reloaded = Image.open(temp_buf).resize((400, 400), Image.NEAREST)
        reloaded.save(str(output_path), format="JPEG", quality=30)

    return output_path.read_bytes()


def _generate_synthetic_audio(
    output_path: Path,
    duration_sec: float = 4.0,
    harmonic: bool = False,
    mode: str = "default",
) -> bytes:
    """Generates 16kHz mono synthetic audio WAV asset across realistic forensic profiles."""
    sr = 16000
    t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)

    if mode == "robocall":
        from scipy.signal import butter, sosfilt

        raw = 0.45 * np.sin(2 * np.pi * 380.0 * t) + 0.3 * np.sin(2 * np.pi * 760.0 * t) + 0.15 * np.sin(2 * np.pi * 1520.0 * t)
        sos = butter(4, [300, 3400], btype="bandpass", fs=sr, output="sos")
        audio = sosfilt(sos, raw)
        audio += 0.02 * np.sin(2 * np.pi * 60.0 * t) + 0.015 * np.random.normal(0, 0.05, size=t.shape)

    elif mode == "spliced":
        half = int(sr * 1.8)
        audio = np.zeros_like(t)
        audio[:half] = 0.45 * np.sin(2 * np.pi * 160.0 * t[:half]) + 0.25 * np.sin(2 * np.pi * 320.0 * t[:half])
        audio[half:] = 0.45 * np.sin(2 * np.pi * 290.0 * t[half:]) + 0.25 * np.sin(2 * np.pi * 580.0 * t[half:])
        audio[half - 10 : half + 10] = 0.8 * np.random.normal(0, 0.2, size=20)

    elif mode == "authentic":
        f0 = 128.0 + 3.5 * np.sin(2 * np.pi * 4.5 * t)
        glottal = sum((1.0 / h) * np.sin(2 * np.pi * h * f0 * t) for h in range(1, 12))
        vowels = 0.5 * np.sin(2 * np.pi * 730 * t) + 0.3 * np.sin(2 * np.pi * 1090 * t) + 0.15 * np.sin(2 * np.pi * 2440 * t)
        envelope = np.clip(0.5 + 0.4 * np.sin(2 * np.pi * 1.1 * t), 0.05, 1.0)
        audio = 0.35 * glottal * vowels * envelope

    elif mode == "cloned_exec" or harmonic:
        audio = 0.5 * np.sin(2 * np.pi * 320.0 * t) + 0.3 * np.sin(2 * np.pi * 640.0 * t)
        audio[int(sr * 1.5) : int(sr * 3.0)] += 0.18 * np.sin(2 * np.pi * 1280.0 * t[int(sr * 1.5) : int(sr * 3.0)])
        audio += 0.02 * np.random.normal(0, 0.05, size=t.shape)

    else:
        audio = 0.4 * np.sin(2 * np.pi * 440.0 * t)

    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val
    audio_int16 = (audio * 28000).astype(np.int16)

    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio_int16.tobytes())

    return output_path.read_bytes()


def _create_heatmap_artifact(output_path: Path, anomaly_level: float = 0.2) -> None:
    """Generates visual ELA / Grad-CAM heatmap PNG."""
    size = (300, 300)
    grid = np.zeros(size, dtype=np.uint8)
    if anomaly_level > 0.6:
        # Strong localized hotspot
        cv2.circle(grid, (150, 150), 60, 240, -1)
        cv2.GaussianBlur(grid, (31, 31), 10, dst=grid)
    elif anomaly_level > 0.35:
        # Moderate diffuse spread
        cv2.circle(grid, (150, 150), 90, 150, -1)
        cv2.GaussianBlur(grid, (51, 51), 15, dst=grid)
    else:
        # Uniform low noise
        grid = np.random.randint(10, 35, size=size, dtype=np.uint8)

    colored = cv2.applyColorMap(grid, cv2.COLORMAP_INFERNO)
    cv2.imwrite(str(output_path), colored)


def load_demo_case(sample_id: str) -> Dict[str, Any]:
    """Loads one of 7 bulletproof stage demo bundles, creating real DB records and real media assets."""
    ensure_demo_dirs()

    ALIASES = {
        "deepfake_speech": "cloned_executive_scam",
        "deepfake_audio": "cloned_executive_scam",
        "cloned_voice": "cloned_executive_scam",
        "ceo_scam": "cloned_executive_scam",
        "spliced_audio": "spliced_political_testimony",
        "spliced_voice": "spliced_political_testimony",
        "robocall": "telecom_robocall_scam",
        "robocall_scam": "telecom_robocall_scam",
        "broadcast_speech": "authentic_broadcast_speech",
        "authentic_speech": "authentic_broadcast_speech",
        "manipulated_image": "manipulated_multimodal",
        "authentic": "authentic_bundle",
        "compressed": "compressed_real_photo",
    }
    sample_id = ALIASES.get(sample_id, sample_id)

    VALID_IDS = [
        "authentic_bundle",
        "manipulated_multimodal",
        "compressed_real_photo",
        "cloned_executive_scam",
        "spliced_political_testimony",
        "telecom_robocall_scam",
        "authentic_broadcast_speech",
    ]

    if sample_id not in VALID_IDS:
        raise ValueError(f"Unknown demo sample_id: '{sample_id}'")

    case_id = f"TL-{secrets.token_hex(4).upper()}"
    created_at = datetime.now(timezone.utc).isoformat()

    if sample_id == "authentic_bundle":
        # 1. Authentic Bundle
        caption = "Field verification photo of wildlife conservation team in Masai Mara, Kenya."
        raw_name = "authentic_field_photo.png"
        asset_file = DEMO_ASSETS_DIR / raw_name
        img_bytes = _generate_synthetic_image(asset_file, mode="clean")

        dest_name = f"{case_id}_image_{raw_name}"
        dest_path = ORIGINALS_DIR / dest_name
        dest_path.write_bytes(img_bytes)
        sha256_hash = hashlib.sha256(img_bytes).hexdigest()

        ela_name = f"{case_id}_image_ela.png"
        gradcam_name = f"{case_id}_image_gradcam.png"
        _create_heatmap_artifact(ARTIFACTS_DIR / ela_name, anomaly_level=0.10)
        _create_heatmap_artifact(ARTIFACTS_DIR / gradcam_name, anomaly_level=0.12)

        files_meta = [
            IngestedFile(
                media_type="image",
                original_filename=raw_name,
                saved_path=str(dest_path.resolve()),
                url_path=f"/storage/originals/{dest_name}",
                sha256_hash=sha256_hash,
                file_size_bytes=len(img_bytes),
                quality_meta={"width": 400, "height": 400, "format": "PNG"},
            ).model_dump()
        ]

        report = ForensicReport(
            case_id=case_id,
            created_at=created_at,
            status="analyzed",
            sha256_hashes={raw_name: sha256_hash},
            overall_risk_band="Low Manipulation Indicator",
            calibrated_confidence=0.14,
            modalities={
                "image": ModalitySummary(
                    media_type="image",
                    calibrated_score=0.14,
                    risk_band="Low Manipulation Indicator",
                    indicators=[
                        "Color temperature and shadow angles follow uniform physical lighting.",
                        "Error Level Analysis demonstrates consistent uniform compression across all quadrant sectors.",
                        "EXIF sensor tags corroborate genuine capture parameters.",
                    ],
                    artifact_urls={
                        "ela": f"/storage/artifacts/{ela_name}",
                        "gradcam": f"/storage/artifacts/{gradcam_name}",
                    },
                    metadata={
                        "model_mode": "custom_trained",
                        "temperature_T": 1.0126,
                        "has_exif": True,
                        "camera_make": "Sony",
                        "camera_model": "ILCE-7RM4",
                        "software": None,
                        "ela_stats": {
                            "mean_diff": 1.42,
                            "max_diff": 12.0,
                            "high_variance_ratio": 0.008,
                            "ela_anomaly_detected": False,
                        },
                    },
                ),
                "text": ModalitySummary(
                    media_type="text",
                    calibrated_score=0.10,
                    risk_band="Low Manipulation Indicator",
                    indicators=["Caption claims align precisely with geographical and visual scene features."],
                    artifact_urls={},
                    metadata={"caption_text": caption, "caption_mismatch_detected": False},
                ),
            },
            flagged_evidence=[],
            cross_modal_correlation=CrossModalResult(
                status="reinforcing",
                summary="Visual forensics, metadata signatures, and caption assertions reinforce authentic media characteristics.",
                details=[
                    "Image neural network score (0.14) reflects low likelihood of synthesis.",
                    "Caption context directly matches visual elements without hyperbole or spatial conflict.",
                ],
            ),
            limitations_and_caveats=[
                "Automated forensic confidence scores are probabilistic indicators, not absolute proof of authenticity or manipulation.",
                "High quality in-camera computational photography enhancements can occasionally mimic subtle digital corrections.",
            ],
            alternative_explanations=[
                "Modern smartphone optical image stabilization and ISP multi-exposure blending produce pristine textures natively.",
            ],
            recommended_human_checks=[
                "Confirm photographer field log entries or RAW camera negative if official courtroom chain-of-custody is required.",
            ],
            summary=(
                f"TruthLens Forensic Audit for Case {case_id}: Media exhibits natural visual continuity with 14.0% "
                "calibrated confidence (Low Manipulation Indicator). Signals across image and caption reinforce authenticity."
            ),
            review_status="confirmed_authentic",
            review_notes="Investigator confirmed authentic metadata and verified field provenance.",
        )

    elif sample_id == "manipulated_multimodal":
        # 2. Manipulated Multimodal Bundle
        caption = "BREAKING: Leaked official emergency press address confirming critical municipal lockdown."
        img_name = "manipulated_face.png"
        aud_name = "cloned_voice.wav"

        img_asset = DEMO_ASSETS_DIR / img_name
        aud_asset = DEMO_ASSETS_DIR / aud_name

        img_bytes = _generate_synthetic_image(img_asset, mode="manipulated")
        aud_bytes = _generate_synthetic_audio(aud_asset, duration_sec=4.0, harmonic=True)

        dest_img_name = f"{case_id}_image_{img_name}"
        dest_aud_name = f"{case_id}_audio_{aud_name}"

        dest_img_path = ORIGINALS_DIR / dest_img_name
        dest_aud_path = ORIGINALS_DIR / dest_aud_name

        dest_img_path.write_bytes(img_bytes)
        dest_aud_path.write_bytes(aud_bytes)

        img_sha = hashlib.sha256(img_bytes).hexdigest()
        aud_sha = hashlib.sha256(aud_bytes).hexdigest()

        ela_name = f"{case_id}_image_ela.png"
        gradcam_name = f"{case_id}_image_gradcam.png"
        _create_heatmap_artifact(ARTIFACTS_DIR / ela_name, anomaly_level=0.85)
        _create_heatmap_artifact(ARTIFACTS_DIR / gradcam_name, anomaly_level=0.88)

        files_meta = [
            IngestedFile(
                media_type="image",
                original_filename=img_name,
                saved_path=str(dest_img_path.resolve()),
                url_path=f"/storage/originals/{dest_img_name}",
                sha256_hash=img_sha,
                file_size_bytes=len(img_bytes),
                quality_meta={"width": 400, "height": 400, "format": "PNG"},
            ).model_dump(),
            IngestedFile(
                media_type="audio",
                original_filename=aud_name,
                saved_path=str(dest_aud_path.resolve()),
                url_path=f"/storage/originals/{dest_aud_name}",
                sha256_hash=aud_sha,
                file_size_bytes=len(aud_bytes),
                quality_meta={"duration_sec": 4.0},
            ).model_dump(),
        ]

        # Waveform peaks
        peaks = [0.12, 0.45, 0.88, 0.95, 0.72, 0.65, 0.91, 0.84, 0.35, 0.18] * 6

        report = ForensicReport(
            case_id=case_id,
            created_at=created_at,
            status="analyzed",
            sha256_hashes={img_name: img_sha, aud_name: aud_sha},
            overall_risk_band="High Manipulation Indicator",
            calibrated_confidence=0.84,
            modalities={
                "image": ModalitySummary(
                    media_type="image",
                    calibrated_score=0.86,
                    risk_band="High Manipulation Indicator",
                    indicators=[
                        "Pronounced boundary discontinuity around central facial perimeter.",
                        "Error Level Analysis variance spike (>0.24) confirms post-capture digital composite.",
                        "Grad-CAM activation focuses intensely on unnatural boundary seams.",
                    ],
                    artifact_urls={
                        "ela": f"/storage/artifacts/{ela_name}",
                        "gradcam": f"/storage/artifacts/{gradcam_name}",
                    },
                    metadata={
                        "model_mode": "custom_trained",
                        "temperature_T": 1.0126,
                        "hotspot_region": "Region (x: 30%-70%, y: 30%-70%)",
                        "has_exif": False,
                        "camera_make": None,
                        "camera_model": None,
                        "software": "Adobe Photoshop 2024 / Generative Fill",
                        "ela_stats": {
                            "mean_diff": 8.75,
                            "max_diff": 48.0,
                            "high_variance_ratio": 0.142,
                            "ela_anomaly_detected": True,
                        },
                    },
                ),
                "audio": ModalitySummary(
                    media_type="audio",
                    calibrated_score=0.81,
                    risk_band="High Manipulation Indicator",
                    indicators=[
                        "Acoustic spectral flatness indicates neural vocoder speech synthesis.",
                        "Robotic formant transitions flagged during window 00:01 - 00:03.",
                    ],
                    artifact_urls={},
                    metadata={
                        "duration_sec": 4.0,
                        "waveform_peaks": peaks,
                        "segments": [
                            {"start_sec": 0.0, "end_sec": 2.0, "timestamp_label": "00:00 - 00:02", "score": 0.75, "risk_band": "High Manipulation Indicator"},
                            {"start_sec": 1.0, "end_sec": 3.0, "timestamp_label": "00:01 - 00:03", "score": 0.88, "risk_band": "High Manipulation Indicator"},
                            {"start_sec": 2.0, "end_sec": 4.0, "timestamp_label": "00:02 - 00:04", "score": 0.79, "risk_band": "High Manipulation Indicator"},
                        ],
                    },
                ),
                "text": ModalitySummary(
                    media_type="text",
                    calibrated_score=0.85,
                    risk_band="High Manipulation Indicator",
                    indicators=["Caption text presents fabricated emergency claims inconsistent with official registries."],
                    artifact_urls={},
                    metadata={"caption_text": caption, "caption_mismatch_detected": True},
                ),
            },
            flagged_evidence=[
                FlaggedEvidence(
                    media_type="image",
                    location_or_timestamp="Region (x: 30%-70%, y: 30%-70%)",
                    indicator="Neural Network Feature Anomaly (Grad-CAM Hotspot)",
                    severity="high",
                    explanation="Elevated activation concentrated on composite boundary suggesting deepfake face swap insertion.",
                    artifact_url=f"/storage/artifacts/{gradcam_name}",
                ),
                FlaggedEvidence(
                    media_type="audio",
                    location_or_timestamp="00:01 - 00:03",
                    indicator="Acoustic Discontinuity / Deepfake Voice Indicator",
                    severity="high",
                    explanation="High synthetic voice anomaly score (0.88) during speech window with metallic harmonic overtones.",
                    artifact_url=None,
                ),
                FlaggedEvidence(
                    media_type="text",
                    location_or_timestamp="Caption vs. Media Context",
                    indicator="Cross-Modal Context Mismatch",
                    severity="high",
                    explanation="Sensational lockdown claim contradicts verified official civil protection announcements.",
                    artifact_url=None,
                ),
            ],
            cross_modal_correlation=CrossModalResult(
                status="reinforcing",
                summary="Multimodal synthesis flags consistent manipulation across both visual boundaries and acoustic vocoder features.",
                details=[
                    "Image score (0.86) and audio score (0.81) both independently indicate synthetic generation.",
                    "False emergency caption text further amplifies deception probability.",
                ],
            ),
            limitations_and_caveats=[
                "Automated forensic confidence scores are probabilistic indicators, not absolute proof of authenticity or manipulation.",
                "Severely distorted amateur microphones can occasionally produce elevated acoustic anomaly spikes.",
            ],
            alternative_explanations=[
                "Creative dramatic satire or voice actor performance recorded through aggressive noise gate.",
            ],
            recommended_human_checks=[
                "Inspect high-resolution ELA compression heatmap for localized block misalignment.",
                "Cross-check purported lockdown announcement against municipal state government gazette.",
                "Perform spectrographic pitch-track analysis on the audio stream.",
            ],
            summary=(
                f"TruthLens Forensic Investigation for Case {case_id}: CRITICAL RISK. Combined evidence from visual "
                "face swap boundaries, vocoder audio synthesis (84.0% confidence), and fabricated emergency caption."
            ),
            review_status="confirmed_manipulated",
            review_notes="Investigator confirmed synthetic voice clone and spliced face overlay.",
        )

    elif sample_id == "compressed_real_photo":
        # 3. Compressed Real Photo
        caption = "Forwarded photo from WhatsApp family group chat of birthday celebration."
        raw_name = "compressed_photo.jpg"
        asset_file = DEMO_ASSETS_DIR / raw_name
        img_bytes = _generate_synthetic_image(asset_file, mode="compressed")

        dest_name = f"{case_id}_image_{raw_name}"
        dest_path = ORIGINALS_DIR / dest_name
        dest_path.write_bytes(img_bytes)
        sha256_hash = hashlib.sha256(img_bytes).hexdigest()

        ela_name = f"{case_id}_image_ela.png"
        gradcam_name = f"{case_id}_image_gradcam.png"
        _create_heatmap_artifact(ARTIFACTS_DIR / ela_name, anomaly_level=0.45)
        _create_heatmap_artifact(ARTIFACTS_DIR / gradcam_name, anomaly_level=0.42)

        files_meta = [
            IngestedFile(
                media_type="image",
                original_filename=raw_name,
                saved_path=str(dest_path.resolve()),
                url_path=f"/storage/originals/{dest_name}",
                sha256_hash=sha256_hash,
                file_size_bytes=len(img_bytes),
                quality_meta={"width": 400, "height": 400, "format": "JPEG", "quality_warning": "Low resolution re-compressed image"},
            ).model_dump()
        ]

        report = ForensicReport(
            case_id=case_id,
            created_at=created_at,
            status="analyzed",
            sha256_hashes={raw_name: sha256_hash},
            overall_risk_band="Moderate Indicator — Needs Review",
            calibrated_confidence=0.48,
            modalities={
                "image": ModalitySummary(
                    media_type="image",
                    calibrated_score=0.48,
                    risk_band="Moderate Indicator — Needs Review",
                    indicators=[
                        "EXIF metadata header is completely absent from file.",
                        "Widespread 8x8 DCT grid artifacts typical of aggressive JPEG re-compression.",
                        "Neural activation displays diffuse non-localized uncertainty.",
                    ],
                    artifact_urls={
                        "ela": f"/storage/artifacts/{ela_name}",
                        "gradcam": f"/storage/artifacts/{gradcam_name}",
                    },
                    metadata={
                        "model_mode": "custom_trained",
                        "temperature_T": 1.0126,
                        "has_exif": False,
                        "camera_make": None,
                        "camera_model": None,
                        "software": None,
                        "ela_stats": {
                            "mean_diff": 4.12,
                            "max_diff": 28.0,
                            "high_variance_ratio": 0.045,
                            "ela_anomaly_detected": False,
                        },
                    },
                ),
                "text": ModalitySummary(
                    media_type="text",
                    calibrated_score=0.30,
                    risk_band="Low Manipulation Indicator",
                    indicators=["Informal chat caption consistent with common social re-sharing patterns."],
                    artifact_urls={},
                    metadata={"caption_text": caption, "caption_mismatch_detected": False},
                ),
            },
            flagged_evidence=[
                FlaggedEvidence(
                    media_type="image",
                    location_or_timestamp="Full Image (Compression Residuals)",
                    indicator="Error Level Analysis Inconsistency",
                    severity="moderate",
                    explanation="Elevated residual difference caused by low JPEG compression quality (Q~25) rather than selective splicing.",
                    artifact_url=f"/storage/artifacts/{ela_name}",
                )
            ],
            cross_modal_correlation=CrossModalResult(
                status="inconclusive",
                summary="Moderate visual anomaly score driven by severe social media re-compression rather than malicious tampering.",
                details=[
                    "Image score of 0.48 lies in the ambiguous review band.",
                    "Absence of EXIF metadata is standard for WhatsApp/Instagram re-encodings.",
                ],
            ),
            limitations_and_caveats=[
                "Automated forensic confidence scores are probabilistic indicators, not absolute proof of authenticity or manipulation.",
                "Repeated social media re-compression introduces high-frequency loss that degrades deepfake classifier precision.",
                "EXIF metadata stripping is routine across instant messaging platforms for privacy and bandwidth conservation.",
            ],
            alternative_explanations=[
                "Natural photo subjected to multiple forwards and automatic platform downscaling.",
            ],
            recommended_human_checks=[
                "Request original uncompressed image file directly from camera roll of capturing device.",
                "Inspect image zoom for blocky JPEG compression artifacts vs. AI generative texture smoothing.",
            ],
            summary=(
                f"TruthLens Forensic Audit for Case {case_id}: Ambiguous finding (48.0% confidence, Moderate Indicator). "
                "Elevated signals are attributed to severe messaging platform re-compression rather than generative tampering."
            ),
            review_status="needs_review",
            review_notes="Requires original camera file to rule out compression false positive.",
        )

    elif sample_id == "cloned_executive_scam":
        # 4. Executive Voice Clone (CEO Wire Fraud)
        caption = "URGENT: Leaked voice note from CEO authorizing immediate $250,000 emergency treasury wire transfer before market close."
        aud_name = "ceo_wire_transfer_clone.wav"
        aud_asset = DEMO_ASSETS_DIR / aud_name
        aud_bytes = _generate_synthetic_audio(aud_asset, duration_sec=4.0, mode="cloned_exec")

        dest_aud_name = f"{case_id}_audio_{aud_name}"
        dest_aud_path = ORIGINALS_DIR / dest_aud_name
        dest_aud_path.write_bytes(aud_bytes)
        aud_sha = hashlib.sha256(aud_bytes).hexdigest()

        files_meta = [
            IngestedFile(
                media_type="audio",
                original_filename=aud_name,
                saved_path=str(dest_aud_path.resolve()),
                url_path=f"/storage/originals/{dest_aud_name}",
                sha256_hash=aud_sha,
                file_size_bytes=len(aud_bytes),
                quality_meta={"duration_sec": 4.0, "format": "WAV"},
            ).model_dump()
        ]

        peaks = [0.15, 0.42, 0.85, 0.96, 0.82, 0.68, 0.89, 0.91, 0.44, 0.22] * 6
        transcript = "This is CEO John Davis. I am authorizing an immediate emergency wire transfer of two hundred and fifty thousand dollars to the overseas escrow account. Do not delay."

        report = ForensicReport(
            case_id=case_id,
            created_at=created_at,
            status="analyzed",
            sha256_hashes={aud_name: aud_sha},
            overall_risk_band="High Manipulation Indicator",
            calibrated_confidence=0.94,
            modalities={
                "audio": ModalitySummary(
                    media_type="audio",
                    calibrated_score=0.95,
                    risk_band="High Manipulation Indicator",
                    indicators=[
                        "Wav2Vec2 deepfake audio neural classifier detected synthetic speech pattern (score: 0.985).",
                        "Elevated spectral flatness and robotic formant transition anomalies in vocoder synthesis band.",
                        "Absence of authentic human micro-tremor and natural room reverberation signatures.",
                    ],
                    artifact_urls={},
                    metadata={
                        "duration_sec": 4.0,
                        "model_mode": "wav2vec2_pretrained",
                        "waveform_peaks": peaks,
                        "transcript_status": "complete",
                        "transcript_text": transcript,
                        "transcript_segments": [
                            {"start_sec": 0.0, "end_sec": 2.0, "text": "This is CEO John Davis. I am authorizing an immediate emergency wire transfer"},
                            {"start_sec": 2.0, "end_sec": 4.0, "text": "of two hundred and fifty thousand dollars to the overseas escrow account."},
                        ],
                        "segments": [
                            {"start_sec": 0.0, "end_sec": 2.0, "timestamp_label": "00:00 - 00:02", "score": 0.96, "risk_band": "High Manipulation Indicator"},
                            {"start_sec": 1.0, "end_sec": 3.0, "timestamp_label": "00:01 - 00:03", "score": 0.99, "risk_band": "High Manipulation Indicator"},
                            {"start_sec": 2.0, "end_sec": 4.0, "timestamp_label": "00:02 - 00:04", "score": 0.95, "risk_band": "High Manipulation Indicator"},
                        ],
                    },
                ),
                "text": ModalitySummary(
                    media_type="text",
                    calibrated_score=0.92,
                    risk_band="High Manipulation Indicator",
                    indicators=["Viral urgency claim directly matches social engineering and CEO impersonation wire scam vectors."],
                    artifact_urls={},
                    metadata={"caption_text": caption, "caption_mismatch_detected": True},
                ),
            },
            flagged_evidence=[
                FlaggedEvidence(
                    media_type="audio",
                    location_or_timestamp="00:01 - 00:03",
                    indicator="Acoustic Discontinuity / Deepfake Voice Indicator",
                    severity="high",
                    explanation="Elevated acoustic synthesis anomaly score (0.99) during high-pressure monetary demand.",
                    artifact_url=None,
                )
            ],
            cross_modal_correlation=CrossModalResult(
                status="contradictory",
                summary="Voice note exhibits severe synthetic vocoder signatures typical of commercial AI voice cloning used in corporate fraud.",
                details=[
                    "Acoustic features demonstrate artificial harmonic structure and zero natural ambient room acoustics.",
                    "Transcript content presents high-risk urgent financial authorization without standard multi-factor verification.",
                ],
            ),
            limitations_and_caveats=[
                "Automated forensic confidence scores are probabilistic indicators, not absolute proof of authenticity or manipulation.",
            ],
            alternative_explanations=[
                "Scripted voice training demo or cybersecurity awareness phishing test simulation.",
            ],
            recommended_human_checks=[
                "Execute out-of-band telephone verification with executive using verified internal company directory number.",
                "Verify ERP treasury system authorization logs for dual-approval sign-offs.",
            ],
            summary=(
                f"TruthLens Forensic Audit for Case {case_id}: CRITICAL FRAUD RISK (94.0% Calibrated Confidence). "
                "Neural classifier identifies cloned synthetic speech targeting emergency wire transfer authorization."
            ),
            review_status="confirmed_manipulated",
            review_notes="Investigator confirmed cloned voice profile matching commercial voice synthesis.",
        )

    elif sample_id == "spliced_political_testimony":
        # 5. Spliced Deposition Audio
        caption = "LEAKED: Explosive closed-door deposition where director admits to concealing corporate audit findings."
        aud_name = "spliced_testimony.wav"
        aud_asset = DEMO_ASSETS_DIR / aud_name
        aud_bytes = _generate_synthetic_audio(aud_asset, duration_sec=4.0, mode="spliced")

        dest_aud_name = f"{case_id}_audio_{aud_name}"
        dest_aud_path = ORIGINALS_DIR / dest_aud_name
        dest_aud_path.write_bytes(aud_bytes)
        aud_sha = hashlib.sha256(aud_bytes).hexdigest()

        files_meta = [
            IngestedFile(
                media_type="audio",
                original_filename=aud_name,
                saved_path=str(dest_aud_path.resolve()),
                url_path=f"/storage/originals/{dest_aud_name}",
                sha256_hash=aud_sha,
                file_size_bytes=len(aud_bytes),
                quality_meta={"duration_sec": 4.0, "format": "WAV"},
            ).model_dump()
        ]

        peaks = [0.22, 0.48, 0.65, 0.72, 0.58, 0.95, 0.99, 0.88, 0.76, 0.35] * 6
        transcript = "I affirm that our accounting was completely legal and verified... and we hid thirty million dollars in offshore shell companies."

        report = ForensicReport(
            case_id=case_id,
            created_at=created_at,
            status="analyzed",
            sha256_hashes={aud_name: aud_sha},
            overall_risk_band="High Manipulation Indicator",
            calibrated_confidence=0.91,
            modalities={
                "audio": ModalitySummary(
                    media_type="audio",
                    calibrated_score=0.92,
                    risk_band="High Manipulation Indicator",
                    indicators=[
                        "Abrupt spectral boundary discontinuity detected at timestamp 00:01.8.",
                        "Zero-crossing rate and phase coherence collapse confirms digital splice insertion.",
                        "Ambient room noise floor drops to zero across the splice boundary seam.",
                    ],
                    artifact_urls={},
                    metadata={
                        "duration_sec": 4.0,
                        "model_mode": "wav2vec2_pretrained",
                        "waveform_peaks": peaks,
                        "transcript_status": "complete",
                        "transcript_text": transcript,
                        "transcript_segments": [
                            {"start_sec": 0.0, "end_sec": 1.8, "text": "I affirm that our accounting was completely legal and verified..."},
                            {"start_sec": 1.8, "end_sec": 4.0, "text": "and we hid thirty million dollars in offshore shell companies."},
                        ],
                        "segments": [
                            {"start_sec": 0.0, "end_sec": 1.8, "timestamp_label": "00:00 - 00:01", "score": 0.25, "risk_band": "Low Manipulation Indicator"},
                            {"start_sec": 1.5, "end_sec": 2.5, "timestamp_label": "00:01 - 00:02", "score": 0.96, "risk_band": "High Manipulation Indicator"},
                            {"start_sec": 2.0, "end_sec": 4.0, "timestamp_label": "00:02 - 00:04", "score": 0.78, "risk_band": "High Manipulation Indicator"},
                        ],
                    },
                ),
                "text": ModalitySummary(
                    media_type="text",
                    calibrated_score=0.88,
                    risk_band="High Manipulation Indicator",
                    indicators=["Viral headline selectively amplifies spliced sentence out of context."],
                    artifact_urls={},
                    metadata={"caption_text": caption, "caption_mismatch_detected": True},
                ),
            },
            flagged_evidence=[
                FlaggedEvidence(
                    media_type="audio",
                    location_or_timestamp="00:01.8 - 00:02.2",
                    indicator="Acoustic Phase Discontinuity / Digital Splice",
                    severity="high",
                    explanation="Sharp frequency leap from 160Hz to 290Hz with inverted phase indicates post-recording audio editing.",
                    artifact_url=None,
                )
            ],
            cross_modal_correlation=CrossModalResult(
                status="contradictory",
                summary="Digital splicing joins two mutually contradictory statements into a fabricated confession.",
                details=[
                    "The first half of the recording (0.0s - 1.8s) possesses authentic acoustic properties.",
                    "A severe phase discontinuity at 1.8s splices in a distinct second voice profile.",
                ],
            ),
            limitations_and_caveats=[
                "Automated forensic confidence scores are probabilistic indicators, not absolute proof of authenticity or manipulation.",
            ],
            alternative_explanations=[
                "Rough editorial cut made for television soundbite preview without malicious intent.",
            ],
            recommended_human_checks=[
                "Obtain court stenographer official transcript and unedited master recording of the complete deposition.",
            ],
            summary=(
                f"TruthLens Forensic Audit for Case {case_id}: TAMPERING DETECTED (91.0% Confidence). "
                "Digital splice boundary at 00:01.8 inverts the legal meaning of speaker deposition."
            ),
            review_status="confirmed_manipulated",
            review_notes="Investigator confirmed abrupt phase cut and digital splicing at 00:01.8.",
        )

    elif sample_id == "telecom_robocall_scam":
        # 6. AI Robocall Banking Scam
        caption = "Automated security alert robocall warning bank account holders of suspicious account seizure."
        aud_name = "banking_robocall_scam.wav"
        aud_asset = DEMO_ASSETS_DIR / aud_name
        aud_bytes = _generate_synthetic_audio(aud_asset, duration_sec=4.0, mode="robocall")

        dest_aud_name = f"{case_id}_audio_{aud_name}"
        dest_aud_path = ORIGINALS_DIR / dest_aud_name
        dest_aud_path.write_bytes(aud_bytes)
        aud_sha = hashlib.sha256(aud_bytes).hexdigest()

        files_meta = [
            IngestedFile(
                media_type="audio",
                original_filename=aud_name,
                saved_path=str(dest_aud_path.resolve()),
                url_path=f"/storage/originals/{dest_aud_name}",
                sha256_hash=aud_sha,
                file_size_bytes=len(aud_bytes),
                quality_meta={"duration_sec": 4.0, "format": "WAV"},
            ).model_dump()
        ]

        peaks = [0.35, 0.75, 0.82, 0.78, 0.65, 0.80, 0.85, 0.79, 0.68, 0.45] * 6
        transcript = "Alert from fraud prevention. Your primary debit card has been placed on hold due to suspicious transactions. Press one to verify your social security number."

        report = ForensicReport(
            case_id=case_id,
            created_at=created_at,
            status="analyzed",
            sha256_hashes={aud_name: aud_sha},
            overall_risk_band="High Manipulation Indicator",
            calibrated_confidence=0.89,
            modalities={
                "audio": ModalitySummary(
                    media_type="audio",
                    calibrated_score=0.91,
                    risk_band="High Manipulation Indicator",
                    indicators=[
                        "Automated speech synthesizer rhythm detected with unnatural uniform pacing.",
                        "PSTN 300Hz-3400Hz bandpass filtering simulated over cellular telephony channel.",
                        "Monotonic pitch contour characteristic of automated scam dialer synthesis.",
                    ],
                    artifact_urls={},
                    metadata={
                        "duration_sec": 4.0,
                        "model_mode": "wav2vec2_pretrained",
                        "waveform_peaks": peaks,
                        "transcript_status": "complete",
                        "transcript_text": transcript,
                        "transcript_segments": [
                            {"start_sec": 0.0, "end_sec": 2.0, "text": "Alert from fraud prevention. Your primary debit card has been placed on hold"},
                            {"start_sec": 2.0, "end_sec": 4.0, "text": "due to suspicious transactions. Press one to verify your social security number."},
                        ],
                        "segments": [
                            {"start_sec": 0.0, "end_sec": 2.0, "timestamp_label": "00:00 - 00:02", "score": 0.89, "risk_band": "High Manipulation Indicator"},
                            {"start_sec": 1.0, "end_sec": 3.0, "timestamp_label": "00:01 - 00:03", "score": 0.93, "risk_band": "High Manipulation Indicator"},
                            {"start_sec": 2.0, "end_sec": 4.0, "timestamp_label": "00:02 - 00:04", "score": 0.88, "risk_band": "High Manipulation Indicator"},
                        ],
                    },
                ),
                "text": ModalitySummary(
                    media_type="text",
                    calibrated_score=0.86,
                    risk_band="High Manipulation Indicator",
                    indicators=["Script follows recognized social engineering patterns used to harvest financial credentials."],
                    artifact_urls={},
                    metadata={"caption_text": caption, "caption_mismatch_detected": True},
                ),
            },
            flagged_evidence=[
                FlaggedEvidence(
                    media_type="audio",
                    location_or_timestamp="00:00 - 00:04",
                    indicator="Synthetic Robocall Speech Cadence / Bandpass Channel",
                    severity="high",
                    explanation="Automated text-to-speech cadence matched to high-volume telecommunication phishing campaigns.",
                    artifact_url=None,
                )
            ],
            cross_modal_correlation=CrossModalResult(
                status="contradictory",
                summary="Acoustic analysis confirms automated AI voice engine operating through telephony bandpass channel.",
                details=[
                    "Robotic prosody and absence of biological breathing cadence strongly corroborate synthetic voice generation.",
                ],
            ),
            limitations_and_caveats=[
                "Automated forensic confidence scores are probabilistic indicators, not absolute proof of authenticity or manipulation.",
            ],
            alternative_explanations=[
                "Legitimate automated IVR customer notification system from registered financial institution.",
            ],
            recommended_human_checks=[
                "Cross-check caller originating telephone number against telecommunication spoofing databases.",
            ],
            summary=(
                f"TruthLens Forensic Audit for Case {case_id}: SUSPECTED SCAM (89.0% Confidence). "
                "Automated voice engine requesting sensitive credential input over filtered voice channel."
            ),
            review_status="confirmed_manipulated",
            review_notes="Investigator verified automated robocall scam targeting banking credentials.",
        )

    elif sample_id == "authentic_broadcast_speech":
        # 7. Authentic Broadcast Speech
        caption = "Official live press address by university spokesperson announcing medical research grant awards."
        aud_name = "authentic_broadcast_speech.wav"
        aud_asset = DEMO_ASSETS_DIR / aud_name
        aud_bytes = _generate_synthetic_audio(aud_asset, duration_sec=4.0, mode="authentic")

        dest_aud_name = f"{case_id}_audio_{aud_name}"
        dest_aud_path = ORIGINALS_DIR / dest_aud_name
        dest_aud_path.write_bytes(aud_bytes)
        aud_sha = hashlib.sha256(aud_bytes).hexdigest()

        files_meta = [
            IngestedFile(
                media_type="audio",
                original_filename=aud_name,
                saved_path=str(dest_aud_path.resolve()),
                url_path=f"/storage/originals/{dest_aud_name}",
                sha256_hash=aud_sha,
                file_size_bytes=len(aud_bytes),
                quality_meta={"duration_sec": 4.0, "format": "WAV"},
            ).model_dump()
        ]

        peaks = [0.18, 0.45, 0.62, 0.58, 0.42, 0.65, 0.72, 0.68, 0.35, 0.15] * 6
        transcript = "Good afternoon everyone. We are delighted to announce that the foundation has awarded forty million dollars in competitive research grants for pediatric neuroscience."

        report = ForensicReport(
            case_id=case_id,
            created_at=created_at,
            status="analyzed",
            sha256_hashes={aud_name: aud_sha},
            overall_risk_band="Low Manipulation Indicator",
            calibrated_confidence=0.11,
            modalities={
                "audio": ModalitySummary(
                    media_type="audio",
                    calibrated_score=0.11,
                    risk_band="Low Manipulation Indicator",
                    indicators=[
                        "Vocal tract formant resonances (F1, F2, F3) match natural physiological human acoustics.",
                        "Dynamic pitch cadence, respiratory pauses, and ambient room reverberation corroborate authentic human speech.",
                        "Zero anomalous phase cuts or vocoder artifacts detected across time domain.",
                    ],
                    artifact_urls={},
                    metadata={
                        "duration_sec": 4.0,
                        "model_mode": "wav2vec2_pretrained",
                        "waveform_peaks": peaks,
                        "transcript_status": "complete",
                        "transcript_text": transcript,
                        "transcript_segments": [
                            {"start_sec": 0.0, "end_sec": 2.0, "text": "Good afternoon everyone. We are delighted to announce that the foundation"},
                            {"start_sec": 2.0, "end_sec": 4.0, "text": "has awarded forty million dollars in competitive research grants for pediatric neuroscience."},
                        ],
                        "segments": [
                            {"start_sec": 0.0, "end_sec": 2.0, "timestamp_label": "00:00 - 00:02", "score": 0.09, "risk_band": "Low Manipulation Indicator"},
                            {"start_sec": 1.0, "end_sec": 3.0, "timestamp_label": "00:01 - 00:03", "score": 0.12, "risk_band": "Low Manipulation Indicator"},
                            {"start_sec": 2.0, "end_sec": 4.0, "timestamp_label": "00:02 - 00:04", "score": 0.10, "risk_band": "Low Manipulation Indicator"},
                        ],
                    },
                ),
                "text": ModalitySummary(
                    media_type="text",
                    calibrated_score=0.08,
                    risk_band="Low Manipulation Indicator",
                    indicators=["Context and entities align with verified university institutional press releases."],
                    artifact_urls={},
                    metadata={"caption_text": caption, "caption_mismatch_detected": False},
                ),
            },
            flagged_evidence=[],
            cross_modal_correlation=CrossModalResult(
                status="reinforcing",
                summary="Acoustic features, natural speech cadence, and contextual claims reinforce genuine broadcast provenance.",
                details=[
                    "Voice stream exhibits continuous vocal tract formants and unperturbed room reverberation.",
                    "Claim text corresponds directly with transcribed speech without exaggeration.",
                ],
            ),
            limitations_and_caveats=[
                "Automated forensic confidence scores are probabilistic indicators, not absolute proof of authenticity or manipulation.",
            ],
            alternative_explanations=[
                "Authentic studio broadcast recording.",
            ],
            recommended_human_checks=[
                "Confirm official publication on the university press portal for full transcript verification.",
            ],
            summary=(
                f"TruthLens Forensic Audit for Case {case_id}: VERIFIED AUTHENTIC (11.0% Confidence, Low Risk). "
                "Natural acoustic vocal resonances and reinforcing claim context confirm genuine broadcast origin."
            ),
            review_status="confirmed_authentic",
            review_notes="Investigator confirmed genuine studio microphone recording and institutional provenance.",
        )

    # Persist case in SQLite
    create_case(
        case_id=case_id,
        created_at=created_at,
        status="analyzed",
        caption_text=caption,
        files=files_meta,
        review_status=report.review_status,
        review_notes=report.review_notes,
        result=report.model_dump(),
    )

    return report.model_dump()
