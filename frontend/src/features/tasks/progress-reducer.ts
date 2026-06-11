/**
 * Pure reducer that folds the Wave-0 SSE ledger into renderable progress state.
 *
 * Wave-0 emits 8 coarse events (task.started → 3×(delegation_started +
 * delegation_completed) → task.completed). The contract also lists per-token
 * Wave-1 types (task.step_started / step_token / step_completed); the reducer
 * TOLERATES all 9 types gracefully (AC11) — unknown/Wave-1 events append to the
 * log without breaking the 3 coarse agent cards.
 */
import type { SseEvent } from "@/api/sse";
import type { Artifact } from "@/api/tasks";

export type AgentSlug = "researcher" | "analyst" | "writer";
export type AgentStatus = "pending" | "running" | "done";
export type ProgressPhase = "idle" | "running" | "completed" | "failed" | "cancelled";

export interface AgentCard {
  slug: AgentSlug;
  label: string;
  status: AgentStatus;
}

export interface LogEntry {
  type: string;
  label: string;
}

export interface CostRow {
  slug: AgentSlug;
  label: string;
  costCredits: number;
  tokens: number;
}

export interface ProgressState {
  phase: ProgressPhase;
  agents: AgentCard[];
  log: LogEntry[];
  artifacts: Artifact[];
  costRows: CostRow[];
  startedAt: string | null;
}

const AGENT_ORDER: AgentSlug[] = ["researcher", "analyst", "writer"];

const AGENT_LABEL: Record<AgentSlug, string> = {
  researcher: "Исследователь",
  analyst: "Аналитик",
  writer: "Райтер",
};

const EVENT_LABEL: Record<string, string> = {
  "task.started": "Задача запущена",
  "task.delegation_started": "Делегирование",
  "task.delegation_completed": "Делегирование завершено",
  "task.completed": "Задача завершена",
  "task.failed": "Задача завершилась с ошибкой",
  "task.cancelled": "Задача отменена",
  "task.step_started": "Шаг начат",
  "task.step_token": "Генерация",
  "task.step_completed": "Шаг завершён",
};

export function initialProgressState(): ProgressState {
  return {
    phase: "idle",
    agents: AGENT_ORDER.map((slug) => ({ slug, label: AGENT_LABEL[slug], status: "pending" })),
    log: [],
    artifacts: [],
    costRows: [],
    startedAt: null,
  };
}

function readCostRow(slug: AgentSlug, data: unknown): CostRow {
  const obj = (data ?? {}) as { cost_credits?: unknown; tokens_used?: unknown };
  return {
    slug,
    label: AGENT_LABEL[slug],
    costCredits: Number(obj.cost_credits ?? 0) || 0,
    tokens: Number(obj.tokens_used ?? 0) || 0,
  };
}

function isAgentSlug(value: unknown): value is AgentSlug {
  return value === "researcher" || value === "analyst" || value === "writer";
}

function setAgentStatus(agents: AgentCard[], slug: AgentSlug, status: AgentStatus): AgentCard[] {
  return agents.map((a) => (a.slug === slug ? { ...a, status } : a));
}

function readSlug(data: unknown): AgentSlug | null {
  if (data && typeof data === "object" && "target_agent_slug" in data) {
    const slug = (data).target_agent_slug;
    if (isAgentSlug(slug)) return slug;
  }
  return null;
}

function readArtifacts(data: unknown): Artifact[] {
  if (
    data &&
    typeof data === "object" &&
    "result" in data &&
    (data).result &&
    typeof (data).result === "object"
  ) {
    const result = (data as { result: { artifacts?: unknown } }).result;
    if (Array.isArray(result.artifacts)) return result.artifacts as Artifact[];
  }
  return [];
}

export function progressReducer(state: ProgressState, event: SseEvent): ProgressState {
  const label = EVENT_LABEL[event.event] ?? event.event;
  const withLog = (next: Partial<ProgressState>): ProgressState => ({
    ...state,
    ...next,
    log: [...state.log, { type: event.event, label }],
  });

  switch (event.event) {
    case "task.started": {
      const startedAt =
        event.data && typeof event.data === "object" && "started_at" in event.data
          ? String((event.data).started_at)
          : null;
      return withLog({ phase: "running", startedAt });
    }

    case "task.delegation_started":
    case "task.step_started": {
      const slug = readSlug(event.data);
      return withLog(slug ? { agents: setAgentStatus(state.agents, slug, "running") } : {});
    }

    case "task.delegation_completed":
    case "task.step_completed": {
      const slug = readSlug(event.data);
      if (!slug) return withLog({});
      return withLog({
        agents: setAgentStatus(state.agents, slug, "done"),
        costRows: [...state.costRows, readCostRow(slug, event.data)],
      });
    }

    case "task.completed": {
      const artifacts = readArtifacts(event.data);
      return withLog({
        phase: "completed",
        // any unfinished card is implicitly done once the task completes
        agents: state.agents.map((a) => ({ ...a, status: "done" })),
        ...(artifacts.length > 0 ? { artifacts } : {}),
      });
    }

    case "task.failed":
      return withLog({ phase: "failed" });

    case "task.cancelled":
      return withLog({ phase: "cancelled" });

    // task.step_token (Wave-1 per-token) and any unknown type: log only,
    // never break the coarse cards.
    default:
      return withLog({});
  }
}

/** Replay a whole ledger (used for late-subscribe drain + tests). */
export function replayProgress(events: SseEvent[]): ProgressState {
  return events.reduce(progressReducer, initialProgressState());
}
