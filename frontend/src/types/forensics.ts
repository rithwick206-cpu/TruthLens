export type MediaType = "image" | "video" | "audio" | "text";

export type RiskBand =
  | "Low Manipulation Indicator"
  | "Moderate Indicator — Needs Review"
  | "High Manipulation Indicator"
  | "Insufficient Media — Needs Review"
  | string;

export type ReviewStatus =
  | "needs_review"
  | "confirmed_manipulated"
  | "confirmed_authentic"
  | "inconclusive";

export type CrossModalStatus =
  | "reinforcing"
  | "contradictory"
  | "single_modality"
  | "inconclusive";

export interface IngestedFile {
  media_type: "image" | "video" | "audio";
  original_filename: string;
  saved_path: string;
  url_path: string;
  sha256_hash: string;
  file_size_bytes: number;
  quality_meta: Record<string, any>;
}

export interface CaseIngestResponse {
  case_id: string;
  status: string;
  created_at: string;
  caption_text?: string | null;
  files: IngestedFile[];
}

export interface FlaggedEvidence {
  media_type: MediaType;
  location_or_timestamp: string;
  indicator: string;
  severity: "low" | "moderate" | "high";
  explanation: string;
  artifact_url?: string | null;
}

export interface ElaStats {
  mean_diff: number;
  max_diff: number;
  high_variance_ratio: number;
  ela_anomaly_detected?: boolean;
}

export interface ImageMetadata {
  exif?: Record<string, any>;
  has_exif?: boolean;
  camera_make?: string | null;
  camera_model?: string | null;
  software?: string | null;
  ela_stats?: ElaStats;
  model_mode?: string;
  temperature_T?: number;
  hotspot_region?: string;
  sightengine?: Record<string, any>;
  width?: number;
  height?: number;
  format?: string;
}

export interface AudioSegment {
  start_sec: number;
  end_sec: number;
  timestamp_label: string;
  score: number;
  risk_band: string;
}

export interface TranscriptSegment {
  id?: number;
  seek?: number;
  start?: number;
  end?: number;
  text: string;
}

export interface AudioMetadata {
  duration_sec?: number;
  model_mode?: string;
  segments?: AudioSegment[];
  waveform_peaks?: number[];
  transcript_status?: string;
  transcript_text?: string;
  transcript_segments?: TranscriptSegment[];
}

export interface VideoFramePoint {
  frame_index: number;
  timestamp_sec: number;
  timestamp_str: string;
  score: number;
}

export interface VideoKeyframe {
  frame_index: number;
  timestamp_str: string;
  timestamp_sec: number;
  score: number;
  artifact_urls: Record<string, string>;
}

export interface VideoTemporalStats {
  mean_score: number;
  max_score: number;
  score_std: number;
  max_frame_delta: number;
  total_sampled: number;
}

export interface VideoMetadata {
  duration_sec?: number;
  fps?: number;
  total_frames?: number;
  width?: number;
  height?: number;
  frame_timeline?: VideoFramePoint[];
  temporal_stats?: VideoTemporalStats;
  keyframes?: VideoKeyframe[];
  has_audio?: boolean;
}

export interface ModalitySummary {
  media_type: MediaType;
  calibrated_score: number;
  risk_band: RiskBand;
  indicators: string[];
  artifact_urls: Record<string, string>;
  metadata: Record<string, any>;
}

export interface CrossModalResult {
  status: CrossModalStatus;
  summary: string;
  details: string[];
}

export interface ForensicReport {
  case_id: string;
  created_at: string;
  status: string;
  sha256_hashes: Record<string, string>;
  overall_risk_band: RiskBand;
  calibrated_confidence: number;
  modalities: Record<string, ModalitySummary>;
  flagged_evidence: FlaggedEvidence[];
  cross_modal_correlation: CrossModalResult | null;
  limitations_and_caveats: string[];
  alternative_explanations: string[];
  recommended_human_checks: string[];
  summary: string;
  review_status: ReviewStatus | string;
  review_notes: string;
}

export interface CaseRecord {
  id?: string;
  case_id: string;
  created_at: string;
  status: string;
  review_status: ReviewStatus | string;
  review_notes: string;
  caption_text?: string | null;
  files: IngestedFile[];
  result?: ForensicReport | null;
}

export interface DemoSample {
  sample_id: string;
  title: string;
  description: string;
  expected_risk_band: string;
}

export interface ReviewUpdateRequest {
  review_status: ReviewStatus;
  review_notes: string;
}

export interface ReviewUpdateResponse {
  case_id: string;
  review_status: string;
  review_notes: string;
  updated_at: string;
}

export interface ModelMetrics {
  status: string;
  checkpoint_loaded: boolean;
  model: string;
  dataset?: string;
  train_samples?: number;
  val_samples?: number;
  classes?: string[];
  fake_class_index?: number;
  temperature_T?: number;
  val_accuracy?: number | null;
  f1_score?: number | null;
  roc_auc?: number | null;
  confusion_matrix?: number[][] | null;
  note?: string;
}
