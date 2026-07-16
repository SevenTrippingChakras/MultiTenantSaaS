"""Stripe billing (Phase 11): checkout + subscription webhooks (arch I).

Test mode by default: with empty Stripe keys the API refuses billing calls
rather than talking to Stripe. A subscription maps a Stripe recurring *price* to
one of our plans; the tenant's `plan` is the durable subscription state that the
quota check enforces on.

Webhook events are applied **inline against Mongo** (durable + idempotent), not
queued: subscription state is money-critical, so it must not ride the
best-effort Redis path the metering cache uses. Stripe retries on a non-2xx, so
a failed apply is re-delivered rather than lost.
"""

import logging

import stripe

from app import plans
from app.config import settings
from app.core.errors import BillingError
from app.repositories import tenant_repo

logger = logging.getLogger("aichat")


def _price_to_plan() -> dict[str, str]:
    """Map configured Stripe price ids to plan names (skips unset prices)."""
    mapping = {}
    if settings.stripe_price_pro:
        mapping[settings.stripe_price_pro] = plans.PRO
    if settings.stripe_price_enterprise:
        mapping[settings.stripe_price_enterprise] = plans.ENTERPRISE
    return mapping


def _plan_to_price(plan_name: str) -> str | None:
    return {plan: price for price, plan in _price_to_plan().items()}.get(plan_name)


def _require_api_key() -> None:
    if not settings.stripe_api_key:
        raise BillingError("Billing is not configured")
    stripe.api_key = settings.stripe_api_key


async def create_checkout(tenant: dict, email: str, plan_name: str) -> str:
    """Create a Stripe Checkout session for a paid plan and return its URL.

    Reuses the tenant's Stripe customer if one exists (so a repeat purchase
    doesn't duplicate customers), otherwise creates and stores one.
    """
    _require_api_key()
    price_id = _plan_to_price(plan_name)
    if not price_id:
        raise BillingError(f"No purchasable price for plan '{plan_name}'")

    tenant_id = tenant["_id"]
    customer_id = tenant.get("stripe_customer_id")
    if not customer_id:
        customer = stripe.Customer.create(
            email=email, metadata={"tenant_id": str(tenant_id)}
        )
        customer_id = customer.id
        await tenant_repo.set_stripe_customer(tenant_id, customer_id)

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        client_reference_id=str(tenant_id),
        success_url=settings.checkout_success_url,
        cancel_url=settings.checkout_cancel_url,
    )
    if not session.url:
        raise BillingError("Stripe did not return a checkout URL")
    return session.url


def parse_event(payload: bytes, sig_header: str) -> stripe.Event:
    """Verify a webhook's signature and return the event, or raise BillingError."""
    if not settings.stripe_webhook_secret:
        raise BillingError("Webhook secret not configured")
    try:
        return stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except (ValueError, stripe.SignatureVerificationError) as e:
        raise BillingError("Invalid webhook signature") from e


async def _set_plan_for_customer(customer_id: str, plan_name: str) -> None:
    tenant = await tenant_repo.find_by_stripe_customer(customer_id)
    if not tenant:
        logger.warning("stripe webhook for unknown customer %s", customer_id)
        return
    await tenant_repo.set_plan(tenant["_id"], plan_name)
    logger.info("tenant %s moved to plan %s via Stripe", tenant["_id"], plan_name)


async def handle_event(event: stripe.Event) -> None:
    """Apply a subscription lifecycle event to the tenant's plan (idempotent)."""
    etype = event["type"]
    obj = event["data"]["object"]
    if etype in ("customer.subscription.created", "customer.subscription.updated"):
        price_id = obj["items"]["data"][0]["price"]["id"]
        plan_name = _price_to_plan().get(price_id, plans.FREE)
        await _set_plan_for_customer(obj["customer"], plan_name)
    elif etype == "customer.subscription.deleted":
        await _set_plan_for_customer(obj["customer"], plans.FREE)
    else:
        logger.info("stripe webhook ignored: %s", etype)
