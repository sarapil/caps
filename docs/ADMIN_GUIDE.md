# CAPS Administrator Guide

Complete guide for system administrators to set up, configure, and manage CAPS.

---

## Table of Contents

1. [Installation](#installation)
2. [Initial Configuration](#initial-configuration)
3. [Managing Capabilities](#managing-capabilities)
4. [User Assignment](#user-assignment)
5. [Field & Action Restrictions](#field--action-restrictions)
6. [Permission Groups](#permission-groups)
7. [Capability Policies](#capability-policies)
8. [Managing Requests](#managing-requests)
9. [Delegation](#delegation)
10. [Import/Export](#importexport)
11. [Monitoring & Audit](#monitoring--audit)
12. [Troubleshooting](#troubleshooting)

---

## Installation

```bash
bench get-app caps
bench --site your-site install-app caps
bench --site your-site migrate
```

This creates:
- Two roles: **CAPS Admin** (full management) and **CAPS Manager** (delegation + requests)
- All DocTypes: Capabilities, Bundles, Groups, Maps, Policies, etc.
- CAPS Settings with sensible defaults
- CAPS Workspace in the Frappe sidebar

---

## Initial Configuration

Navigate to **CAPS Settings** (`/app/caps-settings`):

| Setting | Default | Description |
|---------|---------|-------------|
| **Enable CAPS** | ✅ On | Global kill-switch. When off, ALL capabilities are granted to everyone |
| **Debug Mode** | ❌ Off | Logs resolution details to Error Log (performance impact) |
| **Cache TTL** | 300s | How long user capabilities are cached in Redis |
| **Field Map Cache TTL** | 600s | How long field/action maps are cached |
| **Audit Retention Days** | 90 | Days to keep audit logs before auto-cleanup |
| **Enable Audit Logging** | ✅ On | Toggle audit trail |
| **Admin Bypass** | ✅ On | Administrator gets all capabilities automatically |
| **Guest Empty Set** | ✅ On | Guest user gets no capabilities |
| **Expiry Warning Days** | 7 | Days before expiry to send notifications |
| **Enable Expiry Notifications** | ✅ On | Toggle expiry alerts |
| **Enable Delegation** | ✅ On | Allow CAPS Managers to delegate capabilities |
| **Require Delegation Reason** | ❌ Off | Force a reason when delegating |

### Recommended Production Settings

```
Enable CAPS: ✅
Debug Mode: ❌ (only enable for troubleshooting)
Cache TTL: 300 (5 minutes)
Field Map Cache TTL: 600 (10 minutes)
Audit Retention Days: 365 (1 year for compliance)
Admin Bypass: ✅ (Administrator always has full access)
```

---

## Managing Capabilities

### Creating Capabilities

Go to **Capability** → New:

1. **Capability Name**: Format `{category}:{scope}:{detail}` — e.g., `field:Lead:phone`
2. **Label**: Human-readable name — e.g., "View Lead Phone Number"
3. **Category**: Field, Action, Workflow, Report, API, Module, or Custom
4. **Scope DocType**: (Optional) The DocType this capability applies to
5. **Scope Field/Action**: (Optional) The specific field or action
6. **Parent Capability**: (Optional) Makes this a child of another capability
7. **Is Active**: Must be checked for the capability to work
8. **Is Delegatable**: Check to allow delegation by managers

### Capability Bundles

Bundles group capabilities by job function. Go to **Capability Bundle** → New:

1. **Label**: e.g., "Sales Agent Bundle"
2. **Capabilities**: Add all capabilities for this role
3. **Is Template**: Mark as template if it's a standard bundle

### Capability Hierarchy

Parent capabilities automatically grant all their children:

```
crm:all (Parent)
├── crm:read (Child — auto-granted when parent is held)
├── crm:write (Child)
└── crm:admin (Child)
    ├── crm:admin:users (Grandchild — also auto-granted)
    └── crm:admin:settings (Grandchild)
```

Set the **Parent Capability** field on child capabilities.

---

## User Assignment

### Direct Assignment

Go to **User Capability** → New (or find existing by user email):

- **Direct Capabilities**: Add individual capabilities with optional expiry dates
- **Direct Bundles**: Add capability bundles with optional expiry dates

### Role-Based Assignment

Go to **Role Capability Map** → New:

1. Select a **Frappe Role** (e.g., "Sales Agent")
2. Add **Role Capabilities**: Individual capabilities
3. Add **Role Bundles**: Capability bundles

All users with that Frappe role automatically get these capabilities.

### Group-Based Assignment

Go to **Permission Group** → New:

1. **Group Name**: e.g., "MENA Sales Team"
2. **Sync Type**:
   - **Manual**: Add members manually
   - **Department Sync**: Auto-sync from Frappe Department
   - **Branch Sync**: Auto-sync from Branch
   - **Custom Query**: Use a Python expression to resolve members
3. **Members**: Add users (for Manual type)
4. **Group Capabilities**: Shared capabilities
5. **Group Bundles**: Shared bundles

---

## Field & Action Restrictions

### Field Capability Map

Restricts access to specific fields on any DocType. Go to **Field Capability Map** → New:

| Field | Description |
|-------|-------------|
| **DocType Name** | Target DocType (e.g., Lead, Customer) |
| **Fieldname** | Target field (e.g., phone, email_id, tax_id) |
| **Capability** | Required capability to see/edit this field |
| **Behavior** | What happens when user LACKS the capability: `hide`, `read_only`, `mask`, `custom` |
| **Mask Pattern** | For `mask` behavior: `{last4}`, `{first3}`, `***` |
| **Priority** | Higher number wins if multiple maps for same field |

**Example**: To mask phone numbers for junior agents:
- DocType Name: Lead
- Fieldname: phone
- Capability: `field:Lead:phone`
- Behavior: mask
- Mask Pattern: `{last4}` → Shows `●●●●●1234`

### Action Capability Map

Restricts access to buttons and actions. Go to **Action Capability Map** → New:

| Field | Description |
|-------|-------------|
| **DocType Name** | Target DocType |
| **Action ID** | Button/action label text |
| **Action Type** | button, menu_item, workflow_action, print_format |
| **Capability** | Required capability |
| **Behavior** | hide or disable |

---

## Permission Groups

### Manual Groups

1. Create group → Add members manually
2. Assign capabilities and bundles to the group
3. All members get the group's capabilities

### Auto-Sync Groups

**Department Sync:**
1. Set Sync Type = "Department Sync"
2. Set Sync Source = Department name (e.g., "Sales")
3. Set Sync Frequency = Realtime/Hourly/Daily
4. All employees in that department are auto-synced as members

**Custom Query Sync:**
1. Set Sync Type = "Custom Query"
2. Write Python expression in Custom Query field
3. Expression should return a list of user emails

### Group Hierarchy

Groups can have a **Parent Group**. Child group members inherit parent group capabilities.

### Group Management Delegation

- **Managed By**: Assign a user as group manager
- **Can Manager Add Members**: Allow manager to add users
- **Can Manager Assign Bundles**: Allow manager to assign bundles

---

## Capability Policies

Policies are **time-bound rules** that auto-apply capabilities. Go to **Capability Policy** → New:

| Field | Description |
|-------|-------------|
| **Policy Name** | e.g., "Holiday Season Discount Access" |
| **Is Active** | Toggle policy on/off |
| **Scope Type** | Role, Department, or User List |
| **Scope Role/Department** | Target scope |
| **Target Users** | Comma-separated emails (for User List) |
| **Grant Type** | Capability or Bundle |
| **Target Capability/Bundle** | What to grant |
| **Valid From** | Start date/time |
| **Valid To** | End date/time (optional for permanent) |

### Policy Lifecycle

1. **Create** → Define scope, target, and schedule
2. **Apply** → Run manually or wait for scheduler (hourly)
3. **Active** → Capabilities granted to target users
4. **Expire** → Capabilities auto-revoked, policy deactivated

### Admin Actions

- **Preview Policy**: See which users/capabilities would be affected
- **Apply All Policies**: Force-apply all active policies now
- **Expire Policies**: Force-expire all past-due policies now

---

## Managing Requests

### Self-Service Flow

1. **User submits** a Capability Request with reason and priority
2. **CAPS Manager/Admin sees** it in Pending Requests
3. **Approve** → Capability auto-granted to user + notification sent
4. **Reject** → Rejection notes sent to user

### Request Statuses

| Status | Meaning |
|--------|---------|
| Pending | Awaiting approval |
| Approved | Approved and capability granted |
| Rejected | Rejected by manager |
| Cancelled | Cancelled by requester |

---

## Delegation

When enabled, CAPS Managers can delegate their own capabilities to other users.

### Rules
- The capability must have `is_delegatable` checked
- The delegator must currently hold the capability
- Delegation must be enabled in CAPS Settings
- Optional: require delegation reason

### Managing Delegations

Delegators can view and revoke their own delegations via the API or admin dashboard.

---

## Import/Export

### Export Configuration

From the **CAPS Admin** page → Quick Actions → Export Config:
- Select what to include (capabilities, bundles, maps, policies, groups)
- Downloads a JSON file with full configuration

### Import Configuration

From the **CAPS Admin** page → Quick Actions → Import Config:
- Upload JSON file
- Choose mode:
  - **Merge**: Add new items, skip existing
  - **Overwrite**: Replace all existing items
- **Validate first**: Dry-run to check for errors

### Use Cases
- Migrate CAPS config between sites
- Version control CAPS configuration
- Backup before major changes

---

## Monitoring & Audit

### Admin Dashboard

Navigate to **CAPS Admin** page (`/app/caps-admin`) for:

- **Stats Cards**: Total capabilities, bundles, users, audit logs (24h), pending requests, active policies
- **User Lookup**: Search any user to see their full capability breakdown
- **Active Policies**: Current policy status
- **Recent Audit Log**: Latest actions
- **Expiring Soon**: Capabilities about to expire

### CAPS Audit Log

16 event types are tracked:

| Event | Description |
|-------|-------------|
| `capability_check` | User's capability was checked |
| `capability_granted` | Capability granted to user |
| `capability_revoked` | Capability revoked from user |
| `delegation_granted` | Capability delegated to user |
| `delegation_revoked` | Delegation revoked |
| `request_submitted` | User submitted a request |
| `request_approved` | Request approved |
| `request_rejected` | Request rejected |
| `policy_applied` | Policy applied capabilities |
| `policy_expired` | Policy expired and revoked |
| `group_join` | User joined a group |
| `group_leave` | User left a group |
| `bundle_assigned` | Bundle assigned to user |
| `bundle_revoked` | Bundle revoked from user |
| `impersonation_start` | Admin started "View As" mode |
| `impersonation_end` | Admin ended impersonation |

### Impersonation (Debug Mode)

Admins can "View As" another user to debug their capability set:

1. Go to CAPS Admin → Impersonation
2. Enter the user's email
3. Start Impersonation → Orange banner appears
4. Navigate the system as that user would see it
5. Click "Stop" to end

Auto-expires after 30 minutes. Fully audited.

---

## Troubleshooting

### User Can't See a Field They Should See

1. Check if CAPS is enabled: `CAPS Settings → Enable CAPS`
2. Check if the capability exists and is active: `Capability → is_active`
3. Check the Field Capability Map exists for that field
4. Check if the user has the capability:
   ```
   CAPS Admin → User Lookup → enter email → check effective caps
   ```
5. Use Impersonation to see what the user sees
6. Bust cache: `CAPS Admin → Bust Cache` or user can press Ctrl+Shift+R

### Capabilities Not Updating After Change

1. **Cache TTL**: Changes take up to `cache_ttl` seconds (default 300s)
2. **Force refresh**: User can call `frappe.caps.refreshCapabilities()` in console
3. **Admin bust**: Use `bust_cache` API or admin dashboard button
4. **Check invalidation**: Ensure the changed DocType has doc_events in hooks.py

### Performance Issues

1. **Reduce cache TTL** only if needed (default is good for most cases)
2. **Disable debug mode** in production
3. **Check audit log size**: Reduce retention days if table is huge
4. **Monitor Redis**: `redis-cli INFO memory`

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| "CAPS is not enabled" | `enable_caps` is off | Enable in CAPS Settings |
| "Capability not found" | Referencing non-existent cap | Check capability name spelling |
| "Circular dependency" | Prerequisite creates a loop | Review prerequisite chain |
| "You do not have permission to modify field" | Writing to restricted field | User needs the capability or admin bypass |
