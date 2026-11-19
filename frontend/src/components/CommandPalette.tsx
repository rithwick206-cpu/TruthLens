"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Search,
  FileText,
  PlusCircle,
  Cpu,
  FileDown,
  Sparkles,
  ShieldCheck,
  ShieldAlert,
  ArrowRight,
  Command,
  X,
} from "lucide-react";
import { CaseRecord } from "@/types/forensics";

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  cases: CaseRecord[];
  onSelectCase: (caseId: string) => void;
  onNavigateTab: (tab: "new" | "active" | "insights") => void;
  onLoadDemo: (sampleId: string) => void;
  onExportPdf?: () => void;
  activeCaseId: string | null;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  cases,
  onSelectCase,
  onNavigateTab,
  onLoadDemo,
  onExportPdf,
  activeCaseId,
}) => {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setQuery("");
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Global keyboard listener for Esc and navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  // Build items list
  const q = query.toLowerCase().trim();

  // Navigation & Tool Actions
  const actionItems = [
    {
      id: "action-new",
      type: "action" as const,
      title: "New Investigation Ingestion",
      shortcut: "N",
      category: "Navigation",
      icon: PlusCircle,
      execute: () => {
        onNavigateTab("new");
        onClose();
      },
    },
    {
      id: "action-insights",
      type: "action" as const,
      title: "Model Insights & Architecture Matrix",
      shortcut: "M",
      category: "Navigation",
      icon: Cpu,
      execute: () => {
        onNavigateTab("insights");
        onClose();
      },
    },
    ...(activeCaseId && onExportPdf
      ? [
          {
            id: "action-export",
            type: "action" as const,
            title: `Export Forensic PDF (${activeCaseId})`,
            shortcut: "E",
            category: "Actions",
            icon: FileDown,
            execute: () => {
              onExportPdf();
              onClose();
            },
          },
        ]
      : []),
    {
      id: "demo-multimodal",
      type: "demo" as const,
      title: "Load Demo: Face Swap & Cloned Audio",
      shortcut: "Demo",
      category: "Presets",
      icon: Sparkles,
      execute: () => {
        onLoadDemo("manipulated_multimodal");
        onClose();
      },
    },
    {
      id: "demo-ceo",
      type: "demo" as const,
      title: "Load Demo: CEO Voice Clone Scam",
      shortcut: "Demo",
      category: "Presets",
      icon: Sparkles,
      execute: () => {
        onLoadDemo("cloned_executive_scam");
        onClose();
      },
    },
    {
      id: "demo-authentic",
      type: "demo" as const,
      title: "Load Demo: Authentic DSLR Photo",
      shortcut: "Demo",
      category: "Presets",
      icon: Sparkles,
      execute: () => {
        onLoadDemo("authentic_bundle");
        onClose();
      },
    },
    {
      id: "demo-spliced",
      type: "demo" as const,
      title: "Load Demo: Spliced Audio Testimony",
      shortcut: "Demo",
      category: "Presets",
      icon: Sparkles,
      execute: () => {
        onLoadDemo("spliced_political_testimony");
        onClose();
      },
    },
  ].filter((a) => !q || a.title.toLowerCase().includes(q) || a.category.toLowerCase().includes(q));

  // Matched Case records
  const matchedCases = cases
    .filter((c) => {
      if (!q) return true;
      return (
        c.case_id.toLowerCase().includes(q) ||
        (c.caption_text && c.caption_text.toLowerCase().includes(q)) ||
        (c.result?.overall_risk_band && c.result.overall_risk_band.toLowerCase().includes(q))
      );
    })
    .slice(0, 8);

  const totalItems = actionItems.length + matchedCases.length;

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % (totalItems || 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + (totalItems || 1)) % (totalItems || 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (selectedIndex < actionItems.length) {
        actionItems[selectedIndex]?.execute();
      } else {
        const caseItem = matchedCases[selectedIndex - actionItems.length];
        if (caseItem) {
          onSelectCase(caseItem.case_id);
          onClose();
        }
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-black/70 backdrop-blur-md animate-in fade-in duration-150">
      <div
        className="w-full max-w-2xl bg-[#0d1424] border border-cyan-500/40 rounded-2xl shadow-2xl shadow-cyan-950/60 overflow-hidden flex flex-col font-sans"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Search Bar */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-[#1f2937] bg-[#090e1a]">
          <Search className="w-5 h-5 text-cyan-400 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Type a case ID, claim keywords, demo preset, or action..."
            className="flex-1 bg-transparent border-none text-sm text-gray-100 placeholder-gray-500 focus:outline-none font-sans"
          />
          <div className="flex items-center gap-1.5 text-[10px] font-mono text-gray-400 bg-[#141e34] px-2 py-0.5 rounded border border-[#233355]">
            <Command className="w-3 h-3" />
            <span>ESC to close</span>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white p-1 rounded transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Results Body */}
        <div className="max-h-96 overflow-y-auto p-2 space-y-4 custom-scrollbar">
          {/* Quick Actions & Navigation */}
          {actionItems.length > 0 && (
            <div>
              <div className="px-3 py-1 text-[10px] uppercase font-bold tracking-wider text-cyan-400/80 font-mono">
                Commands & Presets
              </div>
              <div className="space-y-0.5 mt-1">
                {actionItems.map((item, idx) => {
                  const isSelected = selectedIndex === idx;
                  const Icon = item.icon;

                  return (
                    <div
                      key={item.id}
                      onClick={item.execute}
                      onMouseEnter={() => setSelectedIndex(idx)}
                      className={`flex items-center justify-between px-3 py-2 rounded-xl text-xs cursor-pointer transition-all ${
                        isSelected
                          ? "bg-cyan-600/20 text-cyan-200 border border-cyan-500/50 shadow-sm"
                          : "text-gray-300 hover:bg-[#131d33] border border-transparent"
                      }`}
                    >
                      <div className="flex items-center gap-2.5">
                        <div
                          className={`p-1.5 rounded-lg ${
                            isSelected ? "bg-cyan-500/30 text-cyan-300" : "bg-gray-800/80 text-gray-400"
                          }`}
                        >
                          <Icon className="w-3.5 h-3.5" />
                        </div>
                        <span className="font-medium">{item.title}</span>
                      </div>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#101a2e] text-gray-400 border border-[#1f2937]">
                        {item.shortcut}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Evidence Vault Cases */}
          {matchedCases.length > 0 && (
            <div>
              <div className="px-3 py-1 text-[10px] uppercase font-bold tracking-wider text-gray-400 font-mono flex items-center justify-between">
                <span>Evidence Vault ({matchedCases.length})</span>
                <span className="text-[9px] font-normal lowercase">press Enter to inspect</span>
              </div>
              <div className="space-y-0.5 mt-1">
                {matchedCases.map((c, idx) => {
                  const globalIdx = actionItems.length + idx;
                  const isSelected = selectedIndex === globalIdx;
                  const risk = c.result?.overall_risk_band?.toLowerCase() || "";
                  const isHigh = risk.includes("high");
                  const isLow = risk.includes("low");

                  return (
                    <div
                      key={c.case_id}
                      onClick={() => {
                        onSelectCase(c.case_id);
                        onClose();
                      }}
                      onMouseEnter={() => setSelectedIndex(globalIdx)}
                      className={`flex items-center justify-between px-3 py-2 rounded-xl text-xs cursor-pointer transition-all ${
                        isSelected
                          ? "bg-cyan-600/20 text-cyan-200 border border-cyan-500/50 shadow-sm"
                          : "text-gray-300 hover:bg-[#131d33] border border-transparent"
                      }`}
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <FileText className="w-4 h-4 text-gray-400 shrink-0" />
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-mono font-semibold text-gray-200">
                              {c.case_id}
                            </span>
                            {c.caption_text && (
                              <span className="text-[11px] text-gray-400 truncate max-w-xs">
                                "{c.caption_text}"
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        {isHigh ? (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-rose-950/70 text-rose-300 border border-rose-800/60 flex items-center gap-1">
                            <ShieldAlert className="w-2.5 h-2.5" /> High Risk
                          </span>
                        ) : isLow ? (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950/70 text-emerald-300 border border-emerald-800/60 flex items-center gap-1">
                            <ShieldCheck className="w-2.5 h-2.5" /> Authentic
                          </span>
                        ) : (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-950/70 text-amber-300 border border-amber-800/60">
                            Review
                          </span>
                        )}
                        <ArrowRight className="w-3.5 h-3.5 text-gray-500" />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {totalItems === 0 && (
            <div className="p-8 text-center text-gray-500 text-xs">
              No matching commands, presets, or evidence records found for "{query}".
            </div>
          )}
        </div>

        {/* Footer Shortcut Bar */}
        <div className="px-4 py-2 bg-[#080d17] border-t border-[#1f2937] flex items-center justify-between text-[11px] text-gray-400 font-mono">
          <div className="flex items-center gap-3">
            <span>↑↓ Navigate</span>
            <span>↵ Select</span>
            <span>ESC Close</span>
          </div>
          <span className="text-cyan-400">TRUTHLENS PALETTE</span>
        </div>
      </div>
    </div>
  );
};
