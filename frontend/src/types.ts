export type RunMode = "stub" | "promote" | "prod";

export type Health = {
  status: "ok" | "degraded";
  service: string;
  version: string;
  graph: string;
  database: string;
  mcp_servers: number;
};

export type Citation = {
  source: string;
  excerpt: string;
};

export type ToolCall = {
  server: string;
  tool: string;
  ok: boolean;
};

export type RunStep = {
  node: string;
  detail: string;
};

export type RunRecord = {
  id: string;
  query: string;
  mode: RunMode;
  status: "completed" | "failed";
  accepted: boolean | null;
  critic_notes: string | null;
  steps: RunStep[];
  result: {
    answer: string;
    citations: Citation[];
    tool_calls_summary: ToolCall[];
    confidence: number;
  } | null;
  error: string | null;
  elapsed_ms: number | null;
  tool_count: number | null;
  tool_failures: number | null;
  estimated_cost_usd: number | null;
};

export type Metrics = {
  status: "not_measured" | "measured";
  faithfulness: number | null;
  decision_accuracy: number | null;
  tool_success_rate: number | null;
  latency_p50_ms: number | null;
  latency_p95_ms: number | null;
  estimated_cost_usd_per_success: number | null;
  tasks: number | null;
  baseline_id: string | null;
  runtime: string | null;
  note: string;
};
