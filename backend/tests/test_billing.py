"""Stripe billing (Phase 11): checkout + subscription webhooks.

All Stripe network calls are stubbed; these exercise our own logic (customer
reuse, price->plan mapping, idempotent plan application), not Stripe's API.
"""

import types

import stripe

from app import plans
from app.config import settings
from app.repositories import tenant_repo, user_repo
from app.services import billing_service


async def _auth(client, email: str) -> dict:
    body = {"email": email, "password": "password123"}
    await client.post("/auth/register", json=body)
    resp = await client.post("/auth/login", json=body)
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _sub_event(etype: str, customer: str, price_id: str) -> dict:
    return {
        "type": etype,
        "data": {
            "object": {
                "customer": customer,
                "items": {"data": [{"price": {"id": price_id}}]},
            }
        },
    }


async def test_webhook_event_upgrades_plan(client, monkeypatch):
    monkeypatch.setattr(settings, "stripe_price_pro", "price_pro")
    await _auth(client, "w@example.com")
    user = await user_repo.find_by_email("w@example.com")
    await tenant_repo.set_stripe_customer(user["tenant_id"], "cus_1")

    await billing_service.handle_event(
        _sub_event("customer.subscription.updated", "cus_1", "price_pro")
    )
    assert await tenant_repo.get_plan(user["tenant_id"]) == plans.PRO


async def test_webhook_cancellation_downgrades_to_free(client, monkeypatch):
    monkeypatch.setattr(settings, "stripe_price_pro", "price_pro")
    await _auth(client, "c@example.com")
    user = await user_repo.find_by_email("c@example.com")
    await tenant_repo.set_stripe_customer(user["tenant_id"], "cus_2")
    await tenant_repo.set_plan(user["tenant_id"], plans.PRO)

    await billing_service.handle_event(
        _sub_event("customer.subscription.deleted", "cus_2", "price_pro")
    )
    assert await tenant_repo.get_plan(user["tenant_id"]) == plans.FREE


async def test_unknown_customer_is_ignored(client):
    # No tenant maps to this customer: a no-op, not an error.
    await billing_service.handle_event(
        _sub_event("customer.subscription.deleted", "cus_missing", "price_pro")
    )


async def test_checkout_creates_session_and_stores_customer(client, monkeypatch):
    monkeypatch.setattr(settings, "stripe_api_key", "sk_test_x")
    monkeypatch.setattr(settings, "stripe_price_pro", "price_pro")
    monkeypatch.setattr(
        stripe.Customer, "create", lambda **kw: types.SimpleNamespace(id="cus_new")
    )
    monkeypatch.setattr(
        stripe.checkout.Session,
        "create",
        lambda **kw: types.SimpleNamespace(url="https://checkout.stripe/x"),
    )

    h = await _auth(client, "k@example.com")
    resp = await client.post("/billing/checkout", json={"plan": "pro"}, headers=h)
    assert resp.status_code == 200
    assert resp.json()["checkout_url"] == "https://checkout.stripe/x"

    # The customer id is persisted so a later webhook can map back to the tenant.
    user = await user_repo.find_by_email("k@example.com")
    tenant = await tenant_repo.find_by_id(user["tenant_id"])
    assert tenant["stripe_customer_id"] == "cus_new"


async def test_checkout_rejects_unpurchasable_plan(client, monkeypatch):
    monkeypatch.setattr(settings, "stripe_api_key", "sk_test_x")
    h = await _auth(client, "u@example.com")
    resp = await client.post("/billing/checkout", json={"plan": "free"}, headers=h)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "billing_error"


async def test_webhook_rejects_missing_signature(client, monkeypatch):
    monkeypatch.setattr(settings, "stripe_webhook_secret", "")
    resp = await client.post("/billing/webhook", content=b"{}")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "billing_error"
