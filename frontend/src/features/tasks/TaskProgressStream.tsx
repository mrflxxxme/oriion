/**
 * TaskProgressStream — renders the coarse Wave-0 progress: three agent
 * step-cards (Исследователь → Аналитик → Райтер) driven by the SSE reducer,
 * plus a collapsible raw event log. Per phase-spec ui-spec: aria-live=polite,
 * aria-busy while streaming, reduced-motion respected (no animated transitions
 * on chunk render).
 */
import { useEffect, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Avatar, Badge, Card } from "@/components/ui";
import type { BadgeProps } from "@/components/ui";
import type { AgentCard, ProgressState } from "./progress-reducer";

interface TaskProgressStreamProps {
  progress: ProgressState;
  isRunning: boolean;
  streamError: boolean;
}

const STATUS_BADGE: Record<AgentCard["status"], { variant: BadgeProps["variant"]; label: string }> =
  {
    pending: { variant: "default", label: "Ожидание" },
    running: { variant: "warning", label: "Выполняется" },
    done: { variant: "success", label: "Готово" },
  };

/** Live elapsed timer (seconds) since the task started, while running. */
function ElapsedTimer({ startedAt, running }: { startedAt: string | null; running: boolean }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => {
      setNow(Date.now());
    }, 1000);
    return () => {
      clearInterval(id);
    };
  }, [running]);

  if (!startedAt) return null;
  const started = new Date(startedAt).getTime();
  if (Number.isNaN(started)) return null;
  const seconds = Math.max(0, Math.floor((now - started) / 1000));
  return (
    <span
      className="font-mono text-xs text-tertiary"
      aria-label={`Прошло ${String(seconds)} секунд`}
    >
      {seconds}с
    </span>
  );
}

function AgentStepCard({ agent, startedAt }: { agent: AgentCard; startedAt: string | null }) {
  const badge = STATUS_BADGE[agent.status];
  return (
    <Card variant="outlined" padding="md">
      <div className="flex items-center gap-3">
        <Avatar fallback={agent.label.charAt(0)} size="sm" />
        <div className="flex flex-1 flex-col">
          <span className="text-sm font-medium text-primary">{agent.label}</span>
          <span className="flex items-center gap-2">
            <Badge variant={badge.variant}>{badge.label}</Badge>
            <ElapsedTimer startedAt={startedAt} running={agent.status === "running"} />
          </span>
        </div>
      </div>
    </Card>
  );
}

export function TaskProgressStream({ progress, isRunning, streamError }: TaskProgressStreamProps) {
  const [logOpen, setLogOpen] = useState(false);

  return (
    <div aria-live="polite" aria-busy={isRunning}>
      <div className="grid gap-3 sm:grid-cols-3">
        {progress.agents.map((agent) => (
          <AgentStepCard key={agent.slug} agent={agent} startedAt={progress.startedAt} />
        ))}
      </div>

      {streamError ? (
        <p role="status" className="mt-4 text-sm text-tertiary">
          Поток событий недоступен — статус обновляется опросом.
        </p>
      ) : null}

      <div className="mt-6">
        <button
          type="button"
          onClick={() => {
            setLogOpen((v) => !v);
          }}
          aria-expanded={logOpen}
          className="flex items-center gap-1 rounded-sm text-sm text-secondary hover:text-primary focus-visible:outline-none focus-visible:shadow-focus-ring"
        >
          {logOpen ? (
            <ChevronDown className="size-4" aria-hidden="true" />
          ) : (
            <ChevronRight className="size-4" aria-hidden="true" />
          )}
          Журнал событий ({progress.log.length})
        </button>
        {logOpen ? (
          <ol className="mt-2 flex flex-col gap-1 border-l border-default pl-4">
            {progress.log.map((entry, index) => (
              <li key={`${entry.type}-${String(index)}`} className="text-xs text-tertiary">
                <span className="font-mono text-secondary">{entry.type}</span> — {entry.label}
              </li>
            ))}
          </ol>
        ) : null}
      </div>
    </div>
  );
}
