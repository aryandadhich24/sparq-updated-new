import sys
import os
from datetime import date

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app import models
from app.engine import engine as attribution_engine

# Use in-memory SQLite for testing
TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def test_attribution_logic():
    print("Setting up test database...")
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()

    # Seed Decision
    d1 = models.Decision(
        description="Test Campaign",
        decision_type="AD_CAMPAIGN",
        start_date=date(2026, 1, 1),
        cost=1000.0,
        status="ACTIVE"
    )
    session.add(d1)
    session.commit()
    
    # Seed Outcome
    o1 = models.Outcome(
        metric_name="REVENUE",
        value=5000.0,
        date=date(2026, 1, 10),
        description="Test Deal",
        source="MANUAL"
    )
    session.add(o1)
    session.commit()

    print("Running attribution engine...")
    attribution_engine.run_full_attribution(session)

    # Verify Results
    attributions = session.query(models.Attribution).all()
    print(f"Attribution records found: {len(attributions)}")
    
    # Expect 1 link + 1 summary = 2 records
    if len(attributions) != 2:
        print("FAILED: Expected 2 attribution records.")
        return

    summary = next(a for a in attributions if a.outcome_id is None)
    print(f"Summary ROI: {summary.roi_multiple} (Expected > 0)")
    
    link = next(a for a in attributions if a.outcome_id is not None)
    print(f"Link Weight: {link.weight}")

    if summary.roi_multiple > 0 and link.weight > 0:
        print("SUCCESS: Attribution calculated and saved.")
    else:
        print("FAILED: ROI or Weight is zero.")

    session.close()

if __name__ == "__main__":
    test_attribution_logic()
