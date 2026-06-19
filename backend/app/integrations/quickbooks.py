"""
QuickBooks Online Integration Connector

Connects via OAuth 2.0 to the QuickBooks Online Accounting API to fetch
vendor payments, bills, and expenses, transforming them into Decision records.
"""
import os
import logging
from base64 import b64encode
from datetime import date, timedelta
from typing import Optional, List, Dict, Any

import requests

logger = logging.getLogger(__name__)

INTUIT_TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
SANDBOX_BASE_URL = "https://sandbox-quickbooks.api.intuit.com"
PRODUCTION_BASE_URL = "https://quickbooks.api.intuit.com"


class QuickBooksConnector:
    """Connector for QuickBooks Online API."""

    def __init__(self, access_token: str, refresh_token: str, realm_id: str):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.realm_id = realm_id
        self.client_id = os.getenv("QUICKBOOKS_CLIENT_ID", "")
        self.client_secret = os.getenv("QUICKBOOKS_CLIENT_SECRET", "")

        environment = os.getenv("QUICKBOOKS_ENVIRONMENT", "sandbox")
        self.base_url = (
            PRODUCTION_BASE_URL if environment == "production" else SANDBOX_BASE_URL
        )

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _query(self, sql: str) -> List[Dict]:
        """Execute a QuickBooks query via the REST API."""
        url = (
            f"{self.base_url}/v3/company/{self.realm_id}/query"
            f"?query={requests.utils.quote(sql)}"
        )
        resp = requests.get(url, headers=self._headers(), timeout=20)

        if resp.status_code == 401:
            logger.info("QuickBooks token expired, attempting refresh")
            self._refresh_access_token()
            resp = requests.get(url, headers=self._headers(), timeout=20)

        if resp.status_code != 200:
            logger.error(f"QuickBooks query error: {resp.status_code} {resp.text}")
            return []

        query_response = resp.json().get("QueryResponse", {})
        return query_response.get(list(query_response.keys())[0], []) if query_response else []

    def _refresh_access_token(self):
        """Refresh the access token using the refresh token."""
        auth_header = b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        resp = requests.post(
            INTUIT_TOKEN_URL,
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            },
            timeout=15,
        )

        if resp.status_code != 200:
            logger.error(f"QuickBooks token refresh failed: {resp.status_code}")
            raise ConnectionError("Failed to refresh QuickBooks access token")

        data = resp.json()
        self.access_token = data["access_token"]
        self.refresh_token = data.get("refresh_token", self.refresh_token)

    def get_vendor_payments(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch vendor bills and payments from QuickBooks."""
        if not start_date:
            start_date = date.today() - timedelta(days=90)
        if not end_date:
            end_date = date.today()

        # Check for mock mode
        if not all([self.client_id, self.client_secret]):
            logger.info("QuickBooks credentials not configured, returning mock data")
            return self._mock_payments()

        if self.access_token.startswith("mock"):
            logger.info("QuickBooks: mock token detected, returning mock data")
            return self._mock_payments()

        logger.info(f"Fetching QuickBooks payments from {start_date} to {end_date}")

        # Fetch Bills (vendor invoices)
        bills = self._fetch_bills(start_date, end_date)
        # Fetch Purchase orders / expenses
        purchases = self._fetch_purchases(start_date, end_date)

        return bills + purchases

    def _fetch_bills(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Fetch paid bills from QuickBooks."""
        query = (
            f"SELECT * FROM Bill WHERE TxnDate >= '{start_date}' "
            f"AND TxnDate <= '{end_date}' MAXRESULTS 200"
        )

        try:
            results = self._query(query)
        except Exception as e:
            logger.error(f"QuickBooks bills fetch error: {e}")
            return []

        payments = []
        for bill in results:
            vendor_ref = bill.get("VendorRef", {})
            line_items = bill.get("Line", [])

            # Determine account from first line item
            account_name = ""
            for line in line_items:
                detail = line.get("AccountBasedExpenseLineDetail", {})
                acct = detail.get("AccountRef", {})
                account_name = acct.get("name", "")
                if account_name:
                    break

            payments.append({
                "id": f"BILL-{bill.get('Id', '')}",
                "vendor_name": vendor_ref.get("name", "Unknown Vendor"),
                "total_amount": float(bill.get("TotalAmt", 0)),
                "txn_date": bill.get("TxnDate", str(start_date)),
                "memo": bill.get("PrivateNote", "") or _extract_description(line_items),
                "account_name": account_name,
                "doc_type": "bill",
            })

        return payments

    def _fetch_purchases(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Fetch purchase/expense transactions from QuickBooks."""
        query = (
            f"SELECT * FROM Purchase WHERE TxnDate >= '{start_date}' "
            f"AND TxnDate <= '{end_date}' MAXRESULTS 200"
        )

        try:
            results = self._query(query)
        except Exception as e:
            logger.error(f"QuickBooks purchases fetch error: {e}")
            return []

        payments = []
        for purchase in results:
            entity_ref = purchase.get("EntityRef", {})
            account_ref = purchase.get("AccountRef", {})
            line_items = purchase.get("Line", [])

            payments.append({
                "id": f"PUR-{purchase.get('Id', '')}",
                "vendor_name": entity_ref.get("name", "Unknown"),
                "total_amount": float(purchase.get("TotalAmt", 0)),
                "txn_date": purchase.get("TxnDate", str(start_date)),
                "memo": purchase.get("PrivateNote", "") or _extract_description(line_items),
                "account_name": account_ref.get("name", ""),
                "doc_type": "purchase",
            })

        return payments

    def payment_to_decision(self, payment: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a QuickBooks payment into a Decision format."""
        account_name = payment.get("account_name", "").lower()
        if "software" in account_name or "tool" in account_name or "subscription" in account_name:
            decision_type = "TOOL"
        elif "contractor" in account_name or "consulting" in account_name:
            decision_type = "VENDOR"
        elif "advertising" in account_name or "marketing" in account_name:
            decision_type = "AD_CAMPAIGN"
        else:
            decision_type = "VENDOR"

        return {
            "description": f"{payment['vendor_name']}: {payment.get('memo', 'Payment')}",
            "decision_type": decision_type,
            "start_date": payment.get("txn_date"),
            "cost": payment.get("total_amount", 0),
            "status": "ACTIVE",
            "source": "QUICKBOOKS",
            "external_id": payment.get("id"),
            "details": {
                "vendor": payment.get("vendor_name"),
                "account": payment.get("account_name"),
                "doc_type": payment.get("doc_type"),
                "platform": "quickbooks",
            },
        }

    @staticmethod
    def _mock_payments() -> List[Dict[str, Any]]:
        return [
            {
                "id": "INV-001",
                "vendor_name": "ZoomInfo",
                "total_amount": 15000.00,
                "txn_date": str(date.today() - timedelta(days=30)),
                "memo": "Annual subscription - Sales Intelligence",
                "account_name": "Software & Tools",
                "doc_type": "bill",
            },
            {
                "id": "INV-002",
                "vendor_name": "LinkedIn Sales Navigator",
                "total_amount": 1200.00,
                "txn_date": str(date.today() - timedelta(days=15)),
                "memo": "Monthly subscription - Team plan",
                "account_name": "Software & Tools",
                "doc_type": "bill",
            },
            {
                "id": "INV-003",
                "vendor_name": "AWS",
                "total_amount": 3500.00,
                "txn_date": str(date.today() - timedelta(days=7)),
                "memo": "Infrastructure costs - January",
                "account_name": "Cloud Infrastructure",
                "doc_type": "purchase",
            },
        ]


def _extract_description(line_items: List[Dict]) -> str:
    """Extract a useful description from bill/purchase line items."""
    for line in line_items:
        desc = line.get("Description", "")
        if desc:
            return desc[:120]
    return "Payment"


def get_oauth_url(redirect_uri: str, state: str) -> str:
    """Generate the OAuth authorization URL for QuickBooks."""
    client_id = os.getenv("QUICKBOOKS_CLIENT_ID", "")
    scopes = "com.intuit.quickbooks.accounting"

    return (
        f"https://appcenter.intuit.com/connect/oauth2?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"scope={scopes}&"
        f"response_type=code&"
        f"state={state}"
    )


def exchange_code_for_tokens(code: str, redirect_uri: str) -> Dict[str, str]:
    """Exchange authorization code for access and refresh tokens."""
    client_id = os.getenv("QUICKBOOKS_CLIENT_ID", "")
    client_secret = os.getenv("QUICKBOOKS_CLIENT_SECRET", "")

    auth_header = b64encode(f"{client_id}:{client_secret}".encode()).decode()

    resp = requests.post(
        INTUIT_TOKEN_URL,
        headers={
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=15,
    )

    if resp.status_code != 200:
        logger.error(f"QuickBooks token exchange failed: {resp.status_code} {resp.text}")
        raise ConnectionError(f"Token exchange failed: {resp.text}")

    data = resp.json()
    return {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", ""),
        "realm_id": data.get("realmId", ""),
        "expires_in": data.get("expires_in", 3600),
    }
