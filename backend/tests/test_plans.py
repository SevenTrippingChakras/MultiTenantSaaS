"""Plan catalog (Phase 11): tiers, allowances, and feature flags."""

from app import plans


def test_get_known_plan():
    pro = plans.get_plan("pro")
    assert pro.name == "pro"
    assert pro.monthly_token_limit == 2_000_000


def test_unknown_plan_falls_back_to_free():
    assert plans.get_plan("does-not-exist").name == plans.FREE
    assert plans.get_plan(None).name == plans.FREE


def test_enterprise_is_unlimited():
    assert plans.get_plan("enterprise").monthly_token_limit is None


def test_higher_tier_has_larger_or_unlimited_allowance():
    free = plans.get_plan("free").monthly_token_limit
    pro = plans.get_plan("pro").monthly_token_limit
    assert free is not None and pro is not None and pro > free


def test_feature_flags_gate_by_plan():
    assert plans.has_feature("pro", "export")
    assert not plans.has_feature("free", "export")
    assert plans.has_feature("enterprise", "sso")
    assert not plans.has_feature("pro", "sso")


def test_all_plans_lists_the_catalog():
    names = {p.name for p in plans.all_plans()}
    assert names == {plans.FREE, plans.PRO, plans.ENTERPRISE}
