"use client";

import React, { useState, useRef } from "react";
import {
  UploadCloud,
  FileImage,
  FileVideo,
  FileAudio,
  Trash2,
  AlertTriangle,
  Play,
  Loader2,
  Sparkles,
  ShieldAlert,
  Info,
} from "lucide-react";
import { ingestCase, analyzeCase, getApiBase } from "@/lib/api";
import { ForensicReport } from "@/types/forensics";

interface IngestWorkspaceProps {
  onCaseAnalyzed: (caseId: string, report: ForensicReport) => void;
  onNavigateToDemo: (sampleId: string) => void;
}

interface StagedFile {
  id: string;
  file: File;
  previewUrl?: string;
  typeCategory: "image" | "video" | "audio" | "unknown";
}

const MAX_FILE_SIZE = 25 * 1024 * 1024; // 25 MB

export const IngestWorkspace: React.FC<IngestWorkspaceProps> = ({
  onCaseAnalyzed,
  onNavigateToDemo,
}) => {
  const [stagedFiles, setStagedFiles] = useState<StagedFile[]>([]);
  const [captionText, setCaptionText] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStatus, setProcessingStatus] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const determineCategory = (file: File): "image" | "video" | "audio" | "unknown" => {
    if (file.type.startsWith("image/")) return "image";
    if (file.type.startsWith("video/")) return "video";
    if (file.type.startsWith("audio/")) return "audio";
    const name = file.name.toLowerCase();
    if (name.endsWith(".jpg") || name.endsWith(".jpeg") || name.endsWith(".png") || name.endsWith(".webp")) return "image";
    if (name.endsWith(".mp4") || name.endsWith(".avi") || name.endsWith(".mov") || name.endsWith(".mkv")) return "video";
    if (name.endsWith(".wav") || name.endsWith(".mp3") || name.endsWith(".m4a") || name.endsWith(".ogg")) return "audio";
    return "unknown";
  };

  const handleFiles = (incomingFiles: FileList | File[]) => {
    setErrorMessage(null);
    const newStaged: StagedFile[] = [];

    Array.from(incomingFiles).forEach((file) => {
      if (file.size > MAX_FILE_SIZE) {
        setErrorMessage(`File "${file.name}" exceeds 25 MB limit (${(file.size / (1024 * 1024)).toFixed(1)} MB).`);
        return;
      }
      const cat = determineCategory(file);
      const staged: StagedFile = {
        id: Math.random().toString(36).substring(7),
        file,
        typeCategory: cat,
      };
      if (cat === "image") {
        staged.previewUrl = URL.createObjectURL(file);
      }
      newStaged.push(staged);
    });

    setStagedFiles((prev) => [...prev, ...newStaged]);
  };

  const removeFile = (id: string) => {
    setStagedFiles((prev) => {
      const target = prev.find((f) => f.id === id);
      if (target?.previewUrl) {
        URL.revokeObjectURL(target.previewUrl);
      }
      return prev.filter((f) => f.id !== id);
    });
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleStartAnalysis = async () => {
    if (stagedFiles.length === 0 && !captionText.trim()) {
      setErrorMessage("Please attach at least one media file (image, video, or audio) or claim text.");
      return;
    }

    setErrorMessage(null);
    setIsProcessing(true);

    try {
      // Step 1: Ingest files & caption
      setProcessingStatus("Stage 1/2: Ingesting assets & computing cryptographic SHA-256 hashes...");
      const formData = new FormData();
      if (captionText.trim()) {
        formData.append("caption_text", captionText.trim());
      }
      stagedFiles.forEach((sf) => {
        // Append by category and generic key to guarantee matching FastAPI params
        formData.append(sf.typeCategory, sf.file);
        formData.append("files", sf.file);
      });

      const ingestRes = await ingestCase(formData);
      const caseId = ingestRes.case_id;

      // Step 2: Trigger Deepfake & Cross-Modal ML Analysis
      setProcessingStatus(
        "Stage 2/2: Executing EfficientNet-B0, ELA, Wav2Vec2 & Gemini Correlator..."
      );
      const report = await analyzeCase(caseId);

      // Clean up object URLs
      stagedFiles.forEach((sf) => {
        if (sf.previewUrl) URL.revokeObjectURL(sf.previewUrl);
      });
      setStagedFiles([]);
      setCaptionText("");

      onCaseAnalyzed(caseId, report);
    } catch (err: any) {
      console.error("Forensic analysis failed:", err);
      const target = getApiBase() || "backend service";
      setErrorMessage(
        err.message || `Forensic analysis failed. Verify backend service is running on ${target}.`
      );
    } finally {
      setIsProcessing(false);
      setProcessingStatus("");
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Intro Banner */}
      <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 shadow-lg relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-500/5 rounded-full blur-3xl -z-0 pointer-events-none" />
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-5 relative z-10">
          <div className="flex-1 min-w-[280px]">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/40">
                PHASE 1 INGESTION
              </span>
              <span className="text-xs text-gray-400 font-mono">Chain of Custody</span>
            </div>
            <h1 className="text-xl font-bold text-gray-100 tracking-tight">
              Submit Digital Evidence for Deepfake & Forensic Analysis
            </h1>
            <p className="text-xs text-gray-400 mt-1 max-w-2xl leading-relaxed">
              Upload uncompressed image, video, or audio media along with any purported context or viral
              claim text. Original files are preserved untouched with deterministic SHA-256 verification.
            </p>
          </div>

          <div className="flex flex-col items-start sm:items-end gap-1.5 text-[11px] font-mono text-gray-400 bg-[#090d16] p-3 rounded-xl border border-[#1f2937] w-full lg:w-auto shrink-0">
            <div className="w-full flex items-center justify-between gap-2 border-b border-gray-800/80 pb-1.5">
              <span className="text-gray-200 font-semibold flex items-center gap-1.5 text-xs">
                <Sparkles className="w-3.5 h-3.5 text-cyan-400" /> Forensic Demo Presets
              </span>
              <span className="text-[10px] text-gray-400">Click any preset to run live instant audit</span>
            </div>
            
            {/* Voice Forensics Presets */}
            <div className="w-full flex flex-col gap-1 mt-0.5">
              <span className="text-[10px] uppercase font-bold text-cyan-400 tracking-wider">Voice & Speech Deepfakes:</span>
              <div className="flex flex-wrap gap-1.5">
                <button
                  type="button"
                  onClick={() => onNavigateToDemo("cloned_executive_scam")}
                  className="px-2 py-1 bg-rose-950/70 hover:bg-rose-900 text-rose-300 border border-rose-700/60 rounded cursor-pointer transition-colors text-[11px] font-medium flex items-center gap-1"
                  title="CEO emergency wire transfer deepfake clone with neural vocoder harmonics"
                >
                  <FileAudio className="w-3 h-3 text-rose-400" /> CEO Voice Clone
                </button>
                <button
                  type="button"
                  onClick={() => onNavigateToDemo("spliced_political_testimony")}
                  className="px-2 py-1 bg-purple-950/70 hover:bg-purple-900 text-purple-300 border border-purple-700/60 rounded cursor-pointer transition-colors text-[11px] font-medium flex items-center gap-1"
                  title="Spliced deposition audio with abrupt phase discontinuity cut"
                >
                  <FileAudio className="w-3 h-3 text-purple-400" /> Spliced Testimony
                </button>
                <button
                  type="button"
                  onClick={() => onNavigateToDemo("telecom_robocall_scam")}
                  className="px-2 py-1 bg-amber-950/70 hover:bg-amber-900 text-amber-300 border border-amber-700/60 rounded cursor-pointer transition-colors text-[11px] font-medium flex items-center gap-1"
                  title="Automated banking scam call with 300Hz-3400Hz telephone line bandpass"
                >
                  <FileAudio className="w-3 h-3 text-amber-400" /> Banking Robocall
                </button>
                <button
                  type="button"
                  onClick={() => onNavigateToDemo("authentic_broadcast_speech")}
                  className="px-2 py-1 bg-emerald-950/70 hover:bg-emerald-900 text-emerald-300 border border-emerald-700/60 rounded cursor-pointer transition-colors text-[11px] font-medium flex items-center gap-1"
                  title="Pristine broadcast speech with natural human vocal formants and room acoustics"
                >
                  <FileAudio className="w-3 h-3 text-emerald-400" /> Broadcast Speech
                </button>
              </div>
            </div>

            {/* Visual & Multimodal Presets */}
            <div className="w-full flex flex-col gap-1 mt-1 pt-1.5 border-t border-gray-800/60">
              <span className="text-[10px] uppercase font-bold text-gray-400 tracking-wider">Visual & Multimodal Bundles:</span>
              <div className="flex flex-wrap gap-1.5">
                <button
                  type="button"
                  onClick={() => onNavigateToDemo("manipulated_multimodal")}
                  className="px-2 py-1 bg-rose-950/50 hover:bg-rose-900/80 text-rose-300 border border-rose-800/50 rounded cursor-pointer transition-colors text-[11px] font-medium flex items-center gap-1"
                  title="Face swap composite paired with synthetic voice and fake lockdown claim"
                >
                  <FileImage className="w-3 h-3 text-rose-400" /> Deepfake Face & Voice
                </button>
                <button
                  type="button"
                  onClick={() => onNavigateToDemo("authentic_bundle")}
                  className="px-2 py-1 bg-emerald-950/50 hover:bg-emerald-900/80 text-emerald-300 border border-emerald-800/50 rounded cursor-pointer transition-colors text-[11px] font-medium flex items-center gap-1"
                  title="Authentic DSLR photo with intact sensor metadata and aligned caption"
                >
                  <FileImage className="w-3 h-3 text-emerald-400" /> Authentic Photo
                </button>
                <button
                  type="button"
                  onClick={() => onNavigateToDemo("compressed_real_photo")}
                  className="px-2 py-1 bg-gray-900/90 hover:bg-gray-800 text-gray-300 border border-gray-700 rounded cursor-pointer transition-colors text-[11px] font-medium flex items-center gap-1"
                  title="Real smartphone photo re-compressed through messaging apps"
                >
                  <FileImage className="w-3 h-3 text-gray-400" /> Compressed Social
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Error Banner */}
      {errorMessage && (
        <div className="bg-rose-950/40 border border-rose-500/60 p-3.5 rounded-xl flex items-start gap-3 text-rose-300 text-xs">
          <ShieldAlert className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-semibold block mb-0.5">Forensic Ingestion Error</span>
            <span>{errorMessage}</span>
          </div>
        </div>
      )}

      {/* Drag & Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
          isDragging
            ? "border-cyan-400 bg-cyan-950/20 shadow-[0_0_20px_rgba(34,211,238,0.2)]"
            : "border-[#2d3748] hover:border-cyan-500/50 bg-[#111827]/70 hover:bg-[#111827]"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/*,video/*,audio/*,.jpg,.jpeg,.png,.webp,.mp4,.mov,.avi,.mkv,.wav,.mp3,.m4a,.ogg"
          className="hidden"
          onChange={(e) => e.target.files && handleFiles(e.target.files)}
        />
        <div className="flex flex-col items-center justify-center gap-2">
          <div className="w-12 h-12 rounded-xl bg-[#090d16] border border-[#1f2937] flex items-center justify-center text-cyan-400 mb-1">
            <UploadCloud className="w-6 h-6" />
          </div>
          <span className="text-sm font-semibold text-gray-200">
            Drag & drop media files here, or <span className="text-cyan-400 underline">browse</span>
          </span>
          <p className="text-xs text-gray-400">
            Supports JPEG, PNG, WEBP, MP4, MOV, WAV, MP3, M4A up to 25 MB per file
          </p>
          <div className="flex items-center gap-4 mt-2 text-[11px] font-mono text-gray-500">
            <span className="flex items-center gap-1">
              <FileImage className="w-3.5 h-3.5 text-cyan-400" /> Image (ELA & Grad-CAM)
            </span>
            <span className="flex items-center gap-1">
              <FileVideo className="w-3.5 h-3.5 text-purple-400" /> Video (1 FPS sampling)
            </span>
            <span className="flex items-center gap-1">
              <FileAudio className="w-3.5 h-3.5 text-blue-400" /> Audio (Wav2Vec2 + Whisper)
            </span>
          </div>
        </div>
      </div>

      {/* Staged Files Preview Grid */}
      {stagedFiles.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs text-gray-300 font-semibold px-1">
            <span>Staged Media Assets ({stagedFiles.length})</span>
            <button
              type="button"
              onClick={() => {
                stagedFiles.forEach((f) => f.previewUrl && URL.revokeObjectURL(f.previewUrl));
                setStagedFiles([]);
              }}
              className="text-gray-400 hover:text-rose-400 text-xs font-mono transition-colors"
            >
              Clear All
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {stagedFiles.map((sf) => (
              <div
                key={sf.id}
                className="bg-[#090d16] border border-[#1f2937] rounded-lg p-3 flex flex-col justify-between gap-2 relative group"
              >
                <div className="flex items-start gap-2.5">
                  {sf.typeCategory === "image" && sf.previewUrl ? (
                    <div className="w-12 h-12 rounded bg-black overflow-hidden shrink-0 border border-gray-800">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={sf.previewUrl}
                        alt="Preview"
                        className="w-full h-full object-cover"
                      />
                    </div>
                  ) : sf.typeCategory === "video" ? (
                    <div className="w-12 h-12 rounded bg-purple-950/40 border border-purple-800/40 flex items-center justify-center text-purple-400 shrink-0">
                      <FileVideo className="w-6 h-6" />
                    </div>
                  ) : (
                    <div className="w-12 h-12 rounded bg-blue-950/40 border border-blue-800/40 flex items-center justify-center text-blue-400 shrink-0">
                      <FileAudio className="w-6 h-6" />
                    </div>
                  )}

                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-mono text-gray-200 truncate">{sf.file.name}</p>
                    <p className="text-[10px] text-gray-500 font-mono mt-0.5">
                      {(sf.file.size / (1024 * 1024)).toFixed(2)} MB • {sf.typeCategory.toUpperCase()}
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      removeFile(sf.id);
                    }}
                    className="text-gray-500 hover:text-rose-400 p-1 rounded transition-colors"
                    title="Remove file"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Claim / Context Text Input */}
      <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-4 space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-xs font-semibold text-gray-200 uppercase tracking-wider flex items-center gap-1.5">
            <span>Viral Context or Purported Claim</span>
            <span className="text-[10px] font-mono text-gray-500 font-normal">
              (Cross-Modal Consistency Check)
            </span>
          </label>
          <span className="text-[10px] font-mono text-gray-500">Optional</span>
        </div>
        <textarea
          rows={3}
          value={captionText}
          onChange={(e) => setCaptionText(e.target.value)}
          placeholder="E.g., 'Leaked video of minister announcing emergency currency recall yesterday in Geneva' — used by Gemini to detect semantic inconsistencies between context and visual/audio facts."
          className="w-full bg-[#090d16] border border-[#1f2937] rounded-lg p-3 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500/60 font-sans resize-y"
        />
      </div>

      {/* Context-Only Warning if no media attached */}
      {stagedFiles.length === 0 && captionText.trim() && (
        <div className="bg-amber-950/40 border border-amber-500/50 p-3.5 rounded-xl flex items-start gap-3 text-xs text-amber-300">
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <span className="font-semibold block text-amber-200">
              Context-Only Mode: No media files attached above.
            </span>
            <p className="text-amber-300/90 font-sans leading-relaxed">
              Submitting now will register a text-only contextual claim and evaluate disinformation patterns via LLM. To run full multimodal deepfake forensics (EfficientNet-B0 Grad-CAM heatmaps, ELA compression analysis, Wav2Vec2 speech feature inspection, or video frame audits), drag or upload an image, audio clip, or video into the drop zone above.
            </p>
          </div>
        </div>
      )}

      {/* Action Trigger Button */}
      <div className="flex items-center justify-end gap-3 pt-2">
        <button
          type="button"
          disabled={isProcessing || (stagedFiles.length === 0 && !captionText.trim())}
          onClick={handleStartAnalysis}
          className={`px-6 py-3 rounded-xl font-semibold text-xs tracking-wider uppercase transition-all flex items-center gap-2 cursor-pointer ${
            isProcessing
              ? "bg-cyan-950 text-cyan-400 border border-cyan-800 cursor-not-allowed"
              : stagedFiles.length === 0 && !captionText.trim()
              ? "bg-gray-800 text-gray-500 border border-gray-700 cursor-not-allowed"
              : "bg-gradient-to-r from-cyan-600 via-cyan-500 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white shadow-lg shadow-cyan-900/30 border border-cyan-400/40"
          }`}
        >
          {isProcessing ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
              <span>{processingStatus || "Analyzing Digital Evidence..."}</span>
            </>
          ) : (
            <>
              <Play className="w-4 h-4 fill-white" />
              <span>Ingest & Run Forensic Analysis</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};
