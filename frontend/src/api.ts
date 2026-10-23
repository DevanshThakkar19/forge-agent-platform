import type { Health, Metrics, RunMode, RunRecord } from "./types";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getHealth(): Promise<Health> {
  return send<Health>("/health", null);
}

export function createRun(apiKey: string, query: string, mode: RunMode): Promise<RunRecord> {
  return send<RunRecord>("/v1/runs", apiKey, {
    method: "POST",
    body: JSON.stringify({ query, mode }),
  });
}

export function getRun(apiKey: string, id: string): Promise<RunRecord> {
  return send<RunRecord>(`/v1/runs/${id}`, apiKey);
}

export function getMetrics(apiKey: string): Promise<Metrics> {
  return send<Metrics>("/v1/metrics", apiKey);
}

async function send<T>(path: string, apiKey: string | null, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (apiKey) headers.set("X-API-Key", apiKey);
  if (init?.body) headers.set("Content-Type", "application/json");
  let response: Response;
  try {
    response = await fetch(path, { ...init, headers });
  } catch {
    throw new ApiError(0, "API unreachable");
  }
  const text = await response.text();
  const body: unknown = text ? JSON.parse(text) : null;
  if (!response.ok) throw new ApiError(response.status, messageFrom(body));
  return body as T;
}

function messageFrom(body: unknown): string {
  if (!body || typeof body !== "object" || !("detail" in body)) return "Request failed";
  const detail = (body as { detail: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && "message" in detail) {
    const message = String((detail as { message: unknown }).message);
    const reasons = (detail as { reasons?: unknown }).reasons;
    if (Array.isArray(reasons) && reasons.length > 0) {
      return `${message}: ${reasons.map(String).join("; ")}`;
    }
    return message;
  }
  return "Request failed";
}
