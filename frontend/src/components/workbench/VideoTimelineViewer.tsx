"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Video as VideoIcon,
  Play,
  Pause,
  Clock,
  Activity,
  AlertTriangle,
  Layers,
  ChevronRight,
  TrendingUp,
  Image as ImageIcon,
  CheckCircle2,
} from "lucide-react";
import { VideoMetadata, VideoKeyframe, VideoFramePoint } from "@/types/forensics";
import { assetUrl } from "@/lib/api";
import { VisualEvidenceViewer } from "./VisualEvidenceViewer";

interface VideoTimelineViewerProps {
  videoUrl: string;
  videoFilename?: string;
  metadata?: VideoMetadata;
  onSelectKeyframe?: (keyframe: VideoKeyframe) => void;
  externalSeekTime?: number | null;
  title?: string;
}

export const VideoTimelineViewer: React.FC<VideoTimelineViewerProps> = ({
  videoUrl,
  videoFilename = "Video Evidence",
  metadata,
  onSelectKeyframe,
  externalSeekTime,
  title = "Temporal Inter-Frame Deepfake & Video Risk Analyzer",
}) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);

  const [currentVideoTime, setCurrentVideoTime] = useState<number>(0);
  const [selectedKeyframe, setSelectedKeyframe] = useState<VideoKeyframe | null>(
    metadata?.keyframes && metadata.keyframes.length > 0
      ? metadata.keyframes[0]
      : null
  );

  const resolvedVideoUrl = assetUrl(videoUrl);
  const frameTimeline: VideoFramePoint[] = metadata?.frame_timeline || [];
  const temporalStats = metadata?.temporal_stats;
  const keyframes: VideoKeyframe[] = metadata?.keyframes || [];

  // Handle external seek triggers
  useEffect(() => {
    if (externalSeekTime !== undefined && externalSeekTime !== null && videoRef.current) {
      seekToTime(externalSeekTime);
    }
  }, [externalSeekTime]);

  const seekToTime = (timestampSec: number) => {
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = timestampSec;
    setCurrentVideoTime(timestampSec);
    video.play().catch(() => {});
  };

  const handleKeyframeClick = (kf: VideoKeyframe) => {
    setSelectedKeyframe(kf);
    seekToTime(kf.timestamp_sec);
    if (onSelectKeyframe) {
      onSelectKeyframe(kf);
    }
  };

  const maxDelta = temporalStats?.max_frame_delta ?? 0;
  const isTemporalSpike = maxDelta >= 0.25;

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl overflow-hidden shadow-xl space-y-4">
      {/* Header */}
      <div className="p-4 border-b border-[#1f2937] flex flex-wrap items-center justify-between gap-3 bg-[#0c121e]">
        <div>
          <div className="flex items-center gap-2">
            <VideoIcon className="w-4 h-4 text-purple-400" />
            <h3 className="text-xs font-bold text-gray-100 uppercase tracking-wider">
              {title}
            </h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#090d16] text-gray-400 border border-[#1f2937] truncate max-w-xs">
              {videoFilename}
            </span>
          </div>
          <p className="text-[11px] text-gray-400 mt-0.5">
            1 FPS temporal sampling with neural facial manipulation detection and inter-frame jump tracking
          </p>
        </div>

        {/* Telemetry badges */}
        <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
          <span
            className={`text-[10px] px-2 py-0.5 rounded border ${
              isTemporalSpike
                ? "bg-rose-950 text-rose-300 border-rose-800 font-bold flex items-center gap-1"
                : "bg-emerald-950 text-emerald-300 border-emerald-800"
            }`}
          >
            {isTemporalSpike ? (
              <>
                <AlertTriangle className="w-3 h-3 text-rose-400" />
                Inter-frame Spike ({maxDelta.toFixed(2)})
              </>
            ) : (
              `Temporal Stable (Δ ${maxDelta.toFixed(2)})`
            )}
          </span>

          <span className="text-[10px] px-2 py-0.5 rounded bg-[#090d16] border border-[#1f2937] text-gray-400">
            Peak Frame:{" "}
            <span className="text-cyan-400 font-bold">
              {temporalStats?.max_score !== undefined
                ? (temporalStats.max_score * 100).toFixed(0) + "%"
                : "N/A"}
            </span>
          </span>
        </div>
      </div>

      <div className="p-5 space-y-6">
        {/* Video Player & Current Keyframe Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* HTML5 Video Player */}
          <div className="bg-[#090d16] border border-[#1f2937] rounded-xl overflow-hidden flex flex-col justify-between">
            <div className="px-3 py-1.5 bg-[#111827] border-b border-[#1f2937] flex items-center justify-between text-[11px] font-mono">
              <span className="text-gray-300 font-semibold flex items-center gap-1.5">
                <VideoIcon className="w-3.5 h-3.5 text-purple-400" /> Ingested Video Stream
              </span>
              <span className="text-gray-400">
                {videoRef.current ? `${videoRef.current.currentTime.toFixed(1)}s` : "0.0s"}
              </span>
            </div>

            <div className="p-3 bg-black/60 flex items-center justify-center min-h-[260px] max-h-[380px]">
              <video
                ref={videoRef}
                src={resolvedVideoUrl}
                controls
                playsInline
                className="max-h-[360px] w-auto max-w-full rounded shadow-lg"
                onTimeUpdate={() => {
                  if (videoRef.current) {
                    setCurrentVideoTime(videoRef.current.currentTime);
                  }
                }}
              />
            </div>

            <div className="p-2.5 bg-[#0c121e] border-t border-[#1f2937] flex items-center justify-between text-[10px] font-mono text-gray-500">
              <span>Resolution: {metadata?.width && metadata?.height ? `${metadata.width}x${metadata.height}` : "HD"}</span>
              <span>Total Sampled: {frameTimeline.length} keyframes</span>
            </div>
          </div>

          {/* Temporal Risk Timeline SVG Chart */}
          <div className="bg-[#090d16] border border-[#1f2937] rounded-xl p-4 flex flex-col justify-between space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-gray-200 uppercase tracking-wider flex items-center gap-1.5">
                <TrendingUp className="w-3.5 h-3.5 text-cyan-400" />
                <span>Temporal Risk Curve</span>
              </span>
              <span className="text-[10px] font-mono text-gray-500">
                Click bar to seek video
              </span>
            </div>

            {/* Bar Timeline SVG Plot */}
            <div className="h-48 w-full bg-[#070b12] rounded-lg border border-[#1f2937] p-2 relative flex flex-col justify-end">
              {/* Threshold line at 0.55 */}
              <div
                style={{ bottom: "55%" }}
                className="absolute left-2 right-2 border-b border-dashed border-rose-500/70 z-10 pointer-events-none"
              >
                <span className="text-[9px] font-mono text-rose-400 bg-[#070b12] px-1 absolute right-0 -top-3">
                  0.55 Suspicion Threshold
                </span>
              </div>

              {/* Bars for each frame */}
              {frameTimeline.length > 0 ? (
                <div className="flex items-end justify-between h-full gap-1 pt-4 pb-1">
                  {frameTimeline.map((f, i) => {
                    const heightPct = Math.max(6, Math.min(f.score * 100, 100));
                    const isHigh = f.score >= 0.55;
                    const isMod = f.score >= 0.35 && f.score < 0.55;
                    const isNearCurrent =
                      Math.abs(f.timestamp_sec - currentVideoTime) < 1.0;

                    return (
                      <button
                        key={i}
                        type="button"
                        onClick={() => seekToTime(f.timestamp_sec)}
                        title={`Frame ${f.frame_index} (${f.timestamp_str}) • Score: ${(f.score * 100).toFixed(0)}%`}
                        className="flex-1 flex flex-col items-center justify-end h-full group relative focus:outline-none cursor-pointer"
                      >
                        <div
                          style={{ height: `${heightPct}%` }}
                          className={`w-full max-w-[12px] rounded-t transition-all ${
                            isNearCurrent
                              ? "ring-2 ring-cyan-300 bg-cyan-400 shadow-md shadow-cyan-500/50"
                              : isHigh
                              ? "bg-rose-500 group-hover:bg-rose-400"
                              : isMod
                              ? "bg-amber-500 group-hover:bg-amber-400"
                              : "bg-emerald-500/80 group-hover:bg-emerald-400"
                          }`}
                        />
                        <span className="text-[8px] font-mono text-gray-500 mt-1 truncate max-w-[20px]">
                          {f.timestamp_str.slice(3)}
                        </span>
                      </button>
                    );
                  })}
                </div>
              ) : (
                <div className="h-full flex items-center justify-center text-xs font-mono text-gray-500">
                  No temporal keyframes scored.
                </div>
              )}
            </div>

            <div className="flex items-center justify-between text-[10px] font-mono text-gray-400 pt-1 border-t border-[#1f2937]">
              <span>Mean Score: {((temporalStats?.mean_score || 0) * 100).toFixed(1)}%</span>
              <span>Max Score: {((temporalStats?.max_score || 0) * 100).toFixed(1)}%</span>
              <span>Std Dev: {temporalStats?.score_std?.toFixed(3) || "0.000"}</span>
            </div>
          </div>
        </div>

        {/* Top Flagged Keyframes Cards */}
        {keyframes.length > 0 && (
          <div className="space-y-3 pt-2">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-semibold text-gray-200 uppercase tracking-wider flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-cyan-400" />
                <span>Top Flagged Video Keyframes ({keyframes.length})</span>
              </h4>
              <span className="text-[10px] font-mono text-gray-500">
                Click keyframe to jump video & inspect heatmaps
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {keyframes.map((kf) => {
                const isSelected =
                  selectedKeyframe?.frame_index === kf.frame_index;
                const gradcamArt = kf.artifact_urls?.gradcam;
                const elaArt = kf.artifact_urls?.ela;

                return (
                  <div
                    key={kf.frame_index}
                    onClick={() => handleKeyframeClick(kf)}
                    className={`p-3 rounded-xl border transition-all cursor-pointer flex flex-col justify-between gap-2 ${
                      isSelected
                        ? "bg-purple-950/40 border-purple-500/70 ring-1 ring-purple-500/50 shadow-lg"
                        : "bg-[#090d16] border-[#1f2937] hover:border-gray-700"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono font-bold text-gray-200 flex items-center gap-1">
                        <Clock className="w-3 h-3 text-purple-400" />
                        {kf.timestamp_str}
                      </span>
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                          kf.score >= 0.55
                            ? "bg-rose-950 text-rose-300 border border-rose-800"
                            : kf.score >= 0.35
                            ? "bg-amber-950 text-amber-300 border border-amber-800"
                            : "bg-emerald-950 text-emerald-300 border border-emerald-800"
                        }`}
                      >
                        {(kf.score * 100).toFixed(0)}% Risk
                      </span>
                    </div>

                    {/* Thumbnail preview if Grad-CAM artifact exists */}
                    {gradcamArt && (
                      <div className="h-28 bg-black rounded-lg overflow-hidden border border-gray-800 flex items-center justify-center">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={assetUrl(gradcamArt)}
                          alt={`Keyframe ${kf.timestamp_str}`}
                          className="h-full w-full object-contain"
                        />
                      </div>
                    )}

                    <div className="flex items-center justify-between text-[10px] font-mono text-gray-400 pt-1 border-t border-[#1f2937]">
                      <span>Frame #{kf.frame_index}</span>
                      <span className="text-cyan-400 flex items-center gap-0.5">
                        Inspect Overlays <ChevronRight className="w-3 h-3" />
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Selected Keyframe Deep-Dive in VisualEvidenceViewer */}
        {selectedKeyframe && (selectedKeyframe.artifact_urls?.gradcam || selectedKeyframe.artifact_urls?.ela) && (
          <div className="pt-3 border-t border-[#1f2937]">
            <VisualEvidenceViewer
              title={`Keyframe @ ${selectedKeyframe.timestamp_str} (Frame #${selectedKeyframe.frame_index}) — Side-by-Side Comparison`}
              subtitle="Side-by-side comparison of the video frame vs. neural Grad-CAM activation heatmap & ELA compression residual map"
              originalUrl={selectedKeyframe.artifact_urls?.raw || selectedKeyframe.artifact_urls?.gradcam || ""}
              gradcamUrl={selectedKeyframe.artifact_urls?.gradcam}
              elaUrl={selectedKeyframe.artifact_urls?.ela}
              externalOverlay="gradcam"
              externalViewMode="side_by_side"
            />
          </div>
        )}
      </div>
    </div>
  );
};
