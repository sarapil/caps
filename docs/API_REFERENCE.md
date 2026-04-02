# CAPS API Reference

Complete reference for all 54+ API endpoints across 9 modules.

**Base URL:** `/api/method/caps.{module}.{function}`

**Authentication:** All endpoints require login unless marked `allow_guest`.

---

## 1. Public API (`caps.api`)

### `check_capability`
Check if the current user has a specific capability.

```
POST /api/method/caps.api.check_capability
Body: { "capability": "field:Lead:phone" }
Response: { "message": true }
```

### `check_capabilities`
Batch check multiple capabilities.

```
POST /api/method/caps.api.check_capabilities
Body: { "capabilities": ["cap1", "cap2"] }
Response: { "message": { "cap1": true, "cap2": false } }
```

### `get_my_capabilities`
Get the current user's full resolved capability set (sorted).

```
GET /api/method/caps.api.get_my_capabilities
Response: { "message": ["cap1", "cap2", "cap3"] }
```

### `get_restrictions`
Get field and action restrictions for a specific DocType.

```
POST /api/method/caps.api.get_restrictions
Body: { "doctype": "Lead" }
Response: {
    "message": {
        "field_restrictions": { "phone": { "behavior": "mask", "mask_pattern": "{last4}" } },
        "action_restrictions": { "approve_discount": { "behavior": "hide" } }
    }
}
```

### `get_prerequisite_graph`
Get the prerequisite dependency graph for visualization.

```
POST /api/method/caps.api.get_prerequisite_graph
Body: { "capability": "cap_name" }
Response: { "message": { "nodes": [...], "edges": [...] } }
```

### `check_prerequisites`
Check if a user satisfies prerequisites for a capability.

```
POST /api/method/caps.api.check_prerequisites
Body: { "capability": "cap_name", "user": "optional@user.com" }
Response: { "message": { "satisfied": true, "missing": [] } }
```

### `get_all_restrictions`
Get all restrictions + map version for client cache optimization.

```
GET /api/method/caps.api.get_all_restrictions
Response: {
    "message": {
        "field_restrictions": { "Lead": {...}, "Customer": {...} },
        "action_restrictions": { "Sales Order": {...} },
        "map_version": 42
    }
}
```

### `bust_cache`
Force-refresh the current user's capability cache.

```
POST /api/method/caps.api.bust_cache
Response: { "message": "ok" }
```

### `get_user_capabilities` *(Admin only)*
Get detailed capability breakdown for any user.

```
POST /api/method/caps.api.get_user_capabilities
Body: { "user": "user@example.com" }
Response: {
    "message": {
        "direct": ["cap1"],
        "from_groups": ["cap2"],
        "from_roles": ["cap3"],
        "effective": ["cap1", "cap2", "cap3"]
    }
}
```

### `compare_users` *(Admin only)*
Set diff between two users' capabilities.

```
POST /api/method/caps.api.compare_users
Body: { "user1": "a@test.com", "user2": "b@test.com" }
Response: {
    "message": {
        "only_user1": ["cap_x"],
        "only_user2": ["cap_y"],
        "common": ["cap_z"]
    }
}
```

### `grant_capability` *(Admin only)*
Grant a capability directly to a user (with prereq check).

```
POST /api/method/caps.api.grant_capability
Body: { "user": "user@example.com", "capability": "cap_name" }
Response: { "message": "ok" }
```

### `revoke_capability` *(Admin only)*
Revoke a directly-granted capability from a user.

```
POST /api/method/caps.api.revoke_capability
Body: { "user": "user@example.com", "capability": "cap_name" }
Response: { "message": "ok" }
```

### `get_capability_tree`
Get capability hierarchy as a nested tree.

```
GET /api/method/caps.api.get_capability_tree
GET /api/method/caps.api.get_capability_tree?root=parent:cap
Response: {
    "message": {
        "nodes": [
            {
                "name": "parent:cap",
                "label": "Parent",
                "children": [
                    { "name": "child:cap", "label": "Child", "children": [] }
                ]
            }
        ]
    }
}
```

---

## 2. Admin API (`caps.api_admin`)

### `bulk_grant`
Grant multiple capabilities to multiple users.

```
POST /api/method/caps.api_admin.bulk_grant
Body: { "users": ["a@t.com", "b@t.com"], "capabilities": ["cap1", "cap2"] }
Response: { "message": { "granted": 4, "skipped": 0 } }
```

### `bulk_revoke`
Revoke multiple capabilities from multiple users.

```
POST /api/method/caps.api_admin.bulk_revoke
Body: { "users": ["a@t.com"], "capabilities": ["cap1"] }
Response: { "message": { "revoked": 1, "skipped": 0 } }
```

### `clone_user_capabilities`
Copy all direct capabilities and bundles from one user to another.

```
POST /api/method/caps.api_admin.clone_user_capabilities
Body: { "source_user": "a@t.com", "target_user": "b@t.com" }
Response: { "message": { "capabilities_cloned": 5, "bundles_cloned": 2 } }
```

### `get_capability_usage_report`
Per-capability user counts.

```
GET /api/method/caps.api_admin.get_capability_usage_report
Response: { "message": [{ "capability": "cap1", "user_count": 15 }, ...] }
```

### `get_effective_capability_matrix`
Effective capability sets for all users.

```
GET /api/method/caps.api_admin.get_effective_capability_matrix
Response: { "message": { "user@t.com": ["cap1", "cap2"], ... } }
```

### `trace_capability_resolution`
Full resolution debug trace for a user.

```
POST /api/method/caps.api_admin.trace_capability_resolution
Body: { "user": "user@example.com" }
Response: {
    "message": {
        "user": "user@example.com",
        "direct_capabilities": [...],
        "direct_bundles": [...],
        "group_capabilities": [...],
        "role_capabilities": [...],
        "hierarchy_expanded": [...],
        "prerequisites_removed": [...],
        "final_set": [...]
    }
}
```

### `explain_capability`
Channel-by-channel breakdown for one capability.

```
POST /api/method/caps.api_admin.explain_capability
Body: { "user": "user@example.com", "capability": "cap_name" }
Response: {
    "message": {
        "has_capability": true,
        "channels": {
            "direct": true,
            "groups": ["Group A"],
            "roles": ["Sales Manager"],
            "hierarchy": "parent:cap"
        }
    }
}
```

---

## 3. Delegation API (`caps.api_delegation`)

### `delegate_capability`
Delegate a capability you hold to another user.

```
POST /api/method/caps.api_delegation.delegate_capability
Body: {
    "target_user": "user@example.com",
    "capability": "cap_name",
    "reason": "Covering for vacation"
}
Response: { "message": "ok" }
```

**Rules:** Capability must be `is_delegatable`, delegator must hold it, delegation must be enabled in settings.

### `revoke_delegation`
Revoke a delegation you previously made.

```
POST /api/method/caps.api_delegation.revoke_delegation
Body: { "target_user": "user@example.com", "capability": "cap_name" }
Response: { "message": "ok" }
```

### `get_delegatable_capabilities`
List capabilities the current user can delegate.

```
GET /api/method/caps.api_delegation.get_delegatable_capabilities
Response: { "message": ["cap1", "cap2"] }
```

### `get_my_delegations`
List capabilities the current user has delegated to others.

```
GET /api/method/caps.api_delegation.get_my_delegations
Response: { "message": [{ "capability": "cap1", "target_user": "a@t.com" }] }
```

---

## 4. Policy API (`caps.api_policies`)

### `preview_policy`
Preview which users/capabilities a policy would affect.

```
POST /api/method/caps.api_policies.preview_policy
Body: { "policy": "Policy Name" }
Response: { "message": { "users": [...], "capabilities": [...] } }
```

### `apply_policy`
Manually apply a single policy.

```
POST /api/method/caps.api_policies.apply_policy
Body: { "policy": "Policy Name" }
```

### `apply_all_policies`
Apply all active policies.

```
POST /api/method/caps.api_policies.apply_all_policies
```

### `expire_policies`
Process all expired policies (revoke grants, deactivate).

```
POST /api/method/caps.api_policies.expire_policies
```

### `get_policy_status`
Detailed policy status with affected user counts.

```
POST /api/method/caps.api_policies.get_policy_status
Body: { "policy": "Policy Name" }
```

### `get_active_policies`
List all currently active policies.

```
GET /api/method/caps.api_policies.get_active_policies
```

---

## 5. Request API (`caps.api_requests`)

### `submit_request`
Submit a capability request (self-service).

```
POST /api/method/caps.api_requests.submit_request
Body: {
    "capability": "cap_name",
    "reason": "I need this for my new role",
    "priority": "High"
}
```

### `approve_request`
Approve a request (auto-grants the capability).

```
POST /api/method/caps.api_requests.approve_request
Body: { "request": "CAPS-REQ-2026-00001", "notes": "Approved per manager" }
```

### `reject_request`
Reject a request.

```
POST /api/method/caps.api_requests.reject_request
Body: { "request": "CAPS-REQ-2026-00001", "notes": "Not needed for your role" }
```

### `cancel_request`
Cancel own pending request.

```
POST /api/method/caps.api_requests.cancel_request
Body: { "request": "CAPS-REQ-2026-00001" }
```

### `get_my_requests`
Get current user's requests.

```
GET /api/method/caps.api_requests.get_my_requests
```

### `get_pending_requests`
Get all pending requests (for approvers).

```
GET /api/method/caps.api_requests.get_pending_requests
```

---

## 6. Snapshot API (`caps.api_snapshots`)

### `take_snapshot`
Capture a user's current capability state.

```
POST /api/method/caps.api_snapshots.take_snapshot
Body: { "user": "user@example.com", "label": "Before role change" }
```

### `compare_snapshots`
Diff two snapshots.

```
POST /api/method/caps.api_snapshots.compare_snapshots
Body: { "snapshot1": "hash1", "snapshot2": "hash2" }
Response: { "message": { "added": [...], "removed": [...], "unchanged": [...] } }
```

### `compare_with_current`
Diff a snapshot against current live state.

```
POST /api/method/caps.api_snapshots.compare_with_current
Body: { "snapshot": "hash1" }
```

### `get_snapshot_history`
List a user's snapshots.

```
POST /api/method/caps.api_snapshots.get_snapshot_history
Body: { "user": "user@example.com" }
```

### `restore_snapshot`
Restore a user's capabilities to a snapshot state.

```
POST /api/method/caps.api_snapshots.restore_snapshot
Body: { "snapshot": "hash1" }
```

---

## 7. Impersonation API (`caps.api_impersonation`)

### `start_impersonation`
Start viewing as another user (30-min auto-expiry).

```
POST /api/method/caps.api_impersonation.start_impersonation
Body: { "target_user": "user@example.com" }
```

**Rules:** Admin/CAPS Admin only. Cannot impersonate self. No double impersonation.

### `stop_impersonation`
End impersonation mode.

```
POST /api/method/caps.api_impersonation.stop_impersonation
```

### `get_impersonation_status`
Check if impersonation is active.

```
GET /api/method/caps.api_impersonation.get_impersonation_status
Response: {
    "message": {
        "active": true,
        "target_user": "user@example.com",
        "started_at": "2026-03-14 12:00:00"
    }
}
```

---

## 8. Import/Export API (`caps.api_transfer`)

### `export_config`
Export full CAPS configuration as JSON.

```
POST /api/method/caps.api_transfer.export_config
Body: {
    "include_capabilities": true,
    "include_bundles": true,
    "include_role_maps": true,
    "include_field_maps": true,
    "include_action_maps": true,
    "include_policies": true,
    "include_groups": true
}
Response: { "message": { "version": "1.0", "exported_at": "...", "capabilities": [...], ... } }
```

### `import_config`
Import CAPS configuration (merge or overwrite).

```
POST /api/method/caps.api_transfer.import_config
Body: {
    "config": { ... },  // Exported JSON
    "mode": "merge"      // or "overwrite"
}
```

### `validate_import`
Dry-run validation without applying changes.

```
POST /api/method/caps.api_transfer.validate_import
Body: { "config": { ... } }
Response: { "message": { "valid": true, "warnings": [], "errors": [] } }
```

---

## 9. Dashboard API (`caps.api_dashboard`)

### `get_dashboard_stats`
Summary numbers for the admin dashboard.

```
GET /api/method/caps.api_dashboard.get_dashboard_stats
Response: {
    "message": {
        "total_capabilities": 80,
        "active_capabilities": 75,
        "total_bundles": 5,
        "users_with_capabilities": 25,
        "total_groups": 3,
        "active_policies": 2,
        "pending_requests": 4,
        "audit_logs_24h": 156,
        "expiring_soon": 3,
        "total_delegations": 8
    }
}
```

### `get_capability_distribution`
Top 20 capabilities by user count.

```
GET /api/method/caps.api_dashboard.get_capability_distribution
```

### `get_audit_timeline`
Audit activity grouped by day.

```
GET /api/method/caps.api_dashboard.get_audit_timeline
```

### `get_expiry_forecast`
Upcoming expiries grouped by day.

```
GET /api/method/caps.api_dashboard.get_expiry_forecast
```

### `get_request_summary`
Request counts by status.

```
GET /api/method/caps.api_dashboard.get_request_summary
```

### `get_delegation_summary`
Top delegators and most-delegated capabilities.

```
GET /api/method/caps.api_dashboard.get_delegation_summary
```

### `get_policy_summary`
Policy counts by type.

```
GET /api/method/caps.api_dashboard.get_policy_summary
```

---

## Error Codes

| Error | When |
|-------|------|
| `frappe.PermissionError` | User lacks required capability |
| `frappe.ValidationError` | Invalid input (bad capability name, circular dep, etc.) |
| `frappe.DoesNotExistError` | Referenced capability/user/policy not found |
| `frappe.DuplicateEntryError` | Duplicate grant/delegation/request |
