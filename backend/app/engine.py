"""
Attribution Engine v2 — Multi-signal, source-aware, with honest confidence tiers.

Signals used (in priority order):
1. Hard link      — manual or CRM-imported decision_id on outcome → weight 1.0
2. Source match   — outcome.source matches decision.source (e.g. both HUBSPOT)
3. Metadata match — structured field comparison (campaign IDs, vendor names)
4. Semantic       — sentence-transformer similarity on descriptions
5. Temporal       — exponential decay based on days between decision start and outcome date

Confidence tiers:
- DIRECT     — hard-linked outcome (manual or imported with decision_id)
- HIGH       — source match + temporal proximity, or strong semantic + source
- MODERATE   — semantic match without source, or source without semantic
- LOW        — temporal proximity only (the weakest signal)
"""

import math
from datetime import date
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session

from . import models
from .services.matching import SemanticMatcher

WINDOW_DAYS = 90

# Per-type default windows: hires/tools have longer-lasting impact than campaigns
TYPE_WINDOW_MULTIPLIERS = {
    "HIRE": 1.5,        # 135 days — people ramp up slowly
    "TOOL": 1.2,        # 108 days — tools need adoption time
    "AD_CAMPAIGN": 0.7, # 63 days — campaigns have fast, short impact
    "VENDOR": 1.0,      # 90 days — standard
}

# Signal blend weights (must sum to 1.0)
SOURCE_BLEND = 0.30     # Source/metadata match
SEMANTIC_BLEND = 0.40   # NLP text similarity
TEMPORAL_BLEND = 0.30   # Time proximity

# Source compatibility map: which outcome sources relate to which decision sources
SOURCE_AFFINITY = {
    # outcome_source → set of compatible decision sources
    "HUBSPOT": {"HUBSPOT", "MANUAL"},
    "SALESFORCE": {"SALESFORCE", "MANUAL"},
    "MANUAL": {"MANUAL", "HUBSPOT", "SALESFORCE", "GOOGLE_ADS", "META_ADS", "LINKEDIN_ADS", "QUICKBOOKS"},
}

# Decision source → likely outcome sources
DECISION_SOURCE_AFFINITY = {
    "GOOGLE_ADS": {"MANUAL", "HUBSPOT", "SALESFORCE"},
    "META_ADS": {"MANUAL", "HUBSPOT", "SALESFORCE"},
    "LINKEDIN_ADS": {"MANUAL", "HUBSPOT", "SALESFORCE"},
    "QUICKBOOKS": {"MANUAL"},
    "HUBSPOT": {"HUBSPOT", "MANUAL"},
    "SALESFORCE": {"SALESFORCE", "MANUAL"},
    "MANUAL": {"MANUAL", "HUBSPOT", "SALESFORCE"},
}

# Metric reliability multipliers for confidence scoring
METRIC_CONFIDENCE = {
    "REVENUE": 1.0,
    "PIPELINE_VALUE": 0.7,
    "LEADS": 0.5,
}

# Hire/tool ramp-up: fraction of cost that's "productive" per month
RAMP_UP_CURVE = [0.4, 0.7, 1.0]

# Confidence tier thresholds
CONFIDENCE_TIER_THRESHOLDS = {
    "DIRECT": 0.85,    # hard-linked, very high trust
    "HIGH": 0.60,      # source + temporal/semantic, good trust
    "MODERATE": 0.40,  # some signal but incomplete
    "LOW": 0.0,        # temporal only, low trust
}


class AttributionEngine:
    def __init__(self):
        self.matcher = SemanticMatcher()

    # ------------------------------------------------------------------
    # Signal Computation
    # ------------------------------------------------------------------

    def _exponential_decay(self, days_diff: float, window_days: float) -> float:
        """Exponential decay — drops fast early, long tail near zero."""
        half_life = window_days * 0.4
        decay = math.exp(-0.693 * days_diff / half_life)
        return max(0.0, decay)

    def _graduated_semantic_weight(self, similarity: float) -> float:
        """Scale semantic weight by similarity strength."""
        if similarity < 0.3:
            return 0.0
        return min(0.95, 0.3 + 0.65 * similarity)

    def _effective_window(self, decision, base_window: int) -> int:
        """Return the attribution window adjusted for decision type."""
        multiplier = TYPE_WINDOW_MULTIPLIERS.get(decision.decision_type, 1.0)
        return int(base_window * multiplier)

    def _source_match_score(self, decision, outcome) -> float:
        """
        Score based on source field compatibility.
        Returns 0.0–1.0 based on how well the sources align.
        """
        d_source = (decision.source or "").upper()
        o_source = (outcome.source or "").upper()

        if not d_source or not o_source:
            return 0.0

        # Direct source match (both from same integration)
        if d_source == o_source and d_source != "MANUAL":
            return 1.0

        # Check source affinity (e.g. HUBSPOT outcome → HUBSPOT decision)
        compatible_sources = SOURCE_AFFINITY.get(o_source, set())
        if d_source in compatible_sources and d_source != "MANUAL":
            return 0.7

        # Check reverse: decision source expects these outcome sources
        expected_outcomes = DECISION_SOURCE_AFFINITY.get(d_source, set())
        if o_source in expected_outcomes and o_source != "MANUAL":
            return 0.5

        # Both manual — no source signal
        if d_source == "MANUAL" and o_source == "MANUAL":
            return 0.0

        return 0.1  # Weak cross-source connection

    def _metadata_match_score(self, decision, outcome) -> float:
        """
        Score based on structured metadata comparison.
        Looks for matching campaign IDs, vendor names, platform fields.
        """
        d_meta = decision.meta_data if decision.meta_data else {}
        o_desc = (outcome.description or "").lower()
        d_desc = (decision.description or "").lower()

        score = 0.0

        # Check if decision's platform/vendor name appears in outcome description
        platform = d_meta.get("platform", "")
        vendor = d_meta.get("vendor", "")
        campaign_name = d_meta.get("campaign_name", "")

        if platform and platform.lower() in o_desc:
            score += 0.4
        if vendor and vendor.lower() in o_desc:
            score += 0.5
        if campaign_name and campaign_name.lower() in o_desc:
            score += 0.6

        # Check type-to-metric alignment
        # AD_CAMPAIGN decisions should preferentially link to REVENUE/LEADS outcomes
        # HIRE decisions should preferentially link to REVENUE/PIPELINE outcomes
        type_metric_affinity = {
            "AD_CAMPAIGN": {"REVENUE": 0.3, "LEADS": 0.4, "PIPELINE_VALUE": 0.2},
            "HIRE": {"REVENUE": 0.4, "PIPELINE_VALUE": 0.3, "LEADS": 0.1},
            "TOOL": {"REVENUE": 0.2, "PIPELINE_VALUE": 0.2, "LEADS": 0.3},
            "VENDOR": {"REVENUE": 0.2, "PIPELINE_VALUE": 0.2, "LEADS": 0.2},
        }

        metric_scores = type_metric_affinity.get(decision.decision_type, {})
        metric_bonus = metric_scores.get(outcome.metric_name, 0.0)
        score += metric_bonus

        return min(1.0, score)

    def calculate_weight(self, decision, outcome, window_days: int = 90) -> Tuple[float, str]:
        """
        Multi-signal attribution weight combining source match, semantic
        similarity, metadata, and temporal proximity.

        Returns (weight, signal_type) where signal_type indicates the
        strongest signal used for this attribution.
        """
        # Hard link — manual override always wins
        if outcome.decision_id == decision.id:
            return (1.0, "DIRECT")

        if not decision.start_date:
            return (0.0, "NONE")

        effective_window = self._effective_window(decision, window_days)
        days_diff = (outcome.date - decision.start_date).days

        if days_diff < 0 or days_diff > effective_window:
            return (0.0, "NONE")

        # --- Compute individual signals ---

        # Temporal signal: exponential decay
        temporal = self._exponential_decay(days_diff, effective_window)

        # Source signal: integration source matching
        source = self._source_match_score(decision, outcome)

        # Metadata signal: structured field comparison
        metadata = self._metadata_match_score(decision, outcome)

        # Semantic signal: NLP text similarity
        semantic = 0.0
        if decision.description and outcome.description:
            similarity = self.matcher.compute_similarity(
                decision.description, outcome.description
            )
            if similarity > 0.3:
                semantic = self._graduated_semantic_weight(similarity)

        # Combined source+metadata signal (take the stronger one)
        source_combined = max(source, metadata)

        # --- Determine signal type and blend ---

        if source_combined > 0.5 and semantic > 0.3:
            # Strong: both source/metadata AND semantic match
            signal_type = "HIGH"
            weight = SOURCE_BLEND * source_combined + SEMANTIC_BLEND * semantic + TEMPORAL_BLEND * temporal
        elif source_combined > 0.3:
            # Source/metadata match but weak/no semantic
            signal_type = "MODERATE"
            weight = 0.45 * source_combined + 0.15 * semantic + 0.40 * temporal
        elif semantic > 0.4:
            # Semantic match but no source
            signal_type = "MODERATE"
            weight = 0.15 * source_combined + 0.50 * semantic + 0.35 * temporal
        else:
            # Temporal only — weakest signal
            signal_type = "LOW"
            weight = temporal * 0.5  # Penalize heavily

        return (round(max(0.0, weight), 4), signal_type)

    # ------------------------------------------------------------------
    # Cost Calculation
    # ------------------------------------------------------------------

    def calculate_total_cost(self, decision) -> float:
        """
        HIRE/TOOL: monthly cost * months active, with ramp-up curve.
        AD_CAMPAIGN/VENDOR: one-time cost as-is.
        """
        cost = decision.cost if decision.cost and decision.cost > 0 else 0.0
        if cost == 0:
            return 0.0

        if decision.decision_type in ("HIRE", "TOOL"):
            start = decision.start_date
            end = decision.end_date or date.today()
            months = max(1, (end.year - start.year) * 12 + end.month - start.month + 1)

            effective_months = 0.0
            for m in range(months):
                ramp = RAMP_UP_CURVE[m] if m < len(RAMP_UP_CURVE) else 1.0
                effective_months += ramp
            return round(cost * effective_months, 2)

        return cost

    # ------------------------------------------------------------------
    # Confidence Scoring (accuracy-based, not volume-based)
    # ------------------------------------------------------------------

    def calculate_confidence(
        self,
        decision,
        linked_outcomes: list,
        signal_types: list,
        total_outcomes: int,
        attributed_value: float = 0.0,
    ) -> Tuple[float, str]:
        """
        Confidence score that reflects ATTRIBUTION ACCURACY, not data volume.

        Returns (score, tier) where tier is DIRECT/HIGH/MODERATE/LOW.

        Key change from v1: hard-linked outcomes dramatically boost confidence,
        temporal-only attributions are capped at 0.35.
        """
        if not linked_outcomes:
            return (0.15, "LOW")

        # --- Signal quality (primary driver of confidence) ---
        direct_count = signal_types.count("DIRECT")
        high_count = signal_types.count("HIGH")
        moderate_count = signal_types.count("MODERATE")
        low_count = signal_types.count("LOW")
        total_links = len(signal_types)

        # Base confidence from signal quality
        if direct_count > 0:
            # At least one hard link — high base confidence
            direct_ratio = direct_count / total_links
            base = 0.70 + (0.20 * direct_ratio)  # 0.70–0.90
        elif high_count > 0:
            high_ratio = high_count / total_links
            base = 0.45 + (0.20 * high_ratio)  # 0.45–0.65
        elif moderate_count > 0:
            base = 0.30 + (0.10 * (moderate_count / total_links))  # 0.30–0.40
        else:
            # All temporal-only — cap at 0.35
            base = min(0.35, 0.15 + (0.05 * low_count))

        # --- Secondary factors (smaller adjustments) ---

        # Source quality bonus
        if decision.source in ("HUBSPOT", "SALESFORCE", "QUICKBOOKS"):
            base += 0.05

        # Maturity bonus (decision active > 30 days)
        days_active = (
            (date.today() - decision.start_date).days if decision.start_date else 0
        )
        if days_active > 30:
            base += 0.03

        # Metric quality — REVENUE is more reliable than LEADS
        if linked_outcomes:
            avg_metric = sum(
                METRIC_CONFIDENCE.get(o.metric_name, 0.5) for o in linked_outcomes
            ) / len(linked_outcomes)
            base += 0.02 * avg_metric

        # Value spread — multiple outcomes is slightly more trustworthy
        if total_links >= 3:
            base += 0.03

        score = min(1.0, round(base, 2))

        # Determine tier
        if direct_count > 0 or score >= CONFIDENCE_TIER_THRESHOLDS["DIRECT"]:
            tier = "DIRECT"
        elif score >= CONFIDENCE_TIER_THRESHOLDS["HIGH"]:
            tier = "HIGH"
        elif score >= CONFIDENCE_TIER_THRESHOLDS["MODERATE"]:
            tier = "MODERATE"
        else:
            tier = "LOW"

        return (score, tier)

    # ------------------------------------------------------------------
    # Recommendations
    # ------------------------------------------------------------------

    def generate_recommendation(
        self, roi: float, confidence: float, confidence_tier: str, decision_type: str = ""
    ) -> str:
        """
        Decision-type-aware recommendations with confidence-gated actions.

        Key change: LOW confidence tier always → INVESTIGATE, regardless of ROI.
        This prevents the system from recommending KILL on thin evidence.
        """
        # Guard: low-quality attribution should never trigger strong action
        if confidence_tier == "LOW" or confidence < 0.35:
            return "INVESTIGATE"

        # Patient types: hires and tools have longer payback periods
        if decision_type in ("HIRE", "TOOL"):
            if roi >= 2.0 and confidence >= 0.55:
                return "SCALE"
            if roi >= 0.8:
                return "MAINTAIN"
            if roi >= 0.3:
                return "INVESTIGATE"
            # Only KILL with MODERATE+ confidence
            if confidence_tier in ("DIRECT", "HIGH"):
                return "KILL"
            return "INVESTIGATE"

        # Fast-return types: ad campaigns and vendors
        if roi >= 3.0 and confidence >= 0.55:
            return "SCALE"
        if roi >= 1.0:
            return "MAINTAIN"
        if roi >= 0.5:
            return "INVESTIGATE"
        # Only KILL with MODERATE+ confidence
        if confidence_tier in ("DIRECT", "HIGH"):
            return "KILL"
        return "INVESTIGATE"

    # ------------------------------------------------------------------
    # Full Attribution Run
    # ------------------------------------------------------------------

    def run_full_attribution(self, db: Session, organization_id: int):
        """
        Full attribution pipeline scoped to an organization:
        1. Fetch Decisions / Outcomes for the org
        2. Calculate multi-signal weights (source + semantic + temporal)
        3. Normalize weights and distribute outcome value across decisions
        4. Calculate total cost (with ramp-up for HIRE/TOOL)
        5. Score confidence with honest tiers, compute ROI, generate recommendation
        6. Persist per-outcome attribution rows + summary rows
        """
        # Clear old attribution data for this org
        decision_ids_subquery = db.query(models.Decision.id).filter(
            models.Decision.organization_id == organization_id
        )
        db.query(models.Attribution).filter(
            models.Attribution.decision_id.in_(decision_ids_subquery)
        ).delete(synchronize_session=False)

        decisions = db.query(models.Decision).filter(
            models.Decision.organization_id == organization_id
        ).all()
        outcomes = db.query(models.Outcome).filter(
            models.Outcome.organization_id == organization_id
        ).all()

        if not decisions:
            return

        # Organisation settings
        org = db.query(models.Organization).filter(
            models.Organization.id == organization_id
        ).first()
        window_days = 90
        if org and org.settings and "attribution_window" in org.settings:
            try:
                window_days = int(org.settings["attribution_window"])
            except Exception:
                pass

        outcome_map = {o.id: o for o in outcomes}

        # ----------------------------------------------------------
        # Stage 2: Calculate Weights (source + semantic + temporal)
        # ----------------------------------------------------------
        outcome_weights: Dict[int, Dict[int, Tuple[float, str]]] = {}

        for outcome in outcomes:
            weights: Dict[int, Tuple[float, str]] = {}

            if outcome.decision_id:
                # Hard link — 100% to that decision
                weights[outcome.decision_id] = (1.0, "DIRECT")
            else:
                for decision in decisions:
                    w, signal = self.calculate_weight(decision, outcome, window_days=window_days)
                    if w > 0:
                        weights[decision.id] = (w, signal)

            if weights:
                outcome_weights[outcome.id] = weights

        # ----------------------------------------------------------
        # Stage 3: Normalize weights and distribute value
        # ----------------------------------------------------------
        decision_stats: Dict[int, dict] = {
            d.id: {"value": 0.0, "linked_outcome_ids": [], "signal_types": []}
            for d in decisions
        }

        attributions_to_create = []

        for outcome in outcomes:
            if outcome.id not in outcome_weights:
                continue

            weights = outcome_weights[outcome.id]
            total_weight = sum(w for w, _ in weights.values())

            for decision_id, (weight, signal_type) in weights.items():
                if decision_id not in decision_stats:
                    continue

                share = weight / total_weight if total_weight > 0 else 0
                attr_value = outcome.value * share

                decision_stats[decision_id]["value"] += attr_value
                decision_stats[decision_id]["linked_outcome_ids"].append(outcome.id)
                decision_stats[decision_id]["signal_types"].append(signal_type)

                attributions_to_create.append(
                    models.Attribution(
                        decision_id=decision_id,
                        outcome_id=outcome.id,
                        weight=round(share, 4),
                        roi_multiple=0,
                        confidence_score=0,
                        attributed_value=round(attr_value, 2),
                        total_cost=0,
                        recommendation=signal_type,  # Store signal type per-outcome row
                    )
                )

        # ----------------------------------------------------------
        # Stages 4-5: Cost, confidence, ROI, recommendation per decision
        # ----------------------------------------------------------
        total_outcomes = len(outcomes)

        for decision in decisions:
            stats = decision_stats[decision.id]
            total_cost = self.calculate_total_cost(decision)
            attributed_val = stats["value"]

            roi = attributed_val / total_cost if total_cost > 0 else 0.0

            linked_outcomes = [
                outcome_map[oid]
                for oid in stats["linked_outcome_ids"]
                if oid in outcome_map
            ]

            confidence, confidence_tier = self.calculate_confidence(
                decision, linked_outcomes, stats["signal_types"],
                total_outcomes, attributed_val
            )

            recommendation = self.generate_recommendation(
                roi, confidence, confidence_tier, decision.decision_type
            )

            attributions_to_create.append(
                models.Attribution(
                    decision_id=decision.id,
                    outcome_id=None,  # Summary row
                    weight=0,
                    roi_multiple=round(roi, 4),
                    attributed_value=round(attributed_val, 2),
                    total_cost=round(total_cost, 2),
                    confidence_score=confidence,
                    recommendation=f"{recommendation}|{confidence_tier}",  # Encode tier in recommendation
                )
            )

        # Bulk insert
        db.add_all(attributions_to_create)
        db.commit()


engine = AttributionEngine()
