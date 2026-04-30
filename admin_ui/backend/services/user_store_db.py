from typing import Any, Dict, List, Optional, Iterable
from datetime import datetime, timedelta
import secrets
import uuid
from sqlalchemy.orm import Session
from database import get_session
from models import Tenant, User, Invite, Session as DBSession, WorkspaceSetup, UsageTracking
from .security import hash_password

_DEFAULT_TENANT = "platform"
_DEFAULT_WORKSPACE = "platform-workspace"
_INVITE_TTL = timedelta(hours=24)

ROLE_PERMISSIONS = {
    "super_admin": ["super_admin", "manage_platform", "impersonate"],
    "admin": [
        "manage_workspace",
        "manage_users",
        "configure_providers",
        "view_billing",
        "manage_agents",
    ],
    "reseller_admin": ["manage_users", "manage_agents", "view_billing"],
    "end_user": ["consume_voice", "view_call_history", "view_assigned_agents"],
    "readonly_user": ["view_call_history", "view_assigned_agents"],
}


def _slugify(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    return "-".join(part for part in slug.split("-") if part) or "tenant"


def _workspace_id_for_tenant(tenant_id: str) -> str:
    return f"{tenant_id}-workspace"


def serialize_user(user: User) -> Dict[str, Any]:
    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "tenant_id": user.tenant_id,
        "workspace_id": user.workspace_id,
        "role": user.role,
        "status": user.status,
        "permissions": user.permissions or [],
        "assigned_agent_id": user.assigned_agent_id,
        "department": user.department,
        "phone_number": user.phone_number,
        "created_at": user.created_at.isoformat() + "Z" if user.created_at else None,
        "updated_at": user.updated_at.isoformat() + "Z" if user.updated_at else None,
        "last_login": user.last_login.isoformat() + "Z" if user.last_login else None,
        "must_change_password": user.must_change_password,
        "password_hash": user.password_hash,
        "parent_user_id": user.parent_user_id,
        "permission_group": user.permission_group,
        "permission_scope": user.permission_scope or {},
        "created_by": user.created_by,
    }

def serialize_tenant(tenant: Tenant) -> Dict[str, Any]:
    return {
        "id": tenant.id,
        "company_name": tenant.company_name,
        "slug": tenant.slug,
        "domain": tenant.domain,
        "status": tenant.status,
        "subscription_plan": tenant.subscription_plan,
        "created_at": tenant.created_at.isoformat() + "Z" if tenant.created_at else None,
        "max_users": tenant.max_users,
        "max_agents": tenant.max_agents,
        "max_calls_per_day": tenant.max_calls_per_day,
        "api_quota": tenant.api_quota,
        "branding_settings": tenant.branding_settings or {},
        "owner_username": tenant.owner_username,
        "reseller_enabled": tenant.reseller_enabled,
    }


def serialize_invite(invite: Invite) -> Dict[str, Any]:
    return {
        "token": invite.token,
        "tenant_id": invite.tenant_id,
        "workspace_id": invite.workspace_id,
        "email": invite.email,
        "role": invite.role,
        "inviter": invite.inviter,
        "status": invite.status,
        "expires_at": invite.expires_at.isoformat() + "Z" if invite.expires_at else None,
    }


def serialize_workspace_setup(setup: WorkspaceSetup) -> Dict[str, Any]:
    return {
        "tenant_id": setup.tenant_id,
        "workspace_id": setup.workspace_id,
        "setup_completed": setup.setup_completed,
        "asterisk_connected": setup.asterisk_connected,
        "sip_configured": setup.sip_configured,
        "api_connected": setup.api_connected,
        "provider_configured": setup.provider_configured,
        "asterisk_settings": setup.asterisk_settings or {},
        "updated_at": setup.updated_at.isoformat() + "Z" if setup.updated_at else None,
    }


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    db = get_session()
    try:
        user = db.query(User).filter(User.username == username).first()
        return serialize_user(user) if user else None
    finally:
        db.close()


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    db = get_session()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        return serialize_user(user) if user else None
    finally:
        db.close()


def list_users(tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
    db = get_session()
    try:
        query = db.query(User)
        if tenant_id:
            query = query.filter(User.tenant_id == tenant_id)
        users = query.all()
        return [serialize_user(user) for user in users]
    finally:
        db.close()


def list_tenants() -> List[Dict[str, Any]]:
    db = get_session()
    try:
        tenants = db.query(Tenant).all()
        return [serialize_tenant(tenant) for tenant in tenants]
    finally:
        db.close()


def get_tenant(tenant_id: str) -> Optional[Dict[str, Any]]:
    db = get_session()
    try:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        return serialize_tenant(tenant) if tenant else None
    finally:
        db.close()


def create_tenant(
    *,
    company_name: str,
    slug: Optional[str] = None,
    domain: Optional[str] = None,
    subscription_plan: str = "starter",
    owner_username: Optional[str] = None,
    max_users: Optional[int] = 5,
    max_agents: Optional[int] = 2,
    max_calls_per_day: Optional[int] = 100,
    api_quota: Optional[int] = 1000,
    branding_settings: Optional[Dict[str, Any]] = None,
    asterisk_settings: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    db = get_session()
    try:
        base_slug = _slugify(slug or company_name)
        tenant_id = base_slug
        suffix = 2
        while db.query(Tenant).filter(Tenant.slug == tenant_id).first():
            tenant_id = f"{base_slug}-{suffix}"
            suffix += 1

        tenant = Tenant(
            id=tenant_id,
            company_name=company_name,
            slug=base_slug,
            domain=domain,
            status="active",
            subscription_plan=subscription_plan,
            max_users=max_users,
            max_agents=max_agents,
            max_calls_per_day=max_calls_per_day,
            api_quota=api_quota,
            branding_settings=branding_settings or {},
            owner_username=owner_username,
            reseller_enabled=True,
        )
        db.add(tenant)

        workspace_setup = WorkspaceSetup(
            tenant_id=tenant_id,
            workspace_id=_workspace_id_for_tenant(tenant_id),
            setup_completed=False,
            asterisk_connected=False,
            sip_configured=False,
            api_connected=False,
            provider_configured=False,
            asterisk_settings=asterisk_settings or {},
        )
        db.add(workspace_setup)

        db.commit()
        return serialize_tenant(tenant)
    except:
        db.rollback()
        raise
    finally:
        db.close()


def create_user(
    username: str,
    email: str,
    password: str,
    role: str,
    tenant_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    assigned_agent_id: Optional[str] = None,
    department: Optional[str] = None,
    permissions: Optional[Iterable[str]] = None,
    must_change_password: bool = False,
    parent_user_id: Optional[str] = None,
    permission_group: str = "global",
    permission_scope: Optional[Dict[str, Any]] = None,
    created_by: Optional[str] = None,
) -> Dict[str, Any]:
    db = get_session()
    try:
        # Check if username exists
        if db.query(User).filter(User.username == username).first():
            raise ValueError("username already exists")

        user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            tenant_id=tenant_id or _DEFAULT_TENANT,
            workspace_id=workspace_id or _DEFAULT_WORKSPACE,
            role=role,
            status="active",
            permissions=list(permissions or ROLE_PERMISSIONS.get(role, [])),
            assigned_agent_id=assigned_agent_id,
            department=department,
            must_change_password=must_change_password,
            password_hash=hash_password(password),
            parent_user_id=parent_user_id,
            permission_group=permission_group,
            permission_scope=permission_scope or {},
            created_by=created_by,
        )
        db.add(user)
        db.commit()
        return serialize_user(user)
    except:
        db.rollback()
        raise
    finally:
        db.close()


def assign_tenant_owner(tenant_id: str, username: str) -> None:
    db = get_session()
    try:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if tenant:
            tenant.owner_username = username
            db.commit()
    except:
        db.rollback()
        raise
    finally:
        db.close()


def update_user(
    username: str,
    *,
    email: Optional[str] = None,
    role: Optional[str] = None,
    permissions: Optional[Iterable[str]] = None,
    assigned_agent_id: Optional[str] = None,
    department: Optional[str] = None,
    phone_number: Optional[str] = None,
    status: Optional[str] = None,
    parent_user_id: Optional[str] = None,
    permission_group: Optional[str] = None,
    permission_scope: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    db = get_session()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise KeyError("user not found")

        if email is not None:
            user.email = email
        if role is not None:
            user.role = role
            user.permissions = list(permissions or ROLE_PERMISSIONS.get(role, []))
        if permissions is not None:
            user.permissions = list(permissions)
        if assigned_agent_id is not None:
            user.assigned_agent_id = assigned_agent_id
        if department is not None:
            user.department = department
        if phone_number is not None:
            user.phone_number = phone_number
        if status is not None:
            user.status = status
        if parent_user_id is not None:
            user.parent_user_id = parent_user_id
        if permission_group is not None:
            user.permission_group = permission_group
        if permission_scope is not None:
            user.permission_scope = permission_scope

        user.updated_at = datetime.utcnow()
        db.commit()
        return serialize_user(user)
    except:
        db.rollback()
        raise
    finally:
        db.close()


def disable_user(username: str) -> Dict[str, Any]:
    db = get_session()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise KeyError("user not found")
        user.status = "disabled"
        user.updated_at = datetime.utcnow()
        db.commit()
        return serialize_user(user)
    except:
        db.rollback()
        raise
    finally:
        db.close()


def delete_user(username: str) -> None:
    db = get_session()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user:
            db.delete(user)
            db.commit()
    except:
        db.rollback()
        raise
    finally:
        db.close()


def reset_password(username: str, password: str, *, must_change_password: bool = True) -> Dict[str, Any]:
    db = get_session()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise KeyError("user not found")
        user.password_hash = hash_password(password)
        user.must_change_password = must_change_password
        user.updated_at = datetime.utcnow()
        db.commit()
        return serialize_user(user)
    except:
        db.rollback()
        raise
    finally:
        db.close()


def record_login(username: str) -> None:
    db = get_session()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user:
            user.last_login = datetime.utcnow()
            user.updated_at = datetime.utcnow()
            db.commit()
    except:
        db.rollback()
        raise
    finally:
        db.close()


def create_invite(
    tenant_id: str,
    email: str,
    role: str,
    inviter: str,
    workspace_id: Optional[str] = None,
) -> Dict[str, Any]:
    db = get_session()
    try:
        token = secrets.token_urlsafe(32)
        invite = Invite(
            token=token,
            tenant_id=tenant_id,
            workspace_id=workspace_id or _DEFAULT_WORKSPACE,
            email=email,
            role=role,
            inviter=inviter,
            status="pending",
            expires_at=datetime.utcnow() + _INVITE_TTL,
        )
        db.add(invite)
        db.commit()
        return serialize_invite(invite)
    except:
        db.rollback()
        raise
    finally:
        db.close()


def list_invites() -> List[Dict[str, Any]]:
    db = get_session()
    try:
        invites = db.query(Invite).all()
        return [serialize_invite(invite) for invite in invites]
    finally:
        db.close()


def update_workspace_setup(tenant_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    db = get_session()
    try:
        setup = db.query(WorkspaceSetup).filter(WorkspaceSetup.tenant_id == tenant_id).first()
        if not setup:
            setup = WorkspaceSetup(tenant_id=tenant_id, workspace_id=_workspace_id_for_tenant(tenant_id))
            db.add(setup)

        for key, value in updates.items():
            if hasattr(setup, key):
                setattr(setup, key, value)

        setup.updated_at = datetime.utcnow()
        db.commit()
        return serialize_workspace_setup(setup)
    except:
        db.rollback()
        raise
    finally:
        db.close()


def get_workspace_setup(tenant_id: str) -> Dict[str, Any]:
    db = get_session()
    try:
        setup = db.query(WorkspaceSetup).filter(WorkspaceSetup.tenant_id == tenant_id).first()
        if setup:
            return serialize_workspace_setup(setup)
        return {
            "tenant_id": tenant_id,
            "workspace_id": _workspace_id_for_tenant(tenant_id),
            "setup_completed": False,
            "asterisk_connected": False,
            "sip_configured": False,
            "api_connected": False,
            "provider_configured": False,
            "asterisk_settings": {},
            "updated_at": None,
        }
    finally:
        db.close()
