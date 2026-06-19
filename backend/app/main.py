import os
import time
import logging
import sentry_sdk

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date

from .database import engine as db_engine, Base, get_db
from . import models, schemas
from .engine import engine as attribution_engine
from .integrations.hubspot import HubSpotConnector
from .routes import auth, integrations, organization, team, audit, export, billing
from .routes import csv_import as csv_routes
from .core import config, security
from .core.crypto import decrypt
from .middleware.auth import get_current_user
from .middleware.rate_limit import RateLimitMiddleware

# Structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("sparqai")

# Initialize Sentry
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=0.2,
        profiles_sample_rate=0.1,
        environment=os.getenv("ENVIRONMENT", "development"),
    )
    logger.info("Sentry initialized for error tracking.")
else:
    logger.info("SENTRY_DSN not set, Sentry disabled.")

# Create tables (fallback for local dev with SQLite — production uses Alembic migrations)
DATABASE_URL = os.getenv("DATABASE_URL", "")
if "sqlite" in DATABASE_URL or not DATABASE_URL:
    try:
        Base.metadata.create_all(bind=db_engine)
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

app = FastAPI(
    title="SparqAI — ROI Decision Intelligence",
    version="0.3.0",
    docs_url="/docs" if ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if ENVIRONMENT != "production" else None,
)

# --- Middleware stack (order matters — last added runs first) ---

# CORS — configurable via env
allowed_origins = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:8000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowed_origins],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# Rate limiting (60 req/min per IP)
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

# Trusted hosts in production
if ENVIRONMENT == "production":
    domain = os.getenv("DOMAIN_NAME", "sparqai.com")
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[f"api.{domain}", f"app.{domain}", domain],
    )


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000
    if request.url.path != "/health":
        logger.info(
            f"{request.method} {request.url.path} {response.status_code} {duration_ms:.0f}ms"
        )
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.on_event("startup")
def on_startup():
    """Start background scheduler for auto-sync and weekly digests."""
    try:
        from .services.scheduler import start_scheduler
        start_scheduler()
    except Exception as e:
        logger.warning(f"Scheduler failed to start: {e}")


@app.on_event("shutdown")
def on_shutdown():
    """Stop background scheduler gracefully."""
    try:
        from .services.scheduler import stop_scheduler
        stop_scheduler()
    except Exception:
        pass


@app.get("/")
def read_root():
    return {"message": "SparqAI — ROI Decision Intelligence API", "version": "0.3.0"}

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(integrations.router, prefix="/api/v1/integrations", tags=["integrations"])
app.include_router(csv_routes.router, prefix="/api/v1/import", tags=["import"])
app.include_router(organization.router, prefix="/api/v1/organization", tags=["organization"])
app.include_router(team.router, prefix="/api/v1/team", tags=["team"])
app.include_router(audit.router, prefix="/api/v1/audit", tags=["audit"])
app.include_router(export.router, prefix="/api/v1/export", tags=["export"])
app.include_router(billing.router, prefix="/api/v1/billing", tags=["billing"])

# Phase 6: Differentiation - Ad Platforms & QuickBooks
from .routes import ads, quickbooks
app.include_router(ads.router, prefix="/api/v1/ads", tags=["ads"])
app.include_router(quickbooks.router, prefix="/api/v1/quickbooks", tags=["quickbooks"])

# CSV Analysis Engine
from .routes import analysis
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["analysis"])



@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    status = "ok" if db_status == "connected" else "degraded"
    return {
        "status": status,
        "version": "0.3.0",
        "environment": ENVIRONMENT,
        "database": db_status,
    }


# ---------------------------------------------------------------------------
# Data seeding (demo)
# ---------------------------------------------------------------------------

@app.post("/api/v1/seed")
def seed_data(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Seeds realistic decisions and directly-linked outcomes for demo."""
    if db.query(models.Decision).filter(models.Decision.organization_id == current_user.organization_id).first():
        return {"message": "Data already seeded. Use DELETE /api/v1/reset to start fresh."}

    decisions = [
        models.Decision(
            description="LinkedIn Q1 Campaign",
            decision_type="AD_CAMPAIGN",
            start_date=date(2026, 1, 15),
            cost=5000.0,
            status="ACTIVE",
            source="MANUAL",
            organization_id=current_user.organization_id,
        ),
        models.Decision(
            description="Senior AE Hire (Sarah)",
            decision_type="HIRE",
            start_date=date(2026, 1, 5),
            cost=8500.0,
            status="ACTIVE",
            source="MANUAL",
            organization_id=current_user.organization_id,
        ),
        models.Decision(
            description="ZoomInfo Subscription",
            decision_type="TOOL",
            start_date=date(2025, 12, 1),
            cost=2000.0,
            status="ACTIVE",
            source="QUICKBOOKS",
            organization_id=current_user.organization_id,
        ),
        models.Decision(
            description="Google Ads Experiment",
            decision_type="AD_CAMPAIGN",
            start_date=date(2026, 1, 10),
            cost=7500.0,
            status="ACTIVE",
            source="MANUAL",
            organization_id=current_user.organization_id,
        ),
        models.Decision(
            description="SaaStr Conference Booth",
            decision_type="VENDOR",
            start_date=date(2026, 1, 1),
            cost=15000.0,
            status="ENDED",
            end_date=date(2026, 1, 3),
            source="MANUAL",
            organization_id=current_user.organization_id,
        ),
    ]

    db.add_all(decisions)
    db.flush()  # get IDs assigned

    # Directly-linked outcomes — we know which decision caused these
    sarah = decisions[1]
    conference = decisions[4]

    direct_outcomes = [
        models.Outcome(
            decision_id=sarah.id,
            metric_name="REVENUE",
            value=8500.0,
            date=date(2026, 1, 22),
            description="TechStartup Inc",
            source="MANUAL",
            source_id=f"seed_direct_1_{current_user.organization_id}",
            organization_id=current_user.organization_id,
        ),
        models.Outcome(
            decision_id=sarah.id,
            metric_name="REVENUE",
            value=45000.0,
            date=date(2026, 2, 10),
            description="Globex Enterprise",
            source="MANUAL",
            source_id=f"seed_direct_2_{current_user.organization_id}",
            organization_id=current_user.organization_id,
        ),
        models.Outcome(
            decision_id=conference.id,
            metric_name="REVENUE",
            value=1500.0,
            date=date(2026, 1, 25),
            description="Trade Show Lead Co",
            source="MANUAL",
            source_id=f"seed_direct_3_{current_user.organization_id}",
            organization_id=current_user.organization_id,
        ),
    ]

    db.add_all(direct_outcomes)
    db.commit()

    # Trigger attribution calculation
    attribution_engine.run_full_attribution(db, organization_id=current_user.organization_id)

    return {
        "message": (
            f"Seeded {len(decisions)} decisions and {len(direct_outcomes)} outcomes. "
            f"Attribution calculation triggered."
        )
    }


@app.delete("/api/v1/reset")
def reset_data(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Clears all data for the current user's organization."""
    org_id = current_user.organization_id
    db.query(models.Attribution).filter(
        models.Attribution.decision_id.in_(
            db.query(models.Decision.id).filter(models.Decision.organization_id == org_id)
        )
    ).delete(synchronize_session=False)
    db.query(models.Outcome).filter(models.Outcome.organization_id == org_id).delete()
    db.query(models.Decision).filter(models.Decision.organization_id == org_id).delete()
    db.commit()
    return {"message": "All data cleared for your organization."}


# ---------------------------------------------------------------------------
# HubSpot integration
# ---------------------------------------------------------------------------

@app.post("/api/v1/integrations/hubspot/ingest")
def ingest_hubspot(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Sync HubSpot deals. Token priority:
    1. DB integration record (from OAuth flow)
    2. HUBSPOT_ACCESS_TOKEN env var (private app token)
    3. Mock data fallback
    """
    integration = db.query(models.Integration).filter(
        models.Integration.organization_id == current_user.organization_id,
        models.Integration.provider == "HUBSPOT"
    ).first()

    token = decrypt(integration.access_token) if (integration and integration.access_token) else None
    connector = HubSpotConnector(access_token=token)
    results = connector.sync_outcomes(db, organization_id=current_user.organization_id)

    if results["created"] > 0:
        background_tasks.add_task(attribution_engine.run_full_attribution, db, organization_id=current_user.organization_id)

    source = "mock data" if connector.is_mock else "HubSpot"
    return {
        "message": f"Synced {results['created']} deals from {source}",
        "created": results["created"],
        "skipped": results["skipped"],
    }


@app.post("/api/v1/integrations/salesforce/ingest")
def ingest_salesforce(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Sync Salesforce Closed Won opportunities. Credential priority:
    1. DB integration record (from OAuth flow)
    2. SALESFORCE_USERNAME + SALESFORCE_PASSWORD + SALESFORCE_SECURITY_TOKEN env vars
    3. Mock data fallback
    """
    from .integrations.salesforce import SalesforceConnector

    integration = db.query(models.Integration).filter(
        models.Integration.organization_id == current_user.organization_id,
        models.Integration.provider == "SALESFORCE"
    ).first()

    username = password = security_token = None
    domain = "login"
    access_token = None
    instance_url = None

    if integration and integration.config and integration.config.get("auth_method") == "password":
        # Paste-flow credentials (stored in config, not access_token)
        username = integration.config.get("username")
        password = decrypt(integration.config.get("password", ""))
        security_token = decrypt(integration.config.get("security_token", ""))
        domain = integration.config.get("domain", "login")
    elif integration and integration.access_token:
        # OAuth flow credentials (existing behaviour, unchanged)
        access_token = decrypt(integration.access_token)
        instance_url = integration.portal_id

    connector = SalesforceConnector(
        access_token=access_token,
        instance_url=instance_url,
        username=username,
        password=password,
        security_token=security_token,
        domain=domain,
    )
    results = connector.sync_outcomes(db, organization_id=current_user.organization_id)

    if results["created"] > 0:
        background_tasks.add_task(attribution_engine.run_full_attribution, db, organization_id=current_user.organization_id)

    source = "mock data" if connector.is_mock else "Salesforce"
    return {
        "message": f"Synced {results['created']} opportunities from {source}",
        "created": results["created"],
        "skipped": results["skipped"],
    }


# ---------------------------------------------------------------------------
# Decision Ledger API
# ---------------------------------------------------------------------------

@app.get("/api/v1/decisions")
def list_decisions(
    decision_type: str = None,
    status: str = None,
    sort_by: str = "roi",
    order: str = "desc",
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Returns decisions with filtering and sorting."""
    query = db.query(models.Decision).filter(
        models.Decision.organization_id == current_user.organization_id
    )
    
    if decision_type and decision_type != "ALL":
        query = query.filter(models.Decision.decision_type == decision_type)
        
    if status and status != "ALL":
        query = query.filter(models.Decision.status == status)
        
    decisions = query.all()
    
    if not decisions:
        return []

    # Fetch summary attributions
    decision_ids = [d.id for d in decisions]
    attributions = db.query(models.Attribution).filter(
        models.Attribution.decision_id.in_(decision_ids),
        models.Attribution.outcome_id == None
    ).all()
    
    attr_map = {a.decision_id: a for a in attributions}

    results = []
    for d in decisions:
        attr = attr_map.get(d.id)

        # Default values if no attribution run yet
        roi = attr.roi_multiple if attr else 0.0
        val = attr.attributed_value if attr else 0.0
        cost = attr.total_cost if attr else (d.cost or 0.0)

        # Parse recommendation|tier format
        raw_rec = attr.recommendation if attr else "WAITING"
        if "|" in raw_rec:
            action, confidence_tier = raw_rec.split("|", 1)
        else:
            action = raw_rec
            confidence_tier = "LOW" if attr else "NONE"

        results.append({
            "id": d.id,
            "description": d.description,
            "decision_type": d.decision_type,
            "type": d.decision_type,
            "start_date": d.start_date,
            "end_date": d.end_date,
            "cost": d.cost,
            "total_cost": cost,
            "status": d.status,
            "source": d.source,
            "roi": roi,
            "value": val,
            "confidence": attr.confidence_score if attr else 0.0,
            "confidence_tier": confidence_tier,
            "action": action,
            "details": "",
        })

    # Sorting options
    reverse = (order == "desc")
    if sort_by == "roi":
        results.sort(key=lambda x: x["roi"], reverse=reverse)
    elif sort_by == "value":
        results.sort(key=lambda x: x["value"], reverse=reverse)
    elif sort_by == "cost":
        results.sort(key=lambda x: x["total_cost"], reverse=reverse)
    elif sort_by == "date":
        results.sort(key=lambda x: x["start_date"] or date.min, reverse=reverse)
        
    return results


@app.get("/api/v1/decisions/{decision_id}")
def get_decision_detail(decision_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Returns full attribution detail for a single decision from DB."""
    decision = db.query(models.Decision).filter(
        models.Decision.id == decision_id,
        models.Decision.organization_id == current_user.organization_id
    ).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    # Fetch Summary Attribution
    attr_summary = db.query(models.Attribution).filter(
        models.Attribution.decision_id == decision.id,
        models.Attribution.outcome_id == None
    ).first()

    if not attr_summary:
         # Fallback if no attribution run
         return {
            "id": decision.id,
            "description": decision.description,
            "roi": 0.0,
            "value": 0.0,
            "confidence": 0.0,
            "action": "PENDING",
            "explanation": "Attribution has not run yet.",
            "related_outcomes": []
         }

    # Fetch Linked Outcomes (Details)
    # Join Attribution -> Outcome to get outcome details
    linked_attrs = db.query(models.Attribution, models.Outcome).join(
        models.Outcome, models.Attribution.outcome_id == models.Outcome.id
    ).filter(
        models.Attribution.decision_id == decision.id,
        models.Attribution.outcome_id != None
    ).all()

    related_outcomes = []
    total_attributed_value = 0.0

    for attr, outcome in linked_attrs:
        attributed_amount = outcome.value * attr.weight
        total_attributed_value += attributed_amount

        # Signal type stored in per-outcome recommendation field
        signal_type = attr.recommendation if attr.recommendation else "LOW"

        related_outcomes.append({
            "id": outcome.id,
            "date": outcome.date,
            "description": outcome.description,
            "value": outcome.value,
            "weight": attr.weight,
            "share": attr.weight,
            "attributed_amount": attributed_amount,
            "signal_type": signal_type,
        })

    # Parse recommendation|tier format from summary row
    raw_rec = attr_summary.recommendation or "WAITING"
    if "|" in raw_rec:
        action, confidence_tier = raw_rec.split("|", 1)
    else:
        action = raw_rec
        confidence_tier = "LOW"

    return {
        "id": decision.id,
        "description": decision.description,
        "type": decision.decision_type,
        "start_date": decision.start_date,
        "end_date": decision.end_date,
        "cost": decision.cost,
        "total_cost": attr_summary.total_cost,
        "status": decision.status,
        "roi": attr_summary.roi_multiple,
        "value": attr_summary.attributed_value,
        "confidence": attr_summary.confidence_score,
        "confidence_tier": confidence_tier,
        "action": action,
        "explanation": _generate_decision_explanation(db, current_user.organization_id, decision, attr_summary),
        "related_outcomes": related_outcomes,
    }


def _generate_decision_explanation(db, organization_id, decision, attr_summary):
    """Generate a data-backed explanation for the decision detail view."""
    try:
        from .services.ai_analyzer import ai_analyzer
        result = ai_analyzer.analyze_decision(db, organization_id, decision.id)
        return result.get("analysis", "Based on multi-touch attribution model.")
    except Exception:
        return "Based on multi-touch attribution model."


@app.get("/api/v1/decisions/{decision_id}/insight")
def get_decision_insight(
    decision_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Generates a comprehensive AI-powered analysis for a specific decision.
    Uses historical benchmarks, pattern detection, risk assessment, and LLM synthesis.
    """
    from .services.ai_analyzer import ai_analyzer

    result = ai_analyzer.analyze_decision(db, current_user.organization_id, decision_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@app.post("/api/v1/decisions", response_model=schemas.Decision)
def create_decision(
    decision_in: schemas.DecisionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    from .services.audit import log_action
    
    decision = models.Decision(
        **decision_in.model_dump(),
        organization_id=current_user.organization_id
    )
    db.add(decision)
    db.flush() # Generate ID
    
    log_action(db, current_user, "CREATE", "DECISION", str(decision.id), decision_in.model_dump())
    
    db.commit()
    db.refresh(decision)
    
    background_tasks.add_task(attribution_engine.run_full_attribution, db, organization_id=current_user.organization_id)
    return decision

@app.put("/api/v1/decisions/{decision_id}", response_model=schemas.Decision)
def update_decision(
    decision_id: int,
    decision_in: schemas.DecisionUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    from .services.audit import log_action

    decision = db.query(models.Decision).filter(
        models.Decision.id == decision_id,
        models.Decision.organization_id == current_user.organization_id
    ).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
        
    update_data = decision_in.model_dump(exclude_unset=True)
    
    # Capture before state? For now just logging the update data
    log_action(db, current_user, "UPDATE", "DECISION", str(decision.id), update_data)
    
    for key, value in update_data.items():
        setattr(decision, key, value)
        
    db.add(decision)
    db.commit()
    db.refresh(decision)
    
    background_tasks.add_task(attribution_engine.run_full_attribution, db, organization_id=current_user.organization_id)
    return decision

@app.delete("/api/v1/decisions/{decision_id}")
def delete_decision(
    decision_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    from .services.audit import log_action

    decision = db.query(models.Decision).filter(
        models.Decision.id == decision_id,
        models.Decision.organization_id == current_user.organization_id
    ).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
        
    log_action(db, current_user, "DELETE", "DECISION", str(decision.id), {"description": decision.description})
        
    # Delete related attributions first (cascade usually handles this but let's be safe)
    db.query(models.Attribution).filter(models.Attribution.decision_id == decision.id).delete()
    db.delete(decision)
    db.commit()
    return {"message": "Decision deleted"}

@app.post("/api/v1/outcomes", response_model=schemas.Outcome)
def create_outcome(
    outcome_in: schemas.OutcomeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    from .services.audit import log_action

    # Verify decision ownership if linking
    if outcome_in.decision_id:
        decision = db.query(models.Decision).filter(
            models.Decision.id == outcome_in.decision_id,
            models.Decision.organization_id == current_user.organization_id
        ).first()
        if not decision:
             raise HTTPException(status_code=404, detail="Linked Decision not found")

    outcome = models.Outcome(
        **outcome_in.model_dump(),
        organization_id=current_user.organization_id,
        source="MANUAL"
    )
    db.add(outcome)
    db.flush()
    
    log_action(db, current_user, "CREATE", "OUTCOME", str(outcome.id), outcome_in.model_dump())
    
    db.commit()
    db.refresh(outcome)
    
    attribution_engine.run_full_attribution(db, organization_id=current_user.organization_id)
    return outcome

@app.delete("/api/v1/outcomes/{outcome_id}")
def delete_outcome(
    outcome_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    from .services.audit import log_action

    outcome = db.query(models.Outcome).filter(
        models.Outcome.id == outcome_id,
        models.Outcome.organization_id == current_user.organization_id
    ).first()
    if not outcome:
        raise HTTPException(status_code=404, detail="Outcome not found")
        
    log_action(db, current_user, "DELETE", "OUTCOME", str(outcome.id), {"metric": outcome.metric_name, "value": outcome.value})
        
    db.delete(outcome)
    db.commit()
    
    attribution_engine.run_full_attribution(db, organization_id=current_user.organization_id)
    return {"message": "Outcome deleted"}
