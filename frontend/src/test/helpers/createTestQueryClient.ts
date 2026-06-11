import { QueryClient } from "@tanstack/react-query";

/** A QueryClient tuned for tests — no retries, no caching surprises. */
export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: 0 },
      mutations: { retry: false },
    },
  });
}
