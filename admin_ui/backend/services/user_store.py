from __future__ import annotations

import json
import os
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

from settings import USERS_PATH

from .fs import atomic_write_text
from .security import hash_password


_DEFAULT_TENANT = "platform"
_DEFAULT_WORKSPACE = "platform-workspace"
_INVITE_TTL = timedelta(hours=24)

ROLE_PERMISSIONS = {
    "super_admin": ["super_admin", "manage_platform", "impersonate"],
    "tenant_admin": [
        "manage_workspace",
        "manage_users",
        "configure_providers",
        "view_billing",
        "manage_agents",
    ],
    "tenant_manager": ["manage_users", "manage_agents", "view_billing"],
    "end_user": ["consume_voice", "view_call_history", "view_assigned_agents"],
    "readonly_user": ["view_call_history", "view_assigned_agents"],
}


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _ensure_state_structure(state: Dict[str, Any]) -> None:
    for key in ("users", "tenants", "invites", "sessions", "workspace_setup"):
        state.setdefault(key, {})


def _slugify(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    return "-".join(part for part in slug.split("-") if part) or "tenant"


def _workspace_id_for_tenant(tenant_id: str) -> str:
    return f"{tenant_id}-workspace"


def _is_legacy_user_file(state: Dict[str, Any]) -> bool:
    return "users" not in state and any(
        isinstance(value, dict) and ("hashed_password" in value or "password_hash" in value)
        for value in state.values()
    )


def _migrate_legacy_user_file(state: Dict[str, Any]) -> Dict[str, Any]:
    """Convert the original flat auth file into the SaaS-aware user store."""
    now = _now_iso()
    migrated: Dict[str, Any] = {"users": {}, "tenants": {}, "invites": {}, "sessions": {}, "workspace_setup": {}}
    for username, legacy in state.items():
        if not isinstance(legacy, dict):
            continue
        role = "super_admin" if username == "admin" else legacy.get("role", "end_user")
        user = {
            "user_id": legacy.get("user_id") or str(uuid.uuid4()),
            "username": legacy.get("username") or username,
            "email": legacy.get("email") or f"{username}@example.com",
            "tenant_id": legacy.get("tenant_id") or _DEFAULT_TENANT,
            "workspace_id": legacy.get("workspace_id") or _DEFAULT_WORKSPACE,
            "role": role,
            "status": "disabled" if legacy.get("disabled") else legacy.get("status", "active"),
            "permissions": legacy.get("permissions") or ROLE_PERMISSIONS.get(role, []),
            "assigned_agent_id": legacy.get("assigned_agent_id"),
            "department": legacy.get("department"),
            "phone_number": legacy.get("phone_number"),
            "created_at": legacy.get("created_at") or now,
            "updated_at": legacy.get("updated_at") or now,
            "last_login": legacy.get("last_login"),
            "must_change_password": legacy.get("must_change_password", username == "admin"),
            "password_hash": legacy.get("password_hash") or legacy.get("hashed_password"),
        }
        migrated["users"][user["username"]] = user
    return migrated


def load_state() -> Dict[str, Any]:
    """Load the user store state, creating defaults if missing."""
    if not os.path.exists(USERS_PATH):
        os.makedirs(os.path.dirname(USERS_PATH), exist_ok=True)
        state: Dict[str, Any] = {}
        _ensure_state_structure(state)
        _ensure_default_tenant(state)
        _ensure_default_admin(state)
        save_state(state)
        return state

    with open(USERS_PATH, "r", encoding="utf-8") as f:
        try:
            state = json.load(f)
        except json.JSONDecodeError:
            state = {}
    if _is_legacy_user_file(state):
        state = _migrate_legacy_user_file(state)
    _ensure_state_structure(state)
    changed = False
    if _ensure_default_tenant(state):
        changed = True
    if _ensure_default_admin(state):
        changed = True
    if state.get("workspace_setup") is None:
        state["workspace_setup"] = {}
        changed = True
    if changed:
        save_state(state)
    return state


def save_state(state: Dict[str, Any]) -> None:
    atomic_write_text(USERS_PATH, json.dumps(state, indent=2) + "\n")


def _ensure_default_admin(state: Dict[str, Any]) -> bool:
    if state["users"]:
        return False
    now = _now_iso()
    admin_user = {
        "user_id": str(uuid.uuid4()),
        "username": "admin",
        "email": "admin@example.com",
        "tenant_id": _DEFAULT_TENANT,
        "workspace_id": _DEFAULT_WORKSPACE,
        "role": "super_admin",
        "status": "active",
        "permissions": ROLE_PERMISSIONS["super_admin"],
        "assigned_agent_id": None,
        "department": None,
        "phone_number": None,
        "created_at": now,
        "updated_at": now,
        "last_login": None,
        "must_change_password": True,
        "password_hash": hash_password("admin"),
    }
    state["users"]["admin"] = admin_user
    return True


def _ensure_default_tenant(state: Dict[str, Any]) -> bool:
    tenants = state.setdefault("tenants", {})
    if _DEFAULT_TENANT in tenants:
        return False
    now = _now_iso()
    tenants[_DEFAULT_TENANT] = {
        "id": _DEFAULT_TENANT,
        "company_name": "AVA Platform",
        "slug": "platform",
        "domain": None,
        "status": "active",
        "subscription_plan": "enterprise",
        "created_at": now,
        "max_users": None,
        "max_agents": None,
        "max_calls_per_day": None,
        "api_quota": None,
        "branding_settings": {},
        "owner_username": "admin",
        "reseller_enabled": True,
    }
    state.setdefault("workspace_setup", {})[_DEFAULT_TENANT] = {
        "tenant_id": _DEFAULT_TENANT,
        "setup_completed": False,
        "updated_at": now,
    }
    return True


def serialize_user(user: Dict[str, Any]) -> Dict[str, Any]:
    sanitized = user.copy()
    sanitized.pop("password_hash", None)
    return sanitized


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    state = load_state()
    return state["users"].get(username)


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    state = load_state()
    for user in state["users"].values():
        if user["user_id"] == user_id:
            return user
    return None


def list_users(tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
    state = load_state()
    users = []
    for user in state["users"].values():
        if tenant_id and user["tenant_id"] != tenant_id:
            continue
        users.append(serialize_user(user))
    return users


def list_tenants() -> List[Dict[str, Any]]:
    state = load_state()
    return list(state["tenants"].values())


def get_tenant(tenant_id: str) -> Optional[Dict[str, Any]]:
    state = load_state()
    return state["tenants"].get(tenant_id)


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
    state = load_state()
    base_slug = _slugify(slug or company_name)
    tenant_id = base_slug
    suffix = 2
    while tenant_id in state["tenants"]:
        tenant_id = f"{base_slug}-{suffix}"
        suffix += 1

    now = _now_iso()
    tenant = {
        "id": tenant_id,
        "company_name": company_name,
        "slug": base_slug,
        "domain": domain or None,
        "status": "active",
        "subscription_plan": subscription_plan,
        "created_at": now,
        "max_users": max_users,
        "max_agents": max_agents,
        "max_calls_per_day": max_calls_per_day,
        "api_quota": api_quota,
        "branding_settings": branding_settings or {},
        "owner_username": owner_username,
        "reseller_enabled": True,
    }
    state["tenants"][tenant_id] = tenant
    state["workspace_setup"][tenant_id] = {
        "tenant_id": tenant_id,
        "workspace_id": _workspace_id_for_tenant(tenant_id),
        "setup_completed": False,
        "asterisk_connected": False,
        "sip_configured": False,
        "api_connected": False,
        "provider_configured": False,
        "asterisk_settings": asterisk_settings or {},
        "updated_at": now,
    }
    save_state(state)
    return tenant


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
) -> Dict[str, Any]:
    state = load_state()
    if username in state["users"]:
        raise ValueError("username already exists")

    now = _now_iso()
    user = {
        "user_id": str(uuid.uuid4()),
        "username": username,
        "email": email,
        "tenant_id": tenant_id or _DEFAULT_TENANT,
        "workspace_id": workspace_id or _DEFAULT_WORKSPACE,
        "role": role,
        "status": "active",
        "permissions": list(permissions or ROLE_PERMISSIONS.get(role, [])),
        "assigned_agent_id": assigned_agent_id,
        "department": department,
        "phone_number": None,
        "created_at": now,
        "updated_at": now,
        "last_login": None,
        "must_change_password": must_change_password,
        "password_hash": hash_password(password),
    }
    state["users"][username] = user
    save_state(state)
    return serialize_user(user)


def assign_tenant_owner(tenant_id: str, username: str) -> None:
    state = load_state()
    tenant = state["tenants"].get(tenant_id)
    if not tenant:
        return
    tenant["owner_username"] = username
    save_state(state)


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
) -> Dict[str, Any]:
    state = load_state()
    user = state["users"].get(username)
    if not user:
        raise KeyError("user not found")

    if email is not None:
        user["email"] = email
    if role is not None:
        user["role"] = role
        user["permissions"] = list(permissions or ROLE_PERMISSIONS.get(role, []))
    if permissions is not None:
        user["permissions"] = list(permissions)
    if assigned_agent_id is not None:
        user["assigned_agent_id"] = assigned_agent_id
    if department is not None:
        user["department"] = department
    if phone_number is not None:
        user["phone_number"] = phone_number
    if status is not None:
        user["status"] = status

    user["updated_at"] = _now_iso()
    save_state(state)
    return serialize_user(user)


def disable_user(username: str) -> Dict[str, Any]:
    state = load_state()
    user = state["users"].get(username)
    if not user:
        raise KeyError("user not found")
    user["status"] = "disabled"
    user["updated_at"] = _now_iso()
    save_state(state)
    return serialize_user(user)


def delete_user(username: str) -> None:
    state = load_state()
    if username in state["users"]:
        del state["users"][username]
        save_state(state)


def reset_password(username: str, password: str, *, must_change_password: bool = True) -> Dict[str, Any]:
    state = load_state()
    user = state["users"].get(username)
    if not user:
        raise KeyError("user not found")
    user["password_hash"] = hash_password(password)
    user["must_change_password"] = must_change_password
    user["updated_at"] = _now_iso()
    save_state(state)
    return serialize_user(user)


def record_login(username: str) -> None:
    state = load_state()
    user = state["users"].get(username)
    if not user:
        return
    user["last_login"] = _now_iso()
    user["updated_at"] = _now_iso()
    save_state(state)


def create_invite(
    tenant_id: str,
    email: str,
    role: str,
    inviter: str,
    workspace_id: Optional[str] = None,
) -> Dict[str, Any]:
    state = load_state()
    token = secrets.token_urlsafe(32)
    invite = {
        "tenant_id": tenant_id,
        "workspace_id": workspace_id or _DEFAULT_WORKSPACE,
        "email": email,
        "role": role,
        "inviter": inviter,
        "status": "pending",
        "token": token,
        "expires_at": (_now_iso_from_ttl(_INVITE_TTL)),
    }
    state["invites"][token] = invite
    save_state(state)
    return invite


def _now_iso_from_ttl(ttl: timedelta) -> str:
    return (datetime.utcnow() + ttl).isoformat() + "Z"


def list_invites() -> List[Dict[str, Any]]:
    state = load_state()
    return list(state["invites"].values())


def update_workspace_setup(tenant_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    state = load_state()
    workspace_setup = state.setdefault("workspace_setup", {})
    entry = workspace_setup.get(tenant_id, {})
    entry.update(updates)
    entry.setdefault("tenant_id", tenant_id)
    entry.setdefault("setup_completed", False)
    entry["updated_at"] = _now_iso()
    workspace_setup[tenant_id] = entry
    save_state(state)
    return entry


def get_workspace_setup(tenant_id: str) -> Dict[str, Any]:
    state = load_state()
    return state.get("workspace_setup", {}).get(tenant_id, {"tenant_id": tenant_id, "setup_completed": False})
