from __future__ import annotations

import io
from pathlib import Path
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.schemas import ForensicReport, ReviewUpdateResponse

client = TestClient(app)


def generate_test_image(width: int = 300, height: int = 300) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (width, height), color=(140, 190, 230))
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_review_audit_sync():
    # 1. Ingest & analyze case
    img_bytes = generate_test_image()
    ingest_resp = client.post(
        "/api/cases/ingest",
        data={"caption_text": "Case under investigation for manual audit sign-off."},
        files={"image": ("audit_sample.png", img_bytes, "image/png")},
    )
    assert ingest_resp.status_code == 201
    case_id = ingest_resp.json()["case_id"]

    analyze_resp = client.post(f"/api/analyze/{case_id}")
    assert analyze_resp.status_code == 200

    # 2. Update review decision
    notes = "Investigator verified facial seam warping and confirmed digital manipulation."
    review_resp = client.post(
        f"/api/cases/{case_id}/review",
        json={
            "review_status": "confirmed_manipulated",
            "review_notes": notes,
        },
    )
    assert review_resp.status_code == 200
    rev_data = ReviewUpdateResponse(**review_resp.json())
    assert rev_data.case_id == case_id
    assert rev_data.review_status == "confirmed_manipulated"
    assert rev_data.review_notes == notes

    # 3. Verify GET /api/cases/{case_id} syncs top-level and inside result
    get_resp = client.get(f"/api/cases/{case_id}")
    assert get_resp.status_code == 200
    case_record = get_resp.json()
    assert case_record["review_status"] == "confirmed_manipulated"
    assert case_record["review_notes"] == notes
    assert case_record["result"]["review_status"] == "confirmed_manipulated"
    assert case_record["result"]["review_notes"] == notes


def test_pdf_report_generation():
    img_bytes = generate_test_image()
    ingest_resp = client.post(
        "/api/cases/ingest",
        data={"caption_text": "Image for PDF export verification."},
        files={"image": ("pdf_target.png", img_bytes, "image/png")},
    )
    assert ingest_resp.status_code == 201
    case_id = ingest_resp.json()["case_id"]

    # 1. Verify unanalyzed case rejected with 400
    pre_pdf_resp = client.get(f"/api/report/{case_id}/pdf")
    assert pre_pdf_resp.status_code == 400
    assert "Case must be analyzed" in pre_pdf_resp.json()["detail"]

    # 2. Analyze case
    analyze_resp = client.post(f"/api/analyze/{case_id}")
    assert analyze_resp.status_code == 200

    # 3. Export PDF
    pdf_resp = client.get(f"/api/report/{case_id}/pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers.get("content-type") == "application/pdf"
    assert pdf_resp.content.startswith(b"%PDF")
    assert len(pdf_resp.content) > 2048  # Must be larger than 2KB


def test_model_metrics_endpoint():
    resp = client.get("/api/metrics/model")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "checkpoint_loaded" in data
    assert "model" in data
    assert "note" in data


def test_demo_samples_and_loaders():
    # 1. GET /api/demo/samples
    list_resp = client.get("/api/demo/samples")
    assert list_resp.status_code == 200
    samples = list_resp.json()
    assert len(samples) >= 3
    sample_ids = [s["sample_id"] for s in samples]
    assert "authentic_bundle" in sample_ids
    assert "manipulated_multimodal" in sample_ids
    assert "compressed_real_photo" in sample_ids

    # 2. Load all 3 demos and verify live assets and PDF export
    for s_id in sample_ids:
        load_resp = client.post(f"/api/demo/load/{s_id}")
        assert load_resp.status_code == 200
        report = ForensicReport(**load_resp.json())
        assert report.status == "analyzed"
        assert report.case_id.startswith("TL-")

        # Verify artifacts and originals exist live
        for m_name, m_val in report.modalities.items():
            for art_name, art_url in m_val.artifact_urls.items():
                art_resp = client.get(art_url)
                assert art_resp.status_code == 200
                assert len(art_resp.content) > 0

        # Verify PDF export works for this demo
        pdf_resp = client.get(f"/api/report/{report.case_id}/pdf")
        assert pdf_resp.status_code == 200
        assert pdf_resp.content.startswith(b"%PDF")


def test_unknown_demo_sample_404():
    resp = client.post("/api/demo/load/nonexistent_sample")
    assert resp.status_code == 404
