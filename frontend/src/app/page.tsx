"use client";

import React, { useEffect, useState, useCallback } from "react";
import { TopBar } from "@/components/TopBar";
import { WorkflowStepper } from "@/components/WorkflowStepper";
import { CaseSidebar } from "@/components/CaseSidebar";
import { IngestWorkspace } from "@/components/IngestWorkspace";
import { ForensicWorkbench } from "@/components/workbench/ForensicWorkbench";
import { ModelInsightsModal } from "@/components/ModelInsightsModal";
import { CaseRecord, ForensicReport } from "@/types/forensics";
import { listCases, getCase, loadDemoSample, getReportPdfUrl } from "@/lib/api";
import { FolderArchive, PlusCircle, AlertCircle } from "lucide-react";
import { CommandPalette } from "@/components/CommandPalette";
import { ToastProvider } from "@/components/Toast";
import { ApiConfigModal } from "@/components/ApiConfigModal";

export default function Home() {
  const [activeTab, setActiveTab] = useState<"new" | "active" | "insights">("new");
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [activeCaseId, setActiveCaseId] = useState<string | null>(null);
  const [activeCase, setActiveCase] = useState<CaseRecord | null>(null);
  const [isLoadingCases, setIsLoadingCases] = useState(false);
  const [isLoadingDemo, setIsLoadingDemo] = useState(false);
  const [loadingActiveCase, setLoadingActiveCase] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const [isPaletteOpen, setIsPaletteOpen] = useState(false);
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);

  // Global Keyboard Shortcuts (⌘K, N, M, 1-3, E)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const isInput =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.isContentEditable;

      // ⌘K or Ctrl+K -> Command Palette
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setIsPaletteOpen((prev) => !prev);
        return;
      }

      if (isInput) return;

      if (e.key === "n" || e.key === "N") {
        setActiveTab("new");
      } else if (e.key === "m" || e.key === "M") {
        setActiveTab("insights");
      } else if (e.key === "1") {
        setActiveTab("new");
      } else if (e.key === "2") {
        setActiveTab("active");
      } else if (e.key === "3") {
        setActiveTab("insights");
      } else if ((e.key === "e" || e.key === "E") && activeCaseId) {
        window.open(getReportPdfUrl(activeCaseId), "_blank");
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [activeCaseId]);

  // Load cases on mount
  const refreshCases = useCallback(async () => {
    setIsLoadingCases(true);
    setGlobalError(null);
    try {
      const data = await listCases();
      setCases(data);
      return data;
    } catch (err: any) {
      console.error("Failed to load cases from backend:", err);
      setGlobalError(
        "Could not connect to TruthLens backend at http://127.0.0.1:8000. Ensure FastAPI is running."
      );
      return [];
    } finally {
      setIsLoadingCases(false);
    }
  }, []);

  useEffect(() => {
    refreshCases();
  }, [refreshCases]);

  // Handle case selection
  const handleSelectCase = async (caseId: string) => {
    setActiveCaseId(caseId);
    setActiveTab("active");
    setLoadingActiveCase(true);
    try {
      const record = await getCase(caseId);
      setActiveCase(record);
    } catch (err: any) {
      console.error("Failed to load case detail:", err);
      // Fallback to local memory record if available
      const local = cases.find((c) => c.case_id === caseId) || null;
      setActiveCase(local);
    } finally {
      setLoadingActiveCase(false);
    }
  };

  // Handle loading a demo sample
  const handleLoadDemo = async (sampleId: string) => {
    setIsLoadingDemo(true);
    setGlobalError(null);
    try {
      const report: ForensicReport = await loadDemoSample(sampleId);
      const updatedList = await refreshCases();
      const loaded = updatedList.find((c) => c.case_id === report.case_id);
      if (loaded) {
        setActiveCase(loaded);
        setActiveCaseId(loaded.case_id);
      } else {
        // Fallback synthetic case record
        const synthetic: CaseRecord = {
          case_id: report.case_id,
          created_at: report.created_at,
          status: report.status,
          review_status: report.review_status,
          review_notes: report.review_notes,
          caption_text: report.summary,
          files: [],
          result: report,
        };
        setActiveCase(synthetic);
        setActiveCaseId(report.case_id);
      }
      setActiveTab("active");
    } catch (err: any) {
      console.error("Demo load failed:", err);
      setGlobalError(err.message || "Failed to load forensic demo sample.");
    } finally {
      setIsLoadingDemo(false);
    }
  };

  // When a new analysis finishes in IngestWorkspace
  const handleCaseAnalyzed = async (caseId: string, report: ForensicReport) => {
    const updatedList = await refreshCases();
    const match = updatedList.find((c) => c.case_id === caseId);
    if (match) {
      setActiveCase(match);
      setActiveCaseId(match.case_id);
    } else {
      setActiveCase({
        case_id: caseId,
        created_at: report.created_at,
        status: report.status,
        review_status: report.review_status,
        review_notes: report.review_notes,
        files: [],
        result: report,
      });
      setActiveCaseId(caseId);
    }
    setActiveTab("active");
  };

  // Calculate current pipeline step for WorkflowStepper
  const calculatePipelineStep = (): number => {
    if (activeTab === "new") return 1;
    if (activeTab === "insights") return 2;
    if (!activeCase) return 1;
    if (activeCase.status === "ingested") return 2;
    if (activeCase.status === "analyzing") return 3;
    if (activeCase.status === "analyzed") {
      if (activeCase.review_status && activeCase.review_status !== "needs_review") {
        return 5;
      }
      return 4;
    }
    return 3;
  };

  return (
    <ToastProvider>
      <div className="min-h-screen bg-[#090d16] text-[#f3f4f6] flex flex-col font-sans selection:bg-cyan-900 selection:text-cyan-200">
        {/* Persistent Global TopBar */}
        <TopBar
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          onLoadDemo={handleLoadDemo}
          isLoadingDemo={isLoadingDemo}
          activeCaseId={activeCaseId}
          onOpenPalette={() => setIsPaletteOpen(true)}
          onOpenConfig={() => setIsConfigModalOpen(true)}
        />

        {/* Global Error Banner */}
        {globalError && (
          <div className="bg-rose-950/70 border-b border-rose-500/50 px-4 py-2 flex flex-wrap items-center justify-between gap-3 text-xs text-rose-300">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{globalError}</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setIsConfigModalOpen(true)}
                className="px-2.5 py-1 bg-rose-900/80 hover:bg-rose-800 text-rose-200 border border-rose-600/60 rounded font-mono text-[11px] font-semibold transition-colors cursor-pointer"
              >
                Configure Backend URL
              </button>
              <button
                type="button"
                onClick={() => setGlobalError(null)}
                className="text-gray-400 hover:text-white font-mono text-[10px] px-2 py-1 cursor-pointer"
              >
                DISMISS
              </button>
            </div>
          </div>
        )}

        {/* Main Forensic Workspace Body */}
        <div className="flex-1 flex flex-col md:flex-row w-full">
          {/* Left Case History Sidebar */}
          <CaseSidebar
            cases={cases}
            activeCaseId={activeCaseId}
            onSelectCase={handleSelectCase}
            onNewCase={() => setActiveTab("new")}
            onRefresh={refreshCases}
            isLoading={isLoadingCases}
          />

          {/* Right Main Stage */}
          <main className="flex-1 p-4 md:p-6 overflow-y-auto space-y-5">
            {/* Workflow Stepper Progress Indicator */}
            <WorkflowStepper
              currentStep={calculatePipelineStep()}
              caseStatus={activeCase?.status}
              onStepClick={(step) => {
                if (step === 1) setActiveTab("new");
                if (step === 2 && !activeCase) setActiveTab("insights");
                if (step >= 3 && activeCase) setActiveTab("active");
              }}
            />

            {/* Tab 1: New Case Ingestion */}
            {activeTab === "new" && (
              <IngestWorkspace
                onCaseAnalyzed={handleCaseAnalyzed}
                onNavigateToDemo={handleLoadDemo}
              />
            )}

            {/* Tab 2: Active Case Forensic Analysis & Audit */}
            {activeTab === "active" && (
              <>
                {loadingActiveCase ? (
                  <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-12 text-center text-gray-400 font-mono text-xs">
                    Loading cryptographic evidence record...
                  </div>
                ) : activeCase ? (
                  <ForensicWorkbench
                    caseRecord={activeCase}
                    onCaseUpdated={(updated) => {
                      setActiveCase(updated);
                      setCases((prev) =>
                        prev.map((c) => (c.case_id === updated.case_id ? updated : c))
                      );
                    }}
                  />
                ) : (
                  <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-12 text-center space-y-3">
                    <FolderArchive className="w-10 h-10 text-gray-600 mx-auto" />
                    <h3 className="text-sm font-semibold text-gray-300">No Case Selected</h3>
                    <p className="text-xs text-gray-500 max-w-sm mx-auto">
                      Select an existing digital evidence case from the sidebar or click below to submit
                      a new investigation.
                    </p>
                    <button
                      onClick={() => setActiveTab("new")}
                      className="inline-flex items-center gap-1.5 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-xs font-semibold transition-all cursor-pointer"
                    >
                      <PlusCircle className="w-4 h-4" />
                      <span>Create New Forensic Case</span>
                    </button>
                  </div>
                )}
              </>
            )}

            {/* Tab 3: Model Insights & Architecture Registry */}
            {activeTab === "insights" && <ModelInsightsModal />}
          </main>
        </div>

        {/* Global Command Palette */}
        <CommandPalette
          isOpen={isPaletteOpen}
          onClose={() => setIsPaletteOpen(false)}
          cases={cases}
          onSelectCase={handleSelectCase}
          onNavigateTab={setActiveTab}
          onLoadDemo={handleLoadDemo}
          onExportPdf={() => activeCaseId && window.open(getReportPdfUrl(activeCaseId), "_blank")}
          activeCaseId={activeCaseId}
        />

        {/* Backend API Configuration Modal */}
        <ApiConfigModal
          isOpen={isConfigModalOpen}
          onClose={() => setIsConfigModalOpen(false)}
          onEndpointChanged={refreshCases}
        />
      </div>
    </ToastProvider>
  );
}
