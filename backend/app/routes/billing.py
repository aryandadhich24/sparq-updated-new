"""Stripe billing routes — subscriptions, checkout, portal, webhooks."""

import os
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from .. import models
from ..middleware.auth import get_current_user

logger = logging.getLogger("sparqai.billing")
router = APIRouter()

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Lazy import stripe to avoid crash if not installed yet
_stripe = None


def get_stripe():
    global _stripe
    if _stripe is None:
        try:
            import stripe
            stripe.api_key = STRIPE_SECRET_KEY
            _stripe = stripe
        except ImportError:
            raise HTTPException(status_code=503, detail="Billing service unavailable")
    return _stripe


PLANS = {
    "starter": {
        "name": "Starter",
        "price_monthly": 99,
        "decisions_limit": 50,
        "users_limit": 3,
        "integrations": ["hubspot"],
    },
    "growth": {
        "name": "Growth",
        "price_monthly": 499,
        "decisions_limit": 500,
        "users_limit": 15,
        "integrations": ["hubspot", "salesforce", "google_ads"],
    },
    "enterprise": {
        "name": "Enterprise",
        "price_monthly": 4999,
        "decisions_limit": -1,  # unlimited
        "users_limit": -1,
        "integrations": ["hubspot", "salesforce", "google_ads", "quickbooks", "sso"],
    },
}


class CheckoutRequest(BaseModel):
    plan: str  # starter, growth, enterprise
    billing_cycle: str = "monthly"  # monthly, annual


@router.get("/plans")
def list_plans():
    """Return available pricing plans."""
    return {"plans": PLANS}


@router.get("/status")
def billing_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Return current billing status for the organization."""
    org = db.query(models.Organization).filter(
        models.Organization.id == current_user.organization_id
    ).first()

    return {
        "plan": org.plan or "free",
        "plan_status": org.plan_status or "active",
        "stripe_customer_id": bool(org.stripe_customer_id),
        "plan_expires_at": org.plan_expires_at,
        "limits": PLANS.get(org.plan, PLANS.get("starter", {})),
    }


@router.post("/checkout")
def create_checkout_session(
    req: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a Stripe Checkout session."""
    stripe = get_stripe()

    if req.plan not in PLANS:
        raise HTTPException(status_code=400, detail=f"Invalid plan: {req.plan}")

    org = db.query(models.Organization).filter(
        models.Organization.id == current_user.organization_id
    ).first()

    # Create or retrieve Stripe customer
    if not org.stripe_customer_id:
        customer = stripe.Customer.create(
            email=current_user.email,
            name=org.name,
            metadata={"org_id": str(org.id)},
        )
        org.stripe_customer_id = customer.id
        db.commit()

    plan_config = PLANS[req.plan]
    unit_amount = plan_config["price_monthly"] * 100  # cents

    if req.billing_cycle == "annual":
        unit_amount = int(unit_amount * 12 * 0.8)  # 20% annual discount
        recurring = {"interval": "year"}
    else:
        recurring = {"interval": "month"}

    session = stripe.checkout.Session.create(
        customer=org.stripe_customer_id,
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": f"SparqAI {plan_config['name']}"},
                "unit_amount": unit_amount,
                "recurring": recurring,
            },
            "quantity": 1,
        }],
        mode="subscription",
        success_url=f"{FRONTEND_URL}/settings/billing?success=true",
        cancel_url=f"{FRONTEND_URL}/settings/billing?canceled=true",
        metadata={"org_id": str(org.id), "plan": req.plan},
    )

    return {"checkout_url": session.url, "session_id": session.id}


@router.post("/portal")
def create_portal_session(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a Stripe Customer Portal session for managing subscription."""
    stripe = get_stripe()

    org = db.query(models.Organization).filter(
        models.Organization.id == current_user.organization_id
    ).first()

    if not org.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No billing account found")

    session = stripe.billing_portal.Session.create(
        customer=org.stripe_customer_id,
        return_url=f"{FRONTEND_URL}/settings/billing",
    )

    return {"portal_url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe webhook events."""
    stripe = get_stripe()
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        org_id = data.get("metadata", {}).get("org_id")
        plan = data.get("metadata", {}).get("plan", "starter")
        subscription_id = data.get("subscription")

        if org_id:
            org = db.query(models.Organization).filter(
                models.Organization.id == int(org_id)
            ).first()
            if org:
                org.plan = plan
                org.plan_status = "active"
                org.stripe_subscription_id = subscription_id
                db.commit()
                logger.info(f"Org {org_id} upgraded to {plan}")

    elif event_type == "customer.subscription.updated":
        sub_id = data.get("id")
        org = db.query(models.Organization).filter(
            models.Organization.stripe_subscription_id == sub_id
        ).first()
        if org:
            status = data.get("status")
            if status in ("active", "trialing"):
                org.plan_status = "active"
            elif status == "past_due":
                org.plan_status = "past_due"
            elif status in ("canceled", "unpaid"):
                org.plan_status = "canceled"
            db.commit()

    elif event_type == "customer.subscription.deleted":
        sub_id = data.get("id")
        org = db.query(models.Organization).filter(
            models.Organization.stripe_subscription_id == sub_id
        ).first()
        if org:
            org.plan = "free"
            org.plan_status = "canceled"
            org.stripe_subscription_id = None
            db.commit()
            logger.info(f"Org {org.id} downgraded to free")

    return JSONResponse(content={"received": True})
