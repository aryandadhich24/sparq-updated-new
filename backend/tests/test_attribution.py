import pytest
from backend.app.engine import engine
from backend.app import models
from datetime import date, timedelta

def test_attribution_basic_logic(db):
    # Setup: Org, Decision, Outcome
    org = models.Organization(name="Attribution Test")
    db.add(org)
    db.flush()
    
    decision = models.Decision(
        description="Test Campaign",
        decision_type="AD_CAMPAIGN",
        start_date=date.today() - timedelta(days=5),
        cost=1000.0,
        organization_id=org.id
    )
    db.add(decision)
    db.flush()
    
    outcome = models.Outcome(
        metric_name="REVENUE",
        value=2000.0,
        date=date.today(),
        organization_id=org.id,
        decision_id=decision.id
    )
    db.add(outcome)
    db.commit()
    
    # Run attribution
    engine.run_full_attribution(db, org.id)
    
    # Verify - Summary record has outcome_id=None
    attr = db.query(models.Attribution).filter(
        models.Attribution.decision_id == decision.id,
        models.Attribution.outcome_id == None
    ).first()
    
    assert attr is not None
    assert attr.attributed_value == 2000.0
    assert attr.roi_multiple == 2.0

def test_attribution_split(db):
    # Setup: 1 Outcome linked to 2 Decisions via semantic window
    org = models.Organization(name="Split Test")
    db.add(org)
    db.flush()
    
    # Two decisions at same time
    d1 = models.Decision(description="Campaign A", decision_type="AD_CAMPAIGN", start_date=date.today()-timedelta(10), cost=500, organization_id=org.id)
    d2 = models.Decision(description="Campaign B", decision_type="AD_CAMPAIGN", start_date=date.today()-timedelta(10), cost=500, organization_id=org.id)
    db.add_all([d1, d2])
    db.flush()
    
    # Outcome that matches both via time decay (1.0 - diff/window)
    o1 = models.Outcome(metric_name="REVENUE", value=1000, date=date.today(), organization_id=org.id)
    db.add(o1)
    db.commit()
    
    engine.run_full_attribution(db, org.id)
    
    # Both should get 50% split in their summary records
    a1 = db.query(models.Attribution).filter(
        models.Attribution.decision_id == d1.id,
        models.Attribution.outcome_id == None
    ).first()
    a2 = db.query(models.Attribution).filter(
        models.Attribution.decision_id == d2.id,
        models.Attribution.outcome_id == None
    ).first()
    
    assert a1.attributed_value == 500.0
    assert a2.attributed_value == 500.0
