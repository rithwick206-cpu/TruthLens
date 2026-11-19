"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  ShieldAlert,
  ShieldCheck,
  FileDown,
  RefreshCw,
  Copy,
  Check,
  AlertTriangle,
  FileText,
  Layers,
  Image as ImageIcon,
  Video as VideoIcon,
  Mic,
  UserCheck,
  CheckCircle2,
  ExternalLink,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { CaseRecord, ForensicReport, ReviewStatus, FlaggedEvidence } from "@/types/forensics";
import { assetUrl, getReportPdfUrl, updateCaseReview, analyzeCase } from "@/lib/api";
import { VisualEvidenceViewer, ViewMode, OverlayType } from "./VisualEvidenceViewer";
import { AudioForensicsPlayer } from "./AudioForensicsPlayer";
import { VideoTimelineViewer } from "./VideoTimelineViewer";
import { ConfidenceAndUncertainty } from "./ConfidenceAndUncertainty";

interface ForensicWorkbenchProps {
  caseRecord: CaseRecord;
  onCaseUpdated: (updatedCase: CaseRecord) => void;
}

export const ForensicWorkbench: React.FC<ForensicWorkbenchProps> = ({
  caseRecord,
  onCaseUpdated,
}) => {
  const report: ForensicReport | undefined | null = caseRecord.result;

  // Review states
  const [reviewStatus, setReviewStatus] = useState<string>(
    caseRecord.review_status || "needs_review"
  );
  const [reviewNotes, setReviewNotes] = useState<string>(
    caseRecord.review_notes || ""
  );
  const [isUpdatingReview, setIsUpdatingReview] = useState(false);
  const [reviewSuccessToast, setReviewSuccessToast] = useState(false);

  // Re-analysis states
  const [isReanalyzing, setIsReanalyzing] = useState(false);
  const [reanalyzeError, setReanalyzeError] = useState<string | null>(null);

  // SHA-256 Copy states
  const [copiedHash, setCopiedHash] = useState<string | null>(null);
  const [copiedSummary, setCopiedSummary] = useState(false);
  const [showCustodyTable, setShowCustodyTable] = useState(true);

  const handleCopySummary = () => {
    if (!report) return;
    const text = [
      `TRUTHLENS FORENSIC INVESTIGATION BRIEF`,
      `=======================================`,
      `Case ID: ${caseRecord.case_id}`,
      `Date: ${new Date(caseRecord.created_at).toLocaleString()}`,
      `Risk Assessment: ${report.overall_risk_band} (${(report.calibrated_confidence * 100).toFixed(1)}% Calibrated Likelihood)`,
      `Audit Status: ${caseRecord.review_status?.replace("_", " ") || "Needs Review"}`,
      `Cross-Modal Status: ${report.cross_modal_correlation?.status || "N/A"}`,
      `Executive Summary: ${report.summary}`,
      `---------------------------------------`,
      `Cryptographic Evidence Fingerprints:`,
      ...(caseRecord.files || []).map(
        (f) => `• ${f.original_filename} (${f.media_type}): SHA-256 ${f.sha256_hash}`
      ),
      `=======================================`,
    ].join("\n");

    navigator.clipboard.writeText(text);
    setCopiedSummary(true);
    setTimeout(() => setCopiedSummary(false), 2000);
  };

  // Identify media assets present
  const imageFile = caseRecord.files?.find((f) => f.media_type === "image");
  const videoFile = caseRecord.files?.find((f) => f.media_type === "video");
  const audioFile = caseRecord.files?.find((f) => f.media_type === "audio");

  const imageModality = report?.modalities?.image || report?.modalities?.visual;
  const audioModality = report?.modalities?.audio || report?.modalities?.video_audio || report?.modalities?.sound;
  const videoModality = report?.modalities?.video;

  const effectiveAudioUrl = audioFile?.url_path || videoFile?.url_path;
  const effectiveAudioFilename = audioFile?.original_filename || (videoFile ? `${videoFile.original_filename} (Audio Stream)` : "Extracted Audio Track");

  // Active cross-viewer trigger states from Flagged Evidence row clicks
  const [activeMediaTab, setActiveMediaTab] = useState<"image" | "video" | "audio">(() => {
    if (videoFile) return "video";
    if (audioFile) return "audio";
    return "image";
  });

  // Auto-switch tab to match available media when case changes
  useEffect(() => {
    if (videoFile && !imageFile) {
      setActiveMediaTab("video");
    } else if (audioFile && !imageFile && !videoFile) {
      setActiveMediaTab("audio");
    } else if (imageFile) {
      setActiveMediaTab("image");
    }
  }, [caseRecord.case_id, videoFile, audioFile, imageFile]);

  const [imageViewerOverlay, setImageViewerOverlay] = useState<"gradcam" | "ela" | null>(null);
  const [audioSeekTarget, setAudioSeekTarget] = useState<number | null>(null);
  const [videoSeekTarget, setVideoSeekTarget] = useState<number | null>(null);
  const [highlightedEvidenceIndex, setHighlightedEvidenceIndex] = useState<number | null>(null);

  // Section references for scrolling
  const imageSectionRef = useRef<HTMLDivElement | null>(null);
  const audioSectionRef = useRef<HTMLDivElement | null>(null);
  const videoSectionRef = useRef<HTMLDivElement | null>(null);

  // Handle Human Audit Sign-Off
  const handleSaveReview = async () => {
    setIsUpdatingReview(true);
    setReviewSuccessToast(false);
    try {
      const res = await updateCaseReview(caseRecord.case_id, {
        review_status: reviewStatus as ReviewStatus,
        review_notes: reviewNotes,
      });
      setReviewSuccessToast(true);
      onCaseUpdated({
        ...caseRecord,
        review_status: res.review_status,
        review_notes: res.review_notes,
      });
      setTimeout(() => setReviewSuccessToast(false), 3000);
    } catch (err: any) {
      console.error("Failed to update review status:", err);
      alert(err.message || "Failed to save review status.");
    } finally {
      setIsUpdatingReview(false);
    }
  };

  // Re-run pipeline
  const handleRunAnalysis = async () => {
    setIsReanalyzing(true);
    setReanalyzeError(null);
    try {
      const updatedReport = await analyzeCase(caseRecord.case_id);
      onCaseUpdated({
        ...caseRecord,
        status: "analyzed",
        result: updatedReport,
      });
    } catch (err: any) {
      console.error("Analysis execution failed:", err);
      setReanalyzeError(err.message || "Analysis execution failed.");
    } finally {
      setIsReanalyzing(false);
    }
  };

  const copyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  // Click on Flagged Evidence row -> sync with corresponding viewer
  const handleEvidenceClick = (fe: FlaggedEvidence, index: number) => {
    setHighlightedEvidenceIndex(index);
    const mType = fe.media_type;

    if (mType === "image") {
      setActiveMediaTab("image");
      if (fe.indicator.toLowerCase().includes("ela")) {
        setImageViewerOverlay("ela");
      } else {
        setImageViewerOverlay("gradcam");
      }
      imageSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    } else if (mType === "audio") {
      setActiveMediaTab("audio");
      // Parse timestamp e.g. "00:02 - 00:04"
      const match = fe.location_or_timestamp.match(/(\d+):(\d+)/);
      if (match) {
        const sec = parseInt(match[1], 10) * 60 + parseInt(match[2], 10);
        setAudioSeekTarget(sec);
      }
      audioSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    } else if (mType === "video") {
      setActiveMediaTab("video");
      const match = fe.location_or_timestamp.match(/(\d+):(\d+)/);
      if (match) {
        const sec = parseInt(match[1], 10) * 60 + parseInt(match[2], 10);
        setVideoSeekTarget(sec);
      }
      videoSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. Header Banner & Actions */}
      <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 shadow-lg space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-[#1f2937]">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-[#090d16] text-cyan-400 border border-cyan-800/40">
                CASE ID: {caseRecord.case_id}
              </span>
              <span className="text-[11px] text-gray-400 font-mono">
                {new Date(caseRecord.created_at).toLocaleString()}
              </span>
              <span
                className={`text-[10px] font-mono px-2 py-0.5 rounded uppercase font-semibold ${
                  caseRecord.review_status === "confirmed_manipulated"
                    ? "bg-rose-950 text-rose-300 border border-rose-800"
                    : caseRecord.review_status === "confirmed_authentic"
                    ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                    : "bg-gray-800 text-gray-400 border border-gray-700"
                }`}
              >
                Audit: {caseRecord.review_status?.replace("_", " ") || "Needs Review"}
              </span>
            </div>

            <h1 className="text-lg font-bold text-gray-100">
              Interactive Digital Forensics Workbench
            </h1>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2">
            {report && (
              <button
                type="button"
                onClick={handleCopySummary}
                className="flex items-center gap-1.5 px-3 py-2 bg-[#090d16] hover:bg-[#131d33] text-gray-300 hover:text-white font-medium text-xs rounded-lg transition-all border border-[#1f2937] hover:border-gray-600 cursor-pointer"
                title="Copy structured forensic brief to clipboard"
              >
                {copiedSummary ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="text-emerald-300 font-mono text-[11px]">Copied Brief!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5 text-gray-400" />
                    <span className="font-mono text-[11px]">Copy Summary</span>
                  </>
                )}
              </button>
            )}

            {report ? (
              <a
                href={getReportPdfUrl(caseRecord.case_id)}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold text-xs rounded-lg shadow-md transition-all border border-cyan-400/40 cursor-pointer"
              >
                <FileDown className="w-4 h-4" />
                <span>Export Forensic PDF</span>
              </a>
            ) : (
              <button
                type="button"
                onClick={handleRunAnalysis}
                disabled={isReanalyzing}
                className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs rounded-lg shadow-md transition-all border border-cyan-400/40 cursor-pointer"
              >
                <RefreshCw className={`w-4 h-4 ${isReanalyzing ? "animate-spin" : ""}`} />
                <span>{isReanalyzing ? "Running Pipeline..." : "Execute Forensic Pipeline"}</span>
              </button>
            )}
          </div>
        </div>

        {/* Accompanying Claim / Context Text if present */}
        {caseRecord.caption_text && (
          <div className="bg-[#0c121e] border border-[#1f2937] rounded-lg p-3">
            <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-wider block mb-1">
              Accompanying Context / Viral Claim:
            </span>
            <p className="text-xs text-gray-200 italic font-sans">
              "{caseRecord.caption_text}"
            </p>
          </div>
        )}
      </div>

      {reanalyzeError && (
        <div className="bg-rose-950/40 border border-rose-500/60 p-4 rounded-xl text-rose-300 text-xs">
          {reanalyzeError}
        </div>
      )}

      {/* 2. Confidence, Uncertainty & Honest Disclosures */}
      {report && (
        <ConfidenceAndUncertainty
          calibratedConfidence={report.calibrated_confidence}
          overallRiskBand={report.overall_risk_band}
          crossModalCorrelation={report.cross_modal_correlation}
          limitationsAndCaveats={report.limitations_and_caveats}
          alternativeExplanations={report.alternative_explanations}
          recommendedHumanChecks={report.recommended_human_checks}
          executiveSummary={report.summary}
        />
      )}

      {/* 3. Media Forensics Viewers (Tabs / Modular Sections) */}
      <div className="space-y-4">
        {/* Navigation Selector for multiple media */}
        <div className="flex items-center justify-between border-b border-[#1f2937] pb-2">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-bold text-gray-200 uppercase tracking-wider">
              Multimodal Forensic Inspection Lab
            </h3>
          </div>

          {/* Tab buttons if multiple media exist */}
          <div className="flex items-center gap-1 bg-[#090d16] p-1 rounded-lg border border-[#1f2937] text-xs font-mono">
            {imageFile && (
              <button
                type="button"
                onClick={() => setActiveMediaTab("image")}
                className={`flex items-center gap-1.5 px-3 py-1 rounded transition-colors ${
                  activeMediaTab === "image"
                    ? "bg-cyan-950 text-cyan-300 font-bold border border-cyan-700/50"
                    : "text-gray-400 hover:text-gray-200"
                }`}
              >
                <ImageIcon className="w-3.5 h-3.5 text-cyan-400" />
                <span>Image Inspection</span>
              </button>
            )}
            {videoFile && (
              <button
                type="button"
                onClick={() => setActiveMediaTab("video")}
                className={`flex items-center gap-1.5 px-3 py-1 rounded transition-colors ${
                  activeMediaTab === "video"
                    ? "bg-purple-950 text-purple-300 font-bold border border-purple-700/50"
                    : "text-gray-400 hover:text-gray-200"
                }`}
              >
                <VideoIcon className="w-3.5 h-3.5 text-purple-400" />
                <span>Video Temporal</span>
              </button>
            )}
            {(audioFile || videoFile) && (
              <button
                type="button"
                onClick={() => setActiveMediaTab("audio")}
                className={`flex items-center gap-1.5 px-3 py-1 rounded transition-colors ${
                  activeMediaTab === "audio"
                    ? "bg-blue-950 text-blue-300 font-bold border border-blue-700/50"
                    : "text-gray-400 hover:text-gray-200"
                }`}
              >
                <Mic className="w-3.5 h-3.5 text-blue-400" />
                <span>Acoustic Waveform</span>
              </button>
            )}
          </div>
        </div>

        {/* Viewer 1: Image Inspector */}
        {imageFile && (activeMediaTab === "image" || !videoFile) && (
          <div ref={imageSectionRef}>
            <VisualEvidenceViewer
              originalUrl={imageFile.url_path}
              originalFilename={imageFile.original_filename}
              gradcamUrl={imageModality?.artifact_urls?.gradcam}
              elaUrl={imageModality?.artifact_urls?.ela}
              metadata={imageModality?.metadata}
              externalOverlay={imageViewerOverlay}
              externalViewMode={imageViewerOverlay ? "side_by_side" : undefined}
            />
          </div>
        )}

        {/* Viewer 2: Video Temporal Inspector */}
        {videoFile && activeMediaTab === "video" && (
          <div ref={videoSectionRef}>
            <VideoTimelineViewer
              videoUrl={videoFile.url_path}
              videoFilename={videoFile.original_filename}
              metadata={videoModality?.metadata}
              externalSeekTime={videoSeekTarget}
            />
          </div>
        )}

        {/* Viewer 3: Audio Forensics Player */}
        {effectiveAudioUrl && audioModality && (activeMediaTab === "audio" || (!imageFile && !videoFile)) && (
          <div ref={audioSectionRef}>
            <AudioForensicsPlayer
              audioUrl={effectiveAudioUrl}
              audioFilename={effectiveAudioFilename}
              metadata={audioModality?.metadata}
              externalSeekTime={audioSeekTarget}
              title={videoFile ? "Extracted Audio Track & Synthetic Voice Detector" : undefined}
            />
          </div>
        )}
      </div>

      {/* 4. Interactive Flagged Evidence Table */}
      {report?.flagged_evidence && report.flagged_evidence.length > 0 && (
        <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 shadow-lg space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-[#1f2937]">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-amber-400" />
              <h3 className="text-xs font-bold text-gray-200 uppercase tracking-wider">
                Flagged Forensic Evidence ({report.flagged_evidence.length})
              </h3>
            </div>
            <span className="text-[10px] font-mono text-cyan-400 lowercase">
              Click row to jump and activate corresponding viewer overlay
            </span>
          </div>

          <div className="space-y-2 max-h-72 overflow-y-auto custom-scrollbar pr-1">
            {report.flagged_evidence.map((fe, idx) => {
              const isHighlighted = highlightedEvidenceIndex === idx;

              return (
                <div
                  key={idx}
                  onClick={() => handleEvidenceClick(fe, idx)}
                  className={`p-3 rounded-lg border transition-all cursor-pointer text-xs space-y-1.5 ${
                    isHighlighted
                      ? "bg-cyan-950/40 border-cyan-400 ring-1 ring-cyan-400 shadow-md"
                      : "bg-[#090d16] border-[#1f2937] hover:border-gray-700 hover:bg-[#0c121e]"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 font-mono">
                      <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-gray-800 text-cyan-300 uppercase">
                        {fe.media_type}
                      </span>
                      <span className="text-gray-200 font-semibold">{fe.indicator}</span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono text-gray-500">
                        {fe.location_or_timestamp}
                      </span>
                      <span
                        className={`text-[9px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
                          fe.severity === "high"
                            ? "bg-rose-950 text-rose-300 border border-rose-800"
                            : fe.severity === "moderate"
                            ? "bg-amber-950 text-amber-300 border border-amber-800"
                            : "bg-blue-950 text-blue-300 border border-blue-800"
                        }`}
                      >
                        {fe.severity}
                      </span>
                    </div>
                  </div>

                  <p className="text-gray-300 text-[11px] leading-relaxed">
                    {fe.explanation}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 5. Human Investigator Review & Editorial Sign-Off */}
      <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 shadow-lg space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-[#1f2937]">
          <div className="flex items-center gap-2">
            <UserCheck className="w-5 h-5 text-cyan-400" />
            <h3 className="text-xs font-bold text-gray-100 uppercase tracking-wider">
              Human Investigator Review & Editorial Sign-Off
            </h3>
          </div>
          {reviewSuccessToast && (
            <span className="text-xs font-mono text-emerald-400 flex items-center gap-1.5 animate-fadeIn">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" /> Audit Determination Saved
            </span>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="text-[11px] font-semibold text-gray-300 uppercase tracking-wider block mb-1">
              Forensic Determination
            </label>
            <select
              value={reviewStatus}
              onChange={(e) => setReviewStatus(e.target.value)}
              className="w-full bg-[#090d16] border border-[#1f2937] rounded-lg p-2.5 text-xs text-gray-200 font-mono focus:outline-none focus:border-cyan-500/60"
            >
              <option value="needs_review">Needs Review (Unreviewed)</option>
              <option value="confirmed_manipulated">Confirmed Manipulated / Fake</option>
              <option value="confirmed_authentic">Confirmed Authentic</option>
              <option value="inconclusive">Inconclusive / Insufficient Evidence</option>
            </select>
          </div>

          <div className="md:col-span-2">
            <label className="text-[11px] font-semibold text-gray-300 uppercase tracking-wider block mb-1">
              Examiner Audit Notes
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                placeholder="Enter secondary verification details, camera provenance, or court reference..."
                className="flex-1 bg-[#090d16] border border-[#1f2937] rounded-lg px-3 py-2 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500/60 font-sans"
              />
              <button
                type="button"
                onClick={handleSaveReview}
                disabled={isUpdatingReview}
                className="px-5 py-2 bg-gradient-to-r from-cyan-600 to-cyan-700 hover:from-cyan-500 hover:to-cyan-600 text-white font-semibold text-xs rounded-lg transition-all cursor-pointer shrink-0 shadow-sm"
              >
                {isUpdatingReview ? "Saving..." : "Save Audit Sign-Off"}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 6. Cryptographic Chain-of-Custody & SHA-256 Table */}
      <div className="bg-[#111827] border border-[#1f2937] rounded-xl overflow-hidden shadow-lg">
        <button
          type="button"
          onClick={() => setShowCustodyTable((prev) => !prev)}
          className="w-full px-5 py-3.5 flex items-center justify-between text-xs font-bold text-gray-200 hover:bg-[#0c121e] transition-colors cursor-pointer border-b border-[#1f2937]"
        >
          <div className="flex items-center gap-2">
            <Copy className="w-4 h-4 text-cyan-400" />
            <span className="uppercase tracking-wider">
              Cryptographic Chain-of-Custody & SHA-256 Fingerprints ({caseRecord.files?.length || 0})
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-gray-400 font-mono text-[11px]">
            <span>{showCustodyTable ? "Hide Table" : "Show Table"}</span>
            {showCustodyTable ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </div>
        </button>

        {showCustodyTable && (
          <div className="p-4 overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-[#1f2937] text-gray-400 text-[10px] uppercase">
                  <th className="py-2 px-3">Original Asset</th>
                  <th className="py-2 px-3">Type</th>
                  <th className="py-2 px-3">File Size</th>
                  <th className="py-2 px-3">Cryptographic SHA-256</th>
                  <th className="py-2 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1f2937]">
                {caseRecord.files?.map((f, idx) => (
                  <tr key={idx} className="hover:bg-[#090d16]/50">
                    <td className="py-2 px-3 font-semibold text-gray-200">{f.original_filename}</td>
                    <td className="py-2 px-3 text-gray-400 uppercase">{f.media_type}</td>
                    <td className="py-2 px-3 text-gray-400">
                      {(f.file_size_bytes / (1024 * 1024)).toFixed(2)} MB
                    </td>
                    <td className="py-2 px-3 text-cyan-400 truncate max-w-sm">{f.sha256_hash}</td>
                    <td className="py-2 px-3 text-right">
                      <button
                        type="button"
                        onClick={() => copyHash(f.sha256_hash)}
                        className="px-2 py-1 rounded bg-[#090d16] border border-[#1f2937] hover:border-gray-600 text-gray-300 hover:text-white transition-colors cursor-pointer"
                        title="Copy SHA-256 Hash"
                      >
                        {copiedHash === f.sha256_hash ? (
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
