"""
AI-Powered Decision Analyzer

Uses historical decision-outcome patterns + LLM to generate
data-backed, actionable recommendations. The analysis pipeline:

1. Benchmark: Compare this decision against historical peers (same type, similar cost)
2. Pattern Detection: Find what worked / failed for similar decisions
3. Risk Assessment: Confidence intervals and downside scenarios
4. LLM Synthesis: Turn raw analytics into natural language insights

Training data comes from the org's own decision history — the more
decisions and outcomes tracked, the better the analysis gets.
"""

import math
import logging
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from .. import models

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """Analyzes decisions using historical benchmarks + LLM synthesis."""

    # ------------------------------------------------------------------
    # Benchmarking: compare against historical peers
    # ------------------------------------------------------------------

    def compute_benchmarks(
        self, db: Session, organization_id: int, decision: models.Decision
    ) -> Dict:
        """
        Compute benchmark statistics for decisions of the same type
        within this organization. Returns percentile ranking, averages, etc.
        """
        # Get all summary attributions for same-type decisions in this org
        peer_attrs = (
            db.query(models.Attribution, models.Decision)
            .join(models.Decision, models.Attribution.decision_id == models.Decision.id)
            .filter(
                models.Decision.organization_id == organization_id,
                models.Decision.decision_type == decision.decision_type,
                models.Attribution.outcome_id == None,  # summary rows only
            )
            .all()
        )

        if len(peer_attrs) < 2:
            return {
                "has_benchmarks": False,
                "reason": f"Need at least 2 {decision.decision_type} decisions for benchmarks, have {len(peer_attrs)}",
                "peer_count": len(peer_attrs),
            }

        rois = sorted([a.roi_multiple for a, d in peer_attrs if a.roi_multiple is not None])
        values = [a.attributed_value for a, d in peer_attrs if a.attributed_value]
        costs = [a.total_cost for a, d in peer_attrs if a.total_cost and a.total_cost > 0]
        confidences = [a.confidence_score for a, d in peer_attrs if a.confidence_score]

        # Find this decision's attribution
        this_attr = None
        for a, d in peer_attrs:
            if d.id == decision.id:
                this_attr = a
                break

        this_roi = this_attr.roi_multiple if this_attr else 0.0

        # Percentile rank
        below = sum(1 for r in rois if r < this_roi)
        percentile = round((below / len(rois)) * 100) if rois else 0

        # Compute stats
        avg_roi = sum(rois) / len(rois) if rois else 0.0
        median_roi = rois[len(rois) // 2] if rois else 0.0
        top_quartile = rois[int(len(rois) * 0.75)] if len(rois) >= 4 else rois[-1] if rois else 0.0
        bottom_quartile = rois[int(len(rois) * 0.25)] if len(rois) >= 4 else rois[0] if rois else 0.0

        return {
            "has_benchmarks": True,
            "peer_count": len(peer_attrs),
            "decision_type": decision.decision_type,
            "this_roi": round(this_roi, 2),
            "percentile_rank": percentile,
            "avg_roi": round(avg_roi, 2),
            "median_roi": round(median_roi, 2),
            "top_quartile_roi": round(top_quartile, 2),
            "bottom_quartile_roi": round(bottom_quartile, 2),
            "avg_attributed_value": round(sum(values) / len(values), 2) if values else 0,
            "avg_cost": round(sum(costs) / len(costs), 2) if costs else 0,
            "avg_confidence": round(sum(confidences) / len(confidences), 2) if confidences else 0,
        }

    # ------------------------------------------------------------------
    # Pattern Detection: find what worked for similar decisions
    # ------------------------------------------------------------------

    def find_similar_decisions(
        self, db: Session, organization_id: int, decision: models.Decision, limit: int = 5
    ) -> List[Dict]:
        """
        Find the most comparable past decisions based on:
        - Same decision type
        - Similar cost range (0.5x to 2x)
        - Have completed attribution
        Returns them sorted by ROI descending (best performers first).
        """
        cost = decision.cost or 0.0
        cost_low = cost * 0.5
        cost_high = cost * 2.0

        peers = (
            db.query(models.Decision, models.Attribution)
            .join(models.Attribution, models.Attribution.decision_id == models.Decision.id)
            .filter(
                models.Decision.organization_id == organization_id,
                models.Decision.decision_type == decision.decision_type,
                models.Decision.id != decision.id,
                models.Decision.cost >= cost_low,
                models.Decision.cost <= cost_high,
                models.Attribution.outcome_id == None,  # summary rows
            )
            .order_by(models.Attribution.roi_multiple.desc())
            .limit(limit)
            .all()
        )

        results = []
        for d, a in peers:
            results.append({
                "id": d.id,
                "description": d.description,
                "cost": d.cost,
                "total_cost": a.total_cost,
                "roi": round(a.roi_multiple, 2),
                "attributed_value": round(a.attributed_value, 2),
                "confidence": a.confidence_score,
                "recommendation": a.recommendation,
                "status": d.status,
                "days_active": (date.today() - d.start_date).days if d.start_date else 0,
            })

        return results

    # ------------------------------------------------------------------
    # Outcome Pattern Analysis
    # ------------------------------------------------------------------

    def analyze_outcome_patterns(
        self, db: Session, organization_id: int, decision: models.Decision
    ) -> Dict:
        """
        Analyze the timing, velocity, and quality of outcomes
        linked to this decision vs. organizational averages.
        """
        # Get linked outcomes for this decision
        linked_attrs = (
            db.query(models.Attribution, models.Outcome)
            .join(models.Outcome, models.Attribution.outcome_id == models.Outcome.id)
            .filter(
                models.Attribution.decision_id == decision.id,
                models.Attribution.outcome_id != None,
            )
            .all()
        )

        if not linked_attrs:
            return {
                "outcome_count": 0,
                "has_patterns": False,
                "reason": "No outcomes linked yet",
            }

        outcomes = [o for _, o in linked_attrs]
        weights = [a.weight for a, _ in linked_attrs]

        values = [o.value for o in outcomes]
        dates = [o.date for o in outcomes if o.date]

        # Time to first outcome
        first_outcome_date = min(dates) if dates else None
        time_to_first = (
            (first_outcome_date - decision.start_date).days
            if first_outcome_date and decision.start_date
            else None
        )

        # Outcome velocity: outcomes per 30-day period
        if decision.start_date and dates:
            days_span = max(1, (max(dates) - decision.start_date).days)
            velocity_per_30d = round((len(outcomes) / days_span) * 30, 1)
        else:
            velocity_per_30d = 0

        # Outcome concentration: is revenue spread or concentrated?
        total_value = sum(values)
        if total_value > 0 and len(values) > 1:
            shares = [v / total_value for v in values]
            # Herfindahl index: 1/n = perfectly spread, 1.0 = completely concentrated
            hhi = sum(s * s for s in shares)
            concentration = "concentrated" if hhi > 0.5 else "spread" if hhi < 0.25 else "moderate"
        else:
            hhi = 1.0
            concentration = "single_outcome"

        # Average outcome value vs org average
        org_avg_outcome = (
            db.query(func.avg(models.Outcome.value))
            .filter(models.Outcome.organization_id == organization_id)
            .scalar()
        ) or 0.0

        avg_value = sum(values) / len(values) if values else 0.0

        # Metric breakdown
        metric_breakdown = {}
        for o in outcomes:
            metric_breakdown[o.metric_name] = metric_breakdown.get(o.metric_name, 0) + 1

        return {
            "outcome_count": len(outcomes),
            "has_patterns": True,
            "total_value": round(total_value, 2),
            "avg_outcome_value": round(avg_value, 2),
            "org_avg_outcome_value": round(float(org_avg_outcome), 2),
            "value_vs_org_avg": round(avg_value / float(org_avg_outcome), 2) if org_avg_outcome else 0,
            "time_to_first_outcome_days": time_to_first,
            "velocity_per_30d": velocity_per_30d,
            "concentration": concentration,
            "concentration_index": round(hhi, 3),
            "metric_breakdown": metric_breakdown,
            "avg_weight": round(sum(weights) / len(weights), 3) if weights else 0,
        }

    # ------------------------------------------------------------------
    # Risk Assessment
    # ------------------------------------------------------------------

    def assess_risk(
        self, db: Session, organization_id: int, decision: models.Decision, benchmarks: Dict
    ) -> Dict:
        """
        Generate risk signals based on decision characteristics and benchmarks.
        """
        risks = []
        opportunities = []

        # Fetch this decision's attribution
        attr = (
            db.query(models.Attribution)
            .filter(
                models.Attribution.decision_id == decision.id,
                models.Attribution.outcome_id == None,
            )
            .first()
        )

        roi = attr.roi_multiple if attr else 0.0
        confidence = attr.confidence_score if attr else 0.0
        attributed_value = attr.attributed_value if attr else 0.0

        # Risk: low confidence + high spend
        cost = decision.cost or 0.0
        if confidence < 0.4 and cost > 0:
            risks.append({
                "signal": "low_confidence_high_spend",
                "severity": "high",
                "message": f"Confidence is only {confidence:.0%} but you're spending ${cost:,.0f}/mo — attribution evidence is weak",
            })

        # Risk: decision running too long without outcomes
        if decision.start_date:
            days_active = (date.today() - decision.start_date).days
            if days_active > 60 and attributed_value == 0:
                risks.append({
                    "signal": "no_outcomes_60d",
                    "severity": "high",
                    "message": f"Decision has been active {days_active} days with zero attributed revenue",
                })
            elif days_active > 30 and attributed_value == 0:
                risks.append({
                    "signal": "no_outcomes_30d",
                    "severity": "medium",
                    "message": f"No outcomes after {days_active} days — consider whether this needs more time or a pivot",
                })

        # Risk: below bottom quartile
        if benchmarks.get("has_benchmarks") and benchmarks.get("percentile_rank", 50) < 25:
            risks.append({
                "signal": "below_peers",
                "severity": "medium",
                "message": f"ROI is in the bottom 25% of your {decision.decision_type} decisions (percentile: {benchmarks['percentile_rank']})",
            })

        # Risk: ROI declining (would need time series, approximate with age)
        if roi > 0 and roi < 1.0 and confidence >= 0.5:
            risks.append({
                "signal": "negative_roi",
                "severity": "medium",
                "message": f"Spending more than you're earning ({roi:.2f}x ROI) — monitor closely",
            })

        # Opportunity: top performer
        if benchmarks.get("has_benchmarks") and benchmarks.get("percentile_rank", 0) >= 75:
            opportunities.append({
                "signal": "top_performer",
                "message": f"Top 25% of {decision.decision_type} decisions — strong candidate for scaling",
            })

        # Opportunity: high confidence + positive ROI
        if confidence >= 0.7 and roi >= 2.0:
            opportunities.append({
                "signal": "high_conviction_winner",
                "message": f"High confidence ({confidence:.0%}) with strong ROI ({roi:.1f}x) — double down",
            })

        # Opportunity: fast time-to-value (vs. type expectation)
        if decision.start_date and attributed_value > 0:
            days_active = (date.today() - decision.start_date).days
            if decision.decision_type == "AD_CAMPAIGN" and days_active < 14 and roi > 1:
                opportunities.append({
                    "signal": "fast_payback",
                    "message": "Already ROI-positive within 2 weeks — campaign is resonating quickly",
                })
            elif decision.decision_type == "HIRE" and days_active < 45 and roi > 0.5:
                opportunities.append({
                    "signal": "fast_ramp",
                    "message": "Generating returns within 45 days — faster ramp than typical hires",
                })

        risk_score = "low"
        if any(r["severity"] == "high" for r in risks):
            risk_score = "high"
        elif any(r["severity"] == "medium" for r in risks):
            risk_score = "medium"

        return {
            "risk_score": risk_score,
            "risks": risks,
            "opportunities": opportunities,
        }

    # ------------------------------------------------------------------
    # LLM Synthesis: turn analytics into natural language
    # ------------------------------------------------------------------

    def synthesize_with_llm(
        self,
        decision: models.Decision,
        attr_summary: Optional[models.Attribution],
        benchmarks: Dict,
        patterns: Dict,
        risk_assessment: Dict,
        similar_decisions: List[Dict],
    ) -> str:
        """
        Build a rich, data-grounded prompt and call the LLM to generate
        a comprehensive analysis. Falls back to rule-based analysis if
        no LLM is available.
        """
        try:
            from .llm import llm_service
        except Exception:
            llm_service = None

        roi = attr_summary.roi_multiple if attr_summary else 0.0
        total_cost = attr_summary.total_cost if attr_summary else 0.0
        attributed_value = attr_summary.attributed_value if attr_summary else 0.0
        confidence = attr_summary.confidence_score if attr_summary else 0.0
        recommendation = attr_summary.recommendation if attr_summary else "PENDING"

        # Build the context-rich prompt
        sections = []

        sections.append(f"""DECISION UNDER ANALYSIS:
- Description: {decision.description}
- Type: {decision.decision_type}
- Monthly cost: ${decision.cost:,.0f}
- Total invested: ${total_cost:,.0f}
- Attributed revenue: ${attributed_value:,.0f}
- ROI: {roi:.2f}x
- Confidence: {confidence:.0%}
- Engine recommendation: {recommendation}
- Status: {decision.status}
- Active since: {decision.start_date}""")

        if benchmarks.get("has_benchmarks"):
            sections.append(f"""PEER BENCHMARKS ({benchmarks['peer_count']} similar {decision.decision_type} decisions):
- This decision's ROI percentile: {benchmarks['percentile_rank']}th
- Org average ROI for this type: {benchmarks['avg_roi']:.2f}x
- Median ROI: {benchmarks['median_roi']:.2f}x
- Top quartile ROI: {benchmarks['top_quartile_roi']:.2f}x
- Bottom quartile ROI: {benchmarks['bottom_quartile_roi']:.2f}x
- Avg attributed value: ${benchmarks['avg_attributed_value']:,.0f}""")

        if patterns.get("has_patterns"):
            sections.append(f"""OUTCOME PATTERNS:
- {patterns['outcome_count']} linked outcomes, total value ${patterns['total_value']:,.0f}
- Avg outcome value: ${patterns['avg_outcome_value']:,.0f} (org avg: ${patterns['org_avg_outcome_value']:,.0f})
- Time to first outcome: {patterns['time_to_first_outcome_days']} days
- Velocity: {patterns['velocity_per_30d']} outcomes per 30 days
- Revenue concentration: {patterns['concentration']} (HHI: {patterns['concentration_index']})
- Metrics: {patterns['metric_breakdown']}""")

        if similar_decisions:
            similar_text = "\n".join([
                f"  - {s['description']}: {s['roi']:.2f}x ROI, ${s['attributed_value']:,.0f} revenue, {s['recommendation']}"
                for s in similar_decisions[:3]
            ])
            sections.append(f"COMPARABLE DECISIONS (similar type & cost):\n{similar_text}")

        if risk_assessment["risks"]:
            risk_text = "\n".join([f"  - [{r['severity'].upper()}] {r['message']}" for r in risk_assessment["risks"]])
            sections.append(f"RISK SIGNALS:\n{risk_text}")

        if risk_assessment["opportunities"]:
            opp_text = "\n".join([f"  - {o['message']}" for o in risk_assessment["opportunities"]])
            sections.append(f"OPPORTUNITIES:\n{opp_text}")

        context = "\n\n".join(sections)

        prompt = f"""You are an elite ROI analyst for a B2B SaaS company. Analyze this business decision using the data provided and produce a concise, actionable analysis.

{context}

Write a 3-4 sentence analysis that:
1. States whether this decision is performing above, at, or below expectations (use the benchmark data)
2. Identifies the PRIMARY driver of the result (timing, cost efficiency, outcome quality, etc.)
3. Gives ONE specific, actionable recommendation the team should take next
4. If there are risk signals, mention the most important one

Rules:
- Use actual numbers from the data — do not fabricate statistics
- Be direct and specific, not vague
- Do not use markdown formatting
- Write as if advising a VP of Revenue or CFO
- If confidence is below 50%, emphasize that the analysis is preliminary"""

        # Try LLM first
        if llm_service and llm_service.model:
            try:
                response = llm_service.model.generate_content(prompt)
                return response.text
            except Exception as e:
                logger.warning(f"LLM synthesis failed, falling back to rules: {e}")

        # Rule-based fallback
        return self._rule_based_analysis(
            decision, roi, confidence, total_cost, attributed_value,
            recommendation, benchmarks, patterns, risk_assessment
        )

    def _rule_based_analysis(
        self, decision, roi, confidence, total_cost, attributed_value,
        recommendation, benchmarks, patterns, risk_assessment
    ) -> str:
        """Generate a deterministic analysis when LLM is unavailable."""
        parts = []

        # Performance statement
        if benchmarks.get("has_benchmarks"):
            pct = benchmarks["percentile_rank"]
            avg = benchmarks["avg_roi"]
            if pct >= 75:
                parts.append(
                    f"This {decision.decision_type.lower().replace('_', ' ')} is a top performer, "
                    f"ranking in the {pct}th percentile with {roi:.2f}x ROI vs. the {avg:.2f}x average for similar decisions."
                )
            elif pct >= 50:
                parts.append(
                    f"This {decision.decision_type.lower().replace('_', ' ')} is performing at par, "
                    f"with {roi:.2f}x ROI ({pct}th percentile) against a {avg:.2f}x average."
                )
            else:
                parts.append(
                    f"This {decision.decision_type.lower().replace('_', ' ')} is underperforming at {roi:.2f}x ROI, "
                    f"sitting in the {pct}th percentile vs. the {avg:.2f}x type average."
                )
        else:
            if roi >= 3.0:
                parts.append(f"Strong performance at {roi:.2f}x ROI, generating ${attributed_value:,.0f} from ${total_cost:,.0f} invested.")
            elif roi >= 1.0:
                parts.append(f"Positive but moderate ROI of {roi:.2f}x — generating ${attributed_value:,.0f} from ${total_cost:,.0f} invested.")
            elif roi > 0:
                parts.append(f"Currently underwater at {roi:.2f}x ROI — ${total_cost:,.0f} invested, only ${attributed_value:,.0f} attributed back.")
            else:
                parts.append(f"No attributed revenue yet against ${total_cost:,.0f} invested.")

        # Pattern insight
        if patterns.get("has_patterns"):
            if patterns["velocity_per_30d"] > 2:
                parts.append(f"Outcome velocity is strong at {patterns['velocity_per_30d']} per month.")
            if patterns["concentration"] == "concentrated":
                parts.append("Revenue is concentrated in a few large outcomes — consider diversifying.")
            if patterns.get("time_to_first_outcome_days") is not None:
                ttf = patterns["time_to_first_outcome_days"]
                if ttf <= 14:
                    parts.append(f"Fast time-to-value at {ttf} days to first outcome.")
                elif ttf > 60:
                    parts.append(f"Slow start — {ttf} days before first attributed outcome.")

        # Recommendation
        if recommendation == "SCALE":
            parts.append("Recommendation: increase budget or scope to capture more of this channel's upside.")
        elif recommendation == "KILL":
            parts.append("Recommendation: wind down this investment and reallocate budget to higher-ROI decisions.")
        elif recommendation == "INVESTIGATE":
            parts.append("Recommendation: dig deeper into the data before making budget changes — the signal is not yet clear.")
        elif recommendation == "MAINTAIN":
            parts.append("Recommendation: continue at current levels and monitor for trend changes.")

        # Risk callout
        if risk_assessment["risks"]:
            top_risk = risk_assessment["risks"][0]
            parts.append(f"Key risk: {top_risk['message']}.")

        # Confidence caveat
        if confidence < 0.5:
            parts.append(f"Note: confidence is only {confidence:.0%} — treat this analysis as preliminary.")

        return " ".join(parts)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def analyze_decision(
        self, db: Session, organization_id: int, decision_id: int
    ) -> Dict:
        """
        Run the full AI analysis pipeline for a single decision.
        Returns structured data + natural language synthesis.
        """
        decision = (
            db.query(models.Decision)
            .filter(
                models.Decision.id == decision_id,
                models.Decision.organization_id == organization_id,
            )
            .first()
        )
        if not decision:
            return {"error": "Decision not found"}

        attr_summary = (
            db.query(models.Attribution)
            .filter(
                models.Attribution.decision_id == decision.id,
                models.Attribution.outcome_id == None,
            )
            .first()
        )

        # Run analysis stages
        benchmarks = self.compute_benchmarks(db, organization_id, decision)
        patterns = self.analyze_outcome_patterns(db, organization_id, decision)
        similar = self.find_similar_decisions(db, organization_id, decision)
        risk = self.assess_risk(db, organization_id, decision, benchmarks)

        # Synthesize
        analysis_text = self.synthesize_with_llm(
            decision, attr_summary, benchmarks, patterns, risk, similar
        )

        return {
            "decision_id": decision.id,
            "description": decision.description,
            "analysis": analysis_text,
            "benchmarks": benchmarks,
            "outcome_patterns": patterns,
            "similar_decisions": similar,
            "risk_assessment": risk,
            "data_quality": {
                "confidence": attr_summary.confidence_score if attr_summary else 0.0,
                "recommendation": attr_summary.recommendation if attr_summary else "PENDING",
                "roi": round(attr_summary.roi_multiple, 2) if attr_summary else 0.0,
            },
        }


# Singleton
ai_analyzer = AIAnalyzer()
