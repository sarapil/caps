// Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
// Developer Website: https://arkan.it.com
// License: MIT
// For license information, please see license.txt

/**
 * CAPS Contextual Help — adds ❓ help button to all CAPS DocType forms,
 * reports, and settings pages. Opens help in frappe.visual.floatingWindow()
 * on the opposite side of the sidebar.
 */
(function () {
    "use strict";

    const BRAND = "#10B981";

    // ── DocType → help config mapping ──
    const HELP_MAP = {
        "Capability": {
            title: __("Capability Help"),
            content: __("A Capability represents a single atomic permission — e.g. 'View Cost Data' or 'Approve Invoice'. Capabilities are the building blocks of CAPS access control. They can be assigned directly to users, grouped into bundles, or mapped to Frappe roles."),
        },
        "Capability Bundle": {
            title: __("Capability Bundle Help"),
            content: __("Bundles group related capabilities together for easier assignment. For example, a 'Finance Viewer' bundle might include 'View Invoices', 'View Payments', and 'View Cost Data'. Assign a bundle instead of individual capabilities."),
        },
        "Role Capability Map": {
            title: __("Role Capability Map Help"),
            content: __("Maps Frappe roles to CAPS capabilities. When a user has a specific Frappe role, they automatically receive the mapped capabilities. This bridges traditional role-based access with capability-based control."),
        },
        "User Capability": {
            title: __("User Capability Help"),
            content: __("Direct capability assignment to a specific user. You can set start/end dates for time-boxed access, mark capabilities as delegatable, and track the assignment source (manual, role-map, or policy)."),
        },
        "Permission Group": {
            title: __("Permission Group Help"),
            content: __("Permission Groups are collections of users who share the same set of capabilities. Add members to a group and assign capabilities to the group — all members inherit them. Supports temporary membership with expiry dates."),
        },
        "Field Capability Map": {
            title: __("Field Capability Map Help"),
            content: __("Controls which fields are visible or editable based on capabilities. Map a capability to a specific DocType field with behavior: 'hide' (remove field), 'mask' (show ***), or 'read_only' (disable editing)."),
        },
        "Action Capability Map": {
            title: __("Action Capability Map Help"),
            content: __("Controls which actions (buttons, workflows, submissions) are available based on capabilities. Map a capability to a specific DocType action to enable/disable it per user."),
        },
        "Capability Policy": {
            title: __("Capability Policy Help"),
            content: __("Policies define conditional rules for capability evaluation. A policy can grant or revoke capabilities based on conditions like time of day, IP range, department, or custom expressions. Policies are evaluated daily and on-demand."),
        },
        "Capability Request": {
            title: __("Capability Request Help"),
            content: __("Users can request additional capabilities through this DocType. Requests go through an approval workflow — managers review and approve/reject. Approved requests create User Capability records automatically."),
        },
        "Capability Snapshot": {
            title: __("Capability Snapshot Help"),
            content: __("Point-in-time snapshots of a user's complete capability set. Used for compliance audits, historical reviews, and before/after comparisons when capability changes are made."),
        },
        "CAPS Site Profile": {
            title: __("CAPS Site Profile Help"),
            content: __("Stores site-wide CAPS configuration including default policies, enforcement mode (strict/permissive), and capability inheritance rules. Each Frappe site can have its own profile."),
        },
        "CAPS Integration Pack": {
            title: __("CAPS Integration Pack Help"),
            content: __("Defines how external apps integrate with CAPS. An integration pack declares which capabilities the external app provides, which DocTypes it protects, and how to sync permissions."),
        },
        "Capability Rate Limit": {
            title: __("Capability Rate Limit Help"),
            content: __("Rate limiting prevents abuse by restricting how often a capability can be exercised. Set limits per minute/hour/day for sensitive capabilities like data exports or bulk operations."),
        },
        "CAPS Settings": {
            title: __("CAPS Settings Help"),
            content: __("Global CAPS configuration: enforcement mode, cache TTL, audit log retention, notification preferences, and integration settings. Changes here affect the entire CAPS system."),
        },
        "CAPS Audit Log": {
            title: __("CAPS Audit Log Help"),
            content: __("Every capability check, assignment change, and policy evaluation is logged here. Use audit logs for security reviews, compliance reporting, and troubleshooting access issues."),
        },
        // Child/internal DocTypes
        "Capability Bundle Item": {
            title: __("Bundle Item Help"),
            content: __("A single capability entry within a Capability Bundle. Each item references one Capability and optionally sets override parameters."),
        },
        "Capability Prerequisite": {
            title: __("Capability Prerequisite Help"),
            content: __("Defines a prerequisite relationship: a user must have Capability A before they can be granted Capability B. Prevents invalid capability combinations."),
        },
        "Permission Group Member": {
            title: __("Group Member Help"),
            content: __("A user's membership in a Permission Group. Can have an expiry date for temporary membership. When expired, the user loses group capabilities automatically."),
        },
        "Permission Group Bundle": {
            title: __("Group Bundle Help"),
            content: __("Links a Capability Bundle to a Permission Group. All group members receive all capabilities in the bundle."),
        },
        "Permission Group Capability": {
            title: __("Group Capability Help"),
            content: __("Links a single Capability to a Permission Group. All group members receive this capability."),
        },
        "Role Capability Bundle": {
            title: __("Role Capability Bundle Help"),
            content: __("Links a Capability Bundle to a Role Capability Map. All users with the mapped role receive all capabilities in the bundle."),
        },
        "Role Capability Item": {
            title: __("Role Capability Item Help"),
            content: __("A single capability entry within a Role Capability Map. Links one Frappe role to one CAPS capability."),
        },
        "User Capability Bundle": {
            title: __("User Capability Bundle Help"),
            content: __("Links a Capability Bundle to a User Capability record. The user receives all capabilities in the bundle."),
        },
        "User Capability Item": {
            title: __("User Capability Item Help"),
            content: __("A single capability entry within a User Capability record. Tracks assignment source, dates, and delegation status."),
        },
    };

    // ── Inject ❓ button on form refresh ──
    $(document).on("form-refresh", function (e, frm) {
        if (!frm || !frm.doc || !frm.doc.doctype) return;
        const dt = frm.doc.doctype;
        if (!HELP_MAP[dt]) return;

        // Remove existing help button to avoid duplicates
        frm.page.remove_inner_button(__("Help"));

        frm.page.add_inner_button("❓ " + __("Help"), function () {
            show_help(HELP_MAP[dt]);
        });
    });

    // ── Also add help to list views for CAPS DocTypes ──
    for (const dt of Object.keys(HELP_MAP)) {
        frappe.listview_settings[dt] = frappe.listview_settings[dt] || {};
        const existing = frappe.listview_settings[dt].onload;
        frappe.listview_settings[dt].onload = function (list) {
            if (existing) existing.call(this, list);
            // Add help button to list toolbar
            if (list.page && !list.page._caps_help_added) {
                list.page.add_inner_button("❓ " + __("Help"), function () {
                    show_help(HELP_MAP[dt]);
                });
                list.page._caps_help_added = true;
            }
        };
    }

    // ── Show help in floating window or dialog ──
    function show_help(config) {
        const html = `
            <div style="padding:1.5rem;">
                <h4 style="color:${BRAND};margin-bottom:1rem;">${config.title}</h4>
                <p style="line-height:1.7;font-size:.95rem;">${config.content}</p>
                <div style="margin-top:1.5rem;padding-top:1rem;border-top:1px solid var(--border-color);">
                    <p class="text-muted" style="font-size:.8rem;">
                        ${__("For more help, visit")}
                        <a href="/app/caps-onboarding" style="color:${BRAND}">${__("CAPS Onboarding")}</a>
                        ${__("or")}
                        <a href="/app/caps-about" style="color:${BRAND}">${__("About CAPS")}</a>.
                    </p>
                </div>
            </div>`;

        if (frappe.visual && frappe.visual.floatingWindow) {
            frappe.visual.floatingWindow({
                title: config.title,
                content: html,
                position: document.documentElement.dir === "rtl" ? "left" : "right",
                width: 420,
                brandColor: BRAND,
            });
        } else {
            frappe.msgprint({
                title: config.title,
                message: config.content,
                indicator: "green",
            });
        }
    }
})();
