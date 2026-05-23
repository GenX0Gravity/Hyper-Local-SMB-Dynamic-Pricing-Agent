# PricePulse AI — PostgreSQL Database Design

## Overview

Multi-tenant SaaS schema for hyperlocal dynamic pricing. **Businesses** are tenants; **users** are global accounts linked via **business_users** (many-to-many). Operational data is isolated with `business_id` and **Row Level Security (RLS)** using `current_business_id()`.

| Requirement | Implementation |
|-------------|----------------|
| UUID PKs | `gen_random_uuid()` via `pgcrypto` |
| Normalization | 3NF: catalog vs `location_products`, separate signal fact tables |
| Indexes | Tenant-leading composites, partial indexes on pending actions |
| Multi-tenant | `business_id` + RLS policies + `app.current_business_id` session var |
| Docker | `docker compose up -d db` mounts `database/schema/` on first init |

## ER Diagram

```mermaid
erDiagram
    BUSINESSES ||--o{ BUSINESS_USERS : has
    USERS ||--o{ BUSINESS_USERS : joins
    BUSINESSES ||--o{ LOCATIONS : operates
    BUSINESSES ||--o{ PRODUCTS : catalogs
    BUSINESSES ||--o{ PRICING_RULES : defines
    BUSINESSES ||--o{ DEMAND_PREDICTIONS : forecasts
    BUSINESSES ||--o{ PRICING_ACTIONS : executes
    BUSINESSES ||--o{ NOTIFICATIONS : sends
    BUSINESSES ||--o{ AUDIT_LOGS : audits

    LOCATIONS ||--o{ LOCATION_PRODUCTS : stocks
    PRODUCTS ||--o{ LOCATION_PRODUCTS : "per-outlet"
    LOCATIONS ||--o{ WEATHER_DATA : weather
    LOCATIONS ||--o{ EVENTS : events
    LOCATIONS ||--o{ FOOTFALL_METRICS : footfall

    PRODUCTS ||--o{ DEMAND_PREDICTIONS : predicted
    PRODUCTS ||--o{ PRICING_ACTIONS : repriced
    PRICING_RULES ||--o{ PRICING_ACTIONS : triggers
    DEMAND_PREDICTIONS ||--o{ PRICING_ACTIONS : informs
    USERS ||--o{ PRICING_ACTIONS : applies
    PRICING_ACTIONS ||--o{ NOTIFICATIONS : alerts
    USERS ||--o{ AUDIT_LOGS : actor
```

## Entity Relationships

### Core tenant & auth

| Table | Key relationships | Notes |
|-------|-------------------|-------|
| **businesses** | Root tenant | `slug` unique; `status`, `subscription_plan` enums |
| **users** | Global identity | `email` (CITEXT) unique platform-wide; no `business_id` column |
| **business_users** | `business_id` + `user_id` | Roles per business; supports consultants owning multiple SMBs |

### Operations

| Table | Scoped by | Notes |
|-------|-----------|-------|
| **locations** | `business_id` | Geo (`latitude`/`longitude`); one `is_primary` per business |
| **products** | `business_id` | Catalog: `base_price`, `cost_price`, min/max guardrails |
| **location_products** | `location_id` + `product_id` | Per-outlet `current_price` and `stock_qty` (3NF) |
| **pricing_rules** | `business_id` (+ optional `location_id`, `product_id`) | JSONB `conditions`; `priority` for evaluation order |

### External signals (location-scoped)

| Table | Scoped by | Dedup key |
|-------|-----------|-----------|
| **weather_data** | `location_id` | `(location_id, recorded_at, source)` |
| **events** | `location_id` | `(location_id, external_id, source)` |
| **footfall_metrics** | `location_id` | `(location_id, recorded_at, granularity, source)` |

Business context for signals is resolved via `locations.business_id` (no redundant `business_id` on fact tables).

### Pricing loop

| Table | Purpose |
|-------|---------|
| **demand_predictions** | ML output: `horizon_start/end`, `predicted_units`, `confidence`, `model_version` |
| **pricing_actions** | Price change lifecycle: `pending` → `applied` / `reverted` / `failed` |
| **notifications** | Delivery on `email`, `whatsapp`, `sms`, `push`, `in_app` |
| **audit_logs** | Immutable trail: `entity_type`, `entity_id`, `old_values` / `new_values` |

## Multi-Tenant Isolation

```sql
-- Set once per request (from JWT business_id)
SET LOCAL app.current_business_id = '550e8400-e29b-41d4-a716-446655440000';

-- Helper used by RLS policies
SELECT current_business_id();
```

**RLS enabled** on: `audit_logs`, `business_users`, `businesses`, `demand_predictions`, `location_products`, `locations`, `notifications`, `pricing_actions`, `pricing_rules`, `products`.

Example policy:

```sql
CREATE POLICY tenant_isolation_products ON products
    USING (business_id = current_business_id());
```

## Normalization Highlights

1. **Users ↔ Businesses** — Junction table instead of duplicating user rows per tenant.
2. **Products ↔ Locations** — `location_products` holds outlet-specific price/stock; catalog stays in `products`.
3. **Signals** — Typed columns + `raw_payload` JSONB instead of one generic `demand_signals` blob.
4. **Pricing actions** — Single table for recommendation + apply + revert (replaces `recommendations` + `recommendation_audits`).

## Performance Indexes (selected)

| Index | Query pattern |
|-------|---------------|
| `uq_businesses_slug` | Tenant lookup by subdomain/slug |
| `uq_business_users_membership` | Auth: user’s businesses |
| `idx_products_business_category` | Category filters in dashboard |
| `idx_pricing_rules_business_active` | Active rules sorted by priority |
| `idx_weather_location_recorded` | Latest weather for pricing engine |
| `idx_events_location_window` | Events overlapping a time window |
| `idx_pricing_actions_status` (partial) | Pending approval queue |
| `idx_audit_logs_entity` | Entity change history |

## Docker Commands

```powershell
# Start Postgres (schema auto-applies on empty volume)
docker compose up -d db

# Verify (container: pricepulse_db)
docker exec pricepulse_db psql -U postgres -d pricepulse -c "\dt"

# Re-apply manually (existing data volume — use only on fresh DB or migrations)
Get-Content database\schema\001_init.sql | docker exec -i pricepulse_db psql -U postgres -d pricepulse
```

Connection string (local):

```
postgresql://postgres:postgres@localhost:5432/pricepulse
```

## Legacy SQLModel mapping

| Legacy (`tenants` era) | New schema |
|------------------------|------------|
| `tenants` | `businesses` |
| `users.tenant_id` | `business_users` + global `users` |
| `demand_signals` | `weather_data`, `events`, `footfall_metrics` |
| `recommendations` | `pricing_actions` |
| `recommendation_audits` | `audit_logs` |

Source of truth: [`database/schema/001_init.sql`](schema/001_init.sql) (synced from running Postgres 15).
