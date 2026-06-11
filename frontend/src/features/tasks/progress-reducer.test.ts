import { describe, it, expect } from "vitest";
import { parseSseTranscript, type SseEvent } from "@/api/sse";
import { replayProgress, progressReducer, initialProgressState } from "./progress-reducer";
import transcript from "../../test/fixtures/sse-market-brief.transcript.txt?raw";

describe("progressReducer", () => {
  it("replays the live ledger to completed with 3 done agents + 3 artifacts", () => {
    const state = replayProgress(parseSseTranscript(transcript));
    expect(state.phase).toBe("completed");
    expect(state.agents.map((a) => a.status)).toEqual(["done", "done", "done"]);
    expect(state.agents.map((a) => a.slug)).toEqual(["researcher", "analyst", "writer"]);
    const artifactTypes = state.artifacts.map((a) => a.type).sort();
    expect(artifactTypes).toEqual(["analysis", "brief", "matrix"]);
  });

  it("marks an agent running on delegation_started, done on completed", () => {
    let state = initialProgressState();
    state = progressReducer(state, { event: "task.started", data: { started_at: "now" } });
    expect(state.phase).toBe("running");
    state = progressReducer(state, {
      event: "task.delegation_started",
      data: { target_agent_slug: "researcher" },
    });
    expect(state.agents.find((a) => a.slug === "researcher")?.status).toBe("running");
    expect(state.agents.find((a) => a.slug === "analyst")?.status).toBe("pending");
    state = progressReducer(state, {
      event: "task.delegation_completed",
      data: { target_agent_slug: "researcher" },
    });
    expect(state.agents.find((a) => a.slug === "researcher")?.status).toBe("done");
  });

  it("tolerates all 9 contract event types incl. Wave-1 per-token (AC11)", () => {
    const synthetic: SseEvent[] = [
      { event: "task.started", data: { started_at: "t" } },
      { event: "task.step_started", data: { target_agent_slug: "analyst" } },
      { event: "task.step_token", data: { token: "Ана" } },
      { event: "task.step_token", data: { token: "литик" } },
      { event: "task.step_completed", data: { target_agent_slug: "analyst" } },
      { event: "some.unknown.future.event", data: { x: 1 } },
      { event: "task.completed", data: { result: { artifacts: [] } } },
    ];
    const state = synthetic.reduce(progressReducer, initialProgressState());
    expect(state.phase).toBe("completed");
    // step_started/step_completed drove the analyst card; unknown event tolerated
    expect(state.agents.find((a) => a.slug === "analyst")?.status).toBe("done");
    expect(state.log.some((l) => l.type === "some.unknown.future.event")).toBe(true);
  });

  it("handles failed and cancelled terminal events", () => {
    const failed = progressReducer(initialProgressState(), { event: "task.failed", data: {} });
    expect(failed.phase).toBe("failed");
    const cancelled = progressReducer(initialProgressState(), {
      event: "task.cancelled",
      data: {},
    });
    expect(cancelled.phase).toBe("cancelled");
  });
});
