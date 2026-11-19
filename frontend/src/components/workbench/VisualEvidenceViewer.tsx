"use client";

import React, { useState, useEffect } from "react";
import {
  Layers,
  Columns,
  Eye,
  Sliders,
  Camera,
  Cpu,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Maximize2,
  Info,
  CheckCircle2,
  FileSearch,
} from "lucide-react";
import { ImageMetadata, ElaStats } from "@/types/forensics";
import { assetUrl } from "@/lib/api";

export type ViewMode = "single" | "side_by_side" | "overlay";
export type OverlayType = "original" | "gradcam" | "ela";

interface VisualEvidenceViewerProps {
  originalUrl: string;
  originalFilename?: string;
  gradcamUrl?: string | null;
  elaUrl?: string | null;
  metadata?: ImageMetadata;
  externalOverlay?: "gradcam" | "ela" | null;
  externalViewMode?: ViewMode | null;
  title?: string;
  subtitle?: string;
}

export const VisualEvidenceViewer: React.FC<VisualEvidenceViewerProps> = ({
  originalUrl,
  originalFilename = "Source Evidence",
  gradcamUrl,
  elaUrl,
  metadata,
  externalOverlay,
  externalViewMode,
  title = "Visual Evidence & Heatmap Inspector",
  subtitle = "High-resolution spatial analysis & forensic artifacts",
}) => {
  const [viewMode, setViewMode] = useState<ViewMode>("side_by_side");
  const [activeOverlay, setActiveOverlay] = useState<OverlayType>("gradcam");
  const [blendOpacity, setBlendOpacity] = useState<number>(65); // 0 to 100
  const [showExifTable, setShowExifTable] = useState<boolean>(false);

  // Sync external control (e.g. from clicking flagged evidence)
  useEffect(() => {
    if (externalOverlay) {
      setActiveOverlay(externalOverlay);
    }
  }, [externalOverlay]);

  useEffect(() => {
    if (externalViewMode) {
      setViewMode(externalViewMode);
    }
  }, [externalViewMode]);

  const resolvedOriginal = assetUrl(originalUrl);
  const resolvedGradcam = gradcamUrl ? assetUrl(gradcamUrl) : null;
  const resolvedEla = elaUrl ? assetUrl(elaUrl) : null;

  // Selected secondary overlay URL
  const currentSecondaryUrl =
    activeOverlay === "ela" ? resolvedEla : resolvedGradcam;
  const currentSecondaryLabel =
    activeOverlay === "ela"
      ? "Error Level Analysis (ELA 95%)"
      : "EfficientNet-B0 Grad-CAM Heatmap";

  const elaStats: ElaStats | undefined = metadata?.ela_stats;
  const exif = metadata?.exif;
  const hasExif = metadata?.has_exif;

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl overflow-hidden shadow-xl">
      {/* Viewer Header */}
      <div className="p-4 border-b border-[#1f2937] flex flex-wrap items-center justify-between gap-3 bg-[#0c121e]">
        <div>
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-bold text-gray-100 uppercase tracking-wider">
              {title}
            </h3>
            {originalFilename && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#090d16] text-gray-400 border border-[#1f2937] truncate max-w-xs">
                {originalFilename}
              </span>
            )}
          </div>
          <p className="text-[11px] text-gray-400 mt-0.5">{subtitle}</p>
        </div>

        {/* View Mode & Overlay Switcher Toolbar */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Overlay Selector */}
          <div className="flex items-center bg-[#090d16] p-1 rounded-lg border border-[#1f2937] text-xs font-mono">
            {viewMode === "single" && (
              <button
                type="button"
                onClick={() => setActiveOverlay("original")}
                className={`px-2.5 py-1 rounded transition-colors ${
                  activeOverlay === "original"
                    ? "bg-cyan-950 text-cyan-300 font-bold border border-cyan-700/50"
                    : "text-gray-400 hover:text-gray-200"
                }`}
              >
                Original
              </button>
            )}
            <button
              type="button"
              disabled={!resolvedGradcam}
              onClick={() => setActiveOverlay("gradcam")}
              className={`px-2.5 py-1 rounded transition-colors ${
                !resolvedGradcam
                  ? "opacity-40 cursor-not-allowed text-gray-600"
                  : activeOverlay === "gradcam"
                  ? "bg-cyan-950 text-cyan-300 font-bold border border-cyan-700/50"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              Grad-CAM
            </button>
            <button
              type="button"
              disabled={!resolvedEla}
              onClick={() => setActiveOverlay("ela")}
              className={`px-2.5 py-1 rounded transition-colors ${
                !resolvedEla
                  ? "opacity-40 cursor-not-allowed text-gray-600"
                  : activeOverlay === "ela"
                  ? "bg-cyan-950 text-cyan-300 font-bold border border-cyan-700/50"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              ELA (95%)
            </button>
          </div>

          {/* Mode Switcher */}
          <div className="flex items-center bg-[#090d16] p-1 rounded-lg border border-[#1f2937]">
            <button
              type="button"
              onClick={() => setViewMode("side_by_side")}
              title="Side-by-Side comparison"
              className={`p-1.5 rounded transition-colors ${
                viewMode === "side_by_side"
                  ? "bg-cyan-950 text-cyan-300 border border-cyan-700/50"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              <Columns className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={() => setViewMode("overlay")}
              title="Overlay blend with opacity sweep"
              className={`p-1.5 rounded transition-colors ${
                viewMode === "overlay"
                  ? "bg-cyan-950 text-cyan-300 border border-cyan-700/50"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              <Sliders className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={() => setViewMode("single")}
              title="Single inspect view"
              className={`p-1.5 rounded transition-colors ${
                viewMode === "single"
                  ? "bg-cyan-950 text-cyan-300 border border-cyan-700/50"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              <Eye className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Opacity Slider Bar (Active when in Overlay mode) */}
      {viewMode === "overlay" && (
        <div className="px-5 py-2.5 bg-[#090d16] border-b border-[#1f2937] flex items-center justify-between gap-4 text-xs font-mono">
          <div className="flex items-center gap-2 text-gray-300">
            <Sliders className="w-3.5 h-3.5 text-cyan-400" />
            <span>
              Overlay Blend ({activeOverlay === "ela" ? "ELA" : "Grad-CAM"}):
            </span>
            <span className="text-cyan-400 font-bold">{blendOpacity}%</span>
          </div>

          <div className="flex-1 max-w-md flex items-center gap-2">
            <span className="text-[10px] text-gray-500">Original (0%)</span>
            <input
              type="range"
              min="0"
              max="100"
              value={blendOpacity}
              onChange={(e) => setBlendOpacity(Number(e.target.value))}
              className="flex-1 h-1.5 bg-[#1f2937] rounded-lg appearance-none cursor-pointer accent-cyan-400"
            />
            <span className="text-[10px] text-gray-500">Overlay (100%)</span>
          </div>
        </div>
      )}

      {/* Main Canvas Area */}
      <div className="p-4 bg-[#070b12] min-h-[320px] flex items-center justify-center">
        {/* Mode 1: Side by Side */}
        {viewMode === "side_by_side" && (
          <div className="w-full grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Left: Original Evidence */}
            <div className="flex flex-col bg-[#090d16] border border-[#1f2937] rounded-lg overflow-hidden">
              <div className="px-3 py-1.5 bg-[#111827] border-b border-[#1f2937] flex items-center justify-between text-[11px] font-mono">
                <span className="text-gray-300 font-semibold flex items-center gap-1.5">
                  <Eye className="w-3.5 h-3.5 text-cyan-400" /> Original Evidence
                </span>
                <span className="text-gray-500 text-[10px]">Unprocessed</span>
              </div>
              <div className="p-2 flex items-center justify-center min-h-[280px] max-h-[440px] bg-black/40">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={resolvedOriginal}
                  alt="Original Digital Evidence"
                  className="max-h-[420px] w-auto max-w-full object-contain rounded shadow-md"
                />
              </div>
            </div>

            {/* Right: Selected Forensic Heatmap / ELA */}
            <div className="flex flex-col bg-[#090d16] border border-[#1f2937] rounded-lg overflow-hidden">
              <div className="px-3 py-1.5 bg-[#111827] border-b border-[#1f2937] flex items-center justify-between text-[11px] font-mono">
                <span className="text-cyan-300 font-semibold flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-cyan-400" />
                  {currentSecondaryLabel}
                </span>
                <span className="text-cyan-400 text-[10px] uppercase font-bold">
                  {activeOverlay}
                </span>
              </div>
              <div className="p-2 flex items-center justify-center min-h-[280px] max-h-[440px] bg-black/40">
                {currentSecondaryUrl ? (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img
                    src={currentSecondaryUrl}
                    alt={currentSecondaryLabel}
                    className="max-h-[420px] w-auto max-w-full object-contain rounded shadow-md"
                  />
                ) : (
                  <div className="text-center p-6 text-gray-500 font-mono text-xs">
                    <Info className="w-8 h-8 text-gray-600 mx-auto mb-2" />
                    <span>No {activeOverlay.toUpperCase()} artifact generated for this keyframe.</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Mode 2: Overlay Blend with Opacity Sweep */}
        {viewMode === "overlay" && (
          <div className="w-full flex flex-col items-center justify-center">
            <div className="relative inline-block max-w-full max-h-[480px] rounded-lg overflow-hidden border border-[#1f2937] shadow-2xl bg-black">
              {/* Base layer: Original image */}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={resolvedOriginal}
                alt="Base Original"
                className="max-h-[460px] w-auto max-w-full object-contain block"
              />

              {/* Stacked overlay layer: Grad-CAM or ELA with dynamic opacity */}
              {currentSecondaryUrl && (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img
                  src={currentSecondaryUrl}
                  alt="Forensic Overlay"
                  style={{ opacity: blendOpacity / 100 }}
                  className="absolute inset-0 w-full h-full object-contain pointer-events-none transition-opacity duration-75"
                />
              )}
            </div>
            <p className="text-[10px] text-gray-500 font-mono mt-2">
              Sweep slider to adjust transparency of {currentSecondaryLabel} against raw pixels.
            </p>
          </div>
        )}

        {/* Mode 3: Single View */}
        {viewMode === "single" && (
          <div className="w-full flex flex-col items-center justify-center">
            <div className="max-w-full max-h-[480px] rounded-lg overflow-hidden border border-[#1f2937] shadow-xl bg-black/50 p-2">
              {activeOverlay === "original" ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img
                  src={resolvedOriginal}
                  alt="Original View"
                  className="max-h-[450px] w-auto max-w-full object-contain rounded"
                />
              ) : currentSecondaryUrl ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img
                  src={currentSecondaryUrl}
                  alt={currentSecondaryLabel}
                  className="max-h-[450px] w-auto max-w-full object-contain rounded"
                />
              ) : (
                <div className="text-center p-8 text-gray-500 font-mono text-xs">
                  Artifact unavailable.
                </div>
              )}
            </div>
            <span className="text-[11px] font-mono text-cyan-400 mt-2">
              Displaying:{" "}
              {activeOverlay === "original"
                ? "Original Image"
                : currentSecondaryLabel}
            </span>
          </div>
        )}
      </div>

      {/* Forensic Telemetry Strip */}
      <div className="p-4 bg-[#0c121e] border-t border-[#1f2937] space-y-3">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
          {/* Telemetry 1: Model Mode */}
          <div className="bg-[#090d16] border border-[#1f2937] p-2.5 rounded-lg">
            <span className="text-[10px] text-gray-500 block uppercase">
              Vision Model Head
            </span>
            <span
              className={`font-semibold truncate block ${
                metadata?.model_mode === "custom_trained"
                  ? "text-emerald-400"
                  : "text-amber-400"
              }`}
            >
              {metadata?.model_mode || "efficientnet_b0"}
            </span>
          </div>

          {/* Telemetry 2: Temperature T */}
          <div className="bg-[#090d16] border border-[#1f2937] p-2.5 rounded-lg">
            <span className="text-[10px] text-gray-500 block uppercase">
              Temperature Scaling ($T$)
            </span>
            <span className="text-cyan-400 font-bold">
              T = {metadata?.temperature_T ?? 1.5}
            </span>
          </div>

          {/* Telemetry 3: ELA Mean Diff */}
          <div className="bg-[#090d16] border border-[#1f2937] p-2.5 rounded-lg">
            <span className="text-[10px] text-gray-500 block uppercase">
              ELA Mean / Max Residual
            </span>
            <span className="text-gray-200">
              {elaStats?.mean_diff !== undefined
                ? `${elaStats.mean_diff.toFixed(2)} / ${elaStats.max_diff.toFixed(1)}`
                : "N/A"}
            </span>
          </div>

          {/* Telemetry 4: ELA High Variance */}
          <div className="bg-[#090d16] border border-[#1f2937] p-2.5 rounded-lg">
            <span className="text-[10px] text-gray-500 block uppercase">
              ELA Anomaly Ratio
            </span>
            <span
              className={`font-bold ${
                (elaStats?.high_variance_ratio || 0) > 0.05
                  ? "text-rose-400"
                  : "text-emerald-400"
              }`}
            >
              {elaStats?.high_variance_ratio !== undefined
                ? `${(elaStats.high_variance_ratio * 100).toFixed(2)}%`
                : "N/A"}
            </span>
          </div>
        </div>

        {/* Collapsible EXIF Metadata Drawer */}
        <div className="border border-[#1f2937] rounded-lg overflow-hidden bg-[#090d16]">
          <button
            type="button"
            onClick={() => setShowExifTable((prev) => !prev)}
            className="w-full px-3 py-2 flex items-center justify-between text-xs font-mono text-gray-300 hover:text-white hover:bg-[#111827] transition-colors cursor-pointer"
          >
            <div className="flex items-center gap-2">
              <Camera className="w-3.5 h-3.5 text-cyan-400" />
              <span>EXIF Camera & Editing Software Signatures</span>
              {metadata?.software && (
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-950 text-amber-300 border border-amber-800">
                  Tag: {metadata.software}
                </span>
              )}
              {hasExif === false && (
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-rose-950 text-rose-300 border border-rose-800">
                  EXIF Stripped / Missing
                </span>
              )}
            </div>

            <div className="flex items-center gap-1 text-[11px] text-gray-400">
              <span>{showExifTable ? "Hide EXIF" : "Inspect EXIF"}</span>
              {showExifTable ? (
                <ChevronUp className="w-3.5 h-3.5" />
              ) : (
                <ChevronDown className="w-3.5 h-3.5" />
              )}
            </div>
          </button>

          {showExifTable && (
            <div className="p-3 border-t border-[#1f2937] text-xs font-mono space-y-2 max-h-60 overflow-y-auto custom-scrollbar">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
                <div className="bg-[#0c121e] p-2 rounded border border-[#1f2937]">
                  <span className="text-gray-500 block">Camera Make:</span>
                  <span className="text-gray-200">{metadata?.camera_make || "None recorded"}</span>
                </div>
                <div className="bg-[#0c121e] p-2 rounded border border-[#1f2937]">
                  <span className="text-gray-500 block">Camera Model:</span>
                  <span className="text-gray-200">{metadata?.camera_model || "None recorded"}</span>
                </div>
                <div className="bg-[#0c121e] p-2 rounded border border-[#1f2937]">
                  <span className="text-gray-500 block">Reported Software:</span>
                  <span className={metadata?.software ? "text-amber-400 font-semibold" : "text-gray-200"}>
                    {metadata?.software || "No editing software tags present"}
                  </span>
                </div>
                <div className="bg-[#0c121e] p-2 rounded border border-[#1f2937]">
                  <span className="text-gray-500 block">Resolution & Format:</span>
                  <span className="text-gray-200">
                    {metadata?.width && metadata?.height
                      ? `${metadata.width} x ${metadata.height} (${metadata.format || "RGB"})`
                      : "Standard"}
                  </span>
                </div>
              </div>

              {exif && Object.keys(exif).length > 0 ? (
                <div className="mt-2 pt-2 border-t border-[#1f2937]">
                  <span className="text-[10px] text-gray-400 uppercase tracking-wider block mb-1">
                    Raw EXIF Tags ({Object.keys(exif).length}):
                  </span>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[10px] text-gray-400 max-h-36 overflow-y-auto custom-scrollbar pr-1">
                    {Object.entries(exif).map(([k, v]) => (
                      <div key={k} className="flex justify-between border-b border-[#1f2937]/50 py-0.5 truncate">
                        <span className="text-gray-500 truncate mr-2">{k}:</span>
                        <span className="text-gray-300 font-mono truncate">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-[10px] text-gray-500 italic pt-1">
                  No extended EXIF header payload found in the ingested image file.
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
