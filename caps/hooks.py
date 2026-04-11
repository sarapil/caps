# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

app_name = "caps"
app_title = "CAPS"
app_publisher = "Arkan Labs"
app_description = "Capability-Based Access Control System for Frappe"
app_email = "dev@arkanlabs.com"
app_license = "MIT"
app_version = "1.0.0"

required_apps = ["frappe", "frappe_visual", "arkan_help"]

# ---------------------------------------------------------------------------
# App Icon / Logo / Desktop
# ---------------------------------------------------------------------------
app_icon = "/assets/caps/images/caps-icon-animated.svg"
app_logo_url = "/assets/caps/images/caps-logo-animated.svg"
app_color = "#10B981"
app_home = "/desk/caps-admin"

add_to_apps_screen = [
    {
        "name": "caps",
        "logo": "/assets/caps/images/caps-icon-animated.svg",
        "title": "CAPS",
        "route": "/desk/caps-admin",
    }
]

# ---------------------------------------------------------------------------
# Frontend Includes
# ---------------------------------------------------------------------------
# MEGA: app_include_js = ["/assets/caps/js/caps_combined.js"]

# MEGA: app_include_css = ["/assets/caps/css/caps_combined.css"]

# ---------------------------------------------------------------------------
# After Install / Before Uninstall
# ---------------------------------------------------------------------------
after_install = "caps.install.after_install"

after_migrate = ["caps.seed.seed_data"]
before_uninstall = "caps.install.before_uninstall"

# ---------------------------------------------------------------------------
# Boot Session — inject user capabilities into session
# ---------------------------------------------------------------------------
boot_session = "caps.boot.boot_session"

# ---------------------------------------------------------------------------
# Notification Configuration — badge counts for navbar bell icon
# ---------------------------------------------------------------------------
get_notification_config = "caps.notifications.get_notification_config"

# ---------------------------------------------------------------------------
# Session / Login Hooks
# ---------------------------------------------------------------------------
on_session_creation = "caps.hooks_integration.on_login_audit"

# ---------------------------------------------------------------------------
# Document Events — cache invalidation + auto-enforcement
# ---------------------------------------------------------------------------
doc_events = {
    "*": {
        "on_load": "caps.hooks_integration.auto_filter_fields",
        "before_save": "caps.hooks_integration.auto_validate_writes",
    },
    "Capability": {
        "on_update": "caps.cache_invalidation.on_capability_change",
    },
    "User Capability": {
        "on_update": "caps.cache_invalidation.on_user_capability_change",
        "after_insert": "caps.cache_invalidation.on_user_capability_change",
        "on_trash": "caps.cache_invalidation.on_user_capability_change",
    },
    "Permission Group": {
        "on_update": "caps.cache_invalidation.on_permission_group_change",
        "after_insert": "caps.cache_invalidation.on_permission_group_change",
        "on_trash": "caps.cache_invalidation.on_permission_group_change",
    },
    "Capability Bundle": {
        "on_update": "caps.cache_invalidation.on_bundle_change",
        "after_insert": "caps.cache_invalidation.on_bundle_change",
        "on_trash": "caps.cache_invalidation.on_bundle_change",
    },
    "Role Capability Map": {
        "on_update": "caps.cache_invalidation.on_role_map_change",
        "after_insert": "caps.cache_invalidation.on_role_map_change",
        "on_trash": "caps.cache_invalidation.on_role_map_change",
    },
    "Field Capability Map": {
        "on_update": "caps.cache_invalidation.on_field_map_change",
        "on_trash": "caps.cache_invalidation.on_field_map_change",
    },
    "Action Capability Map": {
        "on_update": "caps.cache_invalidation.on_action_map_change",
        "on_trash": "caps.cache_invalidation.on_action_map_change",
    },
    "Capability Policy": {
        "on_update": "caps.cache_invalidation.on_capability_change",
        "on_trash": "caps.cache_invalidation.on_capability_change",
    },
    "Capability Rate Limit": {
        "on_update": "caps.cache_invalidation.on_rate_limit_change",
        "after_insert": "caps.cache_invalidation.on_rate_limit_change",
        "on_trash": "caps.cache_invalidation.on_rate_limit_change",
    },
}

# ---------------------------------------------------------------------------
# Scheduled Tasks — expire time-boxed capabilities
# ---------------------------------------------------------------------------
scheduler_events = {
    "hourly": [
        "caps.tasks.expire_timeboxed_capabilities",
        "caps.tasks.expire_temp_group_memberships",
    ],
    "daily": [
        "caps.tasks.sync_permission_groups",
        "caps.tasks.cleanup_audit_logs",
        "caps.tasks.warn_expiring_capabilities",
        "caps.policy_engine.apply_policies",
        "caps.policy_engine.expire_policies",
        "caps.tasks.warm_caches",
    ],
    "weekly": [
        "caps.tasks.weekly_admin_digest",
    ],
}

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
fixtures = [
    {
        "dt": "Role",
        "filters": [["name", "in", ["CAPS Admin", "CAPS Manager"]]],
    },
    {
        "dt": "Workspace",
        "filters": [["module", "=", "CAPS"]],
    },
    {
        "dt": "Desktop Icon",
        "filters": [["app", "=", "caps"]],
    },
]

# ---------------------------------------------------------------------------
# CAPS Capabilities Declaration (for self-referencing)
# ---------------------------------------------------------------------------
caps_capabilities = [
    {"name": "CAPS_view_dashboard", "category": "Module", "description": "Access the CAPS Admin dashboard"},
    {"name": "CAPS_view_graph", "category": "Module", "description": "Access the Capability Graph explorer"},
    {"name": "CAPS_compare_users", "category": "Module", "description": "Access the User Comparison tool"},
    {"name": "CAPS_manage_capabilities", "category": "Action", "description": "Create, edit, delete Capabilities"},
    {"name": "CAPS_manage_bundles", "category": "Action", "description": "Create, edit, delete Capability Bundles"},
    {"name": "CAPS_manage_role_maps", "category": "Action", "description": "Create, edit, delete Role Capability Maps"},
    {"name": "CAPS_assign_capabilities", "category": "Action", "description": "Assign capabilities to users"},
    {"name": "CAPS_manage_groups", "category": "Action", "description": "Create and manage Permission Groups"},
    {"name": "CAPS_configure_field_maps", "category": "Field", "description": "Configure field-level restrictions"},
    {"name": "CAPS_configure_action_maps", "category": "Field", "description": "Configure action-level restrictions"},
    {"name": "CAPS_manage_policies", "category": "Action", "description": "Create and manage Capability Policies"},
    {"name": "CAPS_approve_requests", "category": "Action", "description": "Approve or reject Capability Requests"},
    {"name": "CAPS_view_audit_logs", "category": "Report", "description": "View CAPS Audit Log entries"},
    {"name": "CAPS_view_reports", "category": "Report", "description": "Access Coverage, Matrix, and Audit reports"},
    {"name": "CAPS_export_reports", "category": "Report", "description": "Export CAPS reports to CSV/PDF"},
    {"name": "CAPS_configure_settings", "category": "Action", "description": "Modify CAPS Settings"},
    {"name": "CAPS_manage_rate_limits", "category": "Action", "description": "Configure Capability Rate Limits"},
    {"name": "CAPS_manage_integrations", "category": "Action", "description": "Configure CAPS Integration Packs"},
    {"name": "CAPS_take_snapshots", "category": "Action", "description": "Create Capability Snapshots"},
    {"name": "CAPS_manage_site_profile", "category": "Action", "description": "Configure CAPS Site Profile"},
]

# ---------------------------------------------------------------------------
# CAPS Field Maps — field-level capability restrictions
# ---------------------------------------------------------------------------
caps_field_maps = [
    {"capability": "CAPS_view_audit_logs", "doctype": "CAPS Audit Log", "field": "*", "behavior": "hide"},
    {"capability": "CAPS_configure_settings", "doctype": "CAPS Settings", "field": "*", "behavior": "read_only"},
    {"capability": "CAPS_manage_rate_limits", "doctype": "Capability Rate Limit", "field": "*", "behavior": "read_only"},
    {"capability": "CAPS_manage_integrations", "doctype": "CAPS Integration Pack", "field": "*", "behavior": "read_only"},
    {"capability": "CAPS_manage_site_profile", "doctype": "CAPS Site Profile", "field": "*", "behavior": "read_only"},
]

# Website Route Rules
# --------------------------------------------------------
website_route_rules = [
    {"from_route": "/caps-about", "to_route": "caps_about"},
    {"from_route": "/caps-onboarding", "to_route": "caps_onboarding"},
    {"from_route": "/عن-caps", "to_route": "caps_about"},
    {"from_route": "/caps/<path:app_path>", "to_route": "caps/<app_path>"},
]
