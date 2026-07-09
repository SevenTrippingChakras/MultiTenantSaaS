export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface Session {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id?: string;
  role: "user" | "assistant";
  content: string;
  created_at?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}
