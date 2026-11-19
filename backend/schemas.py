from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


class IngestedFile(BaseModel):
    media_type: Literal["image", "video", "audio"]
    original_filename: str
    saved_path: str
    url_path: str
    sha256_hash: str
    file_size_bytes: int
    quality_meta: Dict[str, Any] = Field(default_factory=dict)


class CaseIngestResponse(BaseModel):
    case_id: str
    status: str = "ingested"
    created_at: str
    caption_text: Optional[str] = None
    files: List[IngestedFile] = Field(default_factory=list)


class FlaggedEvidence(BaseModel):
    media_type: Literal["image", "video", "audio", "text"]
    location_or_timestamp: str
    indicator: str
    severity: Literal["low", "moderate", "high"]
    explanation: str
    artifact_url: Optional[str] = None


class ModalitySummary(BaseModel):
    media_type: Literal["image", "video", "audio", "text"]
    calibrated_score: float = Field(ge=0.0, le=1.0)
    risk_band: str
    indicators: List[str] = Field(default_factory=list)
    artifact_urls: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CrossModalResult(BaseModel):
    status: Literal["reinforcing", "contradictory", "single_modality", "inconclusive"]
    summary: str
    details: List[str] = Field(default_factory=list)


class ForensicReport(BaseModel):
    case_id: str
    created_at: str
    status: str
    sha256_hashes: Dict[str, str] = Field(default_factory=dict)
    overall_risk_band: str
    calibrated_confidence: float = Field(ge=0.0, le=1.0)
    modalities: Union[Dict[str, ModalitySummary], List[ModalitySummary]] = Field(default_factory=dict)
    flagged_evidence: List[FlaggedEvidence] = Field(default_factory=list)
    cross_modal_correlation: Optional[CrossModalResult] = None
    limitations_and_caveats: List[str] = Field(default_factory=list)
    alternative_explanations: List[str] = Field(default_factory=list)
    recommended_human_checks: List[str] = Field(default_factory=list)
    summary: str = ""
    review_status: str = "needs_review"
    review_notes: str = ""


class CaseRecord(BaseModel):
    case_id: str
    created_at: str
    status: str
    review_status: str = "needs_review"
    review_notes: str = ""
    caption_text: Optional[str] = None
    files: List[IngestedFile] = Field(default_factory=list)
    result: Optional[Union[ForensicReport, Dict]] = None


class ReviewUpdateRequest(BaseModel):
    review_status: Literal["needs_review", "confirmed_manipulated", "confirmed_authentic", "inconclusive"]
    review_notes: str = ""


class ReviewUpdateResponse(BaseModel):
    case_id: str
    review_status: str
    review_notes: str
    updated_at: str
