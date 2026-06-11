import { describe, it, expect } from "vitest";
import { SseFrameParser, parseSseTranscript } from "./sse";
import transcript from "../test/fixtures/sse-market-brief.transcript.txt?raw";

describe("SseFrameParser", () => {
  it("parses the live Wave-0 transcript into 8 coarse events", () => {
    const events = parseSseTranscript(transcript);
    const types = events.map((e) => e.event);
    expect(types).toEqual([
      "task.started",
      "task.delegation_started",
      "task.delegation_completed",
      "task.delegation_started",
      "task.delegation_completed",
      "task.delegation_started",
      "task.delegation_completed",
      "task.completed",
    ]);
  });

  it("reassembles events split across arbitrary chunk boundaries", () => {
    const parser = new SseFrameParser();
    const events = [];
    // feed one character at a time — the worst-case boundary split
    for (const ch of transcript) events.push(...parser.push(ch));
    events.push(...parser.flush());
    expect(events.map((e) => e.event).filter((t) => t === "task.completed")).toHaveLength(1);
  });

  it("parses event + JSON data fields", () => {
    const [first] = parseSseTranscript(transcript);
    expect(first?.event).toBe("task.started");
    expect(first?.data).toMatchObject({ started_at: expect.any(String) });
  });

  it("ignores frames without a data line", () => {
    expect(parseSseTranscript("event: ping\n\n")).toEqual([]);
  });
});
