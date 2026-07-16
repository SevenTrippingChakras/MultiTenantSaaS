import { createCheckout, getPlans, getUsage } from "../api";
import type { Plan, UsageResponse } from "../types";

// Data-loading for the Usage & Billing panel: call the services and pull out
// exactly what the view needs, keeping response-shape details out of the component.

export interface UsageData {
  usage: UsageResponse;
  plans: Plan[];
}

// Usage and the plan catalog are independent reads, so fetch them in parallel.
export async function loadUsageData(): Promise<UsageData> {
  const [usage, plans] = await Promise.all([getUsage(), getPlans()]);
  return { usage: usage.data, plans: plans.data.plans };
}

// Start Stripe Checkout for a paid plan and hand the browser off to Stripe.
export async function upgradeTo(plan: string): Promise<void> {
  const res = await createCheckout(plan);
  window.location.href = res.data.checkout_url;
}
