"""
Meta Ads (Facebook / Instagram) Connector

Fetches campaign-level spend data from the Marketing API v19.0
with proper pagination, rate-limit handling, and token refresh.
"""
import os
import logging
import time
from datetime import date, timedelta
from typing import Optional, List, Dict, Any

import requests

logger = logging.getLogger(__name__)

META_GRAPH_BASE = "https://graph.facebook.com"
META_TOKEN_URL = f"{META_GRAPH_BASE}/oauth/access_token"

MAX_RETRIES = 3
RETRY_BACKOFF = 2  # seconds, doubles each retry


class MetaAdsConnector:
    """Connector for Meta Marketing API."""

    def __init__(self, access_token: str, ad_account_id: str = ""):
        self.access_token = access_token
        self.ad_account_id = ad_account_id
        self.api_version = "v19.0"

    def _api_url(self, path: str) -> str:
        return f"{META_GRAPH_BASE}/{self.api_version}/{path}"

    def _get(self, url: str, params: Dict = None, retry: int = 0) -> Optional[Dict]:
        """GET request with retry and rate-limit handling."""
        params = params or {}
        params["access_token"] = self.access_token

        try:
            resp = requests.get(url, params=params, timeout=30)
        except requests.exceptions.Timeout:
            if retry < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF * (2 ** retry))
                return self._get(url, params, retry + 1)
            logger.error("Meta API timeout after retries")
            return None

        if resp.status_code == 200:
            return resp.json()

        # Rate limit (error code 17 or 4)
        error_data = resp.json().get("error", {})
        error_code = error_data.get("code", 0)

        if error_code in (17, 4, 32) and retry < MAX_RETRIES:
            wait = RETRY_BACKOFF * (2 ** retry)
            logger.warning(f"Meta API rate limited (code {error_code}), retrying in {wait}s")
            time.sleep(wait)
            return self._get(url, params, retry + 1)

        if resp.status_code == 400 and error_code == 190:
            logger.error("Meta Ads access token expired or invalid")
            return None

        logger.error(f"Meta API error {resp.status_code}: {error_data.get('message', resp.text)}")
        return None

    def get_campaigns(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        # Mock fallback
        if not self.ad_account_id or self.access_token.startswith("mock"):
            logger.info("Meta Ads: returning mock campaign data")
            return self._mock_campaigns(start_date)

        logger.info(f"Fetching Meta Ads campaigns from {start_date} to {end_date}")

        # Fetch campaigns with pagination
        all_campaigns = self._fetch_all_campaigns()
        if not all_campaigns:
            return []

        # Fetch insights for all campaigns in one batch call
        results = []
        for campaign in all_campaigns:
            insights = self._fetch_campaign_insights(campaign["id"], start_date, end_date)
            results.append(self._merge_campaign_insights(campaign, insights, start_date))

        logger.info(f"Fetched {len(results)} campaigns from Meta Ads")
        return results

    def _fetch_all_campaigns(self) -> List[Dict]:
        """Fetch all campaigns with pagination."""
        url = self._api_url(f"act_{self.ad_account_id}/campaigns")
        params = {
            "fields": "name,status,start_time,objective,daily_budget,lifetime_budget",
            "limit": 100,
        }

        campaigns = []
        data = self._get(url, params)
        if not data:
            return []

        campaigns.extend(data.get("data", []))

        # Handle pagination
        while data and data.get("paging", {}).get("next"):
            data = self._get(data["paging"]["next"])
            if data:
                campaigns.extend(data.get("data", []))

        return campaigns

    def _fetch_campaign_insights(
        self, campaign_id: str, start_date: date, end_date: date
    ) -> Dict:
        """Fetch spend/performance insights for a single campaign."""
        url = self._api_url(f"{campaign_id}/insights")
        params = {
            "fields": "spend,impressions,clicks,actions,cost_per_action_type,cpc,cpm",
            "time_range": f'{{"since":"{start_date}","until":"{end_date}"}}',
        }

        data = self._get(url, params)
        if data and data.get("data"):
            return data["data"][0]
        return {}

    def _merge_campaign_insights(
        self, campaign: Dict, insights: Dict, start_date: date
    ) -> Dict[str, Any]:
        """Merge campaign metadata with insights data."""
        conversions = 0
        for action in insights.get("actions", []):
            if action.get("action_type") in (
                "offsite_conversion",
                "lead",
                "purchase",
                "omni_purchase",
                "complete_registration",
            ):
                conversions += int(float(action.get("value", 0)))

        return {
            "campaign_id": campaign["id"],
            "campaign_name": campaign.get("name", "Unnamed"),
            "status": campaign.get("status", "UNKNOWN"),
            "start_date": campaign.get("start_time", str(start_date))[:10],
            "spend": float(insights.get("spend", 0)),
            "impressions": int(insights.get("impressions", 0)),
            "clicks": int(insights.get("clicks", 0)),
            "conversions": conversions,
            "cpc": float(insights.get("cpc", 0)),
            "cpm": float(insights.get("cpm", 0)),
            "objective": campaign.get("objective", ""),
            "platform": "meta",
        }

    def campaign_to_decision(self, campaign: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "description": f"Meta Ads: {campaign['campaign_name']}",
            "decision_type": "AD_CAMPAIGN",
            "start_date": campaign.get("start_date", str(date.today())),
            "cost": campaign.get("spend", 0),
            "status": "ACTIVE" if campaign.get("status") == "ACTIVE" else "ENDED",
            "source": "META_ADS",
            "meta_data": {
                "campaign_id": campaign.get("campaign_id"),
                "impressions": campaign.get("impressions", 0),
                "clicks": campaign.get("clicks", 0),
                "conversions": campaign.get("conversions", 0),
                "objective": campaign.get("objective", ""),
                "platform": campaign.get("platform", "meta"),
            },
        }

    @staticmethod
    def _mock_campaigns(start_date: date) -> List[Dict[str, Any]]:
        return [
            {
                "campaign_id": "meta_001",
                "campaign_name": "Retargeting - Website Visitors",
                "status": "ACTIVE",
                "start_date": str(start_date),
                "spend": 2500.00,
                "impressions": 120000,
                "clicks": 3600,
                "conversions": 85,
                "cpc": 0.69,
                "cpm": 20.83,
                "objective": "CONVERSIONS",
                "platform": "facebook",
            },
            {
                "campaign_id": "meta_002",
                "campaign_name": "Lookalike - Enterprise Buyers",
                "status": "ACTIVE",
                "start_date": str(start_date),
                "spend": 4200.00,
                "impressions": 95000,
                "clicks": 2100,
                "conversions": 42,
                "cpc": 2.00,
                "cpm": 44.21,
                "objective": "LEAD_GENERATION",
                "platform": "instagram",
            },
        ]


def exchange_code_for_token(code: str, redirect_uri: str) -> Dict[str, str]:
    """Exchange a short-lived code for a long-lived access token."""
    client_id = os.getenv("META_APP_ID", "")
    client_secret = os.getenv("META_APP_SECRET", "")

    # Step 1: exchange code for short-lived token
    resp = requests.get(META_TOKEN_URL, params={
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "code": code,
    }, timeout=15)

    if resp.status_code != 200:
        logger.error(f"Meta token exchange failed: {resp.text}")
        raise ConnectionError(f"Token exchange failed: {resp.text}")

    short_token = resp.json()["access_token"]

    # Step 2: exchange for long-lived token (60-day)
    resp2 = requests.get(META_TOKEN_URL, params={
        "grant_type": "fb_exchange_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "fb_exchange_token": short_token,
    }, timeout=15)

    if resp2.status_code == 200:
        data = resp2.json()
        return {
            "access_token": data["access_token"],
            "expires_in": data.get("expires_in", 5184000),  # ~60 days
        }

    # Fall back to short-lived if long-lived exchange fails
    return {"access_token": short_token, "expires_in": 3600}
