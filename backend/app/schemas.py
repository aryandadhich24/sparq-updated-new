from typing import Optional, List, Dict, Literal
from datetime import date, datetime
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


# ---------------------------------------------------------------------------
# Constrained literal types
# ---------------------------------------------------------------------------

DecisionTypeEnum = Literal["HIRE", "AD_CAMPAIGN", "TOOL", "VENDOR"]
DecisionStatusEnum = Literal["ACTIVE", "ENDED"]
MetricNameEnum = Literal["REVENUE", "PIPELINE_VALUE", "LEADS"]

# Allowed keys for organization settings
ALLOWED_SETTINGS_KEYS = {
    "default_currency", "fiscal_year_start", "attribution_model",
    "weekly_digest", "timezone", "date_format",
}


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    VIEWER = "VIEWER"

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=200)
    organization_name: str = Field(..., min_length=1, max_length=200)

class UserInvite(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.MEMBER

class User(UserBase):
    id: int
    is_active: bool
    full_name: Optional[str] = None
    role: str = "MEMBER"
    organization_id: Optional[int] = None

    class Config:
        from_attributes = True

# ---------------------------------------------------------------------------
# Decisions
# ---------------------------------------------------------------------------

class DecisionBase(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    decision_type: DecisionTypeEnum
    start_date: date
    end_date: Optional[date] = None
    cost: float = Field(..., ge=0, le=100_000_000)
    status: DecisionStatusEnum = "ACTIVE"
    source: str = Field(default="MANUAL", max_length=50)

class DecisionCreate(DecisionBase):
    pass

class DecisionUpdate(BaseModel):
    description: Optional[str] = Field(default=None, min_length=1, max_length=500)
    decision_type: Optional[DecisionTypeEnum] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    cost: Optional[float] = Field(default=None, ge=0, le=100_000_000)
    status: Optional[DecisionStatusEnum] = None
    source: Optional[str] = Field(default=None, max_length=50)

class DecisionInDBBase(DecisionBase):
    id: int
    organization_id: int
    roi: Optional[float] = 0.0
    value: Optional[float] = 0.0
    total_cost: Optional[float] = 0.0
    confidence: Optional[float] = 0.0
    action: Optional[str] = "WAITING"

    @property
    def type(self):
        return self.decision_type

    class Config:
        from_attributes = True

class Decision(DecisionInDBBase):
    pass

# ---------------------------------------------------------------------------
# Outcomes
# ---------------------------------------------------------------------------

class OutcomeBase(BaseModel):
    metric_name: MetricNameEnum
    value: float = Field(..., ge=0)
    date: date
    description: Optional[str] = Field(default=None, max_length=500)
    decision_id: Optional[int] = None

class OutcomeCreate(OutcomeBase):
    pass

class Outcome(OutcomeBase):
    id: int
    organization_id: int
    source: Optional[str] = "MANUAL"

    class Config:
        from_attributes = True

# ---------------------------------------------------------------------------
# Organization
# ---------------------------------------------------------------------------

class OrganizationSettings(BaseModel):
    """Typed settings dict -- only known keys are accepted."""
    default_currency: Optional[str] = Field(default=None, max_length=10)
    fiscal_year_start: Optional[int] = Field(default=None, ge=1, le=12)
    attribution_model: Optional[str] = Field(default=None, max_length=50)
    weekly_digest: Optional[bool] = None
    timezone: Optional[str] = Field(default=None, max_length=50)
    date_format: Optional[str] = Field(default=None, max_length=30)

class OrganizationUpdate(BaseModel):
    settings: Optional[OrganizationSettings] = None

class Organization(BaseModel):
    id: int
    name: str = Field(..., max_length=200)
    settings: Optional[dict] = {}

    class Config:
        from_attributes = True
