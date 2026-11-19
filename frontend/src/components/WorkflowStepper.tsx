"use client";

import React from "react";
import { FileUp, Cpu, GitMerge, UserCheck, FileText, CheckCircle2 } from "lucide-react";

interface WorkflowStepperProps {
  currentStep: number; // 1 to 5
  caseStatus?: string; // "ingested" | "analyzing" | "analyzed"
  onStepClick?: (step: number) => void;
}

interface StepItem {
  id: number;
  label: string;
  tag: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
}

const STEPS: StepItem[] = [
  {
    id: 1,
    label: "Ingest & Trace",
    tag: "SHA-256",
    description: "Multimodal capture & tamper-proof hashing",
    icon: FileUp,
  },
  {
    id: 2,
    label: "Forensics Engine",
    tag: "ML & Signal",
    description: "EfficientNet-B0, ELA, Grad-CAM & Wav2Vec2",
    icon: Cpu,
  },
  {
    id: 3,
    label: "Correlator",
    tag: "Gemini VQA",
    description: "Cross-modal coherence & calibrated risk",
    icon: GitMerge,
  },
  {
    id: 4,
    label: "Human Review",
    tag: "Audit Trail",
    description: "Examiner sign-off & determination",
    icon: UserCheck,
  },
  {
    id: 5,
    label: "Forensic Report",
    tag: "PDF Export",
    description: "Court-ready cryptographic documentation",
    icon: FileText,
  },
];

export const WorkflowStepper: React.FC<WorkflowStepperProps> = ({
  currentStep,
  caseStatus,
  onStepClick,
}) => {
  return (
    <div className="w-full bg-[#111827] border border-[#1f2937] rounded-xl p-4 shadow-lg">
      <div className="flex items-center justify-between mb-3 px-1">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.7)]" />
          <h3 className="text-xs font-semibold text-gray-200 tracking-wider uppercase">
            Forensic Investigation Pipeline
          </h3>
        </div>
        {caseStatus && (
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-[#090d16] border border-[#1f2937] text-gray-400">
            Pipeline Status:{" "}
            <span
              className={
                caseStatus === "analyzed"
                  ? "text-emerald-400 font-semibold"
                  : caseStatus === "analyzing"
                  ? "text-cyan-400 animate-pulse font-semibold"
                  : "text-amber-400 font-semibold"
              }
            >
              {caseStatus.toUpperCase()}
            </span>
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-2 relative">
        {STEPS.map((step) => {
          const Icon = step.icon;
          const isDone = currentStep > step.id;
          const isActive = currentStep === step.id;
          const isUpcoming = currentStep < step.id;

          return (
            <div
              key={step.id}
              onClick={() => onStepClick && onStepClick(step.id)}
              className={`flex flex-col p-3 rounded-lg border transition-all text-left ${
                isActive
                  ? "bg-cyan-950/30 border-cyan-500/60 shadow-[0_0_15px_rgba(6,182,212,0.15)] ring-1 ring-cyan-500/30"
                  : isDone
                  ? "bg-[#0c121e] border-emerald-500/30 text-gray-300"
                  : "bg-[#090d16]/70 border-[#1f2937] text-gray-500 opacity-75"
              } ${onStepClick ? "cursor-pointer hover:border-gray-600" : ""}`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <div
                  className={`w-6 h-6 rounded-md flex items-center justify-center text-xs font-mono font-bold ${
                    isDone
                      ? "bg-emerald-950 text-emerald-400 border border-emerald-500/40"
                      : isActive
                      ? "bg-cyan-950 text-cyan-300 border border-cyan-400/50 shadow-sm"
                      : "bg-[#1f2937] text-gray-400 border border-gray-700"
                  }`}
                >
                  {isDone ? <CheckCircle2 className="w-3.5 h-3.5" /> : step.id}
                </div>
                <span
                  className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                    isActive
                      ? "bg-cyan-900/40 text-cyan-300 border border-cyan-700/50"
                      : isDone
                      ? "bg-emerald-900/30 text-emerald-300 border border-emerald-800/40"
                      : "bg-[#1f2937]/50 text-gray-500 border border-[#1f2937]"
                  }`}
                >
                  {step.tag}
                </span>
              </div>

              <div className="flex items-center gap-1.5 mt-0.5">
                <Icon
                  className={`w-3.5 h-3.5 ${
                    isActive
                      ? "text-cyan-400"
                      : isDone
                      ? "text-emerald-400"
                      : "text-gray-500"
                  }`}
                />
                <span
                  className={`text-xs font-medium tracking-tight ${
                    isActive
                      ? "text-gray-100 font-semibold"
                      : isDone
                      ? "text-gray-200"
                      : "text-gray-400"
                  }`}
                >
                  {step.label}
                </span>
              </div>

              <p className="text-[10px] text-gray-400 mt-1 line-clamp-1 leading-snug">
                {step.description}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
};
