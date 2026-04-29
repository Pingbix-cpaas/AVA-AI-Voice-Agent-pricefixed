#!/usr/bin/env python3
"""
Migration script to move data from JSON user store to PostgreSQL database.
"""

import json
import os
from datetime import datetime
from database import get_session, init_db
from models import Tenant, User, Invite, WorkspaceSetup
from services.user_store import load_state
from services.security import hash_password

def migrate_data():
    """Migrate data from JSON to database"""
    print("Starting data migration from JSON to PostgreSQL...")

    # Initialize database tables
    init_db()
    print("Database tables initialized.")

    # Load current JSON state
    state = load_state()
    print(f"Loaded JSON state with {len(state['users'])} users, {len(state['tenants'])} tenants")

    db = get_session()
    try:
        # Migrate tenants
        for tenant_id, tenant_data in state['tenants'].items():
            tenant = Tenant(
                id=tenant_data['id'],
                company_name=tenant_data['company_name'],
                slug=tenant_data['slug'],
                domain=tenant_data.get('domain'),
                status=tenant_data.get('status', 'active'),
                subscription_plan=tenant_data.get('subscription_plan', 'starter'),
                created_at=datetime.fromisoformat(tenant_data['created_at'].replace('Z', '+00:00')) if tenant_data.get('created_at') else datetime.utcnow(),
                max_users=tenant_data.get('max_users'),
                max_agents=tenant_data.get('max_agents'),
                max_calls_per_day=tenant_data.get('max_calls_per_day'),
                api_quota=tenant_data.get('api_quota'),
                branding_settings=tenant_data.get('branding_settings', {}),
                owner_username=tenant_data.get('owner_username'),
                reseller_enabled=tenant_data.get('reseller_enabled', True),
            )
            db.add(tenant)
            print(f"Migrated tenant: {tenant.company_name}")

        # Migrate users
        for username, user_data in state['users'].items():
            user = User(
                id=user_data['user_id'],
                username=user_data['username'],
                email=user_data['email'],
                tenant_id=user_data['tenant_id'],
                workspace_id=user_data['workspace_id'],
                role=user_data['role'],
                status=user_data.get('status', 'active'),
                permissions=user_data.get('permissions', []),
                assigned_agent_id=user_data.get('assigned_agent_id'),
                department=user_data.get('department'),
                phone_number=user_data.get('phone_number'),
                created_at=datetime.fromisoformat(user_data['created_at'].replace('Z', '+00:00')) if user_data.get('created_at') else datetime.utcnow(),
                updated_at=datetime.fromisoformat(user_data['updated_at'].replace('Z', '+00:00')) if user_data.get('updated_at') else datetime.utcnow(),
                last_login=datetime.fromisoformat(user_data['last_login'].replace('Z', '+00:00')) if user_data.get('last_login') else None,
                must_change_password=user_data.get('must_change_password', False),
                password_hash=user_data.get('password_hash'),
            )
            db.add(user)
            print(f"Migrated user: {user.username}")

        # Migrate invites
        for token, invite_data in state['invites'].items():
            invite = Invite(
                token=invite_data['token'],
                tenant_id=invite_data['tenant_id'],
                workspace_id=invite_data.get('workspace_id'),
                email=invite_data['email'],
                role=invite_data['role'],
                inviter=invite_data['inviter'],
                status=invite_data.get('status', 'pending'),
                expires_at=datetime.fromisoformat(invite_data['expires_at'].replace('Z', '+00:00')) if invite_data.get('expires_at') else None,
            )
            db.add(invite)
            print(f"Migrated invite: {invite.email}")

        # Migrate workspace setup
        for tenant_id, setup_data in state.get('workspace_setup', {}).items():
            setup = WorkspaceSetup(
                tenant_id=setup_data['tenant_id'],
                workspace_id=setup_data.get('workspace_id', f"{tenant_id}-workspace"),
                setup_completed=setup_data.get('setup_completed', False),
                asterisk_connected=setup_data.get('asterisk_connected', False),
                sip_configured=setup_data.get('sip_configured', False),
                api_connected=setup_data.get('api_connected', False),
                provider_configured=setup_data.get('provider_configured', False),
                asterisk_settings=setup_data.get('asterisk_settings', {}),
                updated_at=datetime.fromisoformat(setup_data['updated_at'].replace('Z', '+00:00')) if setup_data.get('updated_at') else datetime.utcnow(),
            )
            db.add(setup)
            print(f"Migrated workspace setup for tenant: {tenant_id}")

        # Commit all changes
        db.commit()
        print("Migration completed successfully!")

        # Backup the original JSON file
        backup_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'users.json.backup')
        with open(backup_path, 'w') as f:
            json.dump(state, f, indent=2)
        print(f"Original JSON data backed up to: {backup_path}")

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate_data()