# Database Migration Guide

This guide explains how to migrate from the JSON-based user store to the PostgreSQL database for the AVA SaaS platform.

## Prerequisites

1. PostgreSQL database server running
2. Database user with CREATE DATABASE privileges
3. Python environment with required packages installed

## Environment Setup

Set the `DATABASE_URL` environment variable in your `.env` file:

```bash
DATABASE_URL=postgresql://username:password@localhost/ava_saas
```

## Migration Steps

### 1. Install Database Dependencies

The database dependencies are already added to `requirements.txt`. If you haven't installed them yet:

```bash
pip install -r requirements.txt
```

### 2. Initialize Database Schema

Run the database initialization script:

```bash
cd admin_ui/backend
python init_db.py
```

This will:
- Create all database tables
- Run Alembic migrations

### 3. Migrate Existing Data

If you have existing JSON user data, run the migration script:

```bash
python migrate_to_db.py
```

This will:
- Read data from `users.json`
- Migrate all users, tenants, invites, and workspace setups to PostgreSQL
- Create a backup of the original JSON file as `users.json.backup`

### 4. Update Application

The application has been updated to use the database by default. The API endpoints and authentication now work with PostgreSQL.

## Database Schema

The database includes the following tables:

- `tenants`: Multi-tenant organizations
- `users`: User accounts with tenant isolation
- `subscriptions`: Billing and subscription management
- `plans`: Subscription plan definitions
- `usage_tracking`: API usage and limits tracking
- `workspace_setup`: Tenant-specific configuration
- `invites`: User invitation system
- `sessions`: User session management

## Rollback

If you need to rollback to JSON storage:

1. Stop the application
2. Restore from `users.json.backup` if it exists
3. Remove or comment out the database initialization in `main.py`
4. Revert the imports in `api/users.py` and `auth.py` to use `user_store` instead of `user_store_db`

## Troubleshooting

- **Connection errors**: Check your `DATABASE_URL` and ensure PostgreSQL is running
- **Migration failures**: Check the database logs and ensure proper permissions
- **Data inconsistencies**: The migration script creates a backup - you can manually reconcile differences

## Next Steps

After migration:
- Test user creation, login, and tenant management
- Verify reseller features work correctly
- Set up database backups and monitoring
- Consider implementing Row-Level Security (RLS) policies for additional tenant isolation