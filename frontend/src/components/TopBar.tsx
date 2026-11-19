"use client";

import React, { useEffect, useState } from "react";
import { ShieldCheck, ShieldAlert, Sparkles, RefreshCw, Cpu, FileText, Search } from "lucide-react";
import { DemoSample } from "@/types/forensics";
import { checkHealth, listDemoSamples } from "@/lib/api";

interface TopBarProps {
  activeTab: "new" | "active" | "insights";
  setActiveTab: (tab: "new" | "active" | "insights") => void;
  onLoadDemo: (sampleId: string) => Promise<void>;
  isLoadingDemo: boolean;
  activeCaseId: string | null;
  onOpenPalette?: () => void;
  onOpenConfig?: () => void;
}

const DEMO_CONFIG: Record<
  string,
  { label: string; style: string; dotColor: string }
> = {
  authentic_bundle: {
    label: "Authentic Photo",
    style: "bg-emerald-950/40 hover:bg-emerald-950/70 text-emerald-400 border-emerald-800/50",
    dotColor: "bg-emerald-400",
  },
  manipulated_multimodal: {
    label: "Multimodal Fake",
    style: "bg-rose-950/40 hover:bg-rose-950/70 text-rose-400 border-rose-800/50",
    dotColor: "bg-rose-400",
  },
  compressed_real_photo: {
    label: "Compressed Photo",
    style: "bg-amber-950/40 hover:bg-amber-950/70 text-amber-400 border-amber-800/50",
    dotColor: "bg-amber-400",
  },
  cloned_executive_scam: {
    label: "CEO Voice Clone",
    style: "bg-rose-950/40 hover:bg-rose-950/70 text-rose-400 border-rose-800/50",
    dotColor: "bg-rose-400",
  },
  spliced_political_testimony: {
    label: "Spliced Audio",
    style: "bg-purple-950/40 hover:bg-purple-950/70 text-purple-300 border-purple-800/50",
    dotColor: "bg-purple-400",
  },
  telecom_robocall_scam: {
    label: "Robocall Scam",
    style: "bg-rose-950/40 hover:bg-rose-950/70 text-rose-400 border-rose-800/50",
    dotColor: "bg-rose-400",
  },
  authentic_broadcast_speech: {
    label: "Clean Speech",
    style: "bg-emerald-950/40 hover:bg-emerald-950/70 text-emerald-400 border-emerald-800/50",
    dotColor: "bg-emerald-400",
  },
};

export const TopBar: React.FC<TopBarProps> = ({
  activeTab,
  setActiveTab,
  onLoadDemo,
  isLoadingDemo,
  activeCaseId,
  onOpenPalette,
  onOpenConfig,
}) => {
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [demoSamples, setDemoSamples] = useState<DemoSample[]>([]);
  const [loadingSamples, setLoadingSamples] = useState(false);
  const [selectedDemo, setSelectedDemo] = useState<string | null>(null);

  useEffect(() => {
    checkHealth()
      .then(() => setBackendOnline(true))
      .catch(() => setBackendOnline(false));

    setLoadingSamples(true);
    listDemoSamples()
      .then((data) => setDemoSamples(data))
      .catch(() => setDemoSamples([]))
      .finally(() => setLoadingSamples(false));
  }, []);

  const handleDemoClick = async (sampleId: string) => {
    setSelectedDemo(sampleId);
    try {
      await onLoadDemo(sampleId);
    } finally {
      setSelectedDemo(null);
    }
  };

  return (
    <header className="w-full bg-[#111827] border-b border-[#1f2937] px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 sticky top-0 z-40">
      {/* Brand & Health Indicator */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-cyan-950 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-base text-gray-100 tracking-tight">TRUTHLENS</span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-950/80 text-cyan-400 border border-cyan-800/40">
                FORENSICS LAB
              </span>
            </div>
            <p className="text-[10px] text-gray-400 tracking-wide font-sans">
              Multimodal Deepfake & Authentication Suite
            </p>
          </div>
        </div>

        {/* Backend Status Dot (Clickable) */}
        <button
          type="button"
          onClick={onOpenConfig}
          className="hidden sm:flex items-center gap-1.5 ml-3 pl-3 border-l border-gray-800 text-[11px] font-mono hover:text-white transition-colors cursor-pointer group"
          title="Click to configure Backend API endpoint"
        >
          <span
            className={`w-2 h-2 rounded-full ${
              backendOnline === true
                ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"
                : backendOnline === false
                ? "bg-rose-500 animate-pulse"
                : "bg-amber-400 animate-pulse"
            }`}
          />
          <span className="text-gray-400 group-hover:text-gray-200">
            {backendOnline === true
              ? "FastAPI Online"
              : backendOnline === false
              ? "API Offline"
              : "Connecting..."}
          </span>
        </button>
      </div>

      {/* Navigation Switcher */}
      <div className="flex items-center gap-1 bg-[#090d16] p-1 rounded-lg border border-[#1f2937]">
        <button
          onClick={() => setActiveTab("new")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
            activeTab === "new"
              ? "bg-cyan-600/20 text-cyan-300 border border-cyan-500/40 shadow-sm"
              : "text-gray-400 hover:text-gray-200 hover:bg-[#111827]"
          }`}
        >
          <Search className="w-3.5 h-3.5" />
          New Investigation
        </button>

        <button
          onClick={() => setActiveTab("active")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
            activeTab === "active"
              ? "bg-cyan-600/20 text-cyan-300 border border-cyan-500/40 shadow-sm"
              : "text-gray-400 hover:text-gray-200 hover:bg-[#111827]"
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          Active Case {activeCaseId ? `(${activeCaseId})` : ""}
        </button>

        <button
          onClick={() => setActiveTab("insights")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
            activeTab === "insights"
              ? "bg-cyan-600/20 text-cyan-300 border border-cyan-500/40 shadow-sm"
              : "text-gray-400 hover:text-gray-200 hover:bg-[#111827]"
          }`}
        >
          <Cpu className="w-3.5 h-3.5" />
          Model Insights
        </button>
      </div>

      {/* Quick Search & Command Palette Pill */}
      {onOpenPalette && (
        <button
          type="button"
          onClick={onOpenPalette}
          className="hidden lg:flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-[#090d16] hover:bg-[#131d33] border border-[#1f2937] hover:border-cyan-500/50 text-gray-400 hover:text-gray-200 text-xs transition-all shadow-inner group cursor-pointer"
          title="Open Command Palette (⌘K)"
        >
          <Search className="w-3.5 h-3.5 text-cyan-400 group-hover:scale-110 transition-transform" />
          <span className="font-sans text-[11px]">Command Palette</span>
          <kbd className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#111827] text-gray-400 border border-[#1f2937] group-hover:text-cyan-300">
            ⌘K
          </kbd>
        </button>
      )}

      {/* Load Sample Case Bar */}
      <div className="flex items-center gap-2 overflow-x-auto max-w-full py-0.5 scrollbar-thin">
        <span className="text-[11px] text-gray-400 font-mono hidden xl:inline-flex items-center gap-1 shrink-0">
          <Sparkles className="w-3 h-3 text-cyan-400" /> Demo Bundles:
        </span>
        <div className="flex items-center gap-1.5 flex-nowrap">
          {demoSamples.map((sample) => {
            const isLoadingThis = isLoadingDemo && selectedDemo === sample.sample_id;
            const config = DEMO_CONFIG[sample.sample_id] || {
              label: sample.title || sample.sample_id,
              style: "bg-gray-800 hover:bg-gray-700 text-gray-300 border-gray-700",
              dotColor: "bg-gray-400",
            };

            return (
              <button
                key={sample.sample_id}
                onClick={() => handleDemoClick(sample.sample_id)}
                disabled={isLoadingDemo}
                title={sample.description}
                className={`text-[11px] font-mono px-2 py-0.5 rounded border transition-all flex items-center gap-1.5 shrink-0 whitespace-nowrap ${
                  isLoadingThis
                    ? "bg-gray-800 text-gray-300 border-gray-600"
                    : config.style
                }`}
              >
                {isLoadingThis ? (
                  <RefreshCw className="w-3 h-3 animate-spin" />
                ) : (
                  <span className={`w-1.5 h-1.5 rounded-full ${config.dotColor}`} />
                )}
                {config.label}
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
};
