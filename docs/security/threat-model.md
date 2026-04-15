# CAPS Threat Model — نموذج التهديدات

## Overview — نظرة عامة

CAPS (Capability-Based Access Control System) is a **security-critical** component that controls access to features, data, and actions across all Frappe applications. Compromise of CAPS could lead to unauthorized access to sensitive business data.

## Asset Inventory

| Asset                        | Sensitivity | Impact if Compromised            |
| ---------------------------- | ----------- | -------------------------------- |
| Capability definitions       | Medium      | Feature access manipulation      |
| User capability assignments  | High        | Unauthorized data access         |
| Permission group memberships | High        | Privilege escalation             |
| Capability policies          | High        | Mass privilege escalation        |
| Audit logs                   | Medium      | Cover tracks, compliance failure |
| Field/Action capability maps | Critical    | Bypass field-level security      |

## Threat Categories (OWASP Top 10)

| #   | Threat                          | Risk     | CAPS Mitigation                                             |
| --- | ------------------------------- | -------- | ----------------------------------------------------------- |
| A01 | **Broken Access Control**       | Critical | All APIs check `frappe.has_permission()` + CAPS gate checks |
| A02 | **Cryptographic Failures**      | Medium   | Secrets in `frappe.conf`, no hardcoded credentials          |
| A03 | **Injection (SQL/XSS)**         | High     | Parameterized queries only, `frappe.utils.sanitize_html()`  |
| A04 | **Insecure Design**             | Medium   | Thin controller pattern, service layer, capability checks   |
| A05 | **Security Misconfiguration**   | Medium   | Frappe framework defaults, no debug in production           |
| A06 | **Vulnerable Components**       | Low      | Regular dependency updates, Dependabot                      |
| A07 | **Authentication Failures**     | High     | Frappe session management, rate limiting on login           |
| A08 | **Software Integrity Failures** | Medium   | CI/CD with Semgrep, signed releases                         |
| A09 | **Logging Failures**            | Medium   | CAPS Audit Log with retention policies                      |
| A10 | **SSRF**                        | Low      | No external API calls in core CAPS                          |

## Attack Scenarios & Mitigations

### AS-01: Privilege Escalation via Direct API

**Threat**: Attacker calls `/api/method/caps.api.grant_capability` directly.

**Mitigation**:

```python
@frappe.whitelist()
def grant_capability(user, capability):
    # 1. Permission check FIRST
    frappe.has_permission("User Capability", "create", throw=True)

    # 2. CAPS gate check
    from caps.gate import check_user_capability
    check_user_capability("CAPS_manage_user_capabilities", throw=True)

    # 3. Validate inputs
    if not frappe.db.exists("Capability", capability):
        frappe.throw(_("Invalid capability"))
```

### AS-02: SQL Injection in Capability Name

**Threat**: Attacker puts SQL in capability name field.

**Mitigation**:

```python
# ALWAYS parameterized
frappe.db.sql(
    "SELECT * FROM `tabCapability` WHERE name = %(name)s",
    {"name": user_input}
)

# Frappe ORM is safe by default
frappe.get_all("Capability", filters={"name": user_input})
```

### AS-03: Bypass Field-Level Masking

**Threat**: Attacker retrieves sensitive fields via custom API.

**Mitigation**:

- `doc_events["*"]["on_load"]` hooks apply masking universally
- All whitelisted APIs call `apply_field_masks(doc)` before returning
- Raw DB queries bypass masking → NEVER return raw SQL to frontend

### AS-04: Capability Policy Abuse

**Threat**: Malicious admin creates policy granting all capabilities to attacker.

**Mitigation**:

- Capability policies require CAPS Admin role
- All policy changes logged to CAPS Audit Log
- Daily digest emails to security contacts
- Capability snapshots before/after policy application

### AS-05: Session Impersonation Abuse

**Threat**: CAPS impersonation feature used to access data as another user.

**Mitigation**:

- Impersonation requires `CAPS_impersonate` capability
- All impersonation sessions logged with start/end time
- Visual indicator ("Viewing as X") always visible
- Cannot impersonate users with higher roles

### AS-06: Audit Log Tampering

**Threat**: Attacker deletes audit logs to cover tracks.

**Mitigation**:

- CAPS Audit Log is append-only (no delete permission by default)
- Audit log retention configurable but minimum 1 day
- Critical changes also logged to Frappe Error Log (backup)

## Trust Boundaries

```
┌─────────────────────────────────────────────────┐
│                    INTERNET                      │
└─────────────────────────┬───────────────────────┘
                          │ HTTPS
┌─────────────────────────▼───────────────────────┐
│              Frappe Web Server                   │
│  - Session validation                            │
│  - CSRF protection                               │
│  - Rate limiting                                 │
└─────────────────────────┬───────────────────────┘
                          │
┌─────────────────────────▼───────────────────────┐
│              CAPS Permission Layer               │
│  - Capability resolution                         │
│  - Gate checks                                   │
│  - Field masking                                 │
└─────────────────────────┬───────────────────────┘
                          │
┌─────────────────────────▼───────────────────────┐
│              Business Logic Layer                │
│  - Service functions                             │
│  - Document controllers                          │
└─────────────────────────┬───────────────────────┘
                          │
┌─────────────────────────▼───────────────────────┐
│              Database (MariaDB)                  │
│  - Parameterized queries only                    │
│  - No direct frontend access                     │
└─────────────────────────────────────────────────┘
```

## Data Classification

| Data Type                    | Classification | Handling                                |
| ---------------------------- | -------------- | --------------------------------------- |
| Capability names             | Internal       | May be exposed in UI                    |
| User-capability assignments  | Confidential   | Only visible to user + admins           |
| Permission group memberships | Confidential   | Only visible to group managers + admins |
| Audit logs                   | Restricted     | Admins + auditors only                  |
| Policy configurations        | Restricted     | CAPS Admins only                        |
| Rate limit data              | Internal       | Admins only                             |

## Compliance Considerations

### GDPR (EU)

- User capability data is personal data (relates to identified person)
- Export capability snapshots for data subject requests
- Audit log retention aligns with GDPR retention limits

### SOC 2

- Audit logging satisfies CC6.1 (logical access controls)
- Capability snapshots satisfy CC7.2 (change detection)
- Policy automation supports CC6.3 (provisioning)

### ISO 27001

- A.9.2.3 Management of privileged access rights → CAPS capabilities
- A.9.2.5 Review of user access rights → Capability snapshots
- A.12.4.1 Event logging → CAPS Audit Log

## Security Review Schedule

| Review Type           | Frequency           | Owner         |
| --------------------- | ------------------- | ------------- |
| Code review (Semgrep) | Every PR            | CI/CD         |
| Dependency audit      | Weekly              | Dependabot    |
| Penetration test      | Annually            | External      |
| Access review         | Quarterly           | CAPS Admin    |
| Threat model update   | With major releases | Security Lead |
