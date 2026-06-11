/**
 * Hand-rolled SSE reader (phase-spec amendment: native EventSource cannot send
 * an Authorization header, and the backend authenticates the stream with a
 * Bearer token). We read the fetch ReadableStream and parse `event:`/`data:`
 * frames separated by a blank line.
 *
 * Split into a pure frame parser (unit-testable on chunk boundaries) and the
 * fetch driver.
 */

export interface SseEvent {
  event: string;
  data: unknown;
}

/**
 * Stateful frame parser — feed it raw chunks (which may split mid-frame) and it
 * emits complete events. SSE frames are separated by a blank line ("\n\n").
 */
export class SseFrameParser {
  private buffer = "";

  /** Push a chunk; returns any events completed by it. */
  push(chunk: string): SseEvent[] {
    this.buffer += chunk;
    const events: SseEvent[] = [];
    let sep = this.buffer.indexOf("\n\n");
    while (sep !== -1) {
      const frame = this.buffer.slice(0, sep);
      this.buffer = this.buffer.slice(sep + 2);
      const parsed = parseFrame(frame);
      if (parsed) events.push(parsed);
      sep = this.buffer.indexOf("\n\n");
    }
    return events;
  }

  /** Flush a trailing frame with no terminating blank line (stream end). */
  flush(): SseEvent[] {
    const frame = this.buffer.trim();
    this.buffer = "";
    const parsed = frame ? parseFrame(frame) : null;
    return parsed ? [parsed] : [];
  }
}

/** Parse one frame's lines into an event (null if it carries no event/data). */
function parseFrame(frame: string): SseEvent | null {
  let event = "message";
  const dataLines: string[] = [];
  for (const rawLine of frame.split("\n")) {
    const line = rawLine.replace(/\r$/, "");
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).replace(/^ /, ""));
    }
    // comment lines (":") and unknown fields are ignored
  }
  if (dataLines.length === 0) return null;
  const dataStr = dataLines.join("\n");
  let data: unknown = dataStr;
  try {
    data = JSON.parse(dataStr);
  } catch {
    // non-JSON data stays a string
  }
  return { event, data };
}

/** Parse a whole transcript at once (used by fixtures/tests). */
export function parseSseTranscript(text: string): SseEvent[] {
  const parser = new SseFrameParser();
  return [...parser.push(text), ...parser.flush()];
}

export interface StreamOptions {
  signal?: AbortSignal;
  onEvent: (event: SseEvent) => void;
}

/**
 * Open the SSE stream with a Bearer header and dispatch each event.
 * Resolves when the stream ends (terminal event + EOF) or aborts.
 */
export async function streamSse(
  url: string,
  accessToken: string | null,
  opts: StreamOptions,
): Promise<void> {
  const headers: Record<string, string> = { Accept: "text/event-stream" };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;

  const res = await fetch(url, {
    headers,
    ...(opts.signal ? { signal: opts.signal } : {}),
  });
  if (!res.ok || !res.body) {
    throw new Error(`SSE stream failed: ${String(res.status)}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  const parser = new SseFrameParser();
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      for (const event of parser.push(decoder.decode(value, { stream: true }))) {
        opts.onEvent(event);
      }
    }
    for (const event of parser.flush()) opts.onEvent(event);
  } finally {
    reader.releaseLock();
  }
}
