from typing import Any, Dict, List, Optional
from datetime import datetime
import logging
import uuid
from decimal import Decimal
from sqlalchemy.orm import Session
from database import get_session
from models import PricingPlan, UserPricing, UsageEvent, BillingSummary

logger = logging.getLogger(__name__)


def serialize_pricing_plan(plan: PricingPlan) -> Dict[str, Any]:
    return {
        "id": plan.id,
        "name": plan.name,
        "created_by": plan.created_by,
        "inr_per_min": float(plan.inr_per_min or 0),
        "inr_per_1k_tokens": float(plan.inr_per_1k_tokens or 0),
        "inr_per_api_call": float(plan.inr_per_api_call or 0),
        "inr_per_session": float(plan.inr_per_session or 0),
        "flat_monthly_inr": float(plan.flat_monthly_inr or 0),
        "created_at": plan.created_at.isoformat() + "Z" if plan.created_at else None,
        "updated_at": plan.updated_at.isoformat() + "Z" if plan.updated_at else None,
    }


def serialize_user_pricing(up: UserPricing) -> Dict[str, Any]:
    return {
        "id": up.id,
        "username": up.username,
        "plan_id": up.plan_id,
        "credit_limit_inr": float(up.credit_limit_inr or 0),
        "alert_threshold_pct": up.alert_threshold_pct,
        "custom_inr_per_min": float(up.custom_inr_per_min) if up.custom_inr_per_min else None,
        "custom_inr_per_1k_tokens": float(up.custom_inr_per_1k_tokens) if up.custom_inr_per_1k_tokens else None,
        "custom_inr_per_api_call": float(up.custom_inr_per_api_call) if up.custom_inr_per_api_call else None,
        "custom_inr_per_session": float(up.custom_inr_per_session) if up.custom_inr_per_session else None,
        "billing_cycle": up.billing_cycle,
        "assigned_by": up.assigned_by,
        "assigned_at": up.assigned_at.isoformat() + "Z" if up.assigned_at else None,
    }


def serialize_usage_event(event: UsageEvent) -> Dict[str, Any]:
    return {
        "id": event.id,
        "username": event.username,
        "event_type": event.event_type,
        "quantity": float(event.quantity or 0),
        "cost_inr": float(event.cost_inr or 0),
        "event_metadata": event.event_metadata or {},
        "recorded_at": event.recorded_at.isoformat() + "Z" if event.recorded_at else None,
    }


def serialize_billing_summary(summary: BillingSummary) -> Dict[str, Any]:
    return {
        "id": summary.id,
        "username": summary.username,
        "billing_month": summary.billing_month,
        "total_minutes": float(summary.total_minutes or 0),
        "total_tokens": int(summary.total_tokens or 0),
        "total_api_calls": int(summary.total_api_calls or 0),
        "total_sessions": int(summary.total_sessions or 0),
        "total_cost_inr": float(summary.total_cost_inr or 0),
        "flat_fee_inr": float(summary.flat_fee_inr or 0),
        "grand_total_inr": float(summary.grand_total_inr or 0),
        "created_at": summary.created_at.isoformat() + "Z" if summary.created_at else None,
        "updated_at": summary.updated_at.isoformat() + "Z" if summary.updated_at else None,
    }


# ============================================================================
# Pricing Plans
# ============================================================================

def create_plan(
    db: Session,
    name: str,
    created_by: str,
    rates: Dict[str, float],
) -> Dict[str, Any]:
    """Create a new pricing plan."""
    try:
        plan = PricingPlan(
            id=str(uuid.uuid4()),
            name=name,
            created_by=created_by,
            inr_per_min=Decimal(str(rates.get("inr_per_min", 0))),
            inr_per_1k_tokens=Decimal(str(rates.get("inr_per_1k_tokens", 0))),
            inr_per_api_call=Decimal(str(rates.get("inr_per_api_call", 0))),
            inr_per_session=Decimal(str(rates.get("inr_per_session", 0))),
            flat_monthly_inr=Decimal(str(rates.get("flat_monthly_inr", 0))),
        )
        db.add(plan)
        db.commit()
        return serialize_pricing_plan(plan)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating pricing plan: {e}")
        raise


def list_plans(db: Session) -> List[Dict[str, Any]]:
    """List all pricing plans."""
    try:
        plans = db.query(PricingPlan).all()
        return [serialize_pricing_plan(p) for p in plans]
    except Exception as e:
        logger.error(f"Error listing pricing plans: {e}")
        raise


def get_plan(db: Session, plan_id: str) -> Optional[Dict[str, Any]]:
    """Get a pricing plan by ID."""
    try:
        plan = db.query(PricingPlan).filter(PricingPlan.id == plan_id).first()
        return serialize_pricing_plan(plan) if plan else None
    except Exception as e:
        logger.error(f"Error getting pricing plan: {e}")
        raise


def update_plan(
    db: Session,
    plan_id: str,
    rates: Dict[str, float],
) -> Dict[str, Any]:
    """Update a pricing plan's rates."""
    try:
        plan = db.query(PricingPlan).filter(PricingPlan.id == plan_id).first()
        if not plan:
            raise ValueError("Plan not found")
        
        if "inr_per_min" in rates:
            plan.inr_per_min = Decimal(str(rates["inr_per_min"]))
        if "inr_per_1k_tokens" in rates:
            plan.inr_per_1k_tokens = Decimal(str(rates["inr_per_1k_tokens"]))
        if "inr_per_api_call" in rates:
            plan.inr_per_api_call = Decimal(str(rates["inr_per_api_call"]))
        if "inr_per_session" in rates:
            plan.inr_per_session = Decimal(str(rates["inr_per_session"]))
        if "flat_monthly_inr" in rates:
            plan.flat_monthly_inr = Decimal(str(rates["flat_monthly_inr"]))
        
        plan.updated_at = datetime.utcnow()
        db.commit()
        return serialize_pricing_plan(plan)
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating pricing plan: {e}")
        raise


def delete_plan(db: Session, plan_id: str) -> bool:
    """Delete a pricing plan."""
    try:
        plan = db.query(PricingPlan).filter(PricingPlan.id == plan_id).first()
        if plan:
            db.delete(plan)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting pricing plan: {e}")
        raise


# ============================================================================
# User Pricing
# ============================================================================

def assign_pricing(
    db: Session,
    username: str,
    plan_id: Optional[str],
    overrides: Dict[str, float],
    assigned_by: str,
) -> Dict[str, Any]:
    """Assign a pricing plan to a user with optional overrides."""
    try:
        # Check if user pricing already exists
        existing = db.query(UserPricing).filter(UserPricing.username == username).first()
        
        if existing:
            existing.plan_id = plan_id
            existing.custom_inr_per_min = Decimal(str(overrides.get("custom_inr_per_min"))) if "custom_inr_per_min" in overrides else None
            existing.custom_inr_per_1k_tokens = Decimal(str(overrides.get("custom_inr_per_1k_tokens"))) if "custom_inr_per_1k_tokens" in overrides else None
            existing.custom_inr_per_api_call = Decimal(str(overrides.get("custom_inr_per_api_call"))) if "custom_inr_per_api_call" in overrides else None
            existing.custom_inr_per_session = Decimal(str(overrides.get("custom_inr_per_session"))) if "custom_inr_per_session" in overrides else None
            existing.assigned_by = assigned_by
            existing.assigned_at = datetime.utcnow()
            db.commit()
            return serialize_user_pricing(existing)
        
        user_pricing = UserPricing(
            id=str(uuid.uuid4()),
            username=username,
            plan_id=plan_id,
            credit_limit_inr=Decimal(str(overrides.get("credit_limit_inr", 0))),
            alert_threshold_pct=overrides.get("alert_threshold_pct", 80),
            custom_inr_per_min=Decimal(str(overrides.get("custom_inr_per_min"))) if "custom_inr_per_min" in overrides else None,
            custom_inr_per_1k_tokens=Decimal(str(overrides.get("custom_inr_per_1k_tokens"))) if "custom_inr_per_1k_tokens" in overrides else None,
            custom_inr_per_api_call=Decimal(str(overrides.get("custom_inr_per_api_call"))) if "custom_inr_per_api_call" in overrides else None,
            custom_inr_per_session=Decimal(str(overrides.get("custom_inr_per_session"))) if "custom_inr_per_session" in overrides else None,
            billing_cycle=overrides.get("billing_cycle", "monthly"),
            assigned_by=assigned_by,
        )
        db.add(user_pricing)
        db.commit()
        return serialize_user_pricing(user_pricing)
    except Exception as e:
        db.rollback()
        logger.error(f"Error assigning pricing: {e}")
        raise


def get_user_pricing(db: Session, username: str) -> Optional[Dict[str, Any]]:
    """Get pricing configuration for a user."""
    try:
        up = db.query(UserPricing).filter(UserPricing.username == username).first()
        return serialize_user_pricing(up) if up else None
    except Exception as e:
        logger.error(f"Error getting user pricing: {e}")
        raise


def update_user_pricing(
    db: Session,
    username: str,
    updates: Dict[str, Any],
) -> Dict[str, Any]:
    """Update user pricing configuration."""
    try:
        up = db.query(UserPricing).filter(UserPricing.username == username).first()
        if not up:
            raise ValueError("User pricing not found")
        
        if "credit_limit_inr" in updates:
            up.credit_limit_inr = Decimal(str(updates["credit_limit_inr"]))
        if "alert_threshold_pct" in updates:
            up.alert_threshold_pct = updates["alert_threshold_pct"]
        if "billing_cycle" in updates:
            up.billing_cycle = updates["billing_cycle"]
        if "custom_inr_per_min" in updates:
            up.custom_inr_per_min = Decimal(str(updates["custom_inr_per_min"])) if updates["custom_inr_per_min"] is not None else None
        if "custom_inr_per_1k_tokens" in updates:
            up.custom_inr_per_1k_tokens = Decimal(str(updates["custom_inr_per_1k_tokens"])) if updates["custom_inr_per_1k_tokens"] is not None else None
        if "custom_inr_per_api_call" in updates:
            up.custom_inr_per_api_call = Decimal(str(updates["custom_inr_per_api_call"])) if updates["custom_inr_per_api_call"] is not None else None
        if "custom_inr_per_session" in updates:
            up.custom_inr_per_session = Decimal(str(updates["custom_inr_per_session"])) if updates["custom_inr_per_session"] is not None else None
        
        db.commit()
        return serialize_user_pricing(up)
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating user pricing: {e}")
        raise


# ============================================================================
# Usage Recording
# ============================================================================

def record_usage_event(
    db: Session,
    username: str,
    event_type: str,
    quantity: float,
    event_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Record a usage event and calculate cost based on user's pricing.
    Also updates or creates monthly billing summary.
    """
    try:
        # Get user pricing
        user_pricing = db.query(UserPricing).filter(UserPricing.username == username).first()
        
        # Determine effective rate
        effective_rate = Decimal("0")
        if event_type == "minutes":
            effective_rate = user_pricing.custom_inr_per_min if user_pricing and user_pricing.custom_inr_per_min else (
                Decimal(str(user_pricing.plan.inr_per_min or 0)) if user_pricing and user_pricing.plan_id else Decimal("0")
            )
        elif event_type == "tokens":
            effective_rate = user_pricing.custom_inr_per_1k_tokens if user_pricing and user_pricing.custom_inr_per_1k_tokens else (
                Decimal(str(user_pricing.plan.inr_per_1k_tokens or 0)) if user_pricing and user_pricing.plan_id else Decimal("0")
            )
        elif event_type == "api_call":
            effective_rate = user_pricing.custom_inr_per_api_call if user_pricing and user_pricing.custom_inr_per_api_call else (
                Decimal(str(user_pricing.plan.inr_per_api_call or 0)) if user_pricing and user_pricing.plan_id else Decimal("0")
            )
        elif event_type == "session":
            effective_rate = user_pricing.custom_inr_per_session if user_pricing and user_pricing.custom_inr_per_session else (
                Decimal(str(user_pricing.plan.inr_per_session or 0)) if user_pricing and user_pricing.plan_id else Decimal("0")
            )
        
        # Calculate cost
        cost_inr = Decimal(str(quantity)) * effective_rate
        
        # Record event
        event = UsageEvent(
            username=username,
            event_type=event_type,
            quantity=Decimal(str(quantity)),
            cost_inr=cost_inr,
            event_metadata=event_metadata or {},
        )
        db.add(event)
        
        # Update or create billing summary for current month
        current_month = datetime.utcnow().strftime("%Y-%m")
        summary = db.query(BillingSummary).filter(
            BillingSummary.username == username,
            BillingSummary.billing_month == current_month,
        ).first()
        
        if not summary:
            summary = BillingSummary(
                username=username,
                billing_month=current_month,
            )
            db.add(summary)
        
        # Update totals based on event type
        if event_type == "minutes":
            summary.total_minutes = (summary.total_minutes or 0) + Decimal(str(quantity))
        elif event_type == "tokens":
            summary.total_tokens = (summary.total_tokens or 0) + int(quantity)
        elif event_type == "api_call":
            summary.total_api_calls = (summary.total_api_calls or 0) + int(quantity)
        elif event_type == "session":
            summary.total_sessions = (summary.total_sessions or 0) + int(quantity)
        
        summary.total_cost_inr = (summary.total_cost_inr or 0) + cost_inr
        
        # Add flat fee if applicable (monthly)
        if user_pricing and user_pricing.plan_id and not summary.flat_fee_inr:
            flat_fee = user_pricing.plan.flat_monthly_inr if user_pricing.plan else None
            summary.flat_fee_inr = Decimal(str(flat_fee or 0))
        
        summary.grand_total_inr = (summary.total_cost_inr or 0) + (summary.flat_fee_inr or 0)
        summary.updated_at = datetime.utcnow()
        
        # Check alerts
        if user_pricing and user_pricing.credit_limit_inr and user_pricing.credit_limit_inr > 0:
            if summary.grand_total_inr >= user_pricing.credit_limit_inr:
                logger.warning(f"User {username} has exceeded credit limit: ₹{summary.grand_total_inr} >= ₹{user_pricing.credit_limit_inr}")
            elif summary.grand_total_inr >= (user_pricing.credit_limit_inr * user_pricing.alert_threshold_pct / 100):
                logger.warning(f"User {username} has reached {user_pricing.alert_threshold_pct}% of credit limit: ₹{summary.grand_total_inr} / ₹{user_pricing.credit_limit_inr}")
        
        db.commit()
        return serialize_usage_event(event)
    except Exception as e:
        db.rollback()
        logger.error(f"Error recording usage event: {e}")
        raise


def get_usage_history(
    db: Session,
    username: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Get usage events for a user within a date range."""
    try:
        query = db.query(UsageEvent).filter(UsageEvent.username == username)
        
        if start_date:
            query = query.filter(UsageEvent.recorded_at >= start_date)
        if end_date:
            query = query.filter(UsageEvent.recorded_at <= end_date)
        
        events = query.order_by(UsageEvent.recorded_at.desc()).all()
        return [serialize_usage_event(e) for e in events]
    except Exception as e:
        logger.error(f"Error getting usage history: {e}")
        raise


def get_monthly_summary(
    db: Session,
    username: str,
    billing_month: str,
) -> Optional[Dict[str, Any]]:
    """Get monthly billing summary for a user."""
    try:
        summary = db.query(BillingSummary).filter(
            BillingSummary.username == username,
            BillingSummary.billing_month == billing_month,
        ).first()
        return serialize_billing_summary(summary) if summary else None
    except Exception as e:
        logger.error(f"Error getting monthly summary: {e}")
        raise


def get_dashboard_data(db: Session, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get dashboard data for all users (admin only)."""
    try:
        current_month = datetime.utcnow().strftime("%Y-%m")
        summaries = db.query(BillingSummary).filter(
            BillingSummary.billing_month == current_month,
        ).all()
        
        result = []
        for summary in summaries:
            user_pricing = db.query(UserPricing).filter(
                UserPricing.username == summary.username,
            ).first()
            
            result.append({
                "username": summary.username,
                "minutes": float(summary.total_minutes or 0),
                "tokens": int(summary.total_tokens or 0),
                "api_calls": int(summary.total_api_calls or 0),
                "sessions": int(summary.total_sessions or 0),
                "cost_inr": float(summary.total_cost_inr or 0),
                "limit_inr": float(user_pricing.credit_limit_inr or 0) if user_pricing else 0,
                "percent_used": (float(summary.grand_total_inr or 0) / float(user_pricing.credit_limit_inr) * 100) if (user_pricing and user_pricing.credit_limit_inr and user_pricing.credit_limit_inr > 0) else 0,
                "status": "ok" if not user_pricing or not user_pricing.credit_limit_inr or summary.grand_total_inr < user_pricing.credit_limit_inr else "exceeded",
            })
        
        return result
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        raise


def reset_user_usage(
    db: Session,
    username: str,
    billing_month: str,
) -> bool:
    """Reset usage for a user for a specific month."""
    try:
        summary = db.query(BillingSummary).filter(
            BillingSummary.username == username,
            BillingSummary.billing_month == billing_month,
        ).first()
        
        if summary:
            summary.total_minutes = 0
            summary.total_tokens = 0
            summary.total_api_calls = 0
            summary.total_sessions = 0
            summary.total_cost_inr = 0
            summary.grand_total_inr = 0
            summary.updated_at = datetime.utcnow()
            db.commit()
            return True
        
        return False
    except Exception as e:
        db.rollback()
        logger.error(f"Error resetting user usage: {e}")
        raise
