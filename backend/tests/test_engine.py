"""
Unit tests for the attribution engine (backend/app/engine.py).

Tests the core logic directly -- no HTTP layer involved.
"""

import math
import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from backend.app.engine import AttributionEngine, WINDOW_DAYS, SEMANTIC_BLEND, TEMPORAL_BLEND
from backend.app import models


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_decision(**kwargs):
    """Create a Decision model instance with sensible defaults."""
    defaults = {
        "id": 1,
        "description": "Test Campaign",
        "decision_type": "AD_CAMPAIGN",
        "start_date": date.today() - timedelta(days=10),
        "cost": 1000.0,
        "status": "ACTIVE",
        "source": "MANUAL",
        "organization_id": 1,
    }
    defaults.update(kwargs)
    d = models.Decision(**defaults)
    # Set the id explicitly since we are not going through the DB
    d.id = defaults["id"]
    return d


def _make_outcome(**kwargs):
    """Create an Outcome model instance with sensible defaults."""
    defaults = {
        "id": 100,
        "metric_name": "REVENUE",
        "value": 5000.0,
        "date": date.today(),
        "description": "Test deal",
        "source": "MANUAL",
        "organization_id": 1,
        "decision_id": None,
    }
    defaults.update(kwargs)
    o = models.Outcome(**defaults)
    o.id = defaults["id"]
    return o


# ---------------------------------------------------------------------------
# Temporal Weight Calculation
# ---------------------------------------------------------------------------

class TestTemporalWeightCalculation:
    """Tests for calculate_weight focusing on temporal decay."""

    def setup_method(self):
        self.engine = AttributionEngine()

    def test_temporal_weight_same_day(self):
        """An outcome on the same day as the decision should get high weight."""
        decision = _make_decision(start_date=date.today())
        outcome = _make_outcome(date=date.today())

        with patch.object(self.engine.matcher, "compute_similarity", return_value=0.0):
            weight = self.engine.calculate_weight(decision, outcome)

        # Same day -> temporal=1.0 but no semantic -> temporal * 0.6
        assert weight > 0
        assert weight <= 1.0

    def test_temporal_weight_decays_over_time(self):
        """Weight should decrease as the outcome date moves further from decision start."""
        decision = _make_decision(start_date=date.today() - timedelta(days=30))

        with patch.object(self.engine.matcher, "compute_similarity", return_value=0.0):
            weight_close = self.engine.calculate_weight(
                decision,
                _make_outcome(date=date.today() - timedelta(days=25)),
            )
            weight_far = self.engine.calculate_weight(
                decision,
                _make_outcome(date=date.today()),
            )

        assert weight_close > weight_far, "Closer outcomes should have higher weight"

    def test_temporal_weight_zero_outside_window(self):
        """An outcome outside the attribution window should get zero weight."""
        decision = _make_decision(
            start_date=date.today() - timedelta(days=200),
            decision_type="AD_CAMPAIGN",
        )
        outcome = _make_outcome(date=date.today())

        with patch.object(self.engine.matcher, "compute_similarity", return_value=0.0):
            weight = self.engine.calculate_weight(decision, outcome)

        assert weight == 0.0

    def test_temporal_weight_zero_before_decision(self):
        """An outcome that occurs BEFORE the decision should get zero weight."""
        decision = _make_decision(start_date=date.today())
        outcome = _make_outcome(date=date.today() - timedelta(days=5))

        with patch.object(self.engine.matcher, "compute_similarity", return_value=0.0):
            weight = self.engine.calculate_weight(decision, outcome)

        assert weight == 0.0

    def test_hard_link_always_1(self):
        """A hard-linked outcome (decision_id matches) should always get weight=1.0."""
        decision = _make_decision(id=42)
        outcome = _make_outcome(decision_id=42)

        weight = self.engine.calculate_weight(decision, outcome)
        assert weight == 1.0

    def test_type_window_multiplier(self):
        """HIRE decisions have a wider window than AD_CAMPAIGN."""
        base_start = date.today() - timedelta(days=80)
        outcome_date = date.today()

        hire = _make_decision(
            id=1, start_date=base_start, decision_type="HIRE", description="Senior AE"
        )
        campaign = _make_decision(
            id=2, start_date=base_start, decision_type="AD_CAMPAIGN", description="Google PPC"
        )
        outcome = _make_outcome(date=outcome_date, description="Revenue from new client")

        with patch.object(self.engine.matcher, "compute_similarity", return_value=0.0):
            hire_weight = self.engine.calculate_weight(hire, outcome)
            campaign_weight = self.engine.calculate_weight(campaign, outcome)

        # AD_CAMPAIGN window is 90 * 0.7 = 63 days. 80 days > 63 -> 0
        # HIRE window is 90 * 1.5 = 135 days. 80 days < 135 -> positive
        assert campaign_weight == 0.0
        assert hire_weight > 0.0


# ---------------------------------------------------------------------------
# Semantic Matching
# ---------------------------------------------------------------------------

class TestSemanticMatching:
    """Tests for the semantic component of calculate_weight."""

    def setup_method(self):
        self.engine = AttributionEngine()

    def test_semantic_match_increases_weight(self):
        """High semantic similarity should produce a higher weight than none."""
        decision = _make_decision(
            start_date=date.today() - timedelta(days=10),
            description="LinkedIn Ad Campaign for SaaS buyers",
        )
        outcome = _make_outcome(
            date=date.today(),
            description="SaaS buyer deal from LinkedIn",
        )

        with patch.object(self.engine.matcher, "compute_similarity", return_value=0.8):
            weight_with_semantic = self.engine.calculate_weight(decision, outcome)

        with patch.object(self.engine.matcher, "compute_similarity", return_value=0.0):
            weight_without_semantic = self.engine.calculate_weight(decision, outcome)

        assert weight_with_semantic > weight_without_semantic

    def test_low_similarity_ignored(self):
        """Similarity below 0.3 should not contribute a semantic signal."""
        decision = _make_decision(start_date=date.today() - timedelta(days=5))
        outcome = _make_outcome(date=date.today())

        with patch.object(self.engine.matcher, "compute_similarity", return_value=0.2):
            weight_low = self.engine.calculate_weight(decision, outcome)

        with patch.object(self.engine.matcher, "compute_similarity", return_value=0.0):
            weight_zero = self.engine.calculate_weight(decision, outcome)

        # Both should use temporal-only fallback (temporal * 0.6)
        assert weight_low == weight_zero

    def test_graduated_semantic_weight(self):
        """_graduated_semantic_weight should increase monotonically."""
        engine = AttributionEngine()
        w1 = engine._graduated_semantic_weight(0.4)
        w2 = engine._graduated_semantic_weight(0.6)
        w3 = engine._graduated_semantic_weight(0.9)

        assert w1 < w2 < w3
        assert w3 <= 0.95  # capped at 0.95


# ---------------------------------------------------------------------------
# Full Attribution Run
# ---------------------------------------------------------------------------

class TestFullAttributionRun:
    """Integration test for run_full_attribution using the real DB session."""

    def test_full_attribution_run(self, test_db):
        """
        End-to-end: create org + decision + outcome, run attribution,
        verify summary and detail rows are correct.
        """
        org = models.Organization(name="Engine Test Org")
        test_db.add(org)
        test_db.flush()

        decision = models.Decision(
            description="Test Campaign",
            decision_type="AD_CAMPAIGN",
            start_date=date.today() - timedelta(days=5),
            cost=1000.0,
            status="ACTIVE",
            organization_id=org.id,
        )
        test_db.add(decision)
        test_db.flush()

        outcome = models.Outcome(
            metric_name="REVENUE",
            value=3000.0,
            date=date.today(),
            organization_id=org.id,
            decision_id=decision.id,  # hard link
        )
        test_db.add(outcome)
        test_db.commit()

        engine = AttributionEngine()
        engine.run_full_attribution(test_db, organization_id=org.id)

        # Summary row (outcome_id = None)
        summary = test_db.query(models.Attribution).filter(
            models.Attribution.decision_id == decision.id,
            models.Attribution.outcome_id == None,
        ).first()
        assert summary is not None
        assert summary.attributed_value == 3000.0
        assert summary.roi_multiple == pytest.approx(3.0, abs=0.5)
        assert summary.recommendation in ("SCALE", "MAINTAIN", "INVESTIGATE", "KILL")

        # Detail row (outcome_id set)
        detail = test_db.query(models.Attribution).filter(
            models.Attribution.decision_id == decision.id,
            models.Attribution.outcome_id == outcome.id,
        ).first()
        assert detail is not None
        assert detail.weight == 1.0  # hard-linked

    def test_full_attribution_split_across_decisions(self, test_db):
        """Unlinked outcome should be split across eligible decisions."""
        org = models.Organization(name="Split Org")
        test_db.add(org)
        test_db.flush()

        d1 = models.Decision(
            description="Campaign A",
            decision_type="AD_CAMPAIGN",
            start_date=date.today() - timedelta(days=10),
            cost=500.0,
            organization_id=org.id,
        )
        d2 = models.Decision(
            description="Campaign B",
            decision_type="AD_CAMPAIGN",
            start_date=date.today() - timedelta(days=10),
            cost=500.0,
            organization_id=org.id,
        )
        test_db.add_all([d1, d2])
        test_db.flush()

        # Unlinked outcome (no decision_id)
        outcome = models.Outcome(
            metric_name="REVENUE",
            value=1000.0,
            date=date.today(),
            organization_id=org.id,
        )
        test_db.add(outcome)
        test_db.commit()

        engine = AttributionEngine()
        engine.run_full_attribution(test_db, organization_id=org.id)

        a1 = test_db.query(models.Attribution).filter(
            models.Attribution.decision_id == d1.id,
            models.Attribution.outcome_id == None,
        ).first()
        a2 = test_db.query(models.Attribution).filter(
            models.Attribution.decision_id == d2.id,
            models.Attribution.outcome_id == None,
        ).first()

        assert a1 is not None
        assert a2 is not None
        # Both decisions started at the same time with similar descriptions,
        # so the value should be roughly evenly split.
        total = a1.attributed_value + a2.attributed_value
        assert total == pytest.approx(1000.0, abs=0.01)

    def test_full_attribution_no_decisions(self, test_db):
        """run_full_attribution should not crash when there are no decisions."""
        org = models.Organization(name="Empty Org")
        test_db.add(org)
        test_db.commit()

        engine = AttributionEngine()
        # Should not raise
        engine.run_full_attribution(test_db, organization_id=org.id)

    def test_full_attribution_clears_previous(self, test_db):
        """Running attribution twice should replace (not duplicate) rows."""
        org = models.Organization(name="Rerun Org")
        test_db.add(org)
        test_db.flush()

        decision = models.Decision(
            description="Rerun Campaign",
            decision_type="AD_CAMPAIGN",
            start_date=date.today() - timedelta(days=5),
            cost=1000.0,
            organization_id=org.id,
        )
        test_db.add(decision)
        test_db.flush()

        outcome = models.Outcome(
            metric_name="REVENUE",
            value=2000.0,
            date=date.today(),
            organization_id=org.id,
            decision_id=decision.id,
        )
        test_db.add(outcome)
        test_db.commit()

        engine = AttributionEngine()
        engine.run_full_attribution(test_db, organization_id=org.id)
        engine.run_full_attribution(test_db, organization_id=org.id)

        count = test_db.query(models.Attribution).filter(
            models.Attribution.decision_id == decision.id,
            models.Attribution.outcome_id == None,
        ).count()
        assert count == 1, "Should have exactly one summary row, not duplicates"


# ---------------------------------------------------------------------------
# Confidence Scoring
# ---------------------------------------------------------------------------

class TestConfidenceScoring:
    """Tests for calculate_confidence."""

    def setup_method(self):
        self.engine = AttributionEngine()

    def test_confidence_scoring(self):
        """Base confidence (no linked outcomes, short duration, manual source)."""
        decision = _make_decision(
            start_date=date.today() - timedelta(days=5),
            source="MANUAL",
        )
        score = self.engine.calculate_confidence(decision, [], 0)
        assert score == 0.25  # base only

    def test_confidence_increases_with_links(self):
        """More linked outcomes should raise confidence."""
        decision = _make_decision(start_date=date.today() - timedelta(days=5))
        outcomes_1 = [_make_outcome(id=i) for i in range(1)]
        outcomes_5 = [_make_outcome(id=i) for i in range(5)]

        score_1 = self.engine.calculate_confidence(decision, outcomes_1, 5)
        score_5 = self.engine.calculate_confidence(decision, outcomes_5, 5)

        assert score_5 > score_1

    def test_confidence_integrated_source_bonus(self):
        """Decisions from integrated sources (HubSpot, etc.) get a bonus."""
        decision_manual = _make_decision(source="MANUAL")
        decision_hubspot = _make_decision(source="HUBSPOT")

        score_m = self.engine.calculate_confidence(decision_manual, [], 0)
        score_h = self.engine.calculate_confidence(decision_hubspot, [], 0)

        assert score_h > score_m

    def test_confidence_capped_at_1(self):
        """Confidence should never exceed 1.0."""
        decision = _make_decision(
            start_date=date.today() - timedelta(days=60),
            source="HUBSPOT",
        )
        many_outcomes = [_make_outcome(id=i) for i in range(20)]
        score = self.engine.calculate_confidence(decision, many_outcomes, 20)
        assert score <= 1.0

    def test_confidence_maturity_bonus(self):
        """Decisions active > 30 days should get a maturity bonus."""
        young = _make_decision(start_date=date.today() - timedelta(days=5))
        mature = _make_decision(start_date=date.today() - timedelta(days=60))

        score_young = self.engine.calculate_confidence(young, [], 0)
        score_mature = self.engine.calculate_confidence(mature, [], 0)

        assert score_mature > score_young


# ---------------------------------------------------------------------------
# Recommendation Logic
# ---------------------------------------------------------------------------

class TestRecommendationLogic:
    """Tests for generate_recommendation."""

    def setup_method(self):
        self.engine = AttributionEngine()

    def test_recommendation_logic(self):
        """High ROI + high confidence -> SCALE for ad campaigns."""
        rec = self.engine.generate_recommendation(4.0, 0.7, "AD_CAMPAIGN")
        assert rec == "SCALE"

    def test_recommendation_low_confidence(self):
        """Low confidence should always yield INVESTIGATE regardless of ROI."""
        rec = self.engine.generate_recommendation(10.0, 0.3, "AD_CAMPAIGN")
        assert rec == "INVESTIGATE"

    def test_recommendation_kill(self):
        """Low ROI + adequate confidence -> KILL."""
        rec = self.engine.generate_recommendation(0.1, 0.6, "AD_CAMPAIGN")
        assert rec == "KILL"

    def test_recommendation_maintain(self):
        """Moderate ROI -> MAINTAIN."""
        rec = self.engine.generate_recommendation(1.5, 0.6, "AD_CAMPAIGN")
        assert rec == "MAINTAIN"

    def test_recommendation_hire_patience(self):
        """HIRE decisions should have lower thresholds (more patience)."""
        # ROI=1.0 is MAINTAIN for HIRE (threshold 0.8), but for AD_CAMPAIGN
        # that same ROI is also MAINTAIN (threshold 1.0), so let's test
        # a value between the two thresholds.
        rec_hire = self.engine.generate_recommendation(0.9, 0.5, "HIRE")
        rec_campaign = self.engine.generate_recommendation(0.9, 0.5, "AD_CAMPAIGN")

        assert rec_hire == "MAINTAIN"
        assert rec_campaign == "INVESTIGATE"

    def test_recommendation_hire_scale(self):
        """HIRE needs roi >= 2.0 and confidence >= 0.55 to SCALE."""
        rec = self.engine.generate_recommendation(2.5, 0.6, "HIRE")
        assert rec == "SCALE"

    def test_recommendation_tool_kill(self):
        """TOOL with very low ROI should KILL."""
        rec = self.engine.generate_recommendation(0.1, 0.6, "TOOL")
        assert rec == "KILL"


# ---------------------------------------------------------------------------
# Cost Calculation
# ---------------------------------------------------------------------------

class TestCostCalculation:
    """Tests for calculate_total_cost."""

    def setup_method(self):
        self.engine = AttributionEngine()

    def test_ad_campaign_cost_flat(self):
        """AD_CAMPAIGN cost should be the one-time cost as-is."""
        decision = _make_decision(decision_type="AD_CAMPAIGN", cost=5000.0)
        assert self.engine.calculate_total_cost(decision) == 5000.0

    def test_hire_cost_with_ramp(self):
        """HIRE cost uses monthly cost * effective months with ramp-up curve."""
        decision = _make_decision(
            decision_type="HIRE",
            cost=8000.0,
            start_date=date.today() - timedelta(days=90),  # ~3 months
        )
        total = self.engine.calculate_total_cost(decision)
        # 3 months active: effective_months = 0.4 + 0.7 + 1.0 = 2.1
        # total = 8000 * 2.1 = 16800 (approximately, depends on exact month boundaries)
        assert total > 8000.0  # more than one month
        assert total > 0

    def test_zero_cost(self):
        """Zero-cost decision should return 0."""
        decision = _make_decision(cost=0.0)
        assert self.engine.calculate_total_cost(decision) == 0.0

    def test_none_cost(self):
        """None cost should return 0."""
        decision = _make_decision(cost=None)
        assert self.engine.calculate_total_cost(decision) == 0.0
