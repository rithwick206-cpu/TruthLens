import {
  CaseIngestResponse,
  CaseRecord,
  DemoSample,
  ForensicReport,
  ModelMetrics,
  ReviewUpdateRequest,
  ReviewUpdateResponse,
} from "@/types/forensics";

export function getApiBase(): string {
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    // Local development
    if (host === "localhost" || host === "127.0.0.1") {
      return "http://127.0.0.1:8000";
    }

    // Clean up any stale localStorage key if present
    try {
      localStorage.removeItem("truthlens_api_url");
    } catch {}
  }

  let rawEnv = (process.env.NEXT_PUBLIC_API_BASE_URL || "").trim().replace(/\/$/, "");
  if (rawEnv && rawEnv !== "http://127.0.0.1:8000" && rawEnv !== "http://localhost:8000") {
    // If Render injected bare service name without FQDN (e.g. "truthlens-api-nflc")
    if (!rawEnv.includes(".")) {
      rawEnv = `${rawEnv}.onrender.com`;
    }
    if (!rawEnv.startsWith("http://") && !rawEnv.startsWith("https://")) {
      rawEnv = `https://${rawEnv}`;
    }
    return rawEnv;
  }

  // Deployed Cloud Backend on Render
  return "https://truthlens-api-nflc.onrender.com";
}

export function setApiBase(url: string): void {
  // No-op in automated mode
}

export function assetUrl(relativePath?: string | null): string {
  if (!relativePath) return "";
  if (relativePath.startsWith("http://") || relativePath.startsWith("https://")) {
    return relativePath;
  }
  const cleanPath = relativePath.startsWith("/") ? relativePath : `/${relativePath}`;
  return `${getApiBase()}${cleanPath}`;
}

export function getReportPdfUrl(caseId: string): string {
  return `${getApiBase()}/api/report/${caseId}/pdf`;
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const base = getApiBase();
  const url = `${base}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        Accept: "application/json",
        ...options?.headers,
      },
    });

    if (!response.ok) {
      let errorDetail = `Request failed with status ${response.status}`;
      try {
        const errJson = await response.json();
        if (errJson && errJson.detail) {
          errorDetail = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
        }
      } catch {
        // ignore json parse error
      }
      throw new Error(errorDetail);
    }

    return (await response.json()) as T;
  } catch (error: any) {
    if (error.name === "TypeError" && error.message.includes("fetch")) {
      throw new Error("Unable to reach TruthLens backend. Verify the FastAPI server is running on port 8000.");
    }
    throw error;
  }
}

export async function checkHealth(): Promise<{ status: string; service: string }> {
  return request<{ status: string; service: string }>("/health");
}

export async function listCases(): Promise<CaseRecord[]> {
  return request<CaseRecord[]>("/api/cases");
}

export async function getCase(caseId: string): Promise<CaseRecord> {
  return request<CaseRecord>(`/api/cases/${encodeURIComponent(caseId)}`);
}

export async function ingestCase(formData: FormData): Promise<CaseIngestResponse> {
  const url = `${getApiBase()}/api/cases/ingest`;
  try {
    const response = await fetch(url, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Ingestion failed (${response.status})`);
    }
    return (await response.json()) as CaseIngestResponse;
  } catch (error: any) {
    if (error.name === "TypeError" && error.message.includes("fetch")) {
      throw new Error("Backend connection error during ingestion. Please check backend server status.");
    }
    throw error;
  }
}

export async function analyzeCase(caseId: string): Promise<ForensicReport> {
  return request<ForensicReport>(`/api/analyze/${encodeURIComponent(caseId)}`, {
    method: "POST",
  });
}

export async function listDemoSamples(): Promise<DemoSample[]> {
  return request<DemoSample[]>("/api/demo/samples");
}

export async function loadDemoSample(sampleId: string): Promise<ForensicReport> {
  return request<ForensicReport>(`/api/demo/load/${encodeURIComponent(sampleId)}`, {
    method: "POST",
  });
}

export async function updateCaseReview(
  caseId: string,
  payload: ReviewUpdateRequest
): Promise<ReviewUpdateResponse> {
  return request<ReviewUpdateResponse>(`/api/cases/${encodeURIComponent(caseId)}/review`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export async function getModelMetrics(): Promise<ModelMetrics> {
  return request<ModelMetrics>("/api/metrics/model");
}
