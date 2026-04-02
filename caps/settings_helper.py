"""
CAPS — Settings Helper
========================

Central accessor for CAPS Settings (Single DocType).
All settings access goes through get_caps_settings() which caches
in memory for the duration of the request.
"""

import frappe


def get_caps_settings() -> "frappe._dict":
    """
    Return CAPS Settings as a _dict. Cached per-request.

    Defaults are returned if the Single DocType has never been saved,
    so callers never need to handle None.
    """
    if hasattr(frappe.local, "_caps_settings"):
        return frappe.local._caps_settings

    try:
        settings = frappe.get_cached_doc("CAPS Settings")
        result = frappe._dict(
            enable_caps=bool(settings.enable_caps),
            debug_mode=bool(settings.debug_mode),
            cache_ttl=int(settings.cache_ttl or 300),
            field_map_cache_ttl=int(settings.field_map_cache_ttl or 600),
            audit_retention_days=int(settings.audit_retention_days or 90),
            enable_audit_logging=bool(settings.enable_audit_logging),
            admin_bypass=bool(settings.admin_bypass),
            guest_empty_set=bool(settings.guest_empty_set),
            expiry_warning_days=int(settings.expiry_warning_days or 7),
            enable_expiry_notifications=bool(settings.enable_expiry_notifications),
            enable_delegation=bool(settings.enable_delegation),
            require_delegation_reason=bool(settings.require_delegation_reason),
            notify_on_capability_change=bool(settings.notify_on_capability_change),
            email_on_request=bool(settings.email_on_request),
            enable_admin_digest=bool(settings.enable_admin_digest),
            enable_group_hierarchy=bool(settings.enable_group_hierarchy),
        )
    except Exception:
        # Fallback defaults if settings doc doesn't exist or DB is unavailable
        result = frappe._dict(
            enable_caps=True,
            debug_mode=False,
            cache_ttl=300,
            field_map_cache_ttl=600,
            audit_retention_days=90,
            enable_audit_logging=True,
            admin_bypass=True,
            guest_empty_set=True,
            expiry_warning_days=7,
            enable_expiry_notifications=True,
            enable_delegation=True,
            require_delegation_reason=False,
            notify_on_capability_change=True,
            email_on_request=False,
            enable_admin_digest=False,
            enable_group_hierarchy=True,
        )

    frappe.local._caps_settings = result
    return result
