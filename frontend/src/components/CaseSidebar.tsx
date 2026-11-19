"use client";

import React, { useState } from "react";
import {
  FolderArchive,
  PlusCircle,
  RefreshCw,
  Search,
  Image as ImageIcon,
  Video,
  Mic,
  FileText,
  Clock,
  ShieldCheck,
  ShieldAlert,
  HelpCircle,
  CheckCircle,
  Copy,
  Check,
} from "lucide-react";
import { CaseRecord, RiskBand } from "@/types/forensics";

interface CaseSidebarProps {
  cases: CaseRecord[];
  activeCaseId: string | null;
  onSelectCase: (caseId: string) => void;
  onNewCase: () => void;
  onRefresh: () => void;
  isLoading: boolean;
}

export const CaseSidebar: React.FC<CaseSidebarProps> = ({
  cases,
  activeCaseId,
  onSelectCase,
  onNewCase,
  onRefresh,
  isLoading,
}) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [filterRisk, setFilterRisk] = useState<"all" | "high" | "moderate" | "low" | "audited">("all");
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const counts = {
    all: cases.length,
    high: cases.filter((c) => c.result?.overall_risk_band?.toLowerCase().includes("high")).length,
    moderate: cases.filter((c) => c.result?.overall_risk_band?.toLowerCase().includes("moderate")).length,
    low: cases.filter((c) => c.result?.overall_risk_band?.toLowerCase().includes("low")).length,
    audited: cases.filter((c) => c.review_status && c.review_status !== "needs_review").length,
  };

  const filteredCases = cases.filter((c) => {
    // Risk tier filter
    if (filterRisk === "high") {
      if (!c.result?.overall_risk_band?.toLowerCase().includes("high")) return false;
    } else if (filterRisk === "moderate") {
      if (!c.result?.overall_risk_band?.toLowerCase().includes("moderate")) return false;
    } else if (filterRisk === "low") {
      if (!c.result?.overall_risk_band?.toLowerCase().includes("low")) return false;
    } else if (filterRisk === "audited") {
      if (!c.review_status || c.review_status === "needs_review") return false;
    }

    const query = searchQuery.toLowerCase().trim();
    if (!query) return true;
    return (
      c.case_id.toLowerCase().includes(query) ||
      (c.caption_text && c.caption_text.toLowerCase().includes(query)) ||
      c.status.toLowerCase().includes(query) ||
      (c.result?.overall_risk_band && c.result.overall_risk_band.toLowerCase().includes(query))
    );
  });

  const handleCopyCaseId = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  const getRiskBadge = (risk?: RiskBand | string | null) => {
    if (!risk) {
      return (
        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-gray-800 text-gray-400 border border-gray-700">
          PENDING
        </span>
      );
    }
    const r = risk.toLowerCase();
    if (r.includes("low")) {
      return (
        <span className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-500/40 flex items-center gap-1">
          <ShieldCheck className="w-2.5 h-2.5" /> LOW
        </span>
      );
    }
    if (r.includes("moderate")) {
      return (
        <span className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded bg-amber-950/80 text-amber-400 border border-amber-500/40 flex items-center gap-1">
          <ShieldAlert className="w-2.5 h-2.5" /> MODERATE
        </span>
      );
    }
    if (r.includes("high")) {
      return (
        <span className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded bg-rose-950/80 text-rose-400 border border-rose-500/40 flex items-center gap-1">
          <ShieldAlert className="w-2.5 h-2.5" /> HIGH
        </span>
      );
    }
    return (
      <span className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-700 flex items-center gap-1">
        <HelpCircle className="w-2.5 h-2.5" /> REVIEW
      </span>
    );
  };

  const getMediaBadges = (files: CaseRecord["files"], caption?: string | null) => {
    const hasImg = files?.some((f) => f.media_type === "image");
    const hasVid = files?.some((f) => f.media_type === "video");
    const hasAud = files?.some((f) => f.media_type === "audio");
    const hasTxt = !!caption;

    return (
      <div className="flex items-center gap-1">
        {hasImg && (
          <span className="p-0.5 rounded bg-cyan-950/60 text-cyan-400 border border-cyan-800/40" title="Image evidence">
            <ImageIcon className="w-2.5 h-2.5" />
          </span>
        )}
        {hasVid && (
          <span className="p-0.5 rounded bg-purple-950/60 text-purple-400 border border-purple-800/40" title="Video evidence">
            <Video className="w-2.5 h-2.5" />
          </span>
        )}
        {hasAud && (
          <span className="p-0.5 rounded bg-blue-950/60 text-blue-400 border border-blue-800/40" title="Audio evidence">
            <Mic className="w-2.5 h-2.5" />
          </span>
        )}
        {hasTxt && (
          <span className="p-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/40" title="Accompanying context claim">
            <FileText className="w-2.5 h-2.5" />
          </span>
        )}
      </div>
    );
  };

  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return isoString;
    }
  };

  return (
    <aside className="w-full md:w-80 flex flex-col bg-[#0c121e] border-r border-[#1f2937] h-[calc(100vh-61px)] sticky top-[61px] overflow-hidden">
      {/* Sidebar Header */}
      <div className="p-3 border-b border-[#1f2937] flex flex-col gap-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FolderArchive className="w-4 h-4 text-cyan-400" />
            <h2 className="text-xs font-bold tracking-wider text-gray-200 uppercase">
              Evidence Vault
            </h2>
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-gray-800 text-gray-400">
              {cases.length}
            </span>
          </div>
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="p-1 rounded text-gray-400 hover:text-gray-200 hover:bg-gray-800 transition-colors"
            title="Refresh cases from API"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-cyan-400" : ""}`} />
          </button>
        </div>

        {/* Action: + New Case Button */}
        <button
          onClick={onNewCase}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-gradient-to-r from-cyan-600 to-cyan-700 hover:from-cyan-500 hover:to-cyan-600 text-white font-medium text-xs rounded-lg shadow-sm shadow-cyan-900/40 transition-all border border-cyan-400/30 cursor-pointer"
        >
          <PlusCircle className="w-4 h-4" />
          <span>New Forensic Case</span>
        </button>

        {/* Filter Input */}
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-gray-500 absolute left-2.5 top-2.5" />
          <input
            type="text"
            placeholder="Search by Case ID, claim, risk..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#090d16] border border-[#1f2937] rounded-md pl-8 pr-2 py-1.5 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500/60 font-sans"
          />
        </div>

        {/* Risk Filter Pills */}
        <div className="flex items-center gap-1 overflow-x-auto pb-0.5 scrollbar-none text-[10px] font-mono">
          <button
            type="button"
            onClick={() => setFilterRisk("all")}
            className={`px-2 py-0.5 rounded transition-all cursor-pointer whitespace-nowrap ${
              filterRisk === "all"
                ? "bg-cyan-950 text-cyan-300 border border-cyan-700/60 font-semibold"
                : "bg-[#090d16] text-gray-400 hover:text-gray-200 border border-transparent"
            }`}
          >
            All ({counts.all})
          </button>
          <button
            type="button"
            onClick={() => setFilterRisk("high")}
            className={`px-2 py-0.5 rounded transition-all cursor-pointer whitespace-nowrap ${
              filterRisk === "high"
                ? "bg-rose-950 text-rose-300 border border-rose-700/60 font-semibold"
                : "bg-[#090d16] text-gray-400 hover:text-rose-400 border border-transparent"
            }`}
          >
            🔴 High ({counts.high})
          </button>
          <button
            type="button"
            onClick={() => setFilterRisk("moderate")}
            className={`px-2 py-0.5 rounded transition-all cursor-pointer whitespace-nowrap ${
              filterRisk === "moderate"
                ? "bg-amber-950 text-amber-300 border border-amber-700/60 font-semibold"
                : "bg-[#090d16] text-gray-400 hover:text-amber-400 border border-transparent"
            }`}
          >
            🟡 Mod ({counts.moderate})
          </button>
          <button
            type="button"
            onClick={() => setFilterRisk("low")}
            className={`px-2 py-0.5 rounded transition-all cursor-pointer whitespace-nowrap ${
              filterRisk === "low"
                ? "bg-emerald-950 text-emerald-300 border border-emerald-700/60 font-semibold"
                : "bg-[#090d16] text-gray-400 hover:text-emerald-400 border border-transparent"
            }`}
          >
            🟢 Low ({counts.low})
          </button>
          <button
            type="button"
            onClick={() => setFilterRisk("audited")}
            className={`px-2 py-0.5 rounded transition-all cursor-pointer whitespace-nowrap ${
              filterRisk === "audited"
                ? "bg-purple-950 text-purple-300 border border-purple-700/60 font-semibold"
                : "bg-[#090d16] text-gray-400 hover:text-purple-400 border border-transparent"
            }`}
          >
            ✓ Signed ({counts.audited})
          </button>
        </div>
      </div>

      {/* Case List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1.5 custom-scrollbar">
        {filteredCases.length === 0 ? (
          <div className="text-center py-10 px-4 text-gray-500">
            <FolderArchive className="w-8 h-8 mx-auto mb-2 text-gray-600 opacity-60" />
            <p className="text-xs">No forensic cases found.</p>
            <p className="text-[10px] text-gray-600 mt-1">
              Start an investigation or load a pre-built demo case above.
            </p>
          </div>
        ) : (
          filteredCases.map((c) => {
            const isSelected = c.case_id === activeCaseId;
            const risk = c.result?.overall_risk_band || null;
            const confidence = c.result?.calibrated_confidence;

            return (
              <div
                key={c.case_id}
                onClick={() => onSelectCase(c.case_id)}
                className={`p-2.5 rounded-lg border transition-all cursor-pointer text-left ${
                  isSelected
                    ? "bg-cyan-950/30 border-cyan-500/60 shadow-[0_0_12px_rgba(6,182,212,0.15)] ring-1 ring-cyan-500/40"
                    : "bg-[#111827]/80 border-[#1f2937] hover:border-gray-700 hover:bg-[#111827]"
                }`}
              >
                {/* Header row: ID & Risk */}
                <div className="flex items-center justify-between gap-1 mb-1">
                  <div className="flex items-center gap-1.5 truncate">
                    <span
                      className={`text-[11px] font-mono tracking-tight font-semibold truncate ${
                        isSelected ? "text-cyan-300" : "text-gray-300"
                      }`}
                    >
                      {c.case_id}
                    </span>
                    <button
                      type="button"
                      onClick={(e) => handleCopyCaseId(e, c.case_id)}
                      className="text-gray-500 hover:text-cyan-400 p-0.5 rounded transition-colors"
                      title="Copy Case ID"
                    >
                      {copiedId === c.case_id ? (
                        <Check className="w-3 h-3 text-emerald-400" />
                      ) : (
                        <Copy className="w-3 h-3" />
                      )}
                    </button>
                  </div>
                  {getRiskBadge(risk)}
                </div>

                {/* Caption / description preview */}
                {c.caption_text && (
                  <p className="text-[11px] text-gray-400 line-clamp-1 italic mb-1.5">
                    "{c.caption_text}"
                  </p>
                )}

                {/* Footer row: Modality badges + Time + Review Status */}
                <div className="flex items-center justify-between pt-1 border-t border-[#1f2937]/60 text-[10px] text-gray-500">
                  <div className="flex items-center gap-1.5">
                    {getMediaBadges(c.files, c.caption_text)}
                    {confidence !== undefined && (
                      <span className="font-mono text-gray-400 font-semibold">
                        {(confidence * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-1">
                    <Clock className="w-2.5 h-2.5" />
                    <span>{formatDate(c.created_at)}</span>
                  </div>
                </div>

                {/* Review status indicator if marked */}
                {c.review_status && c.review_status !== "needs_review" && (
                  <div className="mt-1 flex items-center gap-1 text-[9px] font-mono text-cyan-400">
                    <CheckCircle className="w-2.5 h-2.5" />
                    <span>Audit: {c.review_status.replace("_", " ")}</span>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
};
