# AVA User & Admin Access Architecture

## Overview
- **Goal:** Ensure AVA becomes a dual-role SaaS platform where infrastructure ownership stays with admins while end users only consume approved voice services.
- **Roles:** `super_admin` (platform-wide control), `tenant_admin` (workspace/infrastructure owner), `end_user` (application consumer). RBAC enforces precise segregation of UI, APIs, secrets, and telemetry.
- **Guiding principles:** never expose Asterisk, API keys, logs, billing, or infrastructure UI to end users. Admins configure everything; end users simply use assigned agents, view analytics, and manage their profile.

## Data Model

### Core Tables
| Table | Purpose |
|---|---|
| `users` | Stores credentials, role, tenant_id, status, hashed password, timestamps. |
| `tenant_admin_profiles` | Tracks workspace metadata (workspace_name, permissions JSON) for tenant admins. |
| `end_user_profiles` | Tracks assigned agent, department, phone, profile data, last login for end users. |
| `user_permissions` | Bridges `users` with granular permission keys (`can_manage_agents`, `can_view_billing`). |
| `user_invites` | Invite workflow (tenant, email, role, token, status, expires_at). |
| `user_sessions` | Device/IP/session tracking for audits and session invalidation. |
| `workspace_setup` | Setup wizard progress guard (`setup_completed`, `asterisk_connected`, `api_connected`, `provider_configured`). |

### Relationships & Constraints
- Each record links to `tenant_id`. Row-level security ensures queries are scoped to the requesting tenant.
- JWT payloads include `user_id`, `tenant_id`, `role`, `workspace_id`, and `permissions` array to simplify frontend guard logic.
- Tenant admins may have multiple permission rows, but end users receive only consumption-related claims (e.g., `can_access_voice_console`).

## API Surface

### User Management
| Method | Path | Notes |
|---|---|---|
| `POST` `/users/create` | Creates tenant admin or end user (admin only). Accepts assigned_agent_id/department/access level. |
| `POST` `/users/invite` | Sends invite email with token, expires in 24h. |
| `GET` `/users/list` | Supports filtering by role/status, returns last login/activity. |
| `PATCH` `/users/update` | Modify role, assigned agent, access flags. |
| `DELETE` `/users/delete` | Hard-delete or soft-delete user (admin only). |
| `POST` `/users/reset-password` | Triggers email + invalidates sessions. |
| `POST` `/users/disable` | Sets `status=disabled`, revokes sessions. |
| `GET` `/users/activity` | Returns login history, device/IP, last actions for auditing. |
- All user APIs require `tenant_admin`+ or platform `super_admin` roles, enforced by middleware.

### Setup Wizard APIs
| Step | Endpoint | Purpose |
|---|---|---|
| Workspace | `POST /setup/workspace` | Save company/workspace metadata, timezone, branding. |
| Asterisk | `POST /setup/asterisk` | Save host/SSH/API details, tests connectivity. |
| API | `POST /setup/api` | Store encrypted API keys, provider selection, test. |
| Pipeline | `POST /setup/pipeline` | Record default agent, voice settings. |
| Routing | `POST /setup/routing` | Configure inbound/outbound routes and DID mappings. |
| Users | `POST /setup/users` | Create initial tenant admins/end users. |
| Complete | `POST /setup/finish` | Set `setup_completed=true`, unlock end-user logins, emit audit log. |
- Step APIs validate `workspace_setup.setup_completed` flag and update progress columns.

## RBAC & Middleware

### JWT Auth
- Issues JWTs with the following claims:
  * `user_id`
  * `tenant_id`
  * `workspace_id`
  * `role`
  * `permissions` (array of strings)
- Tokens refreshed on login, invalidated on password reset/disable via `user_sessions`.

### Backend Guards
- Middleware for FastAPI services runs before request handlers:
  1. `validate_tenant` – ensures tenant_id matches request context.
  2. `validate_role` – checks role requirements (admin-only routes).
  3. `validate_permissions` – ensures specific permission flags exist when needed.
  4. `validate_setup` – prevents end-user login until `workspace_setup.setup_completed = true`.

### Page Guards & Frontend Visibility
- Guards use JWT data to determine UI visibility:
  * Admin sidebars list Setup Wizard, Users, Providers, Billing, Logs.
  * End-user sidebar limited to Voice App, Call Logs, Conversations, Analytics, Profile.
- Routes:
  * `/setup-wizard`, `/users`, `/providers`, `/billing`, `/logs` → admin only.
  * `/voice`, `/call-logs`, `/conversations` → accessible to both but UI hides admin controls for end users.
  * `/dashboard` available to all roles but displays different widgets (admin: workspace status; end user: usage/assigned agents).
- Frontend route guard component reads JWT claims stored in secure storage; unauthorized access redirects to “Not authorized” / login.

## Setup Wizard Flow (Admin Only)

1. **Workspace Setup** – Collect company & workspace info (name, logo, timezone, region). API writes to `workspace_setup`.
2. **Asterisk Server Setup** – Save host/SSH details, SIP transport, RTP range, port settings, API endpoint. Include “Test Connection” before moving forward.
3. **API Configuration** – Collect encrypted API keys, provider choices, voice/LLM models. “Test API” validates provider calls.
4. **Voice Pipeline Setup** – Default agent, language, voice, streaming preferences, silence timeout, turn detection thresholds.
5. **Call Routing** – Configure inbound/outbound DIDs, extensions, queues, SIP endpoints.
6. **User Creation** – Admin seeds additional tenant admins/end users (option to invite via email).
7. **Finish Setup** – Persist `setup_completed = true`, allow login for end users, emit admin audit event.

## Admin User Management UI

### Layout
- **Sidebar Links:** Dashboard, Users, Setup Wizard, Agents, Providers, Billing, Analytics, Logs, Settings.
- **User Table Columns:** Name, Email, Role, Assigned Agent, Status, Created Date, Last Login, Actions (Edit/Suspend/Delete/Assign Agent/Reset Password).
- **Toolbar:** Search, filter by role/status, bulk actions (invite, disable), “Create User” button.
- **Modal Fields:** Name, Email, Password, Role (tenant_admin/end_user), Assigned Agent, Department, Team, Access Level, Custom permissions.
- **Invite Flow:** Generate token, send email via background job, track status in `user_invites`.
- **Activity Panel:** Show last login (from `user_sessions`) and recent actions (from audit logs).

## End User Dashboard
- **Sidebar:** Dashboard, Voice App, Call Logs, Conversations, Analytics, Profile/Notifications.
- **Restrictions:** UI never shows Setup Wizard, Providers, Billing, Logs, or infrastructure settings.
- **Data Access:** Allowed to see only their assigned agents, call history, and analytics scoped to their user_id/tenant. Any attempt to fetch admin data is blocked by backend permission guards.

## Tenant Isolation & Secrets
- Secrets (API keys, SSH keys) stored encrypted with tenant-specific keys; only tenant_admins and super_admins can view secrets.
- Provider configs, YAML overrides, and logs live under `/tenants/{tenant_id}/...` folders to prevent leakage.
- `end_user_profiles` never include API keys; tokens expire quickly and do not provide secret-scoped claims.

## Invite & Session Flows
- Invite workflow: `tenant_admin` POST `/users/invite`, system emails link with token; user sets password through `/auth/complete-invite`. Token stored in `user_invites`.
- Sessions logged in `user_sessions` (device, IP, login_time, last_activity); used for monitoring and forced logout on privilege revocation.

## Migration & Implementation Checklist
1. **DB migrations:** Add new tables with RLS policies, permission defaults, workspace_setup flag.
2. **JWT & Auth:** Ensure login issues tokens with required claims; add middleware to check setup completion.
3. **User APIs:** Implement FastAPI endpoints (create/invite/update/disable/reset/delete/list) plus audit logging and email dispatch.
4. **Setup Wizard APIs:** Build sequential endpoints, update workspace_status, run tests for each step, enforce `setup_completed`.
5. **Frontend:** Build admin user management view, wizard, new sidebars, and the end-user console; guard routes by JWT claims.
6. **Invite/Email:** Integrate background job for invite emails, handle token expiry, and log events.
7. **Tests:** RBAC tests, invite flow tests, page guard tests, middleware permission coverage.

## Next Steps
1. Scaffold FastAPI routers/middleware for the new user/setup APIs.
2. Build React/Tailwind components for the admin user table, wizard steps, and end-user console with route guards.
3. Add migrations and seed data for default roles (`super_admin`, `tenant_admin`, `end_user`).
4. Wire email/invite flows and audit logs; add integration tests for RBAC/policy enforcement.
