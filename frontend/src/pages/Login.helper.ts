import { login, register } from "../api";
import { setToken } from "../token";

// Authenticate the user: register first when signing up, then log in and store
// the returned access token. Throws on failure (the caller shows the message).
export async function authenticate(
  mode: "login" | "register",
  email: string,
  password: string,
): Promise<void> {
  if (mode === "register") await register(email, password);
  const response = await login(email, password);
  setToken(response.data.access_token);
}
