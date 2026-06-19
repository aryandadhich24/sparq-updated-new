from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import ValidationError

from ..database import get_db
from ..models import User, Decision, Outcome
from ..schemas import DecisionCreate, OutcomeCreate, Decision as DecisionSchema, Outcome as OutcomeSchema
from ..middleware.auth import get_current_user
from ..engine import engine as attribution_engine

router = APIRouter()

@router.post("/decisions/bulk", response_model=dict)
def bulk_create_decisions(
    decisions_in: List[DecisionCreate],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    created_count = 0
    errors = []
    
    new_decisions = []
    for i, d_in in enumerate(decisions_in):
        try:
            decision = Decision(
                **d_in.model_dump(),
                organization_id=current_user.organization_id
            )
            new_decisions.append(decision)
        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")
            
    if new_decisions:
        db.add_all(new_decisions)
        db.commit()
        # Trigger attribution
        background_tasks.add_task(attribution_engine.run_full_attribution, db, organization_id=current_user.organization_id)
        created_count = len(new_decisions)
        
    return {
        "message": f"Successfully imported {created_count} decisions.",
        "errors": errors
    }

@router.post("/outcomes/bulk", response_model=dict)
def bulk_create_outcomes(
    outcomes_in: List[OutcomeCreate],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    created_count = 0
    errors = []
    
    new_outcomes = []
    for i, o_in in enumerate(outcomes_in):
        try:
             # Check if decision_id exists and belongs to org if provided
            if o_in.decision_id:
                decision = db.query(Decision).filter(
                    Decision.id == o_in.decision_id,
                    Decision.organization_id == current_user.organization_id
                ).first()
                if not decision:
                     errors.append(f"Row {i}: Linked Decision ID {o_in.decision_id} not found.")
                     continue

            outcome = Outcome(
                **o_in.model_dump(),
                organization_id=current_user.organization_id,
                source="CSV"
            )
            new_outcomes.append(outcome)
        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")

    if new_outcomes:
        db.add_all(new_outcomes)
        db.commit()
        background_tasks.add_task(attribution_engine.run_full_attribution, db, organization_id=current_user.organization_id)
        created_count = len(new_outcomes)
        
    return {
        "message": f"Successfully imported {created_count} outcomes.",
        "errors": errors
    }
