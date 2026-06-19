import os
import logging
from typing import List, Optional
from datetime import datetime

from hubspot import HubSpot
from sqlalchemy.orm import Session

from ..models import Outcome

logger = logging.getLogger(__name__)


class HubSpotConnector:
    """
    Connects to HubSpot using a Private App access token.
    Set HUBSPOT_ACCESS_TOKEN in your .env to use your real account.
    If not set, falls back to mock data automatically.
    """

    def __init__(self, access_token: Optional[str] = None):
        # Priority: passed token → env var → mock
        self.access_token = access_token or os.getenv("HUBSPOT_ACCESS_TOKEN", "")
        self.is_mock = not self.access_token or self.access_token.startswith("mock")
        self.client = None

        if not self.is_mock:
            try:
                self.client = HubSpot(access_token=self.access_token)
                logger.info("HubSpot client initialised with real token.")
            except Exception as e:
                logger.error(f"HubSpot client init failed: {e}")
                self.is_mock = True

    def fetch_recent_deals(self, limit: int = 100) -> List[dict]:
        """Fetch deals from HubSpot CRM, or mock data if no token set."""
        if self.is_mock or not self.client:
            logger.info("HubSpot: using mock deal data (set HUBSPOT_ACCESS_TOKEN to use real data).")
            return self._get_mock_data()

        try:
            all_deals = []
            after = None
            while len(all_deals) < limit:
                response = self.client.crm.deals.basic_api.get_page(
                    limit=min(100, limit - len(all_deals)),
                    after=after,
                    properties=[
                        "dealname", "amount", "closedate", "dealstage",
                        "pipeline", "hubspot_owner_id", "hs_object_id",
                    ],
                    archived=False,
                )
                all_deals.extend(response.results)
                if response.paging and response.paging.next:
                    after = response.paging.next.after
                else:
                    break

            logger.info(f"HubSpot: fetched {len(all_deals)} deals.")
            return all_deals
        except Exception as e:
            logger.error(f"HubSpot API error: {e}")
            return []

    def sync_outcomes(self, db: Session, organization_id: int, limit: int = 100) -> dict:
        """Fetch deals and upsert as Outcome records. Skips duplicates."""
        if organization_id is None:
            raise ValueError("organization_id is required")

        deals = self.fetch_recent_deals(limit=limit)
        created = 0
        skipped = 0

        for deal in deals:
            # Handle both SDK objects and plain dicts (mock data)
            props = deal if isinstance(deal, dict) else deal.properties

            amount      = props.get("amount")
            close_date  = props.get("closedate")
            deal_name   = props.get("dealname", "Unknown Deal")
            deal_id     = props.get("hs_object_id") or props.get("deal_id")
            source_id   = f"hubspot_{deal_id}" if deal_id else None

            if not amount or not close_date:
                skipped += 1
                continue

            # Dedup
            if source_id:
                if db.query(Outcome).filter(Outcome.source_id == source_id).first():
                    skipped += 1
                    continue

            try:
                # HubSpot returns ISO strings or epoch-ms
                if "-" in str(close_date):
                    date_obj = datetime.strptime(str(close_date)[:10], "%Y-%m-%d").date()
                else:
                    date_obj = datetime.fromtimestamp(int(close_date) / 1000.0).date()
            except (ValueError, TypeError):
                logger.warning(f"Skipping deal '{deal_name}': bad date '{close_date}'")
                skipped += 1
                continue

            db.add(Outcome(
                metric_name="REVENUE",
                value=float(amount),
                date=date_obj,
                description=deal_name,
                source="HUBSPOT",
                source_id=source_id,
                organization_id=organization_id,
            ))
            created += 1

        db.commit()
        logger.info(f"HubSpot sync done: {created} created, {skipped} skipped.")
        return {"created": created, "skipped": skipped}

    def _get_mock_data(self) -> List[dict]:
        return [
            {"amount": "15000", "closedate": "2026-01-30", "dealname": "Acme Corp Pilot",    "dealstage": "closedwon", "deal_id": "mock_1"},
            {"amount": "3200",  "closedate": "2026-02-03", "dealname": "SmallBiz Pro",        "dealstage": "closedwon", "deal_id": "mock_2"},
            {"amount": "2800",  "closedate": "2026-02-12", "dealname": "QuickServe LLC",      "dealstage": "closedwon", "deal_id": "mock_3"},
            {"amount": "22000", "closedate": "2026-02-18", "dealname": "DataFlow Systems",    "dealstage": "closedwon", "deal_id": "mock_4"},
            {"amount": "9500",  "closedate": "2026-03-01", "dealname": "Vertex Analytics",   "dealstage": "closedwon", "deal_id": "mock_5"},
            {"amount": "18000", "closedate": "2026-03-15", "dealname": "Pinnacle SaaS Co",   "dealstage": "closedwon", "deal_id": "mock_6"},
        ]
