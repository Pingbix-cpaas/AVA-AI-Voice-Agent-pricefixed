"""RBAC (Role-Based Access Control) Service Layer

This module provides role hierarchy enforcement, permission checking,
and scope validation for the user hierarchy system.
"""

from typing import Dict, List, Optional, Set
from sqlalchemy.orm import Session
from models import User


# Role hierarchy: which roles can manage which other roles
ROLE_HIERARCHY = {
    "super_admin": {
        "can_create": ["super_admin", "admin", "reseller_admin", "end_user", "readonly_user"],
        "can_manage": ["super_admin", "admin", "reseller_admin", "end_user", "readonly_user"],
        "can_view": ["super_admin", "admin", "reseller_admin", "end_user", "readonly_user"],
    },
    "admin": {
        "can_create": ["reseller_admin", "end_user", "readonly_user"],
        "can_manage": ["reseller_admin", "end_user", "readonly_user"],
        "can_view": ["reseller_admin", "end_user", "readonly_user"],
    },
    "reseller_admin": {
        "can_create": ["end_user", "readonly_user"],
        "can_manage": ["end_user", "readonly_user"],
        "can_view": ["end_user", "readonly_user"],
    },
    "end_user": {
        "can_create": [],
        "can_manage": [],
        "can_view": [],
    },
    "readonly_user": {
        "can_create": [],
        "can_manage": [],
        "can_view": [],
    },
}

# Roles that can be created by each role
CREATABLE_ROLES = {
    "super_admin": ["super_admin", "admin", "reseller_admin", "end_user", "readonly_user"],
    "admin": ["reseller_admin", "end_user", "readonly_user"],
    "reseller_admin": ["end_user", "readonly_user"],
    "end_user": [],
    "readonly_user": [],
}

# Roles that can be managed (updated/deleted) by each role
MANAGEABLE_ROLES = {
    "super_admin": ["super_admin", "admin", "reseller_admin", "end_user", "readonly_user"],
    "admin": ["reseller_admin", "end_user", "readonly_user"],
    "reseller_admin": ["end_user", "readonly_user"],
    "end_user": [],
    "readonly_user": [],
}


def can_create_role(current_user: User, target_role: str) -> bool:
    """Check if current_user can create a user with target_role."""
    if current_user.role not in CREATABLE_ROLES:
        return False
    return target_role in CREATABLE_ROLES[current_user.role]


def can_manage_user(current_user: User, target_user: User) -> bool:
    """Check if current_user can manage (update/delete) target_user."""
    # super_admin can manage anyone
    if current_user.role == "super_admin":
        return True
    
    # User can manage someone if:
    # 1. They are in the same tenant AND
    # 2. They can manage the target role AND
    # 3. Target is not super_admin
    if current_user.tenant_id != target_user.tenant_id:
        return False
    
    if target_user.role not in MANAGEABLE_ROLES.get(current_user.role, []):
        return False
    
    return True


def get_visible_users(
    current_user: User,
    db: Session,
    role_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> List[User]:
    """Get list of users visible to current_user based on hierarchy and scope.
    
    Args:
        current_user: The user requesting the list
        db: Database session
        role_filter: Optional role to filter by
        status_filter: Optional status to filter by
        
    Returns:
        List of User objects that current_user is authorized to see
    """
    query = db.query(User)
    
    # super_admin can see all users
    if current_user.role == "super_admin":
        pass  # No filtering
    else:
        # Non-super-admin can only see users in same tenant
        query = query.filter(User.tenant_id == current_user.tenant_id)
        
        # Can only see users with roles they can manage (recursively)
        manageable = ROLE_HIERARCHY.get(current_user.role, {}).get("can_view", [])
        query = query.filter(User.role.in_(manageable))
    
    # Apply optional filters
    if role_filter:
        query = query.filter(User.role == role_filter)
    
    if status_filter:
        query = query.filter(User.status == status_filter)
    
    return query.all()


def enforce_scope(current_user: User, target_user: User) -> bool:
    """Enforce that users can only manage within their assigned scope.
    
    Args:
        current_user: The user making the request
        target_user: The user being accessed
        
    Returns:
        True if access is allowed, False otherwise
    """
    # super_admin bypass
    if current_user.role == "super_admin":
        return True
    
    # Must be in same tenant
    if current_user.tenant_id != target_user.tenant_id:
        return False
    
    # Check permission scope - if target has permission_scope restrictions,
    # current_user must have authority over that scope
    if target_user.permission_scope:
        # Simple implementation: admin can manage anyone in their workspace
        if current_user.role in ("admin", "super_admin"):
            return True
        return False
    
    return True


def get_user_subtree(user: User, db: Session, depth: int = 0, max_depth: int = 10) -> Dict:
    """Build a tree of all users under the given user in the hierarchy.
    
    Args:
        user: The root user
        db: Database session
        depth: Current recursion depth
        max_depth: Maximum recursion depth to prevent infinite loops
        
    Returns:
        Dictionary with user info and children list
    """
    if depth > max_depth:
        return {
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "children": [],
        }
    
    # Get direct children
    children = db.query(User).filter(User.parent_user_id == user.id).all()
    
    return {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "email": user.email,
        "tenant_id": user.tenant_id,
        "status": user.status,
        "permission_group": user.permission_group,
        "children": [get_user_subtree(child, db, depth + 1, max_depth) for child in children],
    }


def build_hierarchy_tree(root_user: User, db: Session) -> Dict:
    """Build complete hierarchy tree starting from root_user.
    
    Args:
        root_user: The root of the hierarchy tree
        db: Database session
        
    Returns:
        Dictionary representation of the hierarchy tree
    """
    return get_user_subtree(root_user, db)


def get_all_children(user: User, db: Session) -> List[User]:
    """Recursively get all child users under the given user.
    
    Args:
        user: The parent user
        db: Database session
        
    Returns:
        Flat list of all descendant users
    """
    children = db.query(User).filter(User.parent_user_id == user.id).all()
    
    all_descendants = []
    for child in children:
        all_descendants.append(child)
        all_descendants.extend(get_all_children(child, db))
    
    return all_descendants


def get_ancestor_chain(user: User, db: Session) -> List[User]:
    """Get chain of all ancestors from user up to root.
    
    Args:
        user: The user
        db: Database session
        
    Returns:
        List of ancestors from immediate parent to root, not including user
    """
    ancestors = []
    current = user
    
    while current.parent_user_id:
        parent = db.query(User).filter(User.id == current.parent_user_id).first()
        if not parent:
            break
        ancestors.append(parent)
        current = parent
    
    return ancestors


def validate_parent_assignment(
    parent_user: Optional[User],
    child_user: User,
    db: Session
) -> bool:
    """Validate that assigning parent_user as child_user's parent is valid.
    
    Checks for:
    - No circular references (parent can't be descendant of child)
    - Both users in same tenant (if parent specified)
    - Parent role >= child role in hierarchy
    
    Args:
        parent_user: The proposed parent (None to unset parent)
        child_user: The user to be assigned a parent
        db: Database session
        
    Returns:
        True if assignment is valid, False otherwise
    """
    if parent_user is None:
        # Unsetting parent is always valid
        return True
    
    # Check same tenant
    if parent_user.tenant_id != child_user.tenant_id:
        return False
    
    # Check no circular reference: child can't be ancestor of parent
    ancestors_of_parent = get_ancestor_chain(parent_user, db)
    if child_user in ancestors_of_parent:
        return False
    
    # Check role hierarchy: parent should have equal or higher role
    parent_level = _get_role_level(parent_user.role)
    child_level = _get_role_level(child_user.role)
    
    return parent_level >= child_level


def _get_role_level(role: str) -> int:
    """Get numeric level of role for hierarchy comparison.
    
    Higher number = higher privilege.
    """
    levels = {
        "super_admin": 5,
        "admin": 4,
        "reseller_admin": 3,
        "end_user": 2,
        "readonly_user": 1,
    }
    return levels.get(role, 0)
