from typing import Iterable, List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

import auth
from database import get_db
from models import User
from services import rbac
from services.user_store_db import (
    assign_tenant_owner,
    create_invite,
    create_tenant,
    create_user,
    delete_user,
    disable_user,
    get_user_by_username,
    get_workspace_setup,
    list_tenants,
    list_users,
    reset_password,
    update_user,
    update_workspace_setup,
)

router = APIRouter()


class UserCreateRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = Field(..., pattern="^(super_admin|admin|reseller_admin|end_user|readonly_user)$")
    tenant_id: Optional[str] = None
    workspace_id: Optional[str] = None
    assigned_agent_id: Optional[str] = None
    department: Optional[str] = None
    permissions: Optional[List[str]] = None
    provision_separate_tenant: bool = False
    company_name: Optional[str] = None
    slug: Optional[str] = None
    domain: Optional[str] = None
    subscription_plan: str = "starter"
    max_users: Optional[int] = 5
    max_agents: Optional[int] = 2
    max_calls_per_day: Optional[int] = 100
    api_quota: Optional[int] = 1000
    asterisk_host: Optional[str] = None
    sip_trunk: Optional[str] = None
    did_number: Optional[str] = None
    sip_username: Optional[str] = None
    sip_transport: Optional[str] = "udp"
    parent_user_id: Optional[str] = None
    permission_group: str = "global"
    permission_scope: Optional[Dict[str, Any]] = None


class UserActionRequest(BaseModel):
    username: str


class UserUpdateRequest(UserActionRequest):
    email: Optional[EmailStr] = None
    role: Optional[str] = Field(None, pattern="^(super_admin|admin|reseller_admin|end_user|readonly_user)$")
    permissions: Optional[List[str]] = None
    assigned_agent_id: Optional[str] = None
    department: Optional[str] = None
    phone_number: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|disabled)$")
    parent_user_id: Optional[str] = None
    permission_group: Optional[str] = None
    permission_scope: Optional[Dict[str, Any]] = None


class ResetPasswordRequest(UserActionRequest):
    password: str

class InviteRequest(BaseModel):
    email: EmailStr
    role: str = Field(..., pattern="^(admin|reseller_admin|end_user|readonly_user)$")
    tenant_id: Optional[str] = None
    workspace_id: Optional[str] = None


def require_admin(user):
    if user.role not in ("super_admin", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def _assert_can_manage_role(current_user, target_role: str, provision_separate_tenant: bool = False) -> None:
    # Use RBAC service to check if user can create target role
    if not rbac.can_create_role(current_user, target_role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Cannot create users with role: {target_role}")
    if current_user.role != "super_admin" and provision_separate_tenant:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only super admins can provision reseller tenants")


def _assert_same_tenant_or_super_admin(current_user, username: str) -> None:
    if current_user.role == "super_admin":
        return
    target = get_user_by_username(username)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.get("tenant_id") != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot manage users outside your tenant")


@router.post("/create")
def create_user_endpoint(
    payload: UserCreateRequest, current_user=Depends(auth.get_current_user)
):
    require_admin(current_user)
    _assert_can_manage_role(current_user, payload.role, payload.provision_separate_tenant)

    tenant = None
    tenant_id = payload.tenant_id or current_user.tenant_id
    workspace_id = payload.workspace_id or current_user.workspace_id
    if payload.provision_separate_tenant:
        if not payload.company_name:
            raise HTTPException(status_code=400, detail="Company name is required for reseller tenant provisioning")
        tenant = create_tenant(
            company_name=payload.company_name,
            slug=payload.slug,
            domain=payload.domain,
            subscription_plan=payload.subscription_plan,
            max_users=payload.max_users,
            max_agents=payload.max_agents,
            max_calls_per_day=payload.max_calls_per_day,
            api_quota=payload.api_quota,
            asterisk_settings={
                "host": payload.asterisk_host,
                "sip_trunk": payload.sip_trunk,
                "did_number": payload.did_number,
                "sip_username": payload.sip_username,
                "sip_transport": payload.sip_transport,
            },
        )
        tenant_id = tenant["id"]
        workspace_id = f"{tenant_id}-workspace"
        if payload.role not in ("admin", "super_admin"):
            raise HTTPException(status_code=400, detail="A reseller tenant owner must be admin or super_admin")
    try:
        user = create_user(
            username=payload.username,
            email=payload.email,
            password=payload.password,
            role=payload.role,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            assigned_agent_id=payload.assigned_agent_id,
            department=payload.department,
            permissions=payload.permissions,
            must_change_password=True,
            parent_user_id=payload.parent_user_id,
            permission_group=payload.permission_group,
            permission_scope=payload.permission_scope,
            created_by=current_user.username,
        )
        if tenant:
            assign_tenant_owner(tenant["id"], payload.username)
            update_workspace_setup(
                tenant["id"],
                {
                    "workspace_id": workspace_id,
                    "tenant_owner": payload.username,
                    "asterisk_settings": {
                        "host": payload.asterisk_host,
                        "sip_trunk": payload.sip_trunk,
                        "did_number": payload.did_number,
                        "sip_username": payload.sip_username,
                        "sip_transport": payload.sip_transport,
                    },
                },
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "created", "user": user, "tenant": tenant}


@router.post("/invite")
def invite_user(payload: InviteRequest, current_user=Depends(auth.get_current_user)):
    require_admin(current_user)
    tenant_id = payload.tenant_id or current_user.tenant_id
    invite = create_invite(
        tenant_id=tenant_id,
        email=payload.email,
        role=payload.role,
        workspace_id=payload.workspace_id or current_user.workspace_id,
        inviter=current_user.username,
    )
    # In a real implementation, enqueue email delivery here.
    return {"status": "pending", "invite": invite}


@router.get("/list")
def list_users_endpoint(role: Optional[str] = None, status: Optional[str] = None, current_user=Depends(auth.get_current_user)):
    require_admin(current_user)
    users = list_users(current_user.tenant_id if current_user.role != "super_admin" else None)
    if role:
        users = [u for u in users if u.get("role") == role]
    if status:
        users = [u for u in users if u.get("status") == status]
    return {"users": users}


@router.get("/tenants")
def list_tenants_endpoint(current_user=Depends(auth.get_current_user)):
    require_admin(current_user)
    if current_user.role != "super_admin":
        return {"tenants": [tenant for tenant in list_tenants() if tenant["id"] == current_user.tenant_id]}
    return {"tenants": list_tenants()}


@router.get("/workspace-setup")
def get_workspace_setup_endpoint(current_user=Depends(auth.get_current_user)):
    return {"workspace_setup": get_workspace_setup(current_user.tenant_id)}


@router.patch("/update")
def update_user_endpoint(payload: UserUpdateRequest, current_user=Depends(auth.get_current_user)):
    require_admin(current_user)
    _assert_same_tenant_or_super_admin(current_user, payload.username)
    if payload.role:
        _assert_can_manage_role(current_user, payload.role)
    try:
        user = update_user(
            payload.username,
            email=payload.email,
            role=payload.role,
            permissions=payload.permissions,
            assigned_agent_id=payload.assigned_agent_id,
            department=payload.department,
            phone_number=payload.phone_number,
            status=payload.status,
            parent_user_id=payload.parent_user_id,
            permission_group=payload.permission_group,
            permission_scope=payload.permission_scope,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "updated", "user": user}


@router.post("/disable")
def disable_user_endpoint(payload: UserActionRequest, current_user=Depends(auth.get_current_user)):
    require_admin(current_user)
    _assert_same_tenant_or_super_admin(current_user, payload.username)
    try:
        user = disable_user(payload.username)
    except KeyError:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "disabled", "user": user}


@router.delete("/delete")
def delete_user_endpoint(payload: UserActionRequest, current_user=Depends(auth.get_current_user)):
    require_admin(current_user)
    _assert_same_tenant_or_super_admin(current_user, payload.username)
    delete_user(payload.username)
    return {"status": "deleted", "username": payload.username}


@router.post("/reset-password")
def reset_password_endpoint(
    payload: ResetPasswordRequest, current_user=Depends(auth.get_current_user)
):
    require_admin(current_user)
    _assert_same_tenant_or_super_admin(current_user, payload.username)
    try:
        user = reset_password(payload.username, payload.password)
    except KeyError:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "reset", "user": user}


@router.get("/activity")
def user_activity(current_user=Depends(auth.get_current_user)):
    require_admin(current_user)
    users = list_users(current_user.tenant_id if current_user.role != "super_admin" else None)
    activity = [
        {
            "username": user["username"],
            "last_login": user.get("last_login"),
            "status": user.get("status"),
            "role": user.get("role"),
        }
        for user in users
    ]
    return {"activity": activity}


# ============================================================================
# Hierarchy Endpoints
# ============================================================================

@router.get("/hierarchy")
def get_hierarchy_endpoint(current_user=Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """Get the full user hierarchy starting from current user's perspective."""
    require_admin(current_user)
    
    # Get the current user from DB to build tree
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Build hierarchy tree starting from current user
    tree = rbac.build_hierarchy_tree(user, db)
    return {"hierarchy": tree}


@router.get("/subtree/{user_id}")
def get_user_subtree_endpoint(user_id: str, current_user=Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """Get the subtree of all child users under a specific user."""
    require_admin(current_user)
    
    # Fetch the target user
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if current user has permission to view this subtree
    if not rbac.enforce_scope(current_user, target_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this user's subtree")
    
    # Build subtree
    subtree = rbac.get_user_subtree(target_user, db)
    return {"subtree": subtree}


@router.get("/children/{user_id}")
def get_user_children_endpoint(user_id: str, current_user=Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """Get direct child users of a specific user."""
    require_admin(current_user)
    
    # Fetch the parent user
    parent_user = db.query(User).filter(User.id == user_id).first()
    if not parent_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if current user has permission
    if not rbac.enforce_scope(current_user, parent_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    # Get direct children
    children = db.query(User).filter(User.parent_user_id == user_id).all()
    
    return {
        "parent_user_id": user_id,
        "children": [
            {
                "user_id": child.id,
                "username": child.username,
                "role": child.role,
                "email": child.email,
                "status": child.status,
                "permission_group": child.permission_group,
            }
            for child in children
        ]
    }
