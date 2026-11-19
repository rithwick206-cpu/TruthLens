"use client";

import React, { useState } from "react";
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  GitMerge,
  FileCheck,
  CheckSquare,
  Square,
  HelpCircle,
  Info,
  Layers,
} from "lucide-react";
import { CrossModalResult, RiskBand } from "@/types/forensics";

interface ConfidenceAndUncertaintyProps {
  calibratedConfidence: number; // 0.0 to 1.0
  overallRiskBand: RiskBand | string;
  crossModalCorrelation?: CrossModalResult | null;
  limitationsAndCaveats?: string[];
  alternativeExplanations?: string[];
  recommendedHumanChecks?: string[];
  executiveSummary?: string;
}

export const ConfidenceAndUncertainty: React.FC<ConfidenceAndUncertaintyProps> = ({
  calibratedConfidence,
  overallRiskBand,
  crossModalCorrelation,
  limitationsAndCaveats = [],
  alternativeExplanations = [],
  recommendedHumanChecks = [],
  executiveSummary,
}) => {
  // Client-side checklist state for human verification
  const [checkedItems, setCheckedItems] = useState<Record<number, boolean>>({});

  const toggleCheck = (index: number) => {
    setCheckedItems((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  };

  const clampedScore = Math.max(0, Math.min(calibratedConfidence, 1));
  const scorePercent = (clampedScore * 100).toFixed(1);

  // Gauge calculations (Semi-circle radius = 80, arc length = pi * 80 ~= 251.33)
  const arcLength = 251.33;
  const strokeDashoffset = arcLength * (1 - clampedScore);

  const isLow = clampedScore < 0.35;
  const isModerate = clampedScore >= 0.35 && clampedScore <= 0.65;
  const isHigh = clampedScore > 0.65;

  const gaugeColor = isLow ? "#10b981" : isModerate ? "#f59e0b" : "#f43f5e";

  const getStatusBadge = (status?: string) => {
    const s = (status || "inconclusive").toLowerCase();
    if (s === "reinforcing") {
      return (
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800 font-bold uppercase">
          Reinforcing Manipulation Evidence
        </span>
      );
    }
    if (s === "contradictory") {
      return (
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800 font-bold uppercase">
          Contradictory Signals Detected
        </span>
      );
    }
    if (s === "single_modality") {
      return (
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800 font-bold uppercase">
          Single Modality Scored
        </span>
      );
    }
    return (
      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-gray-800 text-gray-300 border border-gray-700 font-bold uppercase">
        Inconclusive / Mixed Modalities
      </span>
    );
  };

  return (
    <div className="space-y-4">
      {/* Top Row: Gauge + Executive Summary + Cross-Modal Coherence */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
        {/* Semi-Circular Calibrated Gauge Card */}
        <div className="md:col-span-4 bg-[#111827] border border-[#1f2937] rounded-xl p-5 shadow-lg flex flex-col items-center justify-between text-center relative overflow-hidden">
          <div className="w-full flex items-center justify-between border-b border-[#1f2937] pb-2 mb-2">
            <span className="text-xs font-bold text-gray-200 uppercase tracking-wider">
              Calibrated Confidence
            </span>
            <span className="text-[10px] font-mono text-cyan-400">
              Ensemble T-Scaled
            </span>
          </div>

          {/* SVG Semi-Circle Gauge */}
          <div className="relative w-48 h-28 my-1 flex items-center justify-center">
            <svg
              viewBox="0 0 200 110"
              className="w-full h-full overflow-visible"
            >
              {/* Background Arc */}
              <path
                d="M 20 100 A 80 80 0 0 1 180 100"
                fill="none"
                stroke="#1f2937"
                strokeWidth="16"
                strokeLinecap="round"
              />
              {/* Animated Foreground Arc */}
              <path
                d="M 20 100 A 80 80 0 0 1 180 100"
                fill="none"
                stroke={gaugeColor}
                strokeWidth="16"
                strokeLinecap="round"
                strokeDasharray={arcLength}
                strokeDashoffset={strokeDashoffset}
                className="transition-all duration-700 ease-out"
              />
            </svg>

            {/* Score & Risk Label in center */}
            <div className="absolute bottom-0 flex flex-col items-center">
              <span
                style={{ color: gaugeColor }}
                className="text-3xl font-extrabold font-mono tracking-tight"
              >
                {scorePercent}%
              </span>
              <span className="text-[10px] font-mono text-gray-400 uppercase tracking-wider font-semibold">
                {isLow ? "Low Likelihood" : isModerate ? "Ambiguous" : "High Likelihood"}
              </span>
            </div>
          </div>

          {/* Risk Band Badge */}
          <div className="w-full mt-2 pt-2 border-t border-[#1f2937] space-y-2">
            <div
              className={`text-xs font-mono font-bold px-2.5 py-1 rounded-md border flex items-center justify-center gap-1.5 ${
                isLow
                  ? "bg-emerald-950/80 text-emerald-300 border-emerald-500/50"
                  : isModerate
                  ? "bg-amber-950/80 text-amber-300 border-amber-500/50"
                  : "bg-rose-950/80 text-rose-300 border-rose-500/50"
              }`}
            >
              {isLow ? (
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
              ) : (
                <ShieldAlert className="w-4 h-4 text-amber-400" />
              )}
              <span>{overallRiskBand}</span>
            </div>

            {/* Mandatory Probabilistic Disclaimer Badge */}
            <p className="text-[10px] font-mono text-amber-300/80 bg-amber-950/30 border border-amber-900/40 p-1.5 rounded">
              Probabilistic Indicator — Not Absolute Proof
            </p>
          </div>
        </div>

        {/* Executive Summary & Cross-Modal Correlation Card */}
        <div className="md:col-span-8 bg-[#111827] border border-[#1f2937] rounded-xl p-5 shadow-lg flex flex-col justify-between space-y-4">
          {/* Executive Summary Callout */}
          <div className="space-y-2">
            <div className="flex items-center justify-between border-b border-[#1f2937] pb-2">
              <span className="text-xs font-bold text-gray-200 uppercase tracking-wider flex items-center gap-2">
                <FileCheck className="w-4 h-4 text-cyan-400" />
                <span>Forensic Executive Summary</span>
              </span>
              <span className="text-[10px] font-mono text-gray-400">
                AI + Deterministic Correlator
              </span>
            </div>
            <p className="text-xs text-gray-300 leading-relaxed bg-[#090d16] p-3 rounded-lg border border-[#1f2937]">
              {executiveSummary ||
                "Multimodal evidence analyzed across spatial convolutional heads, acoustic spectrograms, and contextual claims."}
            </p>
          </div>

          {/* Cross-Modal Correlation Card */}
          <div className="bg-[#0c121e] border border-[#1f2937] rounded-lg p-3.5 space-y-2.5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-xs font-semibold text-gray-200">
                <GitMerge className="w-4 h-4 text-purple-400" />
                <span>Cross-Modal Coherence & Semantic Agreement</span>
              </div>
              {getStatusBadge(crossModalCorrelation?.status)}
            </div>

            <p className="text-[11px] text-gray-300 leading-snug">
              {crossModalCorrelation?.summary ||
                "Evidence modalities analyzed in parallel without contradictory indicators."}
            </p>

            {/* Bulleted Details */}
            {crossModalCorrelation?.details &&
              crossModalCorrelation.details.length > 0 && (
                <div className="space-y-1 pt-1 border-t border-[#1f2937]/70">
                  {crossModalCorrelation.details.map((det, i) => (
                    <div
                      key={i}
                      className="text-[10px] font-mono text-gray-400 flex items-start gap-1.5"
                    >
                      <span className="text-cyan-400">•</span>
                      <span>{det}</span>
                    </div>
                  ))}
                </div>
              )}
          </div>
        </div>
      </div>

      {/* Three-Column Forensic Integrity Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Column 1: Limitations & Caveats */}
        <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-4 space-y-2.5 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 pb-2 border-b border-[#1f2937]">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <h4 className="text-xs font-bold text-gray-200 uppercase tracking-wider">
                Limitations & Caveats
              </h4>
            </div>

            <div className="space-y-2 mt-2.5 max-h-56 overflow-y-auto custom-scrollbar pr-1">
              {limitationsAndCaveats.length > 0 ? (
                limitationsAndCaveats.map((lim, idx) => (
                  <div
                    key={idx}
                    className="text-[11px] text-gray-300 bg-[#090d16] p-2 rounded-lg border border-[#1f2937] leading-snug"
                  >
                    • {lim}
                  </div>
                ))
              ) : (
                <p className="text-xs text-gray-500 italic">No explicit limitations noted.</p>
              )}
            </div>
          </div>
          <span className="text-[9px] font-mono text-gray-500 pt-2 border-t border-[#1f2937]">
            Systemic boundary disclosures
          </span>
        </div>

        {/* Column 2: Plausible Alternative Explanations */}
        <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-4 space-y-2.5 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 pb-2 border-b border-[#1f2937]">
              <HelpCircle className="w-4 h-4 text-cyan-400" />
              <h4 className="text-xs font-bold text-gray-200 uppercase tracking-wider">
                Alternative Explanations
              </h4>
            </div>

            <div className="space-y-2 mt-2.5 max-h-56 overflow-y-auto custom-scrollbar pr-1">
              {alternativeExplanations.length > 0 ? (
                alternativeExplanations.map((alt, idx) => (
                  <div
                    key={idx}
                    className="text-[11px] text-cyan-200/90 bg-[#090d16] p-2 rounded-lg border border-[#1f2937] leading-snug"
                  >
                    • {alt}
                  </div>
                ))
              ) : (
                <p className="text-xs text-gray-500 italic">
                  No benign non-manipulation alternatives found.
                </p>
              )}
            </div>
          </div>
          <span className="text-[9px] font-mono text-gray-500 pt-2 border-t border-[#1f2937]">
            Benign causes for anomalies
          </span>
        </div>

        {/* Column 3: Recommended Human Checks (Interactive Checklist) */}
        <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-4 space-y-2.5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-[#1f2937]">
              <div className="flex items-center gap-2">
                <CheckSquare className="w-4 h-4 text-emerald-400" />
                <h4 className="text-xs font-bold text-gray-200 uppercase tracking-wider">
                  Human Verification Checklist
                </h4>
              </div>
              <span className="text-[10px] font-mono text-gray-500">
                {Object.values(checkedItems).filter(Boolean).length}/
                {recommendedHumanChecks.length} Done
              </span>
            </div>

            <div className="space-y-2 mt-2.5 max-h-56 overflow-y-auto custom-scrollbar pr-1">
              {recommendedHumanChecks.length > 0 ? (
                recommendedHumanChecks.map((chk, idx) => {
                  const isChecked = !!checkedItems[idx];

                  return (
                    <div
                      key={idx}
                      onClick={() => toggleCheck(idx)}
                      className={`text-[11px] p-2 rounded-lg border flex items-start gap-2 cursor-pointer transition-colors leading-snug ${
                        isChecked
                          ? "bg-emerald-950/40 border-emerald-800/60 text-emerald-300 line-through opacity-80"
                          : "bg-[#090d16] border-[#1f2937] text-gray-300 hover:border-gray-700"
                      }`}
                    >
                      <button
                        type="button"
                        className="mt-0.5 text-cyan-400 shrink-0"
                        title={isChecked ? "Uncheck" : "Mark verified"}
                      >
                        {isChecked ? (
                          <CheckSquare className="w-3.5 h-3.5 text-emerald-400" />
                        ) : (
                          <Square className="w-3.5 h-3.5 text-gray-500" />
                        )}
                      </button>
                      <span className="font-sans">{chk}</span>
                    </div>
                  );
                })
              ) : (
                <p className="text-xs text-gray-500 italic">No pending checks recommended.</p>
              )}
            </div>
          </div>
          <span className="text-[9px] font-mono text-gray-500 pt-2 border-t border-[#1f2937]">
            Examiner verification protocol
          </span>
        </div>
      </div>
    </div>
  );
};
