/**
 * Auth mutations (TanStack Query). The store is the single auth source; these
 * hooks orchestrate the API round-trips and write the resulting session.
 *
 * Login flow:    POST /auth/login -> GET /users/me -> setSession.
 * Register flow: POST /auth/register -> (REQUIRE_EMAIL_VERIFICATION=false
 *                locally) auto-login with the same credentials -> setSession.
 */
import { useMutation, type UseMutationResult } from "@tanstack/react-query";
import { authApi, type RegisterPayload } from "@/api/auth";
import { ApiException } from "@/api/client";
import { useAuthStore, type AuthUser } from "@/stores/auth";
import { toast } from "@/components/ui";

interface LoginInput {
  email: string;
  password: string;
}

/** Run login then /users/me, and persist the session. Returns the user. */
async function loginAndLoadUser(email: string, password: string): Promise<AuthUser> {
  const tokens = await authApi.login(email, password);
  // Store the tokens BEFORE calling /users/me — apiFetch reads the access token
  // from the store, so without this the me() call would go out unauthenticated
  // (401 → failed refresh → cleared session).
  useAuthStore.getState().setTokens(tokens.access_token, tokens.refresh_token);
  const me = await authApi.me();
  const user: AuthUser = {
    id: me.id,
    email: me.email,
    displayName: me.display_name ?? null,
  };
  useAuthStore.getState().setUser(user);
  return user;
}

function toastApiError(error: unknown): void {
  if (error instanceof ApiException) {
    toast.error(error.error.message);
  }
}

export function useLogin(): UseMutationResult<AuthUser, unknown, LoginInput> {
  return useMutation({
    mutationFn: ({ email, password }: LoginInput) => loginAndLoadUser(email, password),
    onError: toastApiError,
  });
}

export function useRegister(): UseMutationResult<AuthUser, unknown, RegisterPayload> {
  return useMutation({
    mutationFn: async (payload: RegisterPayload): Promise<AuthUser> => {
      await authApi.register(payload);
      // Local env disables email verification, so we can auto-login immediately.
      return loginAndLoadUser(payload.email, payload.password);
    },
    onError: toastApiError,
  });
}
