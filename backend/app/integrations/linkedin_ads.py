"""
LinkedIn Ads Connector

Fetches campaign-level spend data from the LinkedIn Marketing API v202401
with proper pagination, rate-limit handling, and error recovery.
"""
import os
import logging
import time
from datetime import date, timedelta
from typing import Optional, List, Dict, Any

import requests

logger = logging.getLogger(__name__)

LINKEDIN_API_BASE = "https://api.linkedin.com"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_API_VERSION = "202401"

MAX_RETRIES = 3
RETRY_BACKOFF = 2


class LinkedInAdsConnector:
    """Connector for LinkedIn Marketing API."""

    def __init__(self, access_token: str, account_id: str = ""):
        self.access_token = access_token
        self.account_id = account_id

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "LinkedIn-Version": LINKEDIN_API_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def _get(self, url: str, params: Dict = None, retry: int = 0) -> Optional[Dict]:
        """GET request with retry and rate-limit handling."""
        try:
            resp = requests.get(
                url, headers=self._headers(), params=params or {}, timeout=30
            )
        except requests.exceptions.Timeout:
            if retry < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF * (2 ** retry))
                return self._get(url, params, retry + 1)
            logger.error("LinkedIn API timeout after retries")
            return None

        if resp.status_code == 200:
            return resp.json()

        # Rate limit (429)
        if resp.status_code == 429 and retry < MAX_RETRIES:
            retry_after = int(resp.headers.get("Retry-After", RETRY_BACKOFF * (2 ** retry)))
            logger.warning(f"LinkedIn API rate limited, retrying in {retry_after}s")
            time.sleep(retry_after)
            return self._get(url, params, retry + 1)

        # Token expired
        if resp.status_code == 401:
            logger.error("LinkedIn Ads access token expired or invalid")
            return None

        logger.error(f"LinkedIn API error {resp.status_code}: {resp.text[:200]}")
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
        if not self.account_id or self.access_token.startswith("mock"):
            logger.info("LinkedIn Ads: returning mock campaign data")
            return self._mock_campaigns(start_date)

        logger.info(f"Fetching LinkedIn Ads campaigns from {start_date} to {end_date}")

        # Fetch campaigns
        all_campaigns = self._fetch_all_campaigns()
        if not all_campaigns:
            return []

        # Fetch analytics for all campaigns
        analytics = self._fetch_analytics_batch(
            [c["id"] for c in all_campaigns], start_date, end_date
        )

        results = []
        for campaign in all_campaigns:
            cid = str(campaign["id"])
            stats = analytics.get(cid, {})
            results.append({
                "campaign_id": cid,
                "campaign_name": campaign.get("name", f"Campaign {cid}"),
                "status": campaign.get("status", "UNKNOWN"),
                "start_date": str(start_date),
                "spend": float(stats.get("costInLocalCurrency", 0)),
                "impressions": int(stats.get("impressions", 0)),
                "clicks": int(stats.get("clicks", 0)),
                "conversions": int(stats.get("externalWebsiteConversions", 0)),
                "leads": int(stats.get("oneClickLeads", 0)),
                "format": campaign.get("type", "unknown"),
                "objective": campaign.get("objectiveType", ""),
            })

        logger.info(f"Fetched {len(results)} campaigns from LinkedIn Ads")
        return results

    def _fetch_all_campaigns(self) -> List[Dict]:
        """Fetch all campaigns with pagination."""
        url = f"{LINKEDIN_API_BASE}/rest/adAccounts/{self.account_id}/adCampaigns"
        params = {"q": "search", "count": 100, "start": 0}

        campaigns = []
        while True:
            data = self._get(url, params)
            if not data:
                break

            elements = data.get("elements", [])
            campaigns.extend(elements)

            # Check for more pages
            paging = data.get("paging", {})
            total = paging.get("total", len(campaigns))
            if len(campaigns) >= total:
                break
            params["start"] = len(campaigns)

        return campaigns

    def _fetch_analytics_batch(
        self, campaign_ids: List, start_date: date, end_date: date
    ) -> Dict[str, Dict]:
        """Fetch analytics for multiple campaigns."""
        if not campaign_ids:
            return {}

        url = f"{LINKEDIN_API_BASE}/rest/adAnalytics"
        analytics_map = {}

        # LinkedIn API allows up to 20 campaigns per request
        for batch_start in range(0, len(campaign_ids), 20):
            batch = campaign_ids[batch_start:batch_start + 20]
            campaigns_param = ",".join(
                f"urn:li:sponsoredCampaign:{cid}" for cid in batch
            )

            params = {
                "q": "analytics",
                "pivot": "CAMPAIGN",
                "campaigns": campaigns_param,
                "dateRange.start.year": start_date.year,
                "dateRange.start.month": start_date.month,
                "dateRange.start.day": start_date.day,
                "dateRange.end.year": end_date.year,
                "dateRange.end.month": end_date.month,
                "dateRange.end.day": end_date.day,
                "fields": "costInLocalCurrency,impressions,clicks,externalWebsiteConversions,oneClickLeads",
            }

            data = self._get(url, params)
            if data:
                for element in data.get("elements", []):
                    pivot_value = element.get("pivotValue", "")
                    # Extract campaign ID from URN
                    cid = pivot_value.split(":")[-1] if ":" in pivot_value else pivot_value
                    analytics_map[cid] = element

        return analytics_map

    def campaign_to_decision(self, campaign: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "description": f"LinkedIn Ads: {campaign['campaign_name']}",
            "decision_type": "AD_CAMPAIGN",
            "start_date": campaign.get("start_date", str(date.today())),
            "cost": campaign.get("spend", 0),
            "status": "ACTIVE" if campaign.get("status") == "ACTIVE" else "ENDED",
            "source": "LINKEDIN_ADS",
            "meta_data": {
                "campaign_id": campaign.get("campaign_id"),
                "impressions": campaign.get("impressions", 0),
                "clicks": campaign.get("clicks", 0),
                "conversions": campaign.get("conversions", 0),
                "leads": campaign.get("leads", 0),
                "format": campaign.get("format", "unknown"),
                "objective": campaign.get("objective", ""),
            },
        }

    @staticmethod
    def _mock_campaigns(start_date: date) -> List[Dict[str, Any]]:
        return [
            {
                "campaign_id": "li_001",
                "campaign_name": "Sponsored Content - CTO Targeting",
                "status": "ACTIVE",
                "start_date": str(start_date),
                "spend": 3200.00,
                "impressions": 45000,
                "clicks": 890,
                "conversions": 28,
                "leads": 12,
                "format": "sponsored_content",
                "objective": "LEAD_GENERATION",
            },
            {
                "campaign_id": "li_002",
                "campaign_name": "InMail - VP Sales Outreach",
                "status": "ACTIVE",
                "start_date": str(start_date),
                "spend": 1800.00,
                "impressions": 12000,
                "clicks": 420,
                "conversions": 15,
                "leads": 8,
                "format": "message_ad",
                "objective": "LEAD_GENERATION",
            },
        ]


def exchange_code_for_tokens(code: str, redirect_uri: str) -> Dict[str, str]:
    """Exchange authorization code for access token."""
    client_id = os.getenv("LINKEDIN_CLIENT_ID", "")
    client_secret = os.getenv("LINKEDIN_CLIENT_SECRET", "")

    resp = requests.post(LINKEDIN_TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
    }, timeout=15)

    if resp.status_code != 200:
        logger.error(f"LinkedIn token exchange failed: {resp.status_code} {resp.text}")
        raise ConnectionError(f"Token exchange failed: {resp.text}")

    data = resp.json()
    return {
        "access_token": data["access_token"],
        "expires_in": data.get("expires_in", 5184000),  # ~60 days
    }
