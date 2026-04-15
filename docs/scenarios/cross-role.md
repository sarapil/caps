# Cross-Role Scenarios — سيناريوهات متعددة الأدوار

## Overview

This document describes workflows that involve multiple roles interacting in the CAPS permission system.

---

## CR-001: Capability Request Workflow

### Participants

- **Requester**: Regular user needing additional capability
- **Manager**: CAPS Manager approving/rejecting requests
- **Admin**: System Administrator (escalation)

### Flow

```
1. Requester → Creates Capability Request
   ↓
2. System → Validates request, notifies Manager
   ↓
3. Manager → Reviews request and justification
   ↓
4a. Manager → Approves → System grants capability
4b. Manager → Rejects → System notifies Requester with reason
4c. Manager → Escalates → Admin reviews complex cases
```

### Screens Involved

- [capability-request-form](../screens/capability-request-form.md) — Requester
- [capability-requests](../screens/capability-requests.md) — Manager
- [dashboard](../screens/dashboard.md) — All roles (pending count badge)

---

## CR-002: Delegation with Manager Oversight

### Participants

- **Delegator**: User delegating their capability
- **Delegate**: User receiving delegated capability
- **Manager**: Oversight and audit

### Flow

```
1. Delegator → Creates delegation (capability, delegate, duration, reason)
   ↓
2. System → Validates delegatability, creates time-boxed User Capability
   ↓
3. Delegate → Receives notification, capability now active
   ↓
4. Manager → Sees delegation in audit log
   ↓
5. System → Auto-revokes on expiry date
```

### Screens Involved

- [delegation-form](../screens/delegation-form.md) — Delegator
- [my-capabilities](../screens/my-capabilities.md) — Delegate
- [delegation-review](../screens/delegation-review.md) — Manager

---

## CR-003: Onboarding New Employee

### Participants

- **HR**: Creates employee record
- **IT Admin**: System Administrator
- **Manager**: Department manager

### Flow

```
1. HR → Creates new employee in HRMS
   ↓
2. IT Admin → Creates Frappe user account
   ↓
3. Manager → Submits Capability Request for employee (or Admin assigns directly)
   ↓
4. IT Admin → Adds user to appropriate Permission Groups
   ↓
5. System → Resolves effective capabilities from:
   - Frappe roles → Role Capability Maps
   - Permission groups → Group Capabilities
   - Direct user capabilities
   ↓
6. Employee → Logs in, sees capabilities via "My Capabilities"
```

### Screens Involved

- [permission-group](../screens/permission-group.md) — IT Admin
- [user-capability-form](../screens/user-capability-form.md) — IT Admin / Manager
- [my-capabilities](../screens/my-capabilities.md) — Employee

---

## CR-004: Compliance Audit Process

### Participants

- **Auditor**: External/internal auditor
- **Admin**: System Administrator
- **Manager**: Department managers

### Flow

```
1. Auditor → Requests access review for compliance period
   ↓
2. Admin → Generates Capability Snapshots for all users
   ↓
3. Admin → Exports snapshots to Excel/PDF
   ↓
4. Auditor → Reviews:
   - User access vs. job function
   - Separation of duties violations
   - Terminated users with active access
   - Time-boxed access compliance
   ↓
5. Auditor → Flags anomalies
   ↓
6. Manager → Provides justification or requests revocation
   ↓
7. Admin → Implements required changes
   ↓
8. Auditor → Signs off on compliance
```

### Screens Involved

- [snapshot-export](../screens/snapshot-export.md) — Admin
- [audit-report](../screens/audit-report.md) — Admin / Auditor
- [bulk-revocation](../screens/bulk-revocation.md) — Admin

---

## CR-005: Policy-Based Auto-Provisioning

### Participants

- **Admin**: Configures policies
- **System**: Executes policies automatically
- **Users**: Affected by policy changes

### Flow

```
1. Admin → Creates Capability Policy:
   - Target: Department = "Sales"
   - Grant: Bundle "Sales Operations"
   - Starts On: Hire date
   - Ends On: (optional) probation end
   ↓
2. System → Daily policy engine runs:
   - Identifies matching users
   - Applies/removes capabilities
   - Logs changes to audit
   ↓
3. Users → Receive capabilities automatically
   ↓
4. Admin → Reviews policy effectiveness in dashboard
```

### Screens Involved

- [capability-policy](../screens/capability-policy.md) — Admin
- [dashboard](../screens/dashboard.md) — Admin
- [my-capabilities](../screens/my-capabilities.md) — Users

---

## CR-006: Security Incident Response

### Participants

- **InfoSec**: Security team
- **Admin**: System Administrator
- **Manager**: Department manager

### Flow

```
1. InfoSec → Detects suspicious activity
   ↓
2. InfoSec → Reviews CAPS Audit Log:
   - Filter by user/time/action
   - Identify affected capabilities
   ↓
3. Admin → Emergency revocation:
   - Disable user account
   - Bulk delete all User Capabilities
   - Remove from Permission Groups
   ↓
4. InfoSec → Generates compliance snapshot (pre/post)
   ↓
5. Manager → Notified of team member suspension
   ↓
6. HR/Legal → Follows HR process
   ↓
7. Admin → Restores access if cleared, or terminates
```

### Screens Involved

- [audit-report](../screens/audit-report.md) — InfoSec
- [bulk-revocation](../screens/bulk-revocation.md) — Admin
- [snapshot-export](../screens/snapshot-export.md) — InfoSec
