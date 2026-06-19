"""
Tests for integration connectors: HubSpot, Google Ads, Meta Ads,
LinkedIn Ads, and QuickBooks.

These tests exercise the connectors' mock data paths and transformation
logic without making real HTTP calls to external APIs.
"""

import pytest
from datetime import date, timedelta
from unittest.mock import patch

from backend.app.integrations.hubspot import HubSpotConnector
from backend.app.integrations.google_ads import GoogleAdsConnector
from backend.app.integrations.meta_ads import MetaAdsConnector
from backend.app.integrations.linkedin_ads import LinkedInAdsConnector
from backend.app.integrations.quickbooks import QuickBooksConnector
from backend.app import models


# ---------------------------------------------------------------------------
# HubSpot
# ---------------------------------------------------------------------------

class TestHubSpotMockSync:
    """HubSpotConnector in mock mode."""

    def test_hubspot_mock_deals(self):
        """With no token, the connector should return mock deals."""
        connector = HubSpotConnector(access_token=None)
        assert connector.is_mock is True
        deals = connector.fetch_recent_deals()
        assert len(deals) > 0
        # Each mock deal should have required fields
        for deal in deals:
            assert "amount" in deal
            assert "closedate" in deal
            assert "dealname" in deal

    def test_hubspot_mock_sync(self, test_db):
        """sync_outcomes should create Outcome rows from mock deals."""
        org = models.Organization(name="HS Test Org")
        test_db.add(org)
        test_db.commit()

        connector = HubSpotConnector(access_token="mock_token")
        result = connector.sync_outcomes(test_db, organization_id=org.id)

        assert result["created"] > 0
        assert result["skipped"] >= 0

        # Verify outcomes were persisted
        outcomes = test_db.query(models.Outcome).filter(
            models.Outcome.organization_id == org.id,
            models.Outcome.source == "HUBSPOT",
        ).all()
        assert len(outcomes) == result["created"]

    def test_hubspot_dedup(self, test_db):
        """Running sync_outcomes twice should not duplicate outcomes (dedup by source_id)."""
        org = models.Organization(name="HS Dedup Org")
        test_db.add(org)
        test_db.commit()

        connector = HubSpotConnector(access_token=None)
        r1 = connector.sync_outcomes(test_db, organization_id=org.id)
        r2 = connector.sync_outcomes(test_db, organization_id=org.id)

        assert r1["created"] > 0
        assert r2["created"] == 0, "Second sync should create zero new outcomes"
        assert r2["skipped"] == r1["created"]


# ---------------------------------------------------------------------------
# Google Ads
# ---------------------------------------------------------------------------

class TestGoogleAdsMockCampaigns:
    """GoogleAdsConnector in mock mode."""

    def test_google_ads_mock_campaigns(self):
        """With a mock refresh token, should return mock campaign data."""
        connector = GoogleAdsConnector(refresh_token="mock_token", customer_id="123-456-7890")
        campaigns = connector.get_campaigns()
        assert len(campaigns) == 2

        for c in campaigns:
            assert "campaign_id" in c
            assert "campaign_name" in c
            assert "cost_micros" in c
            assert c["cost_micros"] > 0

    def test_google_ads_campaign_to_decision(self):
        """campaign_to_decision should transform raw campaign to Decision format."""
        connector = GoogleAdsConnector(refresh_token="mock_token", customer_id="123")
        campaigns = connector.get_campaigns()
        decision = connector.campaign_to_decision(campaigns[0])

        assert decision["decision_type"] == "AD_CAMPAIGN"
        assert decision["source"] == "GOOGLE_ADS"
        assert decision["description"].startswith("Google Ads:")
        assert decision["cost"] == campaigns[0]["cost_micros"] / 1_000_000

    def test_google_ads_enabled_status_mapping(self):
        """ENABLED status should map to ACTIVE in Decision."""
        connector = GoogleAdsConnector(refresh_token="mock_token", customer_id="123")
        campaigns = connector.get_campaigns()
        # Mock campaigns have status=ENABLED
        decision = connector.campaign_to_decision(campaigns[0])
        assert decision["status"] == "ACTIVE"


# ---------------------------------------------------------------------------
# Meta Ads
# ---------------------------------------------------------------------------

class TestMetaAdsMockCampaigns:
    """MetaAdsConnector in mock mode."""

    def test_meta_ads_mock_campaigns(self):
        """With a mock access token, should return mock campaign data."""
        connector = MetaAdsConnector(access_token="mock_token", ad_account_id="")
        campaigns = connector.get_campaigns()
        assert len(campaigns) == 2

        for c in campaigns:
            assert "campaign_id" in c
            assert "campaign_name" in c
            assert "spend" in c
            assert c["spend"] > 0

    def test_meta_ads_campaign_to_decision(self):
        """campaign_to_decision should transform raw campaign to Decision format."""
        connector = MetaAdsConnector(access_token="mock_token", ad_account_id="")
        campaigns = connector.get_campaigns()
        decision = connector.campaign_to_decision(campaigns[0])

        assert decision["decision_type"] == "AD_CAMPAIGN"
        assert decision["source"] == "META_ADS"
        assert decision["description"].startswith("Meta Ads:")
        assert decision["cost"] == campaigns[0]["spend"]

    def test_meta_ads_active_status(self):
        """ACTIVE campaigns should map to ACTIVE Decision status."""
        connector = MetaAdsConnector(access_token="mock_token", ad_account_id="")
        campaigns = connector.get_campaigns()
        # Mock campaigns have status=ACTIVE
        decision = connector.campaign_to_decision(campaigns[0])
        assert decision["status"] == "ACTIVE"

    def test_meta_ads_meta_data_fields(self):
        """Decision meta_data should contain impressions, clicks, conversions."""
        connector = MetaAdsConnector(access_token="mock_token", ad_account_id="")
        campaigns = connector.get_campaigns()
        decision = connector.campaign_to_decision(campaigns[0])

        meta = decision["meta_data"]
        assert "impressions" in meta
        assert "clicks" in meta
        assert "conversions" in meta
        assert meta["platform"] in ("facebook", "instagram", "meta")


# ---------------------------------------------------------------------------
# LinkedIn Ads
# ---------------------------------------------------------------------------

class TestLinkedInAdsMockCampaigns:
    """LinkedInAdsConnector in mock mode."""

    def test_linkedin_ads_mock_campaigns(self):
        """With a mock access token, should return mock campaign data."""
        connector = LinkedInAdsConnector(access_token="mock_token", account_id="")
        campaigns = connector.get_campaigns()
        assert len(campaigns) == 2

        for c in campaigns:
            assert "campaign_id" in c
            assert "campaign_name" in c
            assert "spend" in c
            assert c["spend"] > 0

    def test_linkedin_ads_campaign_to_decision(self):
        """campaign_to_decision should transform raw campaign to Decision format."""
        connector = LinkedInAdsConnector(access_token="mock_token", account_id="")
        campaigns = connector.get_campaigns()
        decision = connector.campaign_to_decision(campaigns[0])

        assert decision["decision_type"] == "AD_CAMPAIGN"
        assert decision["source"] == "LINKEDIN_ADS"
        assert decision["description"].startswith("LinkedIn Ads:")
        assert decision["cost"] == campaigns[0]["spend"]

    def test_linkedin_ads_meta_data_fields(self):
        """Decision meta_data should contain leads, conversions, format, objective."""
        connector = LinkedInAdsConnector(access_token="mock_token", account_id="")
        campaigns = connector.get_campaigns()
        decision = connector.campaign_to_decision(campaigns[0])

        meta = decision["meta_data"]
        assert "leads" in meta
        assert "conversions" in meta
        assert "format" in meta
        assert "objective" in meta

    def test_linkedin_ads_active_status(self):
        """ACTIVE campaigns should map to ACTIVE Decision status."""
        connector = LinkedInAdsConnector(access_token="mock_token", account_id="")
        campaigns = connector.get_campaigns()
        decision = connector.campaign_to_decision(campaigns[0])
        assert decision["status"] == "ACTIVE"


# ---------------------------------------------------------------------------
# QuickBooks
# ---------------------------------------------------------------------------

class TestQuickBooksMockPayments:
    """QuickBooksConnector in mock mode."""

    def test_quickbooks_mock_payments(self):
        """With no credentials, should return mock vendor payments."""
        connector = QuickBooksConnector(
            access_token="mock_token",
            refresh_token="mock_refresh",
            realm_id="1234567890",
        )
        payments = connector.get_vendor_payments()
        assert len(payments) == 3

        for p in payments:
            assert "vendor_name" in p
            assert "total_amount" in p
            assert p["total_amount"] > 0

    def test_quickbooks_payment_to_decision(self):
        """payment_to_decision should classify based on account name."""
        connector = QuickBooksConnector(
            access_token="mock_token",
            refresh_token="mock_refresh",
            realm_id="1234",
        )
        payments = connector.get_vendor_payments()

        # First mock payment: ZoomInfo with "Software & Tools" account -> TOOL
        decision = connector.payment_to_decision(payments[0])
        assert decision["source"] == "QUICKBOOKS"
        assert decision["decision_type"] == "TOOL"
        assert decision["cost"] == payments[0]["total_amount"]

    def test_quickbooks_vendor_classification(self):
        """Different account names should map to different decision types."""
        connector = QuickBooksConnector(
            access_token="mock_token",
            refresh_token="mock_refresh",
            realm_id="1234",
        )
        payments = connector.get_vendor_payments()

        decisions = [connector.payment_to_decision(p) for p in payments]

        # "Software & Tools" -> TOOL
        assert decisions[0]["decision_type"] == "TOOL"
        # "Software & Tools" -> TOOL
        assert decisions[1]["decision_type"] == "TOOL"
        # "Cloud Infrastructure" -> VENDOR (default)
        assert decisions[2]["decision_type"] == "VENDOR"

    def test_quickbooks_description_format(self):
        """Decision description should include vendor name."""
        connector = QuickBooksConnector(
            access_token="mock_token",
            refresh_token="mock_refresh",
            realm_id="1234",
        )
        payments = connector.get_vendor_payments()
        decision = connector.payment_to_decision(payments[0])
        assert "ZoomInfo" in decision["description"]
