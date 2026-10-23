import type { Citation, RunRecord } from "./types";

const SOURCE_NAMES: Record<string, string> = {
  "corpus/orders.md": "Order record",
  "corpus/overview.md": "Service notes",
  "corpus/tools.md": "Lookup guide",
  "fixture://forge/orders": "Order search",
  "fixture://forge/overview": "Notes search",
  "sql:orders": "Orders",
  "sql:docs": "Notes",
  "http_api:/orders/1001": "Order service",
  "http_api:/docs/overview": "Docs service",
  "file:notes/run.txt": "Saved note",
};

export const EXAMPLES = [
  "Where is order 1001?",
  "What is case 4401?",
  "Which company is on the desk?",
];

const ASIDE =
  /\b(sql_query|http_api|stubs?|schema|corpus|fixture|mcp|postgres|rag|tools?|file_store|sandbox|utf-8|utf8)\b/i;

const STEP_LABELS: Record<string, string> = {
  planner: "Planning",
  worker: "Lookup",
  critic: "Check",
};

export function sourceName(source: string): string {
  const named = SOURCE_NAMES[source];
  if (named) return named;
  const caseId = source.match(/^corpus\/cases\/(\d+)\.md$/);
  if (caseId) return `Case ${caseId[1]}`;
  if (source === "corpus/company.md") return "Company record";
  return "Record";
}

export function askedNumbers(query: string): string[] {
  return query.match(/\d+/g) ?? [];
}

export function coversNumbers(text: string, numbers: string[]): boolean {
  if (numbers.length === 0) return true;
  const found = new Set(text.match(/\d+/g) ?? []);
  return numbers.every((number) => found.has(number));
}

export function focusOnNumbers(text: string, numbers: string[]): string {
  if (numbers.length === 0) return text;
  const kept: string[] = [];
  let open = false;
  for (const sentence of text.split(/(?<=[.!?])\s+/)) {
    const ids = sentence.match(/\d{4,}/g) ?? [];
    if (ids.some((id) => numbers.includes(id))) {
      open = true;
      kept.push(sentence);
      continue;
    }
    if (open && ids.length === 0) {
      kept.push(sentence);
      continue;
    }
    open = false;
  }
  return kept.join(" ");
}

export function stepLabel(node: string): string {
  return STEP_LABELS[node] ?? "Check";
}

export function guestStep(node: string, detail: string): string {
  if (node === "planner") {
    const read = detail.match(/read this as (.+?);/);
    if (read) return `Read this as "${read[1].trim()}".`;
    if (detail.includes("local model unavailable")) {
      return "The local model was down, so the word list chose which records to open.";
    }
    if (detail.startsWith("local model")) return "A local model chose which records to open.";
    return "Chose which records to open.";
  }
  if (node === "worker") {
    return /\bfail|error|not ok\b/i.test(detail)
      ? "One of the lookups did not come back."
      : "Opened those records.";
  }
  if (detail.includes("empty retrieval")) return "Nothing on file matched the question.";
  if (detail.includes("unsupported")) return "The records do not cover part of the question.";
  if (detail.startsWith("accepted")) return "The answer matches what is on file.";
  if (detail.startsWith("rejected")) return "Held the answer back.";
  return "Checked the answer against the records.";
}

export function staffText(excerpt: string): string {
  const stripped = excerpt.replace(/^#\s+[^\n]+\n+/, "").replace(/\s+/g, " ").trim();
  if (!stripped || stripped.startsWith("[") || stripped.startsWith("{")) return "";
  return stripped
    .split(/(?<=[.!?])\s+/)
    .map(hostSentence)
    .filter((sentence) => sentence && !ASIDE.test(sentence))
    .join(" ");
}

function hostSentence(sentence: string): string {
  if (/planner, a worker, and a critic/i.test(sentence)) {
    return "Forge looks the question up, then answers only when the records support it.";
  }
  return sentence;
}

export function guestAnswer(record: RunRecord): { title: string; lines: string[]; saved: boolean } {
  if (record.status === "failed") {
    return { title: "Something went wrong", lines: [record.error || "Try that again."], saved: false };
  }
  if (!record.accepted) {
    const notes = record.critic_notes ?? "";
    if (notes.includes("empty retrieval")) {
      return {
        title: "Nothing came up",
        lines: ["Nothing on file mentions this."],
        saved: false,
      };
    }
    if (notes.includes("unsupported")) {
      const terms = notes.replace("rejected: unsupported", "").trim();
      return {
        title: "We can't confirm that",
        lines: [`Nothing on file covers ${terms}.`],
        saved: false,
      };
    }
    return { title: "We can't confirm that", lines: ["There isn't enough on file to answer."], saved: false };
  }

  const citations = record.result?.citations ?? [];
  const saved = citations.some((item) => item.source.startsWith("file:"));
  const lines = distinct(plainLines(citations, record.query));
  return {
    title: "Here's what we found",
    lines: lines.length > 0 ? lines : ["Forge checked this and kept the supporting notes."],
    saved,
  };
}

function plainLines(citations: Citation[], query: string): string[] {
  const numbers = askedNumbers(query);
  const seen = new Set<string>();
  const lines: string[] = [];
  for (const cite of citations) {
    if (cite.source.startsWith("file:")) continue;
    const text = focusOnNumbers(staffText(cite.excerpt), numbers);
    const key = text.toLowerCase();
    if (!text || seen.has(key)) continue;
    seen.add(key);
    lines.push(text);
  }
  return lines;
}

function distinct(lines: string[]): string[] {
  const kept: string[] = [];
  const covered = new Set<string>();
  for (const line of lines) {
    const words = tokens(line);
    const novel = [...words].some((word) => !covered.has(word));
    if (kept.length > 0 && !novel) continue;
    kept.push(line);
    for (const word of words) covered.add(word);
    if (kept.length === 2) break;
  }
  return kept;
}

function tokens(text: string): string[] {
  return fold(text)
    .split(" ")
    .filter((word) => word && !FILLER.has(word));
}

const FILLER = new Set(["with", "its", "the", "and", "from", "this", "that", "for", "was", "are"]);

function fold(text: string): string {
  return text
    .toLowerCase()
    .replace(/\bdemo\b/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}
