import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.core.deps import CurrentUser
from app.core.errors import BillingError
from app.repositories import tenant_repo
from app.services import billing_service

logger = logging.getLogger("aichat")

router = APIRouter(prefix="/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    plan: str


@router.post("/checkout")
async def create_checkout(data: CheckoutRequest, user: CurrentUser):
    """Start a Stripe Checkout for a paid plan; returns the redirect URL."""
    tenant = await tenant_repo.find_by_id(user["tenant_id"])
    if tenant is None:
        raise BillingError("Tenant not found")
    url = await billing_service.create_checkout(tenant, user["email"], data.plan)
    return {"checkout_url": url}


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Receive Stripe subscription events (no auth: Stripe signs the payload).

    The signature is the authentication; a bad/absent one is a 400. Handling is
    inline and idempotent, so Stripe's retry-on-non-2xx makes delivery durable.
    """
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    event = billing_service.parse_event(payload, sig)
    await billing_service.handle_event(event)
    return {"received": True}
