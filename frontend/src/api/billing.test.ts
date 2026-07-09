import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { billingApi } from "./billing";
import { useAuthStore } from "@/stores/auth";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("billingApi", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "access-1",
      refreshToken: "refresh-1",
      user: null,
      isAuthenticated: true,
    });
  });
  afterEach(() => vi.restoreAllMocks());

  it("getBalance() GETs /billing/balance", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(200, {
        cell_id: "c1",
        balance_credits: "100.0000",
        period_usage_credits: "5.0000",
        daily_usage_credits: "1.0000",
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await billingApi.getBalance();

    expect(result.balance_credits).toBe("100.0000");
    const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/billing/balance");
  });
});
