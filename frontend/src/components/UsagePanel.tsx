import { useEffect, useState } from "react";
import { ArrowLeft, Check, Gauge, Loader2, RefreshCw, Sparkles } from "lucide-react";
import { loadUsageData, upgradeTo, type UsageData } from "./UsagePanel.helper";
import type { Plan, Quota } from "../types";
import { cn } from "@/lib/utils";

interface UsagePanelProps {
  onClose: () => void;
}

const fmt = (n: number) => n.toLocaleString();
const usd = (n: number) => "$" + n.toFixed(4);
const label = (name: string) => name.charAt(0).toUpperCase() + name.slice(1);

// The plan's monthly token allowance as a share used; `null` limit = unlimited.
function QuotaMeter({ quota }: { quota: Quota }) {
  const unlimited = quota.monthly_token_limit === null;
  const limit = quota.monthly_token_limit ?? 0;
  const pct = unlimited ? 0 : Math.min(100, Math.round((quota.used_tokens / limit) * 100));
  const over = !unlimited && quota.used_tokens >= limit;

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Gauge className="size-5 text-moss" />
          <span className="font-semibold">This month</span>
        </div>
        <span className="rounded-full bg-moss/15 px-3 py-1 text-xs font-semibold text-moss uppercase ring-1 ring-moss/30">
          {label(quota.plan)} plan
        </span>
      </div>

      {unlimited ? (
        <p className="mt-4 text-2xl font-bold">
          {fmt(quota.used_tokens)}{" "}
          <span className="text-base font-normal text-muted-foreground">tokens · unlimited</span>
        </p>
      ) : (
        <>
          <div className="mt-4 flex items-baseline justify-between">
            <p className="text-2xl font-bold">{fmt(quota.used_tokens)}</p>
            <p className="text-sm text-muted-foreground">of {fmt(limit)} tokens</p>
          </div>
          <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-white/10">
            <div
              className={cn("h-full rounded-full transition-all", over ? "bg-destructive" : "bg-moss")}
              style={{ width: `${pct}%` }}
            />
          </div>
          <p className={cn("mt-2 text-sm", over ? "text-destructive" : "text-muted-foreground")}>
            {over
              ? "Quota reached — new messages are blocked until you upgrade."
              : `${fmt(quota.remaining_tokens ?? 0)} tokens remaining (${100 - pct}%)`}
          </p>
        </>
      )}
    </div>
  );
}

function PlanCard({
  plan,
  current,
  busy,
  onUpgrade,
}: {
  plan: Plan;
  current: boolean;
  busy: boolean;
  onUpgrade: (name: string) => void;
}) {
  const purchasable = plan.name !== "free" && !current;
  return (
    <div
      className={cn(
        "flex flex-col gap-3 rounded-2xl border p-5",
        current ? "border-moss/50 bg-moss/10" : "border-white/10 bg-white/5",
      )}
    >
      <div className="flex items-center justify-between">
        <span className="font-semibold">{label(plan.name)}</span>
        {current && (
          <span className="rounded-full bg-moss/20 px-2.5 py-0.5 text-xs font-semibold text-moss">
            Current
          </span>
        )}
      </div>
      <p className="text-sm text-muted-foreground">
        {plan.monthly_token_limit === null
          ? "Unlimited tokens / month"
          : `${fmt(plan.monthly_token_limit)} tokens / month`}
      </p>
      <ul className="flex flex-col gap-1.5">
        {plan.features.length === 0 ? (
          <li className="text-sm text-muted-foreground">Core chat</li>
        ) : (
          plan.features.map((f) => (
            <li key={f} className="flex items-center gap-2 text-sm">
              <Check className="size-4 text-moss" />
              {f.replace(/_/g, " ")}
            </li>
          ))
        )}
      </ul>
      {purchasable && (
        <button
          onClick={() => onUpgrade(plan.name)}
          disabled={busy}
          className="mt-auto flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-ember to-[#ff6f2a] py-2.5 font-semibold text-[#2a1400] shadow-lg shadow-ember/25 transition hover:brightness-105 active:scale-[0.98] disabled:opacity-60"
        >
          {busy ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
          Upgrade
        </button>
      )}
    </div>
  );
}

export default function UsagePanel({ onClose }: UsagePanelProps) {
  const [data, setData] = useState<UsageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [checkoutBusy, setCheckoutBusy] = useState<string | null>(null);
  const [checkoutError, setCheckoutError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setData(await loadUsageData());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load usage");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function upgrade(plan: string) {
    setCheckoutBusy(plan);
    setCheckoutError(null);
    try {
      // On success the browser navigates away to Stripe; if it returns here,
      // no redirect happened, so surface whatever went wrong.
      await upgradeTo(plan);
    } catch (e) {
      setCheckoutError(e instanceof Error ? e.message : "Could not start checkout");
      setCheckoutBusy(null);
    }
  }

  return (
    <main className="glass flex flex-1 flex-col overflow-hidden rounded-2xl">
      <div className="flex items-center gap-3 border-b border-white/10 px-5 py-4">
        <button
          onClick={onClose}
          title="Back to chat"
          className="flex size-9 items-center justify-center rounded-lg text-muted-foreground transition hover:bg-white/5 hover:text-foreground"
        >
          <ArrowLeft className="size-5" />
        </button>
        <h1 className="text-lg font-bold">Usage &amp; Billing</h1>
        {data && (
          <span className="ml-auto text-sm text-muted-foreground">Period {data.usage.period}</span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-3xl flex-col gap-6 px-5 py-8">
          {loading && (
            <div className="mt-24 flex flex-col items-center gap-3 text-muted-foreground">
              <Loader2 className="size-8 animate-spin text-moss" />
              <span>Loading usage…</span>
            </div>
          )}

          {error && !loading && (
            <div className="mt-24 flex flex-col items-center gap-3 text-center">
              <p className="text-destructive">{error}</p>
              <button
                onClick={load}
                className="flex items-center gap-2 rounded-lg border border-white/15 px-4 py-2 text-sm text-muted-foreground transition hover:text-foreground"
              >
                <RefreshCw className="size-4" /> Retry
              </button>
            </div>
          )}

          {data && !loading && (
            <>
              <QuotaMeter quota={data.usage.quota} />

              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <p className="text-xs font-semibold tracking-widest text-muted-foreground uppercase">
                    You
                  </p>
                  <p className="mt-2 text-xl font-bold">
                    {fmt(data.usage.month_to_date.user.total_tokens)}
                    <span className="text-sm font-normal text-muted-foreground"> tokens</span>
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {usd(data.usage.month_to_date.user.cost_usd)}
                  </p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <p className="text-xs font-semibold tracking-widest text-muted-foreground uppercase">
                    Workspace
                  </p>
                  <p className="mt-2 text-xl font-bold">
                    {fmt(data.usage.month_to_date.tenant.total_tokens)}
                    <span className="text-sm font-normal text-muted-foreground"> tokens</span>
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {usd(data.usage.month_to_date.tenant.cost_usd)}
                  </p>
                </div>
              </div>

              <section>
                <h2 className="mb-2 px-1 text-sm font-semibold tracking-widest text-muted-foreground uppercase">
                  Daily usage
                </h2>
                {data.usage.daily.length === 0 ? (
                  <p className="rounded-2xl border border-white/10 bg-white/5 px-4 py-6 text-center text-sm text-muted-foreground">
                    No usage recorded yet this period.
                  </p>
                ) : (
                  <div className="overflow-x-auto rounded-2xl border border-white/10">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-white/10 text-left text-xs tracking-wider text-muted-foreground uppercase">
                          <th className="px-4 py-2.5 font-semibold">Date</th>
                          <th className="px-4 py-2.5 font-semibold">Model</th>
                          <th className="px-4 py-2.5 text-right font-semibold">Tokens</th>
                          <th className="px-4 py-2.5 text-right font-semibold">Cost</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.usage.daily.map((d, i) => (
                          <tr key={`${d.date}-${d.model}-${i}`} className="border-b border-white/5 last:border-0">
                            <td className="px-4 py-2.5">{d.date}</td>
                            <td className="px-4 py-2.5 text-muted-foreground">{d.model}</td>
                            <td className="px-4 py-2.5 text-right tabular-nums">{fmt(d.total_tokens)}</td>
                            <td className="px-4 py-2.5 text-right tabular-nums">{usd(d.cost_usd)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>

              <section>
                <h2 className="mb-2 px-1 text-sm font-semibold tracking-widest text-muted-foreground uppercase">
                  Plans
                </h2>
                {checkoutError && (
                  <p className="mb-3 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-2 text-sm text-destructive">
                    {checkoutError}
                  </p>
                )}
                <div className="grid gap-3 sm:grid-cols-3">
                  {data.plans.map((p) => (
                    <PlanCard
                      key={p.name}
                      plan={p}
                      current={p.name === data.usage.quota.plan}
                      busy={checkoutBusy === p.name}
                      onUpgrade={upgrade}
                    />
                  ))}
                </div>
              </section>
            </>
          )}
        </div>
      </div>
    </main>
  );
}
