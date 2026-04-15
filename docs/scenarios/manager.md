# Manager — Usage Scenarios

# سيناريوهات المدير التنفيذي

## Role Overview

- **Title**: CAPS Manager / مدير CAPS
- **CAPS Capabilities**: `CAPS_manage_groups`, `CAPS_assign_capabilities`, `CAPS_view_audit`
- **Primary DocTypes**: Permission Group, User Capability, Capability Request
- **Device**: Desktop / Tablet

## Daily Scenarios (يومي)

### DS-001: Review Pending Capability Requests

- **Goal**: Process user requests for additional capabilities
- **Pre-conditions**: User submitted capability request, Manager has CAPS_Manager role
- **Steps**:
  1. Navigate to `/desk/caps-admin`
  2. Check "PENDING REQUESTS" badge on dashboard
  3. Click to open Capability Request list
  4. Review request details (user, capability, reason)
  5. Either Approve or Reject with resolution note
- **Screen**: [capability-requests](../screens/capability-requests.md)
- **Breakpoints**: Desktop ✅ / Tablet ✅ / Mobile ⚠️ (limited)
- **Error scenarios**: Approving capability user already has → warning shown

### DS-002: Assign Capability to User

- **Goal**: Grant specific capability to a team member
- **Pre-conditions**: Target user exists, Capability is active
- **Steps**:
  1. Navigate to `User Capability` list
  2. Click "Add User Capability"
  3. Select user and capability
  4. Optionally set expiry date for time-boxed access
  5. Save
- **Screen**: [user-capability-form](../screens/user-capability-form.md)
- **Breakpoints**: Desktop ✅ / Tablet ✅ / Mobile ✅
- **Error scenarios**: Capability prerequisite not met → validation error

### DS-003: Monitor Group Memberships

- **Goal**: Ensure correct users are in permission groups
- **Pre-conditions**: Permission groups configured
- **Steps**:
  1. Navigate to `/desk/caps-admin`
  2. Open "Permission Groups" section
  3. Select a group to view members
  4. Add/remove members as needed
  5. Review effective capabilities inherited
- **Screen**: [permission-group](../screens/permission-group.md)
- **Breakpoints**: Desktop ✅ / Tablet ✅ / Mobile ⚠️

## Weekly Scenarios (أسبوعي)

### WS-001: Review Capability Usage Reports

- **Goal**: Identify unused or underutilized capabilities
- **Pre-conditions**: Audit logs enabled in CAPS Settings
- **Steps**:
  1. Navigate to `CAPS Audit Log` report
  2. Filter by date range (last 7 days)
  3. Review capability usage patterns
  4. Identify capabilities with zero usage
  5. Consider revocation for unused grants
- **Screen**: [audit-report](../screens/audit-report.md)
- **Breakpoints**: Desktop ✅

### WS-002: Manage Capability Bundles

- **Goal**: Create/update bundles for departmental roles
- **Pre-conditions**: Base capabilities defined
- **Steps**:
  1. Navigate to `Capability Bundle` list
  2. Create new bundle or edit existing
  3. Add relevant capabilities to bundle
  4. Set bundle description and labels
  5. Assign to users/groups
- **Screen**: [capability-bundle](../screens/capability-bundle.md)
- **Breakpoints**: Desktop ✅ / Tablet ✅

## Monthly Scenarios (شهري)

### MS-001: Access Review Compliance

- **Goal**: Ensure all user capabilities are justified
- **Pre-conditions**: Compliance requirement, audit snapshots enabled
- **Steps**:
  1. Generate `Capability Snapshot` for all users
  2. Export to Excel for offline review
  3. Compare with HR organizational chart
  4. Flag any anomalies (terminated users with access)
  5. Document findings in compliance report
- **Screen**: [snapshot-export](../screens/snapshot-export.md)
- **Breakpoints**: Desktop ✅

### MS-002: Review Delegations

- **Goal**: Audit temporary delegations made by users
- **Pre-conditions**: Delegation enabled in CAPS Settings
- **Steps**:
  1. Filter User Capabilities where `Delegated By` is not empty
  2. Review delegation reasons
  3. Check expiry dates
  4. Revoke expired or unjustified delegations
- **Screen**: [delegation-review](../screens/delegation-review.md)
- **Breakpoints**: Desktop ✅

## Exception Scenarios (استثنائي)

### ES-001: Emergency Access Grant

- **Goal**: Grant temporary elevated access for critical task
- **Pre-conditions**: Business emergency, manager approval
- **Steps**:
  1. Create User Capability with specific capability
  2. Set short expiry (e.g., 4 hours)
  3. Add audit note explaining emergency
  4. Notify user of temporary access
  5. Monitor CAPS Audit Log during access period
- **Screen**: [user-capability-form](../screens/user-capability-form.md)
- **Breakpoints**: Desktop ✅ / Tablet ✅ / Mobile ✅

### ES-002: Bulk Capability Revocation

- **Goal**: Revoke all capabilities from user (termination/investigation)
- **Pre-conditions**: HR notification, legal/compliance approval
- **Steps**:
  1. Open User Capability list filtered by target user
  2. Select all capabilities
  3. Use bulk action to delete
  4. Remove from all Permission Groups
  5. Generate snapshot for compliance record
- **Screen**: [bulk-revocation](../screens/bulk-revocation.md)
- **Breakpoints**: Desktop ✅
