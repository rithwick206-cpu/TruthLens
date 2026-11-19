from __future__ import annotations

import io
import os
from pathlib import Path
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.schemas import ForensicReport

client = TestClient(app)


def generate_test_image(width: int = 300, height: int = 300) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (width, height), color=(120, 180, 240))
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_analyze_case_end_to_end():
    # 1. Ingest synthetic 300x300 RGB PNG + caption
    png_bytes = generate_test_image(300, 300)
    caption = "Suspect synthetic profile avatar"
    ingest_resp = client.post(
        "/api/cases/ingest",
        data={"caption_text": caption},
        files={"image": ("avatar_synthetic.png", png_bytes, "image/png")},
    )
    assert ingest_resp.status_code == 201
    case_id = ingest_resp.json()["case_id"]

    # 2. Call POST /api/analyze/{case_id}
    analyze_resp = client.post(f"/api/analyze/{case_id}")
    assert analyze_resp.status_code == 200
    report_data = analyze_resp.json()

    # Validate strictly against ForensicReport schema
    report = ForensicReport(**report_data)
    assert report.case_id == case_id
    assert report.status == "analyzed"
    assert 0.0 <= report.calibrated_confidence <= 1.0
    assert report.overall_risk_band in [
        "Low Manipulation Indicator",
        "Moderate Indicator — Needs Review",
        "High Manipulation Indicator",
    ]
    assert report.cross_modal_correlation is not None
    assert report.cross_modal_correlation.status in ["single_modality", "inconclusive"]
    assert len(report.recommended_human_checks) > 0

    # 3. Check Image Modality Summary & Metadata
    assert "image" in report.modalities
    image_mod = report.modalities["image"]
    assert 0.0 <= image_mod.calibrated_score <= 1.0
    assert image_mod.risk_band in [
        "Low Manipulation Indicator",
        "Moderate Indicator — Needs Review",
        "High Manipulation Indicator",
    ]
    assert "ela_stats" in image_mod.metadata
    assert "exif" in image_mod.metadata
    assert "model_mode" in image_mod.metadata

    # 4. Verify ELA and Grad-CAM artifacts exist on disk and serve via static mount
    assert "ela" in image_mod.artifact_urls
    assert "gradcam" in image_mod.artifact_urls

    ela_url = image_mod.artifact_urls["ela"]
    gradcam_url = image_mod.artifact_urls["gradcam"]

    # Fetch artifacts via HTTP static mount
    ela_resp = client.get(ela_url)
    assert ela_resp.status_code == 200
    assert len(ela_resp.content) > 0
    assert "image" in ela_resp.headers.get("content-type", "")

    gradcam_resp = client.get(gradcam_url)
    assert gradcam_resp.status_code == 200
    assert len(gradcam_resp.content) > 0
    assert "image" in gradcam_resp.headers.get("content-type", "")

    # Check files exist on disk
    artifacts_dir = Path(__file__).resolve().parent.parent / "storage" / "artifacts"
    ela_filename = Path(ela_url).name
    gradcam_filename = Path(gradcam_url).name
    assert (artifacts_dir / ela_filename).exists()
    assert (artifacts_dir / gradcam_filename).exists()

    # 5. Verify GET /api/cases/{case_id} reflects "analyzed" status and saved result
    get_resp = client.get(f"/api/cases/{case_id}")
    assert get_resp.status_code == 200
    case_record = get_resp.json()
    assert case_record["status"] == "analyzed"
    assert case_record["result"] is not None
    assert case_record["result"]["overall_risk_band"] == report.overall_risk_band
    assert case_record["result"]["calibrated_confidence"] == report.calibrated_confidence


def test_analyze_nonexistent_case():
    response = client.post("/api/analyze/TL-NONEXISTENT")
    assert response.status_code == 404


def test_multipart_file_upload_runs_custom_model_and_artifacts():
    """Verifies that uploading via generic 'files' field name attaches media,
    runs the custom-trained EfficientNet-B0 (T = 1.0126), computes SHA-256 hashes,
    and generates Grad-CAM and ELA outputs."""
    import hashlib

    png_bytes = generate_test_image(350, 350)
    expected_sha256 = hashlib.sha256(png_bytes).hexdigest()

    # Ingest using generic "files" key as sent by frontend
    ingest_resp = client.post(
        "/api/cases/ingest",
        data={"caption_text": "Live investigation photo with potential splicing."},
        files={"files": ("investigation_photo.png", png_bytes, "image/png")},
    )
    assert ingest_resp.status_code == 201
    ingest_data = ingest_resp.json()
    case_id = ingest_data["case_id"]

    # Verify file was actually attached and hashed
    assert len(ingest_data["files"]) == 1
    file_info = ingest_data["files"][0]
    assert file_info["media_type"] == "image"
    assert file_info["original_filename"] == "investigation_photo.png"
    assert file_info["sha256_hash"] == expected_sha256

    # Run analysis
    analyze_resp = client.post(f"/api/analyze/{case_id}")
    assert analyze_resp.status_code == 200
    report_data = analyze_resp.json()

    assert "image" in report_data["modalities"]
    img_mod = report_data["modalities"]["image"]
    meta = img_mod["metadata"]

    # Verify custom-trained model mode and temperature scaling
    assert meta["model_mode"] == "custom_trained"
    assert 0.5 <= meta["temperature_T"] <= 2.0
    assert "ela_stats" in meta
    assert meta["ela_stats"]["mean_diff"] >= 0

    # Verify real Grad-CAM and ELA artifact outputs
    assert "gradcam" in img_mod["artifact_urls"]
    assert "ela" in img_mod["artifact_urls"]

    gradcam_url = img_mod["artifact_urls"]["gradcam"]
    ela_url = img_mod["artifact_urls"]["ela"]

    # Verify artifact endpoints return image bytes
    assert client.get(gradcam_url).status_code == 200
    assert client.get(ela_url).status_code == 200

    # Verify report SHA-256 matches original file
    assert report_data["sha256_hashes"]["investigation_photo.png"] == expected_sha256
