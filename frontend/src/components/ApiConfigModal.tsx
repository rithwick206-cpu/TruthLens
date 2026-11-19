"use client";

import React, { useState, useEffect } from "react";
import { Server, Globe, CheckCircle2, AlertCircle, RefreshCw, X, Link, HelpCircle } from "lucide-react";
import { getApiBase, setApiBase } from "@/lib/api";

interface ApiConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  onEndpointChanged: () => void;
}

export const ApiConfigModal: React.FC<ApiConfigModalProps> = ({
  isOpen,
  onClose,
  onEndpointChanged,
}) => {
  const [apiUrl, setApiUrl] = useState("");
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);

  useEffect(() => {
    if (isOpen) {
      setApiUrl(getApiBase());
      setTestResult(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleTestAndSave = async () => {
    let cleanUrl = apiUrl.trim().replace(/\/$/, "");
    if (!cleanUrl) {
      setTestResult({ success: false, message: "Please provide a valid backend URL." });
      return;
    }

    // Auto-complete scheme and Render domain if user entered just the service name
    if (!cleanUrl.startsWith("http://") && !cleanUrl.startsWith("https://")) {
      if (cleanUrl.includes("render.com") || cleanUrl.includes("trycloudflare.com")) {
        cleanUrl = `https://${cleanUrl}`;
      } else if (!cleanUrl.includes(".")) {
        // e.g. user typed "truthlens-api-nflc"
        cleanUrl = `https://${cleanUrl}.onrender.com`;
      } else {
        cleanUrl = `https://${cleanUrl}`;
      }
    }
    setApiUrl(cleanUrl);

    setIsTesting(true);
    setTestResult(null);

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 6000);

      const res = await fetch(`${cleanUrl}/health`, {
        signal: controller.signal,
        headers: { Accept: "application/json" },
      });
      clearTimeout(timeoutId);

      if (res.ok) {
        setApiBase(cleanUrl);
        setTestResult({
          success: true,
          message: "Successfully connected to TruthLens FastAPI backend!",
        });
        setTimeout(() => {
          onEndpointChanged();
          onClose();
        }, 800);
      } else {
        setTestResult({
          success: false,
          message: `Endpoint responded with status ${res.status}. Expected 200 OK from /health.`,
        });
      }
    } catch (err: any) {
      setTestResult({
        success: false,
        message:
          err.name === "AbortError"
            ? "Connection timed out. Check that your tunnel or backend server is running."
            : `Could not reach ${cleanUrl}. Check CORS and URL format.`,
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleResetDefault = () => {
    const defaultUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
    setApiBase("");
    setApiUrl(defaultUrl);
    setTestResult({
      success: true,
      message: "Reset to default endpoint. Click Test & Save to apply.",
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div
        className="w-full max-w-lg bg-[#0d1424] border border-cyan-500/40 rounded-2xl shadow-2xl shadow-cyan-950/60 overflow-hidden font-sans flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#1f2937] bg-[#090e1a]">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-cyan-950/80 border border-cyan-800/60 text-cyan-400">
              <Server className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-gray-100">Connect Backend API</h3>
              <p className="text-[11px] text-gray-400">Configure TruthLens FastAPI server endpoint</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white p-1 rounded-lg transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-gray-200 flex items-center justify-between">
              <span>Backend Server URL:</span>
              <span className="text-[10px] text-cyan-400 font-mono">HTTPS required on Vercel</span>
            </label>
            <div className="relative">
              <Globe className="w-4 h-4 text-gray-500 absolute left-3 top-3" />
              <input
                type="text"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                placeholder="https://your-tunnel.trycloudflare.com or http://127.0.0.1:8000"
                className="w-full bg-[#090d16] border border-[#1f2937] focus:border-cyan-500/60 rounded-xl pl-9 pr-3 py-2.5 text-xs text-gray-200 font-mono placeholder-gray-600 focus:outline-none"
              />
            </div>
            <p className="text-[11px] text-gray-400 leading-relaxed">
              When deployed on Vercel (HTTPS), web browsers block insecure <code className="text-gray-300">http://127.0.0.1:8000</code>. Paste your public HTTPS tunnel URL (e.g. from Cloudflare Tunnel or ngrok) to connect.
            </p>
          </div>

          {/* Test Status Feedback */}
          {testResult && (
            <div
              className={`p-3 rounded-xl border flex items-start gap-2.5 text-xs ${
                testResult.success
                  ? "bg-emerald-950/40 border-emerald-500/50 text-emerald-300"
                  : "bg-rose-950/40 border-rose-500/50 text-rose-300"
              }`}
            >
              {testResult.success ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              ) : (
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              )}
              <span className="flex-1 leading-snug">{testResult.message}</span>
            </div>
          )}

          {/* Cloudflare Tunnel Quick Tip */}
          <div className="bg-[#080d17] border border-[#1e293b] rounded-xl p-3 space-y-1.5 text-xs text-gray-400">
            <div className="flex items-center gap-1.5 font-semibold text-gray-200 text-[11px]">
              <HelpCircle className="w-3.5 h-3.5 text-cyan-400" />
              <span>How to tunnel FastAPI to HTTPS for Vercel:</span>
            </div>
            <p className="text-[10px] text-gray-400 leading-relaxed">
              Run this command on your terminal to get a free instant HTTPS tunnel URL:
            </p>
            <div className="bg-[#050811] border border-gray-800 p-2 rounded-lg font-mono text-[10px] text-cyan-300 select-all">
              cloudflared tunnel --url http://127.0.0.1:8000
            </div>
            <p className="text-[10px] text-gray-500">
              Copy the resulting <code className="text-gray-400">https://...trycloudflare.com</code> URL and paste it in the box above!
            </p>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-5 py-3.5 bg-[#090e1a] border-t border-[#1f2937] flex items-center justify-between">
          <button
            type="button"
            onClick={handleResetDefault}
            className="text-xs text-gray-500 hover:text-gray-300 underline font-mono"
          >
            Reset Default
          </button>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-2 text-xs text-gray-400 hover:text-gray-200 transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleTestAndSave}
              disabled={isTesting}
              className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold text-xs rounded-lg shadow-md transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
            >
              {isTesting ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Connecting...</span>
                </>
              ) : (
                <>
                  <Link className="w-3.5 h-3.5" />
                  <span>Test & Save</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
