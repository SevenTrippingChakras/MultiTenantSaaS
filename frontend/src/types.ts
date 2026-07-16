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

// A keyset page from the API: the items plus a cursor for the next page
// (null when there are no more).
export interface Page<T> {
  items: T[];
  next_cursor: string | null;
}

// --- Usage & billing (Phase 10/11) ---

// A month-to-date counter for one scope (user or tenant).
export interface Counter {
  total_tokens: number;
  cost_usd: number;
}

// The signed-in user's quota position for the current period. `null` limit /
// remaining means an unlimited (Enterprise) plan.
export interface Quota {
  plan: string;
  monthly_token_limit: number | null;
  used_tokens: number;
  remaining_tokens: number | null;
}

// One rolled-up day of usage from the worker's summaries.
export interface DailyUsage {
  date: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
}

export interface UsageResponse {
  period: string;
  month_to_date: { user: Counter; tenant: Counter };
  daily: DailyUsage[];
  quota: Quota;
}

// A plan from the public catalog. `null` allowance means unlimited.
export interface Plan {
  name: string;
  monthly_token_limit: number | null;
  features: string[];
}

export interface PlansResponse {
  plans: Plan[];
}

export interface CheckoutResponse {
  checkout_url: string;
}

// A full session transcript, from the feature-gated export endpoint.
export interface ExportResponse {
  session: Session;
  messages: Message[];
}
