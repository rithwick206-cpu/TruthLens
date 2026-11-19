"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Play,
  Pause,
  Volume2,
  VolumeX,
  RotateCcw,
  Mic,
  Cpu,
  Clock,
  AlertTriangle,
  FileText,
  Activity,
  CheckCircle2,
  Info,
} from "lucide-react";
import { AudioMetadata, AudioSegment, TranscriptSegment } from "@/types/forensics";
import { assetUrl } from "@/lib/api";

interface AudioForensicsPlayerProps {
  audioUrl: string;
  audioFilename?: string;
  metadata?: AudioMetadata;
  externalSeekTime?: number | null;
  title?: string;
}

export const AudioForensicsPlayer: React.FC<AudioForensicsPlayerProps> = ({
  audioUrl,
  audioFilename = "Audio Evidence",
  metadata,
  externalSeekTime,
  title = "Acoustic Discontinuity & Deepfake Voice Detector",
}) => {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const waveformContainerRef = useRef<HTMLDivElement | null>(null);

  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [totalDuration, setTotalDuration] = useState<number>(metadata?.duration_sec || 0);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [activeSegmentIndex, setActiveSegmentIndex] = useState<number | null>(null);

  const resolvedAudioUrl = assetUrl(audioUrl);
  const segments: AudioSegment[] = metadata?.segments || [];
  const waveformPeaks: number[] =
    metadata?.waveform_peaks && metadata.waveform_peaks.length > 0
      ? metadata.waveform_peaks
      : Array.from({ length: 60 }, (_, i) => 0.2 + 0.5 * Math.sin((i / 60) * Math.PI));

  const transcriptText = metadata?.transcript_text;
  const transcriptStatus = metadata?.transcript_status || "not_configured";
  const transcriptSegments: TranscriptSegment[] = metadata?.transcript_segments || [];

  // Seek external trigger (e.g. from flagged evidence table click)
  useEffect(() => {
    if (externalSeekTime !== undefined && externalSeekTime !== null && audioRef.current) {
      seekToTime(externalSeekTime);
    }
  }, [externalSeekTime]);

  // Audio event listeners
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleTimeUpdate = () => {
      const cur = audio.currentTime;
      setCurrentTime(cur);

      // Identify active segment
      const idx = segments.findIndex(
        (seg) => cur >= seg.start_sec && cur <= seg.end_sec
      );
      setActiveSegmentIndex(idx !== -1 ? idx : null);
    };

    const handleLoadedMetadata = () => {
      if (audio.duration && !isNaN(audio.duration)) {
        setTotalDuration(audio.duration);
      }
    };

    const handleEnded = () => {
      setIsPlaying(false);
      setCurrentTime(0);
    };

    audio.addEventListener("timeupdate", handleTimeUpdate);
    audio.addEventListener("loadedmetadata", handleLoadedMetadata);
    audio.addEventListener("ended", handleEnded);

    return () => {
      audio.removeEventListener("timeupdate", handleTimeUpdate);
      audio.removeEventListener("loadedmetadata", handleLoadedMetadata);
      audio.removeEventListener("ended", handleEnded);
    };
  }, [segments]);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
    } else {
      audio.play().then(() => setIsPlaying(true)).catch((e) => console.error(e));
    }
  };

  const toggleMute = () => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.muted = !isMuted;
    setIsMuted(!isMuted);
  };

  const seekToTime = (timeSec: number) => {
    const audio = audioRef.current;
    if (!audio) return;
    const clamped = Math.max(0, Math.min(timeSec, totalDuration || 100));
    audio.currentTime = clamped;
    setCurrentTime(clamped);
    if (!isPlaying) {
      audio.play().then(() => setIsPlaying(true)).catch(() => {});
    }
  };

  const handleWaveformClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const container = waveformContainerRef.current;
    if (!container || !totalDuration) return;
    const rect = container.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const pct = Math.max(0, Math.min(clickX / rect.width, 1));
    seekToTime(pct * totalDuration);
  };

  const formatSeconds = (sec: number): string => {
    if (isNaN(sec) || sec < 0) return "00:00";
    const mins = Math.floor(sec / 60);
    const secs = Math.floor(sec % 60);
    return `${mins < 10 ? "0" : ""}${mins}:${secs < 10 ? "0" : ""}${secs}`;
  };

  // Find color for a bar based on timestamp
  const getBarColor = (barIndex: number, totalBars: number) => {
    if (!totalDuration || segments.length === 0) return "#06b6d4"; // default cyan
    const barTime = (barIndex / totalBars) * totalDuration;
    const matchingSeg = segments.find(
      (s) => barTime >= s.start_sec && barTime <= s.end_sec
    );
    if (!matchingSeg) return "#06b6d4";
    if (matchingSeg.score >= 0.55) return "#f43f5e"; // rose/high risk
    if (matchingSeg.score >= 0.35) return "#f59e0b"; // amber/moderate
    return "#10b981"; // emerald/low
  };

  const progressPercent =
    totalDuration > 0 ? (currentTime / totalDuration) * 100 : 0;

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl overflow-hidden shadow-xl">
      {/* Hidden Native Audio Element */}
      <audio ref={audioRef} src={resolvedAudioUrl} preload="metadata" />

      {/* Header */}
      <div className="p-4 border-b border-[#1f2937] flex flex-wrap items-center justify-between gap-3 bg-[#0c121e]">
        <div>
          <div className="flex items-center gap-2">
            <Mic className="w-4 h-4 text-blue-400" />
            <h3 className="text-xs font-bold text-gray-100 uppercase tracking-wider">
              {title}
            </h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#090d16] text-gray-400 border border-[#1f2937] truncate max-w-xs">
              {audioFilename}
            </span>
          </div>
          <p className="text-[11px] text-gray-400 mt-0.5">
            Sliding-window acoustic feature extraction & neural voice synthesis detector
          </p>
        </div>

        {/* Telemetry pill */}
        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="text-[10px] px-2 py-0.5 rounded bg-[#090d16] border border-[#1f2937] text-gray-400">
            Model:{" "}
            <span
              className={
                metadata?.model_mode === "wav2vec2_pretrained"
                  ? "text-emerald-400 font-semibold"
                  : "text-amber-400 font-semibold"
              }
            >
              {metadata?.model_mode || "wav2vec2"}
            </span>
          </span>
          <span className="text-[10px] px-2 py-0.5 rounded bg-[#090d16] border border-[#1f2937] text-gray-400">
            Duration:{" "}
            <span className="text-cyan-400 font-semibold">
              {totalDuration ? `${totalDuration.toFixed(1)}s` : "Unknown"}
            </span>
          </span>
        </div>
      </div>

      {/* Main Interactive Waveform & Scrubber */}
      <div className="p-5 bg-[#070b12] space-y-4">
        {/* Waveform Visualization Canvas */}
        <div
          ref={waveformContainerRef}
          onClick={handleWaveformClick}
          className="relative h-28 bg-[#090d16] rounded-xl border border-[#1f2937] px-4 flex items-center justify-between gap-[2px] cursor-pointer group hover:border-cyan-500/40 transition-colors overflow-hidden select-none"
          title="Click anywhere to seek audio timestamp"
        >
          {/* Subtle grid background */}
          <div className="absolute inset-0 opacity-10 bg-[linear-gradient(to_right,#1f2937_1px,transparent_1px)] bg-[size:20px_100%] pointer-events-none" />

          {/* 60 Normalized Amplitude Bars */}
          {waveformPeaks.map((peak, idx) => {
            const heightPct = Math.max(12, Math.min(peak * 100, 95));
            const barColor = getBarColor(idx, waveformPeaks.length);
            const isPast =
              totalDuration > 0 &&
              (idx / waveformPeaks.length) * totalDuration <= currentTime;

            return (
              <div
                key={idx}
                className="flex-1 flex flex-col items-center justify-center h-full relative"
              >
                <div
                  style={{
                    height: `${heightPct}%`,
                    backgroundColor: barColor,
                    opacity: isPast ? 1 : 0.45,
                  }}
                  className="w-full max-w-[5px] rounded-full transition-all duration-150 group-hover:opacity-85"
                />
              </div>
            );
          })}

          {/* Synchronized Playhead Line */}
          <div
            style={{ left: `${progressPercent}%` }}
            className="absolute top-0 bottom-0 w-[2px] bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.9)] pointer-events-none transition-all duration-75 z-10"
          >
            <div className="w-2.5 h-2.5 rounded-full bg-cyan-300 absolute -top-1 -left-[4px] border border-cyan-800 shadow-sm" />
          </div>
        </div>

        {/* Player Controls Bar */}
        <div className="flex flex-wrap items-center justify-between gap-4 pt-1">
          {/* Play/Pause & Reset */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={togglePlay}
              className="w-10 h-10 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white flex items-center justify-center shadow-md transition-all cursor-pointer"
            >
              {isPlaying ? (
                <Pause className="w-4 h-4 fill-white" />
              ) : (
                <Play className="w-4 h-4 fill-white ml-0.5" />
              )}
            </button>

            <button
              type="button"
              onClick={() => seekToTime(0)}
              className="p-2 rounded-lg bg-[#090d16] border border-[#1f2937] hover:border-gray-700 text-gray-400 hover:text-white transition-colors cursor-pointer"
              title="Restart"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>

            <button
              type="button"
              onClick={toggleMute}
              className="p-2 rounded-lg bg-[#090d16] border border-[#1f2937] hover:border-gray-700 text-gray-400 hover:text-white transition-colors cursor-pointer"
              title={isMuted ? "Unmute" : "Mute"}
            >
              {isMuted ? (
                <VolumeX className="w-3.5 h-3.5 text-rose-400" />
              ) : (
                <Volume2 className="w-3.5 h-3.5" />
              )}
            </button>

            {/* Time Readout */}
            <div className="flex items-center gap-1 text-xs font-mono text-gray-300 ml-2">
              <span className="text-cyan-400 font-bold">
                {formatSeconds(currentTime)}
              </span>
              <span className="text-gray-600">/</span>
              <span>{formatSeconds(totalDuration)}</span>
            </div>
          </div>

          {/* Color Key Legend */}
          <div className="flex items-center gap-3 text-[10px] font-mono text-gray-400 bg-[#090d16] px-3 py-1.5 rounded-lg border border-[#1f2937]">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span>Natural (&lt;0.35)</span>
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-amber-500" />
              <span>Ambiguous (0.35–0.55)</span>
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-rose-500" />
              <span>Flagged Synthetic (&ge;0.55)</span>
            </span>
          </div>
        </div>
      </div>

      {/* 2-Second Sliding Windows & Whisper Transcript Sections */}
      <div className="p-4 bg-[#0c121e] border-t border-[#1f2937] space-y-4">
        {/* Sliding Windows Chips */}
        {segments.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold text-gray-300 uppercase tracking-wider">
              <span className="flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5 text-cyan-400" />
                <span>2.0s Sliding Window Analysis ({segments.length} intervals)</span>
              </span>
              <span className="text-[10px] font-mono text-gray-500 lowercase">
                Click segment chip to seek playhead
              </span>
            </div>

            <div className="flex flex-wrap gap-2">
              {segments.map((seg, idx) => {
                const isHigh = seg.score >= 0.55;
                const isModerate = seg.score >= 0.35 && seg.score < 0.55;
                const isActive = activeSegmentIndex === idx;

                return (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => seekToTime(seg.start_sec)}
                    className={`px-2.5 py-1.5 rounded-lg border text-xs font-mono transition-all flex items-center gap-2 cursor-pointer ${
                      isActive
                        ? "ring-2 ring-cyan-400 border-cyan-400 bg-cyan-950/80 shadow-md"
                        : isHigh
                        ? "bg-rose-950/40 border-rose-800/60 text-rose-300 hover:bg-rose-900/60"
                        : isModerate
                        ? "bg-amber-950/40 border-amber-800/60 text-amber-300 hover:bg-amber-900/60"
                        : "bg-[#090d16] border-[#1f2937] text-gray-300 hover:bg-gray-800"
                    }`}
                  >
                    <Clock className="w-3 h-3 text-gray-400" />
                    <span>{seg.timestamp_label}</span>
                    <span
                      className={`font-bold text-[10px] px-1.5 py-0.2 rounded ${
                        isHigh
                          ? "bg-rose-900 text-rose-200"
                          : isModerate
                          ? "bg-amber-900 text-amber-200"
                          : "bg-emerald-950 text-emerald-300 border border-emerald-800"
                      }`}
                    >
                      {seg.score.toFixed(2)}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Whisper Transcript Section */}
        <div className="space-y-2 pt-2 border-t border-[#1f2937]">
          <div className="flex items-center justify-between text-xs font-semibold text-gray-300 uppercase tracking-wider">
            <span className="flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-blue-400" />
              <span>Automated Speech Transcript (Groq Whisper)</span>
            </span>
            <span
              className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                transcriptStatus === "completed"
                  ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                  : transcriptStatus === "not_configured"
                  ? "bg-gray-800 text-gray-400"
                  : "bg-amber-950 text-amber-300"
              }`}
            >
              Status: {transcriptStatus.toUpperCase()}
            </span>
          </div>

          {transcriptText ? (
            <div className="bg-[#090d16] border border-[#1f2937] rounded-lg p-3 text-xs leading-relaxed space-y-2">
              <p className="text-gray-200 italic font-sans">"{transcriptText}"</p>

              {/* Clickable timestamp segments if present */}
              {transcriptSegments.length > 0 && (
                <div className="mt-2 pt-2 border-t border-[#1f2937]/70 space-y-1">
                  <span className="text-[10px] font-mono text-gray-400 uppercase tracking-wider block">
                    Interactive Transcript Segments:
                  </span>
                  <div className="space-y-1">
                    {transcriptSegments.map((tSeg, i) => (
                      <div
                        key={i}
                        onClick={() => tSeg.start !== undefined && seekToTime(tSeg.start)}
                        className="text-[11px] p-1.5 rounded hover:bg-gray-800/80 cursor-pointer text-gray-300 flex items-start gap-2 font-mono transition-colors"
                      >
                        <span className="text-cyan-400 shrink-0">
                          [{formatSeconds(tSeg.start || 0)} - {formatSeconds(tSeg.end || 0)}]
                        </span>
                        <span className="font-sans text-gray-200">{tSeg.text}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-[#090d16] border border-[#1f2937] rounded-lg p-3 text-xs font-mono text-gray-500 flex items-center gap-2">
              <Info className="w-3.5 h-3.5 text-gray-500" />
              <span>
                {transcriptStatus === "not_configured"
                  ? "Groq Whisper transcription was skipped (no GROQ_API_KEY detected in backend environment)."
                  : "No spoken audio or speech detected in this media track."}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
