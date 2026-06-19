"""Background scheduler for periodic tasks — auto-sync and weekly digests."""

import os
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from ..database import SessionLocal
from .. import models
from ..core.crypto import decrypt

logger = logging.getLogger("sparqai.scheduler")

scheduler = BackgroundScheduler()


def _sync_provider(org_id: int, provider: str):
    """Sync a single provider for a single org."""
    db = SessionLocal()
    try:
        integration = db.query(models.Integration).filter(
            models.Integration.organization_id == org_id,
            models.Integration.provider == provider.upper(),
        ).first()

        if not integration:
            return

        # Log sync start
        sync_log = models.SyncLog(
            organization_id=org_id,
            provider=provider,
            status="running",
        )
        db.add(sync_log)
        db.commit()

        try:
            if provider == "HUBSPOT":
                from ..integrations.hubspot import HubSpotConnector
                connector = HubSpotConnector(access_token=decrypt(integration.access_token))
                results = connector.sync_outcomes(db, organization_id=org_id)
            elif provider == "SALESFORCE":
                from ..integrations.salesforce import SalesforceConnector
                connector = SalesforceConnector(
                    access_token=decrypt(integration.access_token),
                    instance_url=integration.portal_id,
                )
                results = connector.sync_outcomes(db, organization_id=org_id)
            else:
                return

            # Run attribution if new data
            if results["created"] > 0:
                from ..engine import engine as attribution_engine
                attribution_engine.run_full_attribution(db, organization_id=org_id)

            sync_log.status = "success"
            sync_log.created = results["created"]
            sync_log.skipped = results["skipped"]
            sync_log.completed_at = datetime.utcnow()
            db.commit()

            logger.info(f"Auto-sync {provider} for org {org_id}: {results['created']} created, {results['skipped']} skipped")

            # Send sync summary emails
            from .email import send_sync_summary
            admins = db.query(models.User).filter(
                models.User.organization_id == org_id,
                models.User.role.in_(["ADMIN", "MEMBER"]),
                models.User.is_active == True,
            ).all()
            for admin in admins:
                try:
                    send_sync_summary(db, admin, provider, results["created"], results["skipped"])
                except Exception:
                    pass

        except Exception as e:
            sync_log.status = "failed"
            sync_log.error_message = str(e)[:500]
            sync_log.completed_at = datetime.utcnow()
            db.commit()
            logger.error(f"Auto-sync {provider} for org {org_id} failed: {e}")

    finally:
        db.close()


def run_all_syncs():
    """Sync all orgs that have active integrations."""
    db = SessionLocal()
    try:
        integrations = db.query(models.Integration).all()
        for integ in integrations:
            try:
                _sync_provider(integ.organization_id, integ.provider)
            except Exception as e:
                logger.error(f"Sync failed for org {integ.organization_id}/{integ.provider}: {e}")
    finally:
        db.close()


def run_weekly_digests():
    """Send weekly digests to all eligible users."""
    db = SessionLocal()
    try:
        from .email import run_weekly_digests as send_digests
        sent = send_digests(db)
        logger.info(f"Weekly digest job completed: {sent} emails sent")
    finally:
        db.close()


def start_scheduler():
    """Start the background scheduler with default jobs."""
    environment = os.getenv("ENVIRONMENT", "development")

    # Auto-sync every 6 hours
    scheduler.add_job(
        run_all_syncs,
        trigger=IntervalTrigger(hours=6),
        id="auto_sync",
        name="Auto-sync integrations",
        replace_existing=True,
    )

    # Weekly digest every Monday at 9am UTC
    scheduler.add_job(
        run_weekly_digests,
        trigger=CronTrigger(day_of_week="mon", hour=9, minute=0),
        id="weekly_digest",
        name="Weekly ROI digest",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(f"Scheduler started ({environment}) — auto-sync every 6h, digest every Monday 9am UTC")


def stop_scheduler():
    """Stop the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
