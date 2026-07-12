// Access token kept in memory only (never localStorage) so page JavaScript /
// XSS can't read it. The refresh token lives in an httpOnly cookie the browser
// sends automatically; on reload the app silently refreshes to get a new access
// token (see refreshAccessToken in api.ts).
let accessToken: string | null = null;

export const getToken = (): string | null => accessToken;
export const setToken = (t: string): void => {
  accessToken = t;
};
export const clearToken = (): void => {
  accessToken = null;
};
