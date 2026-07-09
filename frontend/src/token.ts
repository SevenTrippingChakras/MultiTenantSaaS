// JWT storage. Kept in localStorage so the session survives page reloads.
const KEY = "aichat_token";

export const getToken = (): string | null => localStorage.getItem(KEY);
export const setToken = (t: string): void => localStorage.setItem(KEY, t);
export const clearToken = (): void => localStorage.removeItem(KEY);
