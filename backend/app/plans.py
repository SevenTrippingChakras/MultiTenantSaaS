"""Plan catalog: the tiers a tenant can subscribe to (arch B3).

A plan bundles a monthly token allowance (the quota the hot path enforces), a
set of feature flags, and a rank. Plans are defined in code, not the DB, because
they are the same for every tenant and change rarely; what lives in the DB is a
tenant's *subscription* (which plan it is on, see `tenant_repo`).

`monthly_token_limit is None` means unlimited (Enterprise) — the quota check
skips those. Stripe price ids are env-specific, so they map to plan names in
config (see the Stripe layer), not here.
"""

from dataclasses import dataclass

FREE = "free"
PRO = "pro"
ENTERPRISE = "enterprise"

DEFAULT_PLAN = FREE


@dataclass(frozen=True)
class Plan:
    """One subscription tier. `monthly_token_limit is None` = unlimited."""

    name: str
    monthly_token_limit: int | None
    features: frozenset[str]


_PLANS: dict[str, Plan] = {
    FREE: Plan(FREE, 100_000, frozenset()),
    PRO: Plan(PRO, 2_000_000, frozenset({"export", "priority_support"})),
    ENTERPRISE: Plan(
        ENTERPRISE, None, frozenset({"export", "priority_support", "sso"})
    ),
}


def get_plan(name: str | None) -> Plan:
    """Resolve a plan by name; unknown or missing falls back to Free."""
    return _PLANS.get(name or "", _PLANS[DEFAULT_PLAN])


def all_plans() -> list[Plan]:
    """Every plan in the catalog (for a plans listing endpoint)."""
    return list(_PLANS.values())


def has_feature(plan_name: str | None, feature: str) -> bool:
    """Whether the named plan includes a feature flag."""
    return feature in get_plan(plan_name).features
