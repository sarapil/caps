# CAPS — Scenarios & Impact Matrix

> **كابس** — نظام الصلاحيات المتقدم
> DocTypes: ~24 | APIs: ~83 | Modules: 7

## 📊 Module Map

| Module | DocTypes | APIs | Pages | Reports |
|--------|----------|------|-------|---------|
| Core | — | — | — | — |
| Capabilities | — | — | — | — |
| Bundles | — | — | — | — |
| Assignments | — | — | — | — |
| Field Maps | — | — | — | — |
| Action Maps | — | — | — | — |
| Audit | — | — | — | — |

## 🔄 Core Workflows

### 1. Setup & Configuration
1. Install CAPS app
2. Configure Settings singleton
3. Assign roles to users
4. Seed reference data

### 2. Daily Operations
- Create / Read / Update / Delete core records
- Submit workflows
- Generate reports

### 3. Reporting & Analytics
- Dashboard overview
- Period reports
- Export data

## 🛡️ Impact Matrix

| Action | Affected DocTypes | Side Effects | Rollback |
|--------|-------------------|-------------|----------|
| Install | All | Creates Module Defs, Roles | Uninstall |
| Migrate | All | Schema changes | bench migrate --rollback |
| Seed | Settings, Lookups | Reference data | Manual delete |

## 📋 API Inventory

> Total `@frappe.whitelist()` endpoints: ~83
> Permission coverage: TBD

| Module | Endpoint | Method | Auth | Rate Limit |
|--------|----------|--------|------|------------|
| — | TBD | — | — | — |

## 🧪 Test Coverage

| Category | Count | Status |
|----------|-------|--------|
| Unit tests | — | ❌ |
| Integration tests | — | ❌ |
| Permission tests | — | ❌ |
| UI contract tests | — | ❌ |

---

*Auto-generated on 2026-04-02 — update as features are added.*
