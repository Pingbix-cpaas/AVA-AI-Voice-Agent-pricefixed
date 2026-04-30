from typing import Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

import auth
from database import get_db
from sqlalchemy.orm import Session
from services import billing_service

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class CreatePricingPlanRequest(BaseModel):
    name: str
    inr_per_min: float = 0
    inr_per_1k_tokens: float = 0
    inr_per_api_call: float = 0
    inr_per_session: float = 0
    flat_monthly_inr: float = 0


class UpdatePricingPlanRequest(BaseModel):
    inr_per_min: Optional[float] = None
    inr_per_1k_tokens: Optional[float] = None
    inr_per_api_call: Optional[float] = None
    inr_per_session: Optional[float] = None
    flat_monthly_inr: Optional[float] = None


class AssignUserPricingRequest(BaseModel):
    username: str
    plan_id: Optional[str] = None
    credit_limit_inr: float = 0
    alert_threshold_pct: int = 80
    custom_inr_per_min: Optional[float] = None
    custom_inr_per_1k_tokens: Optional[float] = None
    custom_inr_per_api_call: Optional[float] = None
    custom_inr_per_session: Optional[float] = None
    billing_cycle: str = "monthly"


class UpdateUserPricingRequest(BaseModel):
    credit_limit_inr: Optional[float] = None
    alert_threshold_pct: Optional[int] = None
    custom_inr_per_min: Optional[float] = None
    custom_inr_per_1k_tokens: Optional[float] = None
    custom_inr_per_api_call: Optional[float] = None
    custom_inr_per_session: Optional[float] = None
    billing_cycle: Optional[str] = None


class RecordUsageRequest(BaseModel):
    username: str
    event_type: str = Field(..., pattern="^(minutes|tokens|api_call|session)$")
    quantity: float
    event_metadata: Optional[Dict] = None


class GetUsageHistoryRequest(BaseModel):
    username: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


# ============================================================================
# Authorization Helpers
# ============================================================================

def require_super_admin(user=Depends(auth.get_current_user)):
    if user.role != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin access required")
    return user


def require_admin(user=Depends(auth.get_current_user)):
    if user.role not in ("super_admin", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def require_admin_or_self(username: str, user=Depends(auth.get_current_user)):
    if user.role not in ("super_admin", "admin") and user.username != username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return user


# ============================================================================
# Pricing Plans Endpoints
# ============================================================================

@router.post("/plans", status_code=status.HTTP_201_CREATED)
def create_pricing_plan(
    payload: CreatePricingPlanRequest,
    current_user=Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Create a new pricing plan (super_admin only)."""
    try:
        rates = {
            "inr_per_min": payload.inr_per_min,
            "inr_per_1k_tokens": payload.inr_per_1k_tokens,
            "inr_per_api_call": payload.inr_per_api_call,
            "inr_per_session": payload.inr_per_session,
            "flat_monthly_inr": payload.flat_monthly_inr,
        }
        plan = billing_service.create_plan(db, payload.name, current_user.username, rates)
        return {"status": "created", "plan": plan}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/plans")
def list_pricing_plans(
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all pricing plans (admin+)."""
    try:
        plans = billing_service.list_plans(db)
        return {"plans": plans}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/plans/{plan_id}")
def get_pricing_plan(
    plan_id: str,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get a specific pricing plan (admin+)."""
    try:
        plan = billing_service.get_plan(db, plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        return {"plan": plan}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/plans/{plan_id}")
def update_pricing_plan(
    plan_id: str,
    payload: UpdatePricingPlanRequest,
    current_user=Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Update a pricing plan (super_admin only)."""
    try:
        rates = {}
        if payload.inr_per_min is not None:
            rates["inr_per_min"] = payload.inr_per_min
        if payload.inr_per_1k_tokens is not None:
            rates["inr_per_1k_tokens"] = payload.inr_per_1k_tokens
        if payload.inr_per_api_call is not None:
            rates["inr_per_api_call"] = payload.inr_per_api_call
        if payload.inr_per_session is not None:
            rates["inr_per_session"] = payload.inr_per_session
        if payload.flat_monthly_inr is not None:
            rates["flat_monthly_inr"] = payload.flat_monthly_inr
        
        plan = billing_service.update_plan(db, plan_id, rates)
        return {"status": "updated", "plan": plan}
    except ValueError:
        raise HTTPException(status_code=404, detail="Plan not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pricing_plan(
    plan_id: str,
    current_user=Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Delete a pricing plan (super_admin only)."""
    try:
        success = billing_service.delete_plan(db, plan_id)
        if not success:
            raise HTTPException(status_code=404, detail="Plan not found")
        return None
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# User Pricing Endpoints
# ============================================================================

@router.post("/assign", status_code=status.HTTP_201_CREATED)
def assign_user_pricing(
    payload: AssignUserPricingRequest,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Assign a pricing plan to a user (admin+)."""
    try:
        overrides = {
            "credit_limit_inr": payload.credit_limit_inr,
            "alert_threshold_pct": payload.alert_threshold_pct,
            "billing_cycle": payload.billing_cycle,
        }
        if payload.custom_inr_per_min is not None:
            overrides["custom_inr_per_min"] = payload.custom_inr_per_min
        if payload.custom_inr_per_1k_tokens is not None:
            overrides["custom_inr_per_1k_tokens"] = payload.custom_inr_per_1k_tokens
        if payload.custom_inr_per_api_call is not None:
            overrides["custom_inr_per_api_call"] = payload.custom_inr_per_api_call
        if payload.custom_inr_per_session is not None:
            overrides["custom_inr_per_session"] = payload.custom_inr_per_session
        
        user_pricing = billing_service.assign_pricing(
            db,
            payload.username,
            payload.plan_id,
            overrides,
            current_user.username,
        )
        return {"status": "assigned", "user_pricing": user_pricing}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/user/{username}")
def get_user_pricing(
    username: str,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Get user pricing (admin+ or self)."""
    require_admin_or_self(username, current_user)
    try:
        user_pricing = billing_service.get_user_pricing(db, username)
        if not user_pricing:
            raise HTTPException(status_code=404, detail="User pricing not found")
        return {"user_pricing": user_pricing}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/user/{username}")
def update_user_pricing(
    username: str,
    payload: UpdateUserPricingRequest,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update user pricing (admin+)."""
    try:
        updates = {}
        if payload.credit_limit_inr is not None:
            updates["credit_limit_inr"] = payload.credit_limit_inr
        if payload.alert_threshold_pct is not None:
            updates["alert_threshold_pct"] = payload.alert_threshold_pct
        if payload.custom_inr_per_min is not None:
            updates["custom_inr_per_min"] = payload.custom_inr_per_min
        if payload.custom_inr_per_1k_tokens is not None:
            updates["custom_inr_per_1k_tokens"] = payload.custom_inr_per_1k_tokens
        if payload.custom_inr_per_api_call is not None:
            updates["custom_inr_per_api_call"] = payload.custom_inr_per_api_call
        if payload.custom_inr_per_session is not None:
            updates["custom_inr_per_session"] = payload.custom_inr_per_session
        if payload.billing_cycle is not None:
            updates["billing_cycle"] = payload.billing_cycle
        
        user_pricing = billing_service.update_user_pricing(db, username, updates)
        return {"status": "updated", "user_pricing": user_pricing}
    except ValueError:
        raise HTTPException(status_code=404, detail="User pricing not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Usage Recording Endpoints
# ============================================================================

@router.post("/usage/record", status_code=status.HTTP_201_CREATED)
def record_usage(
    payload: RecordUsageRequest,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Record a usage event (any authenticated user)."""
    try:
        event = billing_service.record_usage_event(
            db,
            payload.username,
            payload.event_type,
            payload.quantity,
            payload.event_metadata,
        )
        return {"status": "recorded", "event": event}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/usage/{username}")
def get_usage_history(
    username: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Get usage history for a user (admin+ or self)."""
    require_admin_or_self(username, current_user)
    try:
        events = billing_service.get_usage_history(db, username, start_date, end_date)
        return {"events": events}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Billing Summary Endpoints
# ============================================================================

@router.get("/summary/{username}")
def get_monthly_summary(
    username: str,
    billing_month: str,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Get monthly billing summary (admin+ or self)."""
    require_admin_or_self(username, current_user)
    try:
        summary = billing_service.get_monthly_summary(db, username, billing_month)
        if not summary:
            raise HTTPException(status_code=404, detail="Summary not found")
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/dashboard")
def get_dashboard_data(
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get dashboard data for all users (admin+)."""
    try:
        data = billing_service.get_dashboard_data(db, current_user.tenant_id)
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Admin Operations Endpoints
# ============================================================================

@router.post("/reset/{username}", status_code=status.HTTP_200_OK)
def reset_usage(
    username: str,
    billing_month: str,
    current_user=Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Reset usage for a user (super_admin only)."""
    try:
        success = billing_service.reset_user_usage(db, username, billing_month)
        if not success:
            raise HTTPException(status_code=404, detail="Summary not found")
        return {"status": "reset"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
