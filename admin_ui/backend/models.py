from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON, Numeric, BigInteger, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String(255), primary_key=True)
    company_name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True)
    domain = Column(String(255))
    status = Column(String(50), default="active")
    subscription_plan = Column(String(100), default="starter")
    created_at = Column(DateTime, default=datetime.utcnow)
    max_users = Column(Integer)
    max_agents = Column(Integer)
    max_calls_per_day = Column(Integer)
    api_quota = Column(BigInteger)
    branding_settings = Column(JSON)
    owner_username = Column(String(255))
    reseller_enabled = Column(Boolean, default=True)

class User(Base):
    __tablename__ = "users"

    id = Column(String(255), primary_key=True)
    username = Column(String(255), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    tenant_id = Column(String(255), ForeignKey("tenants.id"), nullable=False)
    workspace_id = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    status = Column(String(50), default="active")
    permissions = Column(JSON)
    assigned_agent_id = Column(String(255))
    department = Column(String(255))
    phone_number = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    must_change_password = Column(Boolean, default=False)
    password_hash = Column(String(255))
    parent_user_id = Column(String(255), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    permission_group = Column(String(255), default="global", nullable=False)
    permission_scope = Column(JSON, default={}, nullable=False)
    created_by = Column(String(255), nullable=True)
    
    # Self-referential relationship for hierarchy
    parent = relationship("User", remote_side=[id], backref="children")

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String(255), primary_key=True)
    tenant_id = Column(String(255), ForeignKey("tenants.id"), nullable=False)
    plan_id = Column(String(255), nullable=False)
    payment_status = Column(String(50))
    renewal_date = Column(DateTime)
    billing_cycle = Column(String(50))
    usage_limit = Column(JSON)

class Plan(Base):
    __tablename__ = "plans"

    id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    price = Column(Numeric(10, 2))
    max_users = Column(Integer)
    max_agents = Column(Integer)
    max_minutes = Column(BigInteger)
    storage_limit = Column(BigInteger)
    features = Column(JSON)

class UsageTracking(Base):
    __tablename__ = "usage_tracking"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(String(255), ForeignKey("tenants.id"), nullable=False)
    api_calls = Column(BigInteger, default=0)
    call_minutes = Column(BigInteger, default=0)
    active_agents = Column(Integer, default=0)
    storage_usage = Column(BigInteger, default=0)
    current_cycle = Column(String(50))
    updated_at = Column(DateTime, default=datetime.utcnow)

class WorkspaceSetup(Base):
    __tablename__ = "workspace_setup"

    tenant_id = Column(String(255), primary_key=True)
    workspace_id = Column(String(255), nullable=False)
    setup_completed = Column(Boolean, default=False)
    asterisk_connected = Column(Boolean, default=False)
    sip_configured = Column(Boolean, default=False)
    api_connected = Column(Boolean, default=False)
    provider_configured = Column(Boolean, default=False)
    asterisk_settings = Column(JSON)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Invite(Base):
    __tablename__ = "invites"

    token = Column(String(255), primary_key=True)
    tenant_id = Column(String(255), ForeignKey("tenants.id"), nullable=False)
    workspace_id = Column(String(255))
    email = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    inviter = Column(String(255), nullable=False)
    status = Column(String(50), default="pending")
    expires_at = Column(DateTime, nullable=False)

class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(255), primary_key=True)
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False)
    tenant_id = Column(String(255), ForeignKey("tenants.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

class PricingPlan(Base):
    __tablename__ = "pricing_plans"

    id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    created_by = Column(String(255), nullable=False)
    inr_per_min = Column(Numeric(10, 4), default=0)
    inr_per_1k_tokens = Column(Numeric(10, 4), default=0)
    inr_per_api_call = Column(Numeric(10, 4), default=0)
    inr_per_session = Column(Numeric(10, 4), default=0)
    flat_monthly_inr = Column(Numeric(10, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class UserPricing(Base):
    __tablename__ = "user_pricing"

    id = Column(String(255), primary_key=True)
    username = Column(String(255), nullable=False, unique=True)
    plan_id = Column(String(255), ForeignKey("pricing_plans.id"), nullable=True)
    credit_limit_inr = Column(Numeric(12, 2), default=0)
    alert_threshold_pct = Column(Integer, default=80)
    custom_inr_per_min = Column(Numeric(10, 4), nullable=True)
    custom_inr_per_1k_tokens = Column(Numeric(10, 4), nullable=True)
    custom_inr_per_api_call = Column(Numeric(10, 4), nullable=True)
    custom_inr_per_session = Column(Numeric(10, 4), nullable=True)
    billing_cycle = Column(String(50), default="monthly")
    assigned_by = Column(String(255), nullable=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)

class UsageEvent(Base):
    __tablename__ = "usage_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=False)
    event_type = Column(String(50), nullable=False)
    quantity = Column(Numeric(12, 2), nullable=False)
    cost_inr = Column(Numeric(12, 4), default=0)
    event_metadata = Column(JSON, nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow)

class BillingSummary(Base):
    __tablename__ = "billing_summaries"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=False)
    billing_month = Column(String(7), nullable=False)  # YYYY-MM format
    total_minutes = Column(Numeric(12, 2), default=0)
    total_tokens = Column(BigInteger, default=0)
    total_api_calls = Column(BigInteger, default=0)
    total_sessions = Column(BigInteger, default=0)
    total_cost_inr = Column(Numeric(12, 4), default=0)
    flat_fee_inr = Column(Numeric(10, 2), default=0)
    grand_total_inr = Column(Numeric(12, 4), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('username', 'billing_month', name='uq_username_billing_month'),
    )