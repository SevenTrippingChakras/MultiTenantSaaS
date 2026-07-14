import { logout } from "./api";
import { clearToken } from "./token";

// Log out best-effort, then clear local auth state regardless of the outcome.
export async function signOut(): Promise<void> {
  try {
    await logout();
  } catch {
    // Best effort: still clear local state even if the request fails.
  }
  clearToken();
}
