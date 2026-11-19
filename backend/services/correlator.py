from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH, override=True)

import numpy as np
from pydantic import BaseModel, Field

from ..schemas import CrossModalResult, FlaggedEvidence, ModalitySummary


# Structured Gemini Output Schemas
class VQAProbeFinding(BaseModel):
    probe_question: str
    observation: str
    supports_manipulation: bool
    severity: Literal["low", "moderate", "high"]


class GeminiCorrelationOutput(BaseModel):
    cross_modal_status: Literal["reinforcing", "contradictory", "single_modality", "inconclusive"]
    cross_modal_summary: str
    cross_modal_details: List[str] = Field(default_factory=list)
    vqa_findings: List[VQAProbeFinding] = Field(default_factory=list)
    caption_mismatch_detected: bool
    caption_mismatch_explanation: Optional[str] = None
    additional_limitations: List[str] = Field(default_factory=list)
    additional_alternative_explanations: List[str] = Field(default_factory=list)
    recommended_human_checks: List[str] = Field(default_factory=list)
    executive_summary: str


CORE_CALIBRATION_DISCLAIMER = (
    "Automated forensic confidence scores are probabilistic indicators, not absolute proof of authenticity or manipulation."
)


def compute_deterministic_correlation(
    modalities: Dict[str, Any],
    flagged_evidence: List[Dict[str, Any]],
    caption_text: Optional[str] = None,
    limitations: Optional[List[str]] = None,
    alternative_explanations: Optional[List[str]] = None,
    transcript_text: Optional[str] = None,
) -> Dict[str, Any]:
    """Computes deterministic ensemble score, cross-modal agreement status, and baseline checks."""
    limitations_out = list(limitations or [])
    alternatives_out = list(alternative_explanations or [])

    if CORE_CALIBRATION_DISCLAIMER not in limitations_out:
        limitations_out.append(CORE_CALIBRATION_DISCLAIMER)

    # 1. Filter scored media modalities (exclude text or helper summaries)
    media_modalities: Dict[str, Any] = {}
    for k, m in modalities.items():
        m_type = m.get("media_type") if isinstance(m, dict) else getattr(m, "media_type", None)
        if m_type in ["image", "video", "audio"]:
            media_modalities[k] = m

    scores: List[float] = []
    for k, m in media_modalities.items():
        s = m.get("calibrated_score") if isinstance(m, dict) else getattr(m, "calibrated_score", 0.5)
        scores.append(float(s))

    # 2. Compute Calibrated Confidence
    if not scores:
        calibrated_confidence = 0.25
        overall_risk_band = "Insufficient Media — Needs Review"
        limitations_out.append("No scored media modalities available for forensic deep learning inference.")
    else:
        # Calibrated blend: 60% peak anomaly + 40% mean across modalities
        blended = 0.6 * max(scores) + 0.4 * float(np.mean(scores))
        calibrated_confidence = round(float(np.clip(blended, 0.0, 1.0)), 4)

        if calibrated_confidence < 0.35:
            overall_risk_band = "Low Manipulation Indicator"
        elif calibrated_confidence <= 0.65:
            overall_risk_band = "Moderate Indicator — Needs Review"
        else:
            overall_risk_band = "High Manipulation Indicator"

    # 3. Deterministic Cross-Modal Status
    num_media = len(media_modalities)
    has_text = bool((caption_text and caption_text.strip()) or (transcript_text and transcript_text.strip()))

    details: List[str] = []
    for k, s in zip(media_modalities.keys(), scores):
        details.append(f"Modality '{k}': calibrated_score={s:.2f}")

    if num_media == 0:
        cm_status = "single_modality"
        cm_summary = "Only text context provided; no media files available for forensic cross-modal comparison."
        details.append("Text context ingested without accompanying visual or auditory streams.")
    elif num_media == 1 and not has_text:
        mod_name = list(media_modalities.keys())[0]
        cm_status = "single_modality"
        cm_summary = f"Single-modality ({mod_name}) analysis completed without external text context."
        details.append(f"Single evidence source ({mod_name}) evaluated in isolation.")
    elif num_media > 1:
        score_spread = max(scores) - min(scores)
        if score_spread >= 0.35:
            cm_status = "contradictory"
            high_mods = [k for k, s in zip(media_modalities.keys(), scores) if s >= 0.55]
            low_mods = [k for k, s in zip(media_modalities.keys(), scores) if s < 0.35]
            cm_summary = (
                f"Contradictory signals across modalities: elevated manipulation in {', '.join(high_mods) or 'certain modalities'} "
                f"contrasts with low anomaly levels in {', '.join(low_mods) or 'other modalities'}."
            )
            details.append(f"Modality score spread is {score_spread:.2f} (exceeds 0.35 divergence threshold).")
        elif all(s >= 0.55 for s in scores) or all(s < 0.35 for s in scores):
            cm_status = "reinforcing"
            direction = "elevated manipulation indicators" if all(s >= 0.55 for s in scores) else "low manipulation indicators"
            cm_summary = f"Evidence across all {num_media} media modalities consistently reinforces {direction}."
        else:
            cm_status = "inconclusive"
            cm_summary = f"Moderate or ambiguous scores observed across {num_media} media modalities."
    else:
        # num_media == 1 and has_text
        mod_name = list(media_modalities.keys())[0]
        cm_status = "inconclusive"
        cm_summary = f"Single media modality ({mod_name}) analyzed alongside text context; semantic alignment pending verification."
        if caption_text:
            details.append(f"User caption attached: '{caption_text[:60]}...'")
        if transcript_text:
            details.append(f"Audio transcript attached: '{transcript_text[:60]}...'")

    # 4. Baseline Recommended Human Checks
    recommended_checks = [
        "Verify whether source files originate directly from authentic capture hardware or third-party messaging platforms.",
        "Inspect high-contrast boundary transitions and illumination consistency across all available visual artifacts.",
    ]
    if any("audio" in k for k in media_modalities):
        recommended_checks.append("Listen closely to flagged audio segments for unnatural phoneme truncation or background noise dropouts.")
    if has_text:
        recommended_checks.append("Cross-reference factual assertions in the caption/transcript against independent authoritative news sources.")

    # 5. Deterministic Executive Summary
    summary = (
        f"TruthLens Forensic Analysis Case Summary: Evaluated {num_media} media modality/modalities "
        f"with an overall calibrated confidence of {calibrated_confidence:.1%} ({overall_risk_band}). "
        f"Cross-modal status: {cm_status.upper()}. {cm_summary}"
    )

    return {
        "calibrated_confidence": calibrated_confidence,
        "overall_risk_band": overall_risk_band,
        "cross_modal_correlation": {
            "status": cm_status,
            "summary": cm_summary,
            "details": details,
        },
        "limitations_and_caveats": list(dict.fromkeys(limitations_out)),
        "alternative_explanations": list(dict.fromkeys(alternatives_out)),
        "recommended_human_checks": recommended_checks,
        "summary": summary,
    }


def run_gemini_correlator(
    dossier: Dict[str, Any],
    image_paths: Optional[List[str]] = None,
) -> Tuple[Optional[GeminiCorrelationOutput], str]:
    """Runs Gemini Multimodal Forensic VQA & Cross-Modal reasoning.
    Returns (output_or_none, status_string)."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key.lower() == "optional":
        return None, "not_configured"

    gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        # Collect up to 3 visual attachments
        visual_parts: List[Any] = []
        for p in (image_paths or [])[:3]:
            try:
                img_path = Path(p)
                if img_path.exists() and img_path.stat().st_size > 0:
                    raw_bytes = img_path.read_bytes()
                    mime = "image/png" if img_path.suffix.lower() == ".png" else "image/jpeg"
                    visual_parts.append(types.Part.from_bytes(data=raw_bytes, mime_type=mime))
            except Exception:
                pass

        prompt_text = (
            "Review the following digital forensic investigation dossier and attached visual media:\n\n"
            f"{json.dumps(dossier, indent=2)}\n\n"
            "Perform rigorous cross-modal forensic verification and visual VQA probes. "
            "Examine lighting/shadow physics, anatomical/facial blending borders, text/background inconsistencies, "
            "and caption/transcript semantic correlation. Return structured JSON matching the output schema."
        )

        system_instruction = (
            "You are TruthLens Senior Forensic Intelligence Correlator. "
            "1. Run 3 to 5 targeted forensic VQA probes focusing on physics, boundaries, and semantic text alignment. "
            "2. Evaluate whether multimodal signals reinforce, contradict, or remain inconclusive. "
            "3. If caption claims contradict visual/auditory evidence, flag caption_mismatch_detected=True. "
            "4. Never declare 100% certainty; always maintain rigorous scientific humility, listing honest limitations "
            "and non-malicious alternative explanations (compression, sensor noise, satirical re-captioning)."
        )

        contents = [prompt_text] + visual_parts

        response = client.models.generate_content(
            model=gemini_model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GeminiCorrelationOutput,
                temperature=0.2,
                system_instruction=system_instruction,
            ),
        )

        if hasattr(response, "parsed") and response.parsed is not None:
            return response.parsed, "success"

        # Fallback parse from raw text
        if hasattr(response, "text") and response.text:
            parsed = GeminiCorrelationOutput.model_validate_json(response.text)
            return parsed, "success"

        return None, "empty_response"
    except Exception as e:
        return None, f"error: {type(e).__name__}"


def correlate_case_findings(
    modalities: Dict[str, Any],
    flagged_evidence: List[Dict[str, Any]],
    caption_text: Optional[str] = None,
    limitations: Optional[List[str]] = None,
    alternative_explanations: Optional[List[str]] = None,
    image_paths: Optional[List[str]] = None,
    transcript_text: Optional[str] = None,
) -> Dict[str, Any]:
    """Public unified entrypoint combining deterministic signal calibration and Gemini reasoning."""
    # 1. Deterministic baseline
    det = compute_deterministic_correlation(
        modalities=modalities,
        flagged_evidence=flagged_evidence,
        caption_text=caption_text,
        limitations=limitations,
        alternative_explanations=alternative_explanations,
        transcript_text=transcript_text,
    )

    calibrated_confidence = det["calibrated_confidence"]
    overall_risk_band = det["overall_risk_band"]
    cm_result = det["cross_modal_correlation"]
    limitations_out = list(det["limitations_and_caveats"])
    alternatives_out = list(det["alternative_explanations"])
    recommended_checks = list(det["recommended_human_checks"])
    summary = det["summary"]
    flagged_out = list(flagged_evidence)
    modalities_out = dict(modalities)

    # 2. Build dossier for Gemini
    dossier = {
        "calibrated_confidence": calibrated_confidence,
        "overall_risk_band": overall_risk_band,
        "deterministic_cross_modal": cm_result,
        "caption_text": caption_text,
        "transcript_text": transcript_text,
        "modalities": {
            k: {
                "media_type": m.get("media_type") if isinstance(m, dict) else getattr(m, "media_type", None),
                "score": m.get("calibrated_score") if isinstance(m, dict) else getattr(m, "calibrated_score", None),
                "risk_band": m.get("risk_band") if isinstance(m, dict) else getattr(m, "risk_band", None),
                "indicators": m.get("indicators", []) if isinstance(m, dict) else getattr(m, "indicators", []),
            }
            for k, m in modalities.items()
        },
        "flagged_evidence": [
            {
                "media_type": fe.get("media_type") if isinstance(fe, dict) else getattr(fe, "media_type", None),
                "location": fe.get("location_or_timestamp") if isinstance(fe, dict) else getattr(fe, "location_or_timestamp", None),
                "indicator": fe.get("indicator") if isinstance(fe, dict) else getattr(fe, "indicator", None),
                "severity": fe.get("severity") if isinstance(fe, dict) else getattr(fe, "severity", None),
            }
            for fe in flagged_evidence
        ],
    }

    # 3. Execute Gemini Correlator
    gemini_out, gemini_status = run_gemini_correlator(dossier, image_paths=image_paths)

    if gemini_status == "success" and gemini_out:
        # Override cross modal correlation with Gemini reasoning
        cm_result = {
            "status": gemini_out.cross_modal_status,
            "summary": gemini_out.cross_modal_summary,
            "details": gemini_out.cross_modal_details or cm_result.get("details", []),
        }

        # Append VQA findings that support manipulation
        for vqa in gemini_out.vqa_findings:
            if vqa.supports_manipulation:
                flagged_out.append(
                    {
                        "media_type": "image",
                        "location_or_timestamp": "Visual VQA Probe",
                        "indicator": f"VQA Anomaly: {vqa.probe_question}",
                        "severity": vqa.severity,
                        "explanation": vqa.observation,
                        "artifact_url": None,
                    }
                )

        # Handle caption mismatch
        if gemini_out.caption_mismatch_detected:
            flagged_out.append(
                {
                    "media_type": "text",
                    "location_or_timestamp": "Caption vs. Media Context",
                    "indicator": "Cross-Modal Context Mismatch",
                    "severity": "high",
                    "explanation": (
                        gemini_out.caption_mismatch_explanation
                        or "Extracted media evidence directly contradicts claims made in the caption."
                    ),
                    "artifact_url": None,
                }
            )
            # Nudge confidence upward for verified text-media conflict
            calibrated_confidence = round(float(min(1.0, calibrated_confidence + 0.12)), 4)
            if calibrated_confidence > 0.65:
                overall_risk_band = "High Manipulation Indicator"
            elif calibrated_confidence >= 0.35:
                overall_risk_band = "Moderate Indicator — Needs Review"

        limitations_out.extend(gemini_out.additional_limitations)
        alternatives_out.extend(gemini_out.additional_alternative_explanations)
        recommended_checks.extend(gemini_out.recommended_human_checks)
        if gemini_out.executive_summary:
            summary = gemini_out.executive_summary

    elif gemini_status == "not_configured":
        limitations_out.append(
            "Gemini Multimodal Correlator not configured (GEMINI_API_KEY missing); operating in deterministic baseline mode."
        )
    else:
        limitations_out.append(
            f"Gemini Multimodal Correlator degraded gracefully ({gemini_status}); operating in deterministic baseline mode."
        )

    # 4. Synthesize "text" modality summary if caption or transcript exists
    if caption_text or transcript_text:
        text_score = (
            0.85
            if (gemini_out and gemini_out.caption_mismatch_detected)
            else (0.25 if gemini_status == "success" else 0.5)
        )
        text_risk = (
            "High Manipulation Indicator"
            if (gemini_out and gemini_out.caption_mismatch_detected)
            else ("Low Manipulation Indicator" if gemini_status == "success" else "Moderate Indicator — Needs Review")
        )

        text_indicators: List[str] = []
        if caption_text:
            text_indicators.append("User caption context attached to investigation.")
        if transcript_text:
            text_indicators.append("Whisper automated speech transcript extracted.")
        if gemini_out and gemini_out.caption_mismatch_detected:
            text_indicators.append("Gemini VQA detected factual mismatch between caption and media stream.")

        modalities_out["text"] = {
            "media_type": "text",
            "calibrated_score": text_score,
            "risk_band": text_risk,
            "indicators": text_indicators,
            "artifact_urls": {},
            "metadata": {
                "caption_text": caption_text,
                "transcript_text": transcript_text,
                "gemini_status": gemini_status,
                "caption_mismatch_detected": gemini_out.caption_mismatch_detected if gemini_out else False,
            },
        }

    return {
        "calibrated_confidence": calibrated_confidence,
        "overall_risk_band": overall_risk_band,
        "modalities": modalities_out,
        "flagged_evidence": flagged_out,
        "cross_modal_correlation": cm_result,
        "limitations_and_caveats": list(dict.fromkeys(limitations_out)),
        "alternative_explanations": list(dict.fromkeys(alternatives_out)),
        "recommended_human_checks": list(dict.fromkeys(recommended_checks)),
        "summary": summary,
        "gemini_status": gemini_status,
    }
