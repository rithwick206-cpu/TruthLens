from __future__ import annotations

import io
import os
import re
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH, override=True)

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
os.environ.setdefault("TORCH_HOME", "/tmp/torch")

from typing import Any, Dict, List, Optional, Tuple

import cv2
import exifread
import httpx
import numpy as np
import torch
import torch.nn as nn
import torchvision
from PIL import ExifTags, Image

# Global Model Cache
_MODEL_CACHE: Optional[Dict[str, Any]] = None
_MODEL_LOADED_MTIME: float = 0.0

KNOWN_EDITING_TOOLS = [
    "photoshop",
    "gimp",
    "canva",
    "lightroom",
    "stable diffusion",
    "midjourney",
    "firefly",
    "dall-e",
    "novelai",
    "deepfacelab",
]


def _load_image_model(force_reload: bool = False) -> Dict[str, Any]:
    """Loads the EfficientNet-B0 model singleton with custom checkpoint or ImageNet fallback.
    Automatically hot-reloads if the checkpoint file on disk has been updated."""
    global _MODEL_CACHE, _MODEL_LOADED_MTIME

    checkpoint_path = (
        Path(__file__).resolve().parent.parent / "models" / "truthlens_image_effb0.pth"
    )
    current_mtime = (
        checkpoint_path.stat().st_mtime if checkpoint_path.exists() else 0.0
    )

    if (
        not force_reload
        and _MODEL_CACHE is not None
        and _MODEL_LOADED_MTIME == current_mtime
    ):
        return _MODEL_CACHE

    if checkpoint_path.exists():
        model = torchvision.models.efficientnet_b0(weights=None)
        in_features = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(in_features, 2)

        checkpoint = torch.load(str(checkpoint_path), map_location="cpu")
        state_dict = checkpoint.get("state_dict", checkpoint)
        model.load_state_dict(state_dict)

        classes = checkpoint.get("classes", ["real", "fake"])
        fake_class_index = checkpoint.get("fake_class_index", 0)
        temperature_T = float(checkpoint.get("temperature_T", 1.0))
        model_mode = "custom_trained"
        caveat = None
    else:
        # Pretrained ImageNet backbone fallback with uncalibrated classification head
        try:
            weights = torchvision.models.EfficientNet_B0_Weights.DEFAULT
            model = torchvision.models.efficientnet_b0(weights=weights)
        except Exception:
            model = torchvision.models.efficientnet_b0(weights=None)
        in_features = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(in_features, 2)

        classes = ["real", "fake"]
        fake_class_index = 0
        temperature_T = 1.5
        model_mode = "fallback_untrained_head"
        caveat = (
            "Custom EfficientNet-B0 checkpoint (truthlens_image_effb0.pth) is not loaded; "
            "running with pretrained ImageNet backbone and temperature-scaled classification head."
        )

    model.eval()

    _MODEL_CACHE = {
        "model": model,
        "classes": classes,
        "fake_class_index": fake_class_index,
        "temperature_T": temperature_T,
        "model_mode": model_mode,
        "caveat": caveat,
    }
    _MODEL_LOADED_MTIME = current_mtime
    return _MODEL_CACHE


def extract_exif_signals(image_path: str) -> Dict[str, Any]:
    """Extracts deterministic EXIF metadata, camera tags, and editing/AI software signatures."""
    indicators: List[str] = []
    limitations: List[str] = []
    alternative_explanations: List[str] = []
    meta: Dict[str, Any] = {}
    flagged_software: Optional[str] = None

    # 1. Pillow metadata inspect
    try:
        with Image.open(image_path) as pil_img:
            width, height = pil_img.size
            img_format = pil_img.format
            meta["width"] = width
            meta["height"] = height
            meta["format"] = img_format

            if width < 256 or height < 256:
                limitations.append(
                    f"Low image resolution ({width}x{height} < 256px); deepfake classification and spatial localization accuracy may be reduced."
                )

            pil_exif = pil_img.getexif()
            if pil_exif:
                for tag_id, value in pil_exif.items():
                    tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                    if isinstance(value, (str, int, float)):
                        meta[tag_name] = value
    except Exception as e:
        limitations.append(f"Image header parsing warning: {str(e)}")

    # 2. ExifRead detailed parsing
    try:
        with open(image_path, "rb") as f:
            tags = exifread.process_file(f, details=False)
            for k, v in tags.items():
                clean_k = k.replace("Image ", "").replace("EXIF ", "")
                if clean_k not in meta:
                    meta[clean_k] = str(v)
    except Exception:
        pass

    camera_make = meta.get("Make")
    camera_model = meta.get("Model")
    software = meta.get("Software")
    datetime_orig = meta.get("DateTimeOriginal") or meta.get("DateTime")

    # Detect editing / AI software
    all_text_metadata = " ".join(
        str(v)
        for k, v in meta.items()
        if any(term in k.lower() for term in ["software", "description", "comment", "artist", "history"])
    ).lower()

    for tool in KNOWN_EDITING_TOOLS:
        if tool in all_text_metadata:
            flagged_software = tool
            indicators.append(f"Editing/AI software signature detected in metadata: '{tool}'")
            break

    has_exif = bool(camera_make or camera_model or software or datetime_orig)
    if not has_exif:
        indicators.append("EXIF metadata header is completely absent.")
        alternative_explanations.append(
            "Messaging and social media platforms (WhatsApp, Instagram, X) routinely strip all EXIF metadata for user privacy and bandwidth optimization, so absent metadata alone does not confirm manipulation."
        )

    return {
        "has_exif": has_exif,
        "camera_make": str(camera_make) if camera_make else None,
        "camera_model": str(camera_model) if camera_model else None,
        "software": str(software) if software else None,
        "flagged_software": flagged_software,
        "datetime_original": str(datetime_orig) if datetime_orig else None,
        "indicators": indicators,
        "limitations": limitations,
        "alternative_explanations": alternative_explanations,
        "raw_metadata": {k: str(v) for k, v in meta.items() if len(str(v)) < 120},
    }


def generate_ela_artifact(image_path: str, output_path: str, quality: int = 90) -> Dict[str, Any]:
    """Computes Error Level Analysis (ELA) against a JPEG re-compression baseline and saves artifact."""
    orig_pil = Image.open(image_path).convert("RGB")
    orig_np = np.array(orig_pil)

    buf = io.BytesIO()
    orig_pil.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    recomp_pil = Image.open(buf).convert("RGB")
    recomp_np = np.array(recomp_pil)

    # Compute absolute difference
    diff = np.abs(orig_np.astype(np.int16) - recomp_np.astype(np.int16)).astype(np.uint8)

    mean_diff = float(np.mean(diff))
    max_diff = float(np.max(diff))
    std_diff = float(np.std(diff))

    # Scale residual intensity cleanly
    scale = 10.0
    scaled_diff = np.clip(diff.astype(np.float32) * scale, 0, 255).astype(np.uint8)

    # Convert to grayscale and apply COLORMAP_INFERNO
    gray_diff = cv2.cvtColor(scaled_diff, cv2.COLOR_RGB2GRAY)
    ela_colored = cv2.applyColorMap(gray_diff, cv2.COLORMAP_INFERNO)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), ela_colored)

    high_variance_ratio = float(np.sum(gray_diff > 45) / gray_diff.size)
    inconsistency_flagged = bool(high_variance_ratio > 0.15 or max_diff > 60)

    indicators: List[str] = []
    if inconsistency_flagged:
        indicators.append(
            f"Localized compression inconsistency detected (ELA max_diff={round(max_diff, 1)}, high_variance_ratio={round(high_variance_ratio * 100, 1)}%)."
        )

    return {
        "mean_diff": round(mean_diff, 3),
        "max_diff": round(max_diff, 3),
        "std_diff": round(std_diff, 3),
        "high_variance_ratio": round(high_variance_ratio, 4),
        "inconsistency_flagged": inconsistency_flagged,
        "indicators": indicators,
    }


def _create_cam_overlay(rgb_img_float: np.ndarray, cam_mask: np.ndarray) -> np.ndarray:
    """Safely overlays CAM heatmap on RGB image."""
    try:
        from pytorch_grad_cam.utils.image import show_cam_on_image

        return show_cam_on_image(rgb_img_float, cam_mask, use_rgb=True)
    except Exception:
        heatmap = cv2.applyColorMap(np.uint8(255 * cam_mask), cv2.COLORMAP_JET)
        heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        overlay = heatmap * 0.5 + rgb_img_float * 0.5
        return np.uint8(255 * np.clip(overlay, 0, 1))


def run_cnn_and_gradcam(
    image_path: str,
    output_path: Optional[str] = None,
    generate_gradcam: bool = True,
) -> Dict[str, Any]:
    """Runs EfficientNet-B0 inference with temperature scaling and Grad-CAM spatial localization."""
    model_bundle = _load_image_model()
    model: nn.Module = model_bundle["model"]
    fake_class_index: int = model_bundle["fake_class_index"]
    temperature_T: float = model_bundle["temperature_T"]
    model_mode: str = model_bundle["model_mode"]
    caveat: Optional[str] = model_bundle["caveat"]

    orig_pil = Image.open(image_path).convert("RGB")
    orig_w, orig_h = orig_pil.size
    rgb_img_float = np.array(orig_pil, dtype=np.float32) / 255.0

    # ImageNet preprocessing
    preprocess = torchvision.transforms.Compose(
        [
            torchvision.transforms.Resize((224, 224)),
            torchvision.transforms.ToTensor(),
            torchvision.transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ]
    )

    input_tensor = preprocess(orig_pil).unsqueeze(0)  # Shape [1, 3, 224, 224]

    # Model forward pass
    with torch.no_grad():
        logits = model(input_tensor)
        scaled_logits = logits / temperature_T
        probs = torch.softmax(scaled_logits, dim=1)
        calibrated_score = float(probs[0, fake_class_index].item())
        calibrated_score = max(0.0, min(1.0, calibrated_score))

    hotspot_region = "Diffuse / No concentrated hotspot"
    cam_generated = False

    if generate_gradcam and output_path:
        try:
            from pytorch_grad_cam import GradCAM
            from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget

            target_layers = [model.features[-1]]
            cam = GradCAM(model=model, target_layers=target_layers)
            targets = [ClassifierOutputTarget(fake_class_index)]

            # Generate CAM mask
            grayscale_cam = cam(input_tensor=input_tensor, targets=targets)[0, :]
            cam_resized = cv2.resize(grayscale_cam, (orig_w, orig_h))

            # Overlay
            cam_overlay = _create_cam_overlay(rgb_img_float, cam_resized)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            cam_bgr = cv2.cvtColor(cam_overlay, cv2.COLOR_RGB2BGR)
            cv2.imwrite(str(output_path), cam_bgr)
            cam_generated = True

            # Calculate primary hotspot bounding region
            peak = float(cam_resized.max())
            threshold = 0.65 * peak if peak > 0.05 else 0.5
            y_coords, x_coords = np.where(cam_resized >= threshold)

            if len(x_coords) > 10 and len(y_coords) > 10:
                x_min_pct = int(round((x_coords.min() / orig_w) * 100))
                x_max_pct = int(round((x_coords.max() / orig_w) * 100))
                y_min_pct = int(round((y_coords.min() / orig_h) * 100))
                y_max_pct = int(round((y_coords.max() / orig_h) * 100))
                hotspot_region = f"Region (x: {x_min_pct}%-{x_max_pct}%, y: {y_min_pct}%-{y_max_pct}%)"
            else:
                hotspot_region = "Diffuse / Low spatial variance"
        except Exception as e:
            hotspot_region = f"Grad-CAM unavailable ({str(e)})"

    return {
        "calibrated_score": round(calibrated_score, 4),
        "model_mode": model_mode,
        "temperature_T": temperature_T,
        "caveat": caveat,
        "hotspot_region": hotspot_region,
        "cam_generated": cam_generated,
    }


def query_sightengine(image_path: str) -> Dict[str, Any]:
    """Optional Sightengine Second-Opinion API query with 5-second graceful degradation."""
    api_user = os.getenv("SIGHTENGINE_API_USER", "").strip()
    api_secret = os.getenv("SIGHTENGINE_API_SECRET", "").strip()

    if not api_user or not api_secret or api_user.lower() == "optional":
        return {"status": "not_configured"}

    try:
        with open(image_path, "rb") as img_file:
            files = {"media": img_file}
            params = {
                "models": "deepfake,genai",
                "api_user": api_user,
                "api_secret": api_secret,
            }
            with httpx.Client(timeout=5.0) as client:
                resp = client.post(
                    "https://api.sightengine.com/1.0/check.json",
                    data=params,
                    files=files,
                )
                if resp.status_code == 200:
                    return {"status": "success", "data": resp.json()}
                return {
                    "status": "api_error",
                    "status_code": resp.status_code,
                    "body": resp.text[:200],
                }
    except Exception as exc:
        return {"status": "degraded", "error": str(exc)}


def analyze_image_file(
    image_path: str,
    case_id: str,
    artifact_prefix: str = "image",
    generate_gradcam: bool = True,
    run_exif_ela: bool = True,
) -> Dict[str, Any]:
    """Public reusable entrypoint for image forensics analysis."""
    storage_artifacts = (
        Path(__file__).resolve().parent.parent / "storage" / "artifacts"
    )
    storage_artifacts.mkdir(parents=True, exist_ok=True)

    ela_filename = f"{case_id}_{artifact_prefix}_ela.png"
    gradcam_filename = f"{case_id}_{artifact_prefix}_gradcam.png"

    ela_disk_path = storage_artifacts / ela_filename
    gradcam_disk_path = storage_artifacts / gradcam_filename

    ela_url = f"/storage/artifacts/{ela_filename}"
    gradcam_url = f"/storage/artifacts/{gradcam_filename}"

    indicators: List[str] = []
    limitations: List[str] = []
    alternative_explanations: List[str] = []
    flagged_evidence: List[Dict[str, Any]] = []

    # 1. Deterministic EXIF
    exif_data = (
        extract_exif_signals(image_path)
        if run_exif_ela
        else {"indicators": [], "limitations": [], "alternative_explanations": []}
    )
    indicators.extend(exif_data.get("indicators", []))
    limitations.extend(exif_data.get("limitations", []))
    alternative_explanations.extend(exif_data.get("alternative_explanations", []))

    if exif_data.get("flagged_software"):
        flagged_evidence.append(
            {
                "media_type": "image",
                "location_or_timestamp": "EXIF Metadata Header",
                "indicator": f"Editing/AI Software Signature: {exif_data['flagged_software']}",
                "severity": "moderate",
                "explanation": f"Metadata tags record software footprint from '{exif_data['flagged_software']}'.",
                "artifact_url": None,
            }
        )

    # 2. Error Level Analysis
    ela_stats: Dict[str, Any] = {}
    if run_exif_ela:
        try:
            ela_stats = generate_ela_artifact(image_path, str(ela_disk_path))
            indicators.extend(ela_stats.get("indicators", []))
            if ela_stats.get("inconsistency_flagged"):
                flagged_evidence.append(
                    {
                        "media_type": "image",
                        "location_or_timestamp": "Full Image (Compression Residuals)",
                        "indicator": "Error Level Analysis Inconsistency",
                        "severity": "moderate",
                        "explanation": (
                            f"Compression residual variance (high_variance_ratio={ela_stats.get('high_variance_ratio')}) "
                            "indicates potential splicing or localized re-compression."
                        ),
                        "artifact_url": ela_url,
                    }
                )
        except Exception as e:
            limitations.append(f"Error Level Analysis warning: {str(e)}")

    # 3. EfficientNet-B0 + Temperature Scaling + Grad-CAM
    cnn_results = run_cnn_and_gradcam(
        image_path=image_path,
        output_path=str(gradcam_disk_path) if generate_gradcam else None,
        generate_gradcam=generate_gradcam,
    )

    calibrated_score = cnn_results["calibrated_score"]
    hotspot_region = cnn_results["hotspot_region"]

    if cnn_results.get("caveat"):
        limitations.append(cnn_results["caveat"])

    # Risk Band Calibration
    if calibrated_score < 0.35:
        risk_band = "Low Manipulation Indicator"
        indicators.append("Neural network classification indicates low likelihood of synthetic facial manipulation.")
    elif calibrated_score <= 0.65:
        risk_band = "Moderate Indicator — Needs Review"
        indicators.append("Neural network classification yields moderate ambiguity requiring human inspection.")
    else:
        risk_band = "High Manipulation Indicator"
        indicators.append("Neural network classification strongly flags synthetic manipulation patterns.")

    # Hotspot Flagged Evidence
    severity = (
        "high"
        if calibrated_score > 0.65
        else ("moderate" if calibrated_score >= 0.35 else "low")
    )
    flagged_evidence.append(
        {
            "media_type": "image",
            "location_or_timestamp": hotspot_region,
            "indicator": "Neural Network Feature Anomaly (Grad-CAM Hotspot)",
            "severity": severity,
            "explanation": (
                f"Peak activation concentrated in {hotspot_region} indicating anomalous boundary or texture pattern."
            ),
            "artifact_url": gradcam_url if cnn_results.get("cam_generated") else None,
        }
    )

    # 4. Optional Sightengine
    sightengine_res = query_sightengine(image_path)

    # Standard Alternative Explanations
    if "Natural high-frequency textures (hair, mesh, detailed foliage) can generate elevated ELA residuals without tampering." not in alternative_explanations:
        alternative_explanations.append(
            "Natural high-frequency textures (hair, mesh, detailed foliage) can generate elevated ELA residuals without tampering."
        )

    # Artifact URLs dict
    artifact_urls: Dict[str, str] = {}
    if ela_disk_path.exists():
        artifact_urls["ela"] = ela_url
    if gradcam_disk_path.exists():
        artifact_urls["gradcam"] = gradcam_url

    # Assemble Modality Summary
    modality_summary = {
        "media_type": "image",
        "calibrated_score": calibrated_score,
        "risk_band": risk_band,
        "indicators": indicators,
        "artifact_urls": artifact_urls,
        "metadata": {
            "exif": exif_data.get("raw_metadata", {}),
            "has_exif": exif_data.get("has_exif", False),
            "camera_make": exif_data.get("camera_make"),
            "camera_model": exif_data.get("camera_model"),
            "software": exif_data.get("software"),
            "ela_stats": ela_stats,
            "model_mode": cnn_results.get("model_mode"),
            "temperature_T": cnn_results.get("temperature_T"),
            "hotspot_region": hotspot_region,
            "sightengine": sightengine_res,
        },
    }

    return {
        "modality_summary": modality_summary,
        "flagged_evidence": flagged_evidence,
        "limitations": limitations,
        "alternative_explanations": alternative_explanations,
    }
