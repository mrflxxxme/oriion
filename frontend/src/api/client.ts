/**
 * Typed fetch wrapper (phase-spec §apiFetch).
 *
 * - Injects `Authorization: Bearer <access>` when authRequired (default).
 * - Validates the JSON response against an optional Zod schema.
 * - On 401: single-flight silent refresh -> retry once -> else clearSession.
 * - Maps backend error codes (RFC 7807) to Russian copy via error-mapping.
 *
 * Lives below the auth store in the dep graph (imports it); the refresh call
 * uses raw fetch (not apiFetch) so there is no import cycle.
 */
import type { z } from "zod";
import { useAuthStore } from "@/stores/auth";
import { mapErrorMessage } from "@/lib/error-mapping";

export const API_BASE = "/api/v1";

export interface ApiError {
  status: number;
  code: string;
  message: string;
  details?: unknown;
}

export class ApiException extends Error {
  constructor(public readonly error: ApiError) {
    super(error.message);
    this.name = "ApiException";
  }
}

export interface FetchOptions<T> {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  schema?: z.ZodType<T>;
  signal?: AbortSignal;
  /** Default true. Set false for register/login/refresh. */
  authRequired?: boolean;
}

/** Parse a backend error body (RFC 7807 problem+json or FastAPI 422). */
async function parseError(res: Response): Promise<ApiError> {
  let code: string | undefined;
  let details: unknown;
  try {
    const body = (await res.json()) as Record<string, unknown>;
    if (typeof body.code === "string") code = body.code;
    if ("detail" in body) details = body.detail;
  } catch {
    // non-JSON error body — fall through to status-based copy
  }
  return { status: res.status, code: code ?? "", message: mapErrorMessage(code, res.status), details };
}

// ---- Single-flight refresh -------------------------------------------------

let refreshInFlight: Promise<boolean> | null = null;

interface RawTokenPair {
  access_token: string;
  refresh_token: string;
}

/** Refresh the access token using the stored refresh token. Returns success. */
async function refreshSession(): Promise<boolean> {
  const { refreshToken, setTokens, clearSession } = useAuthStore.getState();
  if (!refreshToken) return false;
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) {
      clearSession();
      return false;
    }
    const pair = (await res.json()) as RawTokenPair;
    setTokens(pair.access_token, pair.refresh_token);
    return true;
  } catch {
    clearSession();
    return false;
  }
}

/** De-duplicate concurrent 401s onto one refresh round-trip. */
function refreshOnce(): Promise<boolean> {
  refreshInFlight ??= refreshSession().finally(() => {
    refreshInFlight = null;
  });
  return refreshInFlight;
}

// ---- Core fetch ------------------------------------------------------------

async function doFetch(path: string, opts: FetchOptions<unknown>, accessToken: string | null): Promise<Response> {
  const headers: Record<string, string> = {};
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if ((opts.authRequired ?? true) && accessToken) headers["Authorization"] = `Bearer ${accessToken}`;

  const init: RequestInit = {
    method: opts.method ?? (opts.body !== undefined ? "POST" : "GET"),
    headers,
    ...(opts.body !== undefined ? { body: JSON.stringify(opts.body) } : {}),
    ...(opts.signal ? { signal: opts.signal } : {}),
  };
  return fetch(`${API_BASE}${path}`, init);
}

export async function apiFetch<T>(path: string, opts: FetchOptions<T> = {}): Promise<T> {
  const authRequired = opts.authRequired ?? true;
  let res = await doFetch(path, opts, useAuthStore.getState().accessToken);

  // Silent refresh on 401, then retry once with the new token.
  if (res.status === 401 && authRequired) {
    const ok = await refreshOnce();
    if (ok) {
      res = await doFetch(path, opts, useAuthStore.getState().accessToken);
    } else {
      throw new ApiException(await parseError(res));
    }
  }

  if (!res.ok) throw new ApiException(await parseError(res));

  // 204 / empty body
  if (res.status === 204) return undefined as T;
  const data = (await res.json()) as unknown;
  if (opts.schema) {
    const parsed = opts.schema.safeParse(data);
    if (!parsed.success) {
      throw new ApiException({
        status: res.status,
        code: "client.schema_mismatch",
        message: "Неожиданный ответ сервера.",
        details: parsed.error.issues,
      });
    }
    return parsed.data;
  }
  return data as T;
}
