from __future__ import annotations

import hashlib
import io
import os
import re
from pathlib import Path
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def generate_png_bytes(width: int = 300, height: int = 300, color: str = "red") -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (width, height), color=color)
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok", "service": "TruthLens Backend"}


def test_ingest_image_and_caption():
    png_bytes = generate_png_bytes(width=320, height=240, color="blue")
    expected_hash = hashlib.sha256(png_bytes).hexdigest()

    caption = "A suspect viral deepfake image found on social media."
    response = client.post(
        "/api/cases/ingest",
        data={"caption_text": caption},
        files={"image": ("suspect_face.png", png_bytes, "image/png")},
    )

    assert response.status_code == 201
    data = response.json()

    # 1. Verify case_id format TL-<8 hex chars>
    case_id = data["case_id"]
    assert re.match(r"^TL-[0-9A-F]{8}$", case_id), f"Invalid case_id format: {case_id}"
    assert data["status"] == "ingested"
    assert data["caption_text"] == caption
    assert len(data["files"]) == 1

    file_info = data["files"][0]
    # 2. Verify exact matching SHA-256 hash
    assert file_info["sha256_hash"] == expected_hash
    assert file_info["media_type"] == "image"
    assert file_info["original_filename"] == "suspect_face.png"
    assert file_info["file_size_bytes"] == len(png_bytes)

    # 3. Verify file saved to storage/originals/ untouched
    saved_path = file_info["saved_path"]
    assert os.path.exists(saved_path), f"Saved file does not exist at {saved_path}"
    assert "storage/originals" in saved_path
    disk_bytes = Path(saved_path).read_bytes()
    assert disk_bytes == png_bytes
    assert hashlib.sha256(disk_bytes).hexdigest() == expected_hash


def test_get_case_record():
    png_bytes = generate_png_bytes(width=400, height=400, color="green")
    caption = "Evidence for retrieval test."
    ingest_resp = client.post(
        "/api/cases/ingest",
        data={"caption_text": caption},
        files={"image": ("green_sample.png", png_bytes, "image/png")},
    )
    assert ingest_resp.status_code == 201
    case_id = ingest_resp.json()["case_id"]

    # Retrieve case
    get_resp = client.get(f"/api/cases/{case_id}")
    assert get_resp.status_code == 200
    record = get_resp.json()
    assert record["case_id"] == case_id
    assert record["caption_text"] == caption
    assert record["status"] == "ingested"
    assert len(record["files"]) == 1
    assert record["files"][0]["original_filename"] == "green_sample.png"

    # Also check listing endpoint contains this case
    list_resp = client.get("/api/cases")
    assert list_resp.status_code == 200
    cases_list = list_resp.json()
    assert any(c["case_id"] == case_id for c in cases_list)


def test_reject_empty_request():
    # Empty POST with no files and no caption
    empty_resp = client.post("/api/cases/ingest", data={}, files={})
    assert empty_resp.status_code == 400
    assert "At least one file or caption must be provided" in empty_resp.json()["detail"]

    # Request with whitespace-only caption and no files
    blank_resp = client.post("/api/cases/ingest", data={"caption_text": "   "}, files={})
    assert blank_resp.status_code == 400


def test_case_not_found():
    response = client.get("/api/cases/TL-NONEXIST")
    assert response.status_code == 404
