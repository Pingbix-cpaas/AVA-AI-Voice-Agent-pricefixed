# AVA SaaS Monetization Architecture

## Executive Summary
- **Goal:** Transform AVA into a production-grade SaaS platform with strict tenant isolation, enterprise billing, and real-time monetization.
- **Layers:** 
  1. **AVA Core Engine** – existing call orchestration, pipelines, YAML config loading.
  2. **Tenant Layer** – metadata, workspace isolation, RBAC, middleware enforcement.
  3. **Billing Layer** – Stripe-backed subscription, metered billing, wallets, invoices.
  4. **Pricing Layer** – plan catalog, dynamic pricing engine, markup/fee controls.
  5. **Usage Tracking Layer** – real-time metrics, events, quotas, cost calculation.
  6. **Admin Control Layer** – tenant lifecycle, revenue insights, soft suspension.
  7. **Tenant Portal** – self-serve dashboard, usage graphs, payment flows.

## Backend Architecture

### Microservice Map
| Service | Primary Responsibility | Tech Stack |
|---|---|---|
| `tenant_service` | Provision tenants, enforce workspace isolation (SQL schema, file paths, secrets). | FastAPI, PostgreSQL |
| `billing_service` | Orchestrate Stripe lifecycle, invoicing, wallet credits, audit logs. | FastAPI, Stripe SDK, PostgreSQL |
| `usage_service` | Ingest call events, maintain usage counters, publish to `pricing_engine`. | FastAPI, Celery consumers, Redis for hot counters |
| `subscription_service` | Handle plan changes, trial logic, upgrade/downgrade flows, soft suspension. | FastAPI, Celery tasks, Stripe webhooks |
| `pricing_engine` | Apply dynamic pricing formula (voice, LLM, STT, TTS, markup, fee). | Python rules engine |
| `invoice_service` | Generate invoices + PDF, sync Stripe invoices, expose download endpoints. | Celery, FastAPI |
| `quota_service` | Enforce per-tenant limits before call starts, signal denial/fallback. | FastAPI middleware |
| `rate_limit_service` | API quotas, JWT-based checks, integration with Redis. | FastAPI, Redis |

### Tenant Isolation Middleware
- JWT token must contain `{tenant_id, workspace_id, role, permissions}`.
- Row-level security policies link every tenant-scoped table to `tenant_id`.
- Tenant middleware injects `TenantContext` with path prefixes, storage roots, API key visibility.
- Filesystem isolation uses `/tenants/{tenant_id}/configs`, `/logs`, `/recordings`, `/exports`.
- Secrets stored encrypted per tenant (AES-GCM with KMS-managed keys); provider keys rotated automatically.

### Multi-Tenant Data Model
#### Core Tables
1. `tenants` – workspace identity and status.  
2. `tenant_users` – RBAC roles + granular permissions (`billing_manager`, `viewer`, etc.).  
3. `tenant_settings` – limits (voice minutes, agents, providers, storage, API rate, concurrent calls), branding, custom domains.  
4. `tenant_usage` – monthly aggregated counters for minutes, calls, tokens, storage, agents, API requests.  
5. `subscriptions` – Stripe lifecycle (trial_end, renewal_date, cancel_at_period_end).  
6. `plans` – catalog (free/starter/pro/pro, enterprise), included units, feature JSON, seat/agent caps.  
7. `invoices` – balanced between Stripe and platform, statuses, amounts, invoice dates.  
8. `usage_events` – raw meter data (call start/end, tokens, costs, metadata, latency).

#### Supporting Tables
- `billing_profiles` – payment method references, wallet/credit balances, auto top-up triggers.  
- `tenant_limits_history` – snapshots used for downgrade/overage decisions and audit trails.  
- `rbac_role_permissions` – mapping for dynamic feature flags (e.g., API key creation).
- `audit_logs` – event_type, initiator, resource, metadata, timestamp; used for billing decisions.

#### Dynamic Pricing Engine
`final_charge = voice_minutes_cost + llm_token_cost + stt_cost + tts_cost + provider_markup + platform_fee`
- Inserted costs into `usage_events`. `pricing_engine` exposes `.calculate` API consumed during call completion (billing event queue).
- Allows override per plan via `plans.features_json` (for example `{"provider_markup": 0.05, "platform_fee": 0.03}`).

## API Catalog

### Tenant Lifecycle
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/tenant/create` | Create tenant + workspace, return onboarding secret. |
| `POST` | `/tenant/invite` | Send invite email, create `tenant_users` entry. |
| `POST` | `/tenant/suspend` | Soft suspend (grace period), integrates with quota service & billing. |
| `GET` | `/tenant/usage` | Aggregate from `tenant_usage`, optionally raw event stream. |

### Billing/Subscription
| Method | Path | Purpose |
|---|---|---|
| `GET` | `/billing/history` | List invoices + status. |
| `POST` | `/billing/checkout` | Trigger Stripe Checkout session (plan, seats, metered). |
| `POST` | `/plan/change` | Upgrade/downgrade, handles trial/limits logic and Stripe subscription patch. |
| `GET` | `/pricing/plans` | Return plan catalog (monthly/yearly toggles). |
| `GET` | `/subscription/status` | Stripe + internal status (balance, grace, soft suspended). |

### Usage & Quotas
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/usage/events` | Ingest call start/end, tokens, STT/TTS, provider cost metadata. |
| `GET` | `/quota/check` | Pre-call check (voice minutes, concurrent calls, API rate). |
| `POST` | `/api-keys/rotate` | Tenant API key rotation. |

### Stripe Webhooks (handled by `subscription_service`)
- `invoice.paid`, `invoice.failed`, `customer.subscription.updated`, `customer.subscription.deleted`, `payment_method.attached`.
- Webhooks update `subscriptions`, trigger billing retries, escalate to admin panel on failures.

## Tenant & Admin Portals

### Tenant Dashboard (React + Tailwind + Shadcn + TypeScript)
- **Widgets:** usage meter gauge, voice-minute graph, agent utilization, cost breakdown, quota alerts.  
- **Actions:** add payment method (Stripe Customer Portal), upgrade plan (modal with monthly/annual toggle), download invoice (PDF link).  
- **Team:** manage `tenant_users`, roles (owner/admin/member/billing_manager/viewer).  
- **API Keys:** list+rotate, with RBAC enforcement.  
- **Pricing Page:** route featuring plan cards, FAQ, CTA buttons, monthly/yearly toggle, “Recommended” badges, Stripe Checkout integration (Checkout session created via backend).  
- **White Label:** optional branding overrides from `tenant_settings.branding`.

### Super Admin Panel
- **Views:** tenant list (status, plan, balance), revenue dashboard (MRR, ARR, churn, billing failures), top tenants, platform usage heatmap.  
- **Actions:** manual plan override, suspend tenant, refund invoice, escalate retry.  
- **Analytics:** provider cost passthrough (per-tenant), billing audit logs, global provider pricing updates.  
- Dashboard built with same stack but limited to super_admin roles.

## Usage Tracking & Real-Time Billing Events
- On call start: create `call_sessions` record, reserve voice minute quota.  
- On call end: compute duration, tokens (LLM), STT/TTS usage, provider cost, total charge via `pricing_engine`.  
- Emit message to `billing_event_queue` (Redis stream/Celery). `billing_service` writes to `usage_events`, updates balances, updates `tenant_usage`.  
- `quota_service` checks usage aggregate before session creation; denies call with fallback audio message if exceeded.  
- `usage_service` and `rate_limit_service` share hot counters in Redis (expire 60s) for API quotas.  
- Observability: Prometheus metrics expose tenant latency, provider failures, revenue metrics, billing event rate.

## Billing Flow
1. Tenant signs up → `tenant_service` provisions workspace, directories, defaults.  
2. Stripe Checkout collects payment; `billing_service` records `subscriptions` entry.  
3. Real-time usage recorded; `pricing_engine` calculates costs; `invoice_service` generates invoice (metered/usage).  
4. Monthly/annual cycle triggers autopay; `billing_service` handles retries, grace period, soft suspension (via `subscription_service`).  
5. Overages billed via metering (Stripe metered billing) + wallet credits auto top-up when threshold hit.  
6. Pay-as-you-go uses prepaid wallet; `usage_events` decrement wallet, `billing_service` auto top-up or disable on zero balance.  
7. Trial handling uses `subscriptions.trial_end`; `quota_service` can block features after trial.  

## Swagger/OpenAPI & Testing
- FastAPI services expose OpenAPI; share reusable schemas (tenant context, billing plan, usage event).  
- Automated tests include tenant isolation, billing lifecycle (ingest event → invoice), quota enforcement, Stripe webhook handling, overage & concurrent billing.
- Integration tests simulate thousands of tenants by faking usage streams + verifying RLS restrictions.

## Deployment & Observability
- **Docker Compose** orchestrates `api`, `worker`, `admin_ui`, `stripe-webhook`, `redis`, `postgres`; TLS termination handled upstream.  
- **Kubernetes-ready** via Helm manifests referencing env secrets (Stripe keys, DB).  
- Horizontal scaling through stateless FastAPI pods, Celery workers for billing/usage. Redis for counters, RabbitMQ for billing queue.  
- Monitoring: Prometheus + Grafana dashboards for call latency, billing events, provider failures, revenue metrics. Logs aggregated via Loki/ELK (tagged with tenant_id).  
- Observability also tracks `billing_event_queue` backlog and `usage_service` ingestion latency.

## Deployment Folder Structure (new)
```
src/
├─ billing_service/
│  └─ ... (FastAPI/, Celery tasks, pricing engine)
├─ usage_service/
├─ tenant_service/
├─ subscription_service/
├─ invoice_service/
├─ quota_service/
├─ rate_limit_service/
admin_ui/
├─ apps/tenant-portal/
├─ apps/super-admin/
docs/
├─ saas-billing-architecture.md  # this file
├─ migration/                           # future migration scripts
```

## Migration Plan
1. **DB migration:** introduce tenant tables with RLS, usage tables, invoice tables via Alembic scripts.  
2. **Legacy YAML compatibility:** keep existing configs; new per-tenant `config/tenants/{tenant_id}/ai-agent.yaml` overrides and importer translating YAML to DB-backed settings.  
3. **Tenant migration:** script to convert current workspace to tenant records, copy configs to isolated directories, generate RBAC users.  
4. **Existing config import:** CLI command + API to pull config from filesystem into new storage (keeps file retention).  
5. **Backward compatibility:** existing CLI commands still read from global YAML while writes go to tenant-scoped directories until migration completes.

## Testing Strategy
- Unit tests for pricing engine formula variations, RBAC matrix enforcement, quota denial responses.  
- Integration tests for subscription lifecycle (Stripe webhook simulation).  
- Quota tests covering voice-minute, API, provider, concurrent call thresholds.  
- Stripe webhook replay tests, billing retry/resume, invoice failure scenarios.  
- Concurrent billing tests ensure `usage_events` atomic pricing updates.  
- Overage tests verify auto-incremented invoices + wallet deduct logic.

## Monitoring & Analytics
- Track metrics per tenant: latency, calls, billing events, provider failures.  
- Aggregations: MRR, churn, top tenants, cost vs revenue ratio.  
- Use `audit_logs` for billing decisions and security investigations.

## Frontend Layout Notes
- **Pricing page:** monthly/yearly toggle, CTA for Stripe Checkout, comparison table across plans (free/starter/pro/enterprise), FAQ CTA anchoring the upgrade modal.  
- **Tenant dashboard:** usage meter, voice plan vs actual, agent usage, cost breakdown, limits warnings, invoice download list.  
- **Super admin:** revenue metrics, tenant status grid, billing failure list, global provider pricing updates.

## Security & Compliance
- JWT policy enforces RBAC with `super_admin`, `tenant_owner`, `tenant_admin`, `tenant_member`, `billing_manager`, `viewer`.  
- Row-level security ensures no tenant-cross data access.  
- Provider keys encrypted per tenant, API key rotation endpoint, secrets stored in Vault or encrypted envs.  
- Audit logs capture tenant logins, billing changes, plan swaps.

## Next Steps
1. Build separate FastAPI services per microservice, share common libraries (tenant context, billing events).  
2. Implement Celery workers for billing, usage, invoice generation.  
3. Create React/Tailwind tenant + super admin portals that leverage new APIs.  
4. Wire Stripe Checkout + customer portal + webhooks.  
5. Expand Docker Compose/k8s manifests to include new services and Redis/Celery infrastructure.  
6. Author migration scripts and tests listed above to ensure safe rollout.
