import os
import logging
from typing import List, Optional
from datetime import datetime

from simple_salesforce import Salesforce
from sqlalchemy.orm import Session

from ..models import Outcome

logger = logging.getLogger(__name__)


class SalesforceConnector:
    """
    Connects to Salesforce using one of three methods, in priority order:

      1. OAuth access_token + instance_url (passed directly — from OAuth exchange flow)
      2. username + password + security_token (passed directly — from paste-token flow,
         OR falls back to SALESFORCE_USERNAME / SALESFORCE_PASSWORD / SALESFORCE_SECURITY_TOKEN
         env vars if not passed)
      3. Mock data fallback if none of the above are available

    This signature is backwards compatible — existing callers that only pass
    access_token/instance_url continue to work unchanged.
    """

    def __init__(
        self,
        access_token: Optional[str] = None,
        instance_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        security_token: Optional[str] = None,
        domain: Optional[str] = None,
    ):
        self.sf = None
        self.is_mock = False

        # --- Method 1: OAuth token (from DB integration record / exchange flow) ---
        if access_token and not access_token.startswith("mock") and instance_url and not instance_url.startswith("mock"):
            try:
                self.sf = Salesforce(instance_url=instance_url, session_id=access_token)
                logger.info("Salesforce client initialised with OAuth token.")
                return
            except Exception as e:
                logger.error(f"Salesforce OAuth init failed: {e}")

        # --- Method 2: Username / Password / Security Token (passed directly, or env vars) ---
        _username = username or os.getenv("SALESFORCE_USERNAME", "")
        _password = password or os.getenv("SALESFORCE_PASSWORD", "")
        _token    = security_token or os.getenv("SALESFORCE_SECURITY_TOKEN", "")
        _domain   = domain or os.getenv("SALESFORCE_DOMAIN", "login")

        if _username and _password and _token:
            try:
                self.sf = Salesforce(
                    username=_username,
                    password=_password,
                    security_token=_token,
                    domain=_domain,
                )
                logger.info("Salesforce client initialised with username/password.")
                return
            except Exception as e:
                logger.error(f"Salesforce username/password init failed: {e}")

        # --- Fallback: mock ---
        logger.info("Salesforce: using mock data (no valid credentials available).")
        self.is_mock = True

    def fetch_closed_won_opportunities(self, limit: int = 100) -> List[dict]:
        """Fetch Closed Won opportunities from Salesforce."""
        if self.is_mock or not self.sf:
            return self._get_mock_data()

        try:
            query = (
                "SELECT Id, Name, Amount, CloseDate, StageName, OwnerId "
                "FROM Opportunity "
                "WHERE StageName = 'Closed Won' "
                "ORDER BY CloseDate DESC "
                f"LIMIT {limit}"
            )
            result = self.sf.query(query)
            records = result.get("records", [])
            logger.info(f"Salesforce: fetched {len(records)} opportunities.")
            return records
        except Exception as e:
            logger.error(f"Salesforce API error: {e}")
            return []

    def sync_outcomes(self, db: Session, organization_id: int, limit: int = 100) -> dict:
        """Fetch opportunities and upsert as Outcome records. Skips duplicates."""
        opportunities = self.fetch_closed_won_opportunities(limit=limit)
        created = 0
        skipped = 0

        for opp in opportunities:
            amount    = opp.get("Amount")
            close_str = opp.get("CloseDate")
            name      = opp.get("Name", "Unknown Opportunity")
            opp_id    = opp.get("Id")
            source_id = f"salesforce_{opp_id}" if opp_id else None

            if not amount or not close_str:
                skipped += 1
                continue

            if source_id:
                if db.query(Outcome).filter(
                    Outcome.source_id == source_id,
                    Outcome.organization_id == organization_id
                ).first():
                    skipped += 1
                    continue

            try:
                date_obj = datetime.strptime(close_str[:10], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                logger.warning(f"Skipping opportunity '{name}': bad date '{close_str}'")
                skipped += 1
                continue

            db.add(Outcome(
                metric_name="REVENUE",
                value=float(amount),
                date=date_obj,
                description=name,
                source="SALESFORCE",
                source_id=source_id,
                organization_id=organization_id,
            ))
            created += 1

        db.commit()
        logger.info(f"Salesforce sync done: {created} created, {skipped} skipped.")
        return {"created": created, "skipped": skipped}

    def _get_mock_data(self) -> List[dict]:
        return [
            {"Id": "sf_mock_1", "Name": "Nexus Global Enterprise",  "Amount": 32000, "CloseDate": "2026-01-28", "StageName": "Closed Won"},
            {"Id": "sf_mock_2", "Name": "CloudBridge SaaS",         "Amount": 8500,  "CloseDate": "2026-02-05", "StageName": "Closed Won"},
            {"Id": "sf_mock_3", "Name": "Pinnacle Consulting",       "Amount": 12000, "CloseDate": "2026-02-14", "StageName": "Closed Won"},
            {"Id": "sf_mock_4", "Name": "Velocity Logistics",        "Amount": 18500, "CloseDate": "2026-02-22", "StageName": "Closed Won"},
            {"Id": "sf_mock_5", "Name": "Apex Digital Partners",     "Amount": 45000, "CloseDate": "2026-03-10", "StageName": "Closed Won"},
            {"Id": "sf_mock_6", "Name": "Meridian Health Systems",   "Amount": 27500, "CloseDate": "2026-03-20", "StageName": "Closed Won"},
        ]
