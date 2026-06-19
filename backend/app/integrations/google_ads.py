"""
Google Ads Integration Connector

Connects via OAuth 2.0 to the Google Ads REST API (v17) to fetch campaign
spend data and transform campaigns into Decision records.
"""
import os
import logging
from datetime import date, timedelta
from typing import Optional, List, Dict, Any

import requests

logger = logging.getLogger(__name__)

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_ADS_API_VERSION = "v17"
GOOGLE_ADS_BASE = f"https://googleads.googleapis.com/{GOOGLE_ADS_API_VERSION}"


class GoogleAdsConnector:
    """Connector for Google Ads REST API."""

    def __init__(self, refresh_token: str, customer_id: str):
        self.refresh_token = refresh_token
        self.customer_id = customer_id.replace("-", "")
        self.client_id = os.getenv("GOOGLE_ADS_CLIENT_ID", "")
        self.client_secret = os.getenv("GOOGLE_ADS_CLIENT_SECRET", "")
        self.developer_token = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "")
        self.login_customer_id = os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "")
        self._access_token: Optional[str] = None

    def _get_access_token(self) -> str:
        """Exchange refresh token for a short-lived access token."""
        if self._access_token:
            return self._access_token

        resp = requests.post(GOOGLE_TOKEN_URL, data={
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }, timeout=15)

        if resp.status_code != 200:
            logger.error(f"Google token refresh failed: {resp.status_code} {resp.text}")
            raise ConnectionError("Failed to refresh Google Ads access token")

        self._access_token = resp.json()["access_token"]
        return self._access_token

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._get_access_token()}",
            "developer-token": self.developer_token,
            "Content-Type": "application/json",
        }
        if self.login_customer_id:
            headers["login-customer-id"] = self.login_customer_id
        return headers

    def _search(self, query: str) -> List[Dict]:
        """Execute a GAQL query via the Google Ads REST search endpoint."""
        url = f"{GOOGLE_ADS_BASE}/customers/{self.customer_id}/googleAds:search"
        resp = requests.post(
            url,
            headers=self._headers(),
            json={"query": query},
            timeout=30,
        )

        if resp.status_code != 200:
            logger.error(f"Google Ads API error: {resp.status_code} {resp.text}")
            return []

        results = resp.json().get("results", [])

        # Handle pagination
        next_page_token = resp.json().get("nextPageToken")
        while next_page_token:
            resp = requests.post(
                url,
                headers=self._headers(),
                json={"query": query, "pageToken": next_page_token},
                timeout=30,
            )
            if resp.status_code != 200:
                break
            page = resp.json()
            results.extend(page.get("results", []))
            next_page_token = page.get("nextPageToken")

        return results

    def get_campaigns(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch campaigns with spend data from Google Ads."""
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        # Check for mock mode
        if not all([self.client_id, self.client_secret, self.developer_token]):
            logger.info("Google Ads credentials not configured, returning mock data")
            return self._mock_campaigns(start_date)

        if self.refresh_token.startswith("mock"):
            logger.info("Google Ads: mock refresh token detected, returning mock data")
            return self._mock_campaigns(start_date)

        logger.info(f"Fetching Google Ads campaigns from {start_date} to {end_date}")

        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.start_date,
                campaign.end_date,
                metrics.cost_micros,
                metrics.impressions,
                metrics.clicks,
                metrics.conversions,
                metrics.conversions_value
            FROM campaign
            WHERE segments.date BETWEEN '{start_date.strftime('%Y-%m-%d')}'
                AND '{end_date.strftime('%Y-%m-%d')}'
                AND campaign.status != 'REMOVED'
            ORDER BY metrics.cost_micros DESC
        """

        try:
            results = self._search(query)
        except ConnectionError:
            logger.warning("Google Ads token refresh failed, returning empty list")
            return []
        except Exception as e:
            logger.error(f"Google Ads fetch error: {e}")
            return []

        campaigns = []
        for row in results:
            campaign = row.get("campaign", {})
            metrics = row.get("metrics", {})

            campaigns.append({
                "campaign_id": str(campaign.get("id", "")),
                "campaign_name": campaign.get("name", "Unnamed Campaign"),
                "status": campaign.get("status", "UNKNOWN"),
                "start_date": campaign.get("startDate", str(start_date)),
                "end_date": campaign.get("endDate"),
                "cost_micros": int(metrics.get("costMicros", 0)),
                "impressions": int(metrics.get("impressions", 0)),
                "clicks": int(metrics.get("clicks", 0)),
                "conversions": float(metrics.get("conversions", 0)),
                "conversions_value": float(metrics.get("conversionsValue", 0)),
            })

        logger.info(f"Fetched {len(campaigns)} campaigns from Google Ads")
        return campaigns

    def campaign_to_decision(self, campaign: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a Google Ads campaign into a Decision format."""
        cost_dollars = campaign.get("cost_micros", 0) / 1_000_000

        return {
            "description": f"Google Ads: {campaign['campaign_name']}",
            "decision_type": "AD_CAMPAIGN",
            "start_date": campaign.get("start_date"),
            "cost": cost_dollars,
            "status": "ACTIVE" if campaign.get("status") == "ENABLED" else "ENDED",
            "source": "GOOGLE_ADS",
            "external_id": campaign.get("campaign_id"),
            "details": {
                "impressions": campaign.get("impressions", 0),
                "clicks": campaign.get("clicks", 0),
                "conversions": campaign.get("conversions", 0),
                "conversions_value": campaign.get("conversions_value", 0),
                "platform": "google_ads",
            },
        }

    @staticmethod
    def _mock_campaigns(start_date: date) -> List[Dict[str, Any]]:
        return [
            {
                "campaign_id": "123456789",
                "campaign_name": "Brand Awareness Q1",
                "status": "ENABLED",
                "start_date": str(start_date),
                "cost_micros": 150000000,
                "impressions": 50000,
                "clicks": 1200,
                "conversions": 45,
                "conversions_value": 4500.0,
            },
            {
                "campaign_id": "987654321",
                "campaign_name": "Lead Gen - Tech Decision Makers",
                "status": "ENABLED",
                "start_date": str(start_date),
                "cost_micros": 300000000,
                "impressions": 80000,
                "clicks": 2400,
                "conversions": 120,
                "conversions_value": 24000.0,
            },
        ]


def get_oauth_url(redirect_uri: str, state: str) -> str:
    """Generate the OAuth authorization URL for Google Ads."""
    client_id = os.getenv("GOOGLE_ADS_CLIENT_ID", "")
    scopes = "https://www.googleapis.com/auth/adwords"

    return (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"scope={scopes}&"
        f"response_type=code&"
        f"state={state}&"
        f"access_type=offline&"
        f"prompt=consent"
    )


def exchange_code_for_tokens(code: str, redirect_uri: str) -> Dict[str, str]:
    """Exchange authorization code for access and refresh tokens."""
    client_id = os.getenv("GOOGLE_ADS_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_ADS_CLIENT_SECRET", "")

    resp = requests.post(GOOGLE_TOKEN_URL, data={
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }, timeout=15)

    if resp.status_code != 200:
        logger.error(f"Google Ads token exchange failed: {resp.status_code} {resp.text}")
        raise ConnectionError(f"Token exchange failed: {resp.text}")

    data = resp.json()
    return {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", ""),
        "expires_in": data.get("expires_in", 3600),
    }
