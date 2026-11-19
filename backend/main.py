from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_PATH, override=True)

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

from .db import (
    create_case,
    get_case,
    init_db,
    list_cases,
    update_case_result,
    update_case_review,
)
from .schemas import (
    CaseIngestResponse,
    CaseRecord,
    CrossModalResult,
    FlaggedEvidence,
    ForensicReport,
    IngestedFile,
    ModalitySummary,
    ReviewUpdateRequest,
    ReviewUpdateResponse,
)
from .services.audio_forensics import analyze_audio_file
from .services.correlator import correlate_case_findings
from .services.demo_loader import list_demo_samples, load_demo_case
from .services.image_forensics import analyze_image_file
from .services.pdf_report import generate_forensic_pdf
from .services.video_forensics import analyze_video_file

BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
ORIGINALS_DIR = STORAGE_DIR / "originals"
ARTIFACTS_DIR = STORAGE_DIR / "artifacts"
REPORTS_DIR = STORAGE_DIR / "reports"

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB


def ensure_directories():
    ORIGINALS_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


ensure_directories()
init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_directories()
    init_db()
    yield


app = FastAPI(
    title="TruthLens Backend",
    description="Multimodal Digital Forensics & Deepfake Detection Backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/storage/originals", StaticFiles(directory=str(ORIGINALS_DIR)), name="originals")
app.mount("/storage/artifacts", StaticFiles(directory=str(ARTIFACTS_DIR)), name="artifacts")
app.mount("/storage/reports", StaticFiles(directory=str(REPORTS_DIR)), name="reports")


def generate_case_id() -> str:
    return f"TL-{secrets.token_hex(4).upper()}"


def sanitize_filename(filename: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename)
    return cleaned or "unnamed_file"


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "TruthLens Backend"}


def _detect_media_type(filename: str, content_type: Optional[str] = None) -> str:
    ct = (content_type or "").lower()
    if ct.startswith("image/"):
        return "image"
    if ct.startswith("video/"):
        return "video"
    if ct.startswith("audio/"):
        return "audio"
    ext = Path(filename).suffix.lower()
    if ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff"]:
        return "image"
    if ext in [".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"]:
        return "video"
    if ext in [".wav", ".mp3", ".m4a", ".ogg", ".flac", ".aac"]:
        return "audio"
    return "image"


@app.post("/api/cases/ingest", response_model=CaseIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_case(
    image: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
    files: Optional[List[UploadFile]] = File(None),
    file: Optional[UploadFile] = File(None),
    media: Optional[UploadFile] = File(None),
    caption_text: Optional[str] = Form(None),
):
    caption = caption_text.strip() if caption_text and caption_text.strip() else None

    media_inputs = []
    if image is not None and image.filename:
        media_inputs.append(("image", image))
    if video is not None and video.filename:
        media_inputs.append(("video", video))
    if audio is not None and audio.filename:
        media_inputs.append(("audio", audio))

    # Also accept generic form keys ('files', 'file', 'media')
    generic_uploads = []
    if files:
        generic_uploads.extend(files)
    if file is not None and file.filename:
        generic_uploads.append(file)
    if media is not None and media.filename:
        generic_uploads.append(media)

    already_added_names = {f.filename for _, f in media_inputs}
    for uf in generic_uploads:
        if uf and uf.filename and uf.filename not in already_added_names:
            m_t = _detect_media_type(uf.filename, uf.content_type)
            media_inputs.append((m_t, uf))
            already_added_names.add(uf.filename)

    if not media_inputs and not caption:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one file or caption must be provided.",
        )

    case_id = generate_case_id()
    created_at = datetime.now(timezone.utc).isoformat()
    ingested_files: List[IngestedFile] = []

    for media_type, upload_file in media_inputs:
        content = await upload_file.read()
        file_size = len(content)

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{upload_file.filename}' exceeds maximum allowed size of 25 MB.",
            )

        sha256_hash = hashlib.sha256(content).hexdigest()
        safe_name = sanitize_filename(upload_file.filename)
        saved_filename = f"{case_id}_{media_type}_{safe_name}"
        dest_path = ORIGINALS_DIR / saved_filename

        dest_path.write_bytes(content)

        quality_meta: Dict[str, Any] = {}
        if media_type == "image":
            try:
                with Image.open(BytesIO(content)) as img:
                    quality_meta["width"] = img.width
                    quality_meta["height"] = img.height
                    quality_meta["format"] = img.format
                    if img.width < 256 or img.height < 256:
                        quality_meta["quality_warning"] = (
                            f"Low resolution image ({img.width}x{img.height} < 256px); "
                            "forensic reliability may be degraded."
                        )
            except Exception as e:
                quality_meta["quality_warning"] = f"Unable to parse image metadata: {str(e)}"

        ingested_files.append(
            IngestedFile(
                media_type=media_type,
                original_filename=upload_file.filename,
                saved_path=str(dest_path.resolve()),
                url_path=f"/storage/originals/{saved_filename}",
                sha256_hash=sha256_hash,
                file_size_bytes=file_size,
                quality_meta=quality_meta,
            )
        )

    files_data = [f.model_dump() for f in ingested_files]
    create_case(
        case_id=case_id,
        created_at=created_at,
        status="ingested",
        caption_text=caption,
        files=files_data,
    )

    return CaseIngestResponse(
        case_id=case_id,
        status="ingested",
        created_at=created_at,
        caption_text=caption,
        files=ingested_files,
    )


@app.get("/api/cases", response_model=List[CaseRecord])
def get_all_cases():
    return list_cases()


@app.get("/api/cases/{case_id}", response_model=CaseRecord)
def get_case_by_id(case_id: str):
    case = get_case(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' not found.",
        )
    return case


@app.post("/api/analyze/{case_id}", response_model=ForensicReport)
async def analyze_case(case_id: str):
    case = get_case(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' not found.",
        )

    all_flagged: List[FlaggedEvidence] = []
    all_limitations: List[str] = []
    all_alternatives: List[str] = []
    modalities_dict: Dict[str, ModalitySummary] = {}
    modality_scores: List[float] = []

    files = case.get("files", [])
    image_files = [f for f in files if f.get("media_type") == "image"]
    audio_files = [f for f in files if f.get("media_type") == "audio"]
    video_files = [f for f in files if f.get("media_type") == "video"]
    caption_text = case.get("caption_text")

    # 1. Process Images
    if image_files:
        for idx, img_info in enumerate(image_files):
            img_path = img_info["saved_path"]
            prefix = f"image_{idx}" if len(image_files) > 1 else "image"
            analysis = analyze_image_file(
                image_path=img_path,
                case_id=case_id,
                artifact_prefix=prefix,
                generate_gradcam=True,
                run_exif_ela=True,
            )
            mod_summary_data = analysis["modality_summary"]
            modality_scores.append(mod_summary_data["calibrated_score"])

            mod_key = f"image_{idx}" if len(image_files) > 1 else "image"
            modalities_dict[mod_key] = ModalitySummary(**mod_summary_data)

            for fe in analysis.get("flagged_evidence", []):
                all_flagged.append(FlaggedEvidence(**fe))

            all_limitations.extend(analysis.get("limitations", []))
            all_alternatives.extend(analysis.get("alternative_explanations", []))

    # 2. Process Audio
    if audio_files:
        for idx, aud_info in enumerate(audio_files):
            aud_path = aud_info["saved_path"]
            prefix = f"audio_{idx}" if len(audio_files) > 1 else "audio"
            aud_analysis = analyze_audio_file(
                audio_path=aud_path,
                case_id=case_id,
                artifact_prefix=prefix,
            )
            aud_summary_data = aud_analysis["modality_summary"]
            modality_scores.append(aud_summary_data["calibrated_score"])

            aud_key = f"audio_{idx}" if len(audio_files) > 1 else "audio"
            modalities_dict[aud_key] = ModalitySummary(**aud_summary_data)

            for fe in aud_analysis.get("flagged_evidence", []):
                all_flagged.append(FlaggedEvidence(**fe))

            all_limitations.extend(aud_analysis.get("limitations", []))
            all_alternatives.extend(aud_analysis.get("alternative_explanations", []))

    # 3. Process Video
    if video_files:
        for idx, vid_info in enumerate(video_files):
            vid_path = vid_info["saved_path"]
            vid_analysis = analyze_video_file(
                video_path=vid_path,
                case_id=case_id,
            )
            vid_summary_data = vid_analysis["modality_summary"]
            modality_scores.append(vid_summary_data["calibrated_score"])

            vid_key = f"video_{idx}" if len(video_files) > 1 else "video"
            modalities_dict[vid_key] = ModalitySummary(**vid_summary_data)

            # Check if video audio track was extracted
            if vid_analysis.get("extracted_audio_result"):
                ext_aud = vid_analysis["extracted_audio_result"]["modality_summary"]
                ext_key = f"video_{idx}_audio" if len(video_files) > 1 else "video_audio"
                modalities_dict[ext_key] = ModalitySummary(**ext_aud)
                modality_scores.append(ext_aud["calibrated_score"])

            for fe in vid_analysis.get("flagged_evidence", []):
                all_flagged.append(FlaggedEvidence(**fe))

            all_limitations.extend(vid_analysis.get("limitations", []))
            all_alternatives.extend(vid_analysis.get("alternative_explanations", []))

    # 4. Handle Caption Text Note
    if caption_text:
        all_limitations.append(
            f"Caption text preserved for Phase 4 cross-modal reasoning: '{caption_text[:80]}...'"
        )

    if not files:
        all_limitations.append("No media files present in case for multimodal forensic analysis.")

    # Deduplicate lists while preserving order
    deduped_limitations = list(dict.fromkeys(all_limitations))
    deduped_alternatives = list(dict.fromkeys(all_alternatives))

    # SHA256 hashes map
    sha256_hashes: Dict[str, str] = {}
    for f in case.get("files", []):
        name = f.get("original_filename") or Path(f.get("saved_path", "unknown")).name
        sha256_hashes[name] = f.get("sha256_hash", "")

    # Collect image paths for visual VQA inspect
    image_paths: List[str] = [f["saved_path"] for f in image_files]

    # Collect transcript if present
    transcript_text: Optional[str] = None
    for m in modalities_dict.values():
        t = m.metadata.get("transcript_text")
        if t:
            transcript_text = str(t)
            break

    # 5. Execute Phase 4 Cross-Modal Correlation Engine
    correlation = correlate_case_findings(
        modalities=modalities_dict,
        flagged_evidence=all_flagged,
        caption_text=caption_text,
        limitations=deduped_limitations,
        alternative_explanations=deduped_alternatives,
        image_paths=image_paths,
        transcript_text=transcript_text,
    )

    # Format final modalities
    final_modalities: Dict[str, ModalitySummary] = {}
    for k, v in correlation["modalities"].items():
        if isinstance(v, ModalitySummary):
            final_modalities[k] = v
        else:
            final_modalities[k] = ModalitySummary(**v)

    final_flagged: List[FlaggedEvidence] = [
        fe if isinstance(fe, FlaggedEvidence) else FlaggedEvidence(**fe)
        for fe in correlation["flagged_evidence"]
    ]

    cm_data = correlation["cross_modal_correlation"]
    cross_modal = (
        cm_data
        if isinstance(cm_data, CrossModalResult)
        else CrossModalResult(**cm_data)
    )

    report = ForensicReport(
        case_id=case_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        status="analyzed",
        sha256_hashes=sha256_hashes,
        overall_risk_band=correlation["overall_risk_band"],
        calibrated_confidence=correlation["calibrated_confidence"],
        modalities=final_modalities,
        flagged_evidence=final_flagged,
        cross_modal_correlation=cross_modal,
        limitations_and_caveats=correlation["limitations_and_caveats"],
        alternative_explanations=correlation["alternative_explanations"],
        recommended_human_checks=correlation["recommended_human_checks"],
        summary=correlation["summary"],
        review_status=case.get("review_status", "needs_review"),
        review_notes=case.get("review_notes", ""),
    )

    update_case_result(case_id, "analyzed", report.model_dump())
    return report


@app.post("/api/cases/{case_id}/review", response_model=ReviewUpdateResponse)
def update_case_review_decision(case_id: str, body: ReviewUpdateRequest):
    case = get_case(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' not found.",
        )

    update_case_review(case_id, body.review_status, body.review_notes)

    # Sync into persisted result json if already analyzed
    if case.get("result"):
        res = case["result"]
        res["review_status"] = body.review_status
        res["review_notes"] = body.review_notes
        update_case_result(case_id, case.get("status", "analyzed"), res)

    return ReviewUpdateResponse(
        case_id=case_id,
        review_status=body.review_status,
        review_notes=body.review_notes,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/api/metrics/model")
def get_model_metrics():
    model_dir = BASE_DIR / "models"
    metrics_path = model_dir / "model_metrics.json"
    ckpt_path = model_dir / "truthlens_image_effb0.pth"
    checkpoint_loaded = ckpt_path.exists()

    if metrics_path.exists():
        try:
            with open(metrics_path, "r") as f:
                data = json.load(f)
            data["checkpoint_loaded"] = checkpoint_loaded
            if "note" not in data:
                data["note"] = "Custom EfficientNet-B0 checkpoint active with calibrated validation metrics."
            return data
        except Exception:
            pass

    return {
        "status": "fallback_untrained_head",
        "checkpoint_loaded": checkpoint_loaded,
        "model": "EfficientNet-B0 (Fallback Backbone)",
        "temperature_T": 1.5,
        "note": "Drop Colab-trained truthlens_image_effb0.pth and model_metrics.json into backend/models/ to display live validation metrics.",
        "val_accuracy": None,
        "f1_score": None,
        "roc_auc": None,
        "confusion_matrix": None,
    }


@app.get("/api/report/{case_id}/pdf")
def export_pdf_report(case_id: str):
    case = get_case(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' not found.",
        )
    if case.get("status") != "analyzed" or not case.get("result"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Case must be analyzed before generating a forensic PDF report.",
        )

    pdf_filename = f"{case_id}_forensic_report.pdf"
    pdf_path = REPORTS_DIR / pdf_filename
    generate_forensic_pdf(case_record=case, output_path=str(pdf_path))

    return FileResponse(
        str(pdf_path),
        media_type="application/pdf",
        filename=f"TruthLens_{case_id}_Report.pdf",
    )


@app.get("/api/demo/samples")
def get_demo_samples():
    return list_demo_samples()


@app.post("/api/demo/load/{sample_id}", response_model=ForensicReport)
def load_demo(sample_id: str):
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
    resolved_id = ALIASES.get(sample_id, sample_id)
    try:
        return load_demo_case(resolved_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Demo sample '{sample_id}' not found.",
        )
