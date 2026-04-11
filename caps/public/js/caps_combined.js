/* caps — Combined JS (reduces HTTP requests) */
/* Auto-generated from 5 individual files */


/* === caps_bootstrap.js === */
// Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
// Developer Website: https://arkan.it.com
// License: MIT
// For license information, please see license.txt

/**
 * CAPS — Bootstrap Loader
 * ════════════════════════════════════════════════════════════════
 * Lightweight namespace setup loaded on every page.
 * Lazy-loads the visual bundle only when CAPS visual pages are opened.
 */
(function () {
	"use strict";

	// Guard: skip if frappe core not loaded (transient HTTP/2 proxy failures)
if (typeof frappe === "undefined" || typeof frappe.provide !== "function") { return; }
frappe.provide("frappe.caps");

	// ── Visual Bundle Lazy Loader ────────────────────────────────
	frappe.caps._visual_loaded = false;

	frappe.caps.ensure_visual = async function () {
		if (frappe.caps._visual_loaded) return;
		if (frappe.visual && frappe.visual.engine) {
			await frappe.visual.engine();
			frappe.caps._visual_loaded = true;
		}
	};

	// ── Brand Constants ──────────────────────────────────────────
	frappe.caps.BRAND_COLOR = "#10B981";
	frappe.caps.APP_NAME = "CAPS";
	frappe.caps.PREFIX = "CAPS";
	frappe.caps.DOMAIN = "Access Control";

	// ── Utility: open contextual help ────────────────────────────
	frappe.caps.show_help = function (topic, title) {
		frappe.caps.ensure_visual().then(() => {
			if (frappe.visual && frappe.visual.FloatingWindow) {
				new frappe.visual.FloatingWindow({
					title: `❓ ${title || __("CAPS Help")}`,
					color: "var(--caps-brand)",
					width: 400,
					height: 300,
					content: `<div style="padding:12px;">
						<p>${__("Loading help for:")} <strong>${topic}</strong></p>
						<p><a href="/app/caps-onboarding">${__("Full Onboarding Guide →")}</a></p>
					</div>`,
				});
			}
		});
	};
})();


/* === caps_controller.js === */
// Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
// Developer Website: https://arkan.it.com
// License: MIT
// For license information, please see license.txt

/**
 * CAPS — Client-Side Controller
 * ===============================
 *
 * Provides `frappe.caps` global object for capability-based UI enforcement.
 *
 * Auto-enforces field + action restrictions on every form refresh.
 * Data is bootstrapped from boot_session and cached client-side.
 *
 * Usage:
 *   frappe.caps.has("field:Customer:phone")  → Promise<boolean>
 *   frappe.caps.enforce(frm)                 → auto-called on form events
 */

(function () {
    "use strict";

    // ── Client-side cache ─────────────────────────────────────────
    let _capabilities = null;
    let _fieldRestrictions = null;
    let _actionRestrictions = null;
    let _version = 0;
    let _cacheTS = 0;
    const _CACHE_TTL = 60000; // 60 seconds

    // ── Initialise from boot ──────────────────────────────────────
    function _initFromBoot() {
        const boot = frappe.boot || {};
        const caps = boot.caps || {};
        _capabilities = new Set(caps.capabilities || []);
        _fieldRestrictions = caps.field_restrictions || {};
        _actionRestrictions = caps.action_restrictions || {};
        _version = caps.version || 0;
        _cacheTS = Date.now();
    }

    // ── Ensure cache is fresh ─────────────────────────────────────
    async function _ensureCache() {
        if (_capabilities && (Date.now() - _cacheTS < _CACHE_TTL)) {
            return;
        }
        // Refresh from server
        try {
            const r = await frappe.xcall("caps.api.get_all_restrictions");
            if (r) {
                _fieldRestrictions = r.field_restrictions || {};
                _actionRestrictions = r.action_restrictions || {};
                _version = r.version || 0;
                _cacheTS = Date.now();
            }
        } catch (e) {
            console.warn("[CAPS] Cache refresh failed:", e);
        }
    }

    // ── Public API ────────────────────────────────────────────────

    frappe.caps = {
        /**
         * Auto-enforce field + action restrictions on a form.
         * Called automatically on form refresh via the hook below.
         */
        async enforce(frm) {
            if (!frm || !frm.doctype) return;
            await _ensureCache();

            const dt = frm.doctype;

            // ── Field restrictions ──────────────────────────
            const fieldRules = _fieldRestrictions[dt] || {};
            for (const [fieldname, rule] of Object.entries(fieldRules)) {
                const field = frm.fields_dict[fieldname];
                if (!field) continue;

                switch (rule.behavior) {
                    case "hide":
                        frm.set_df_property(fieldname, "hidden", 1);
                        break;
                    case "read_only":
                        frm.set_df_property(fieldname, "read_only", 1);
                        break;
                    case "mask":
                        frm.set_df_property(fieldname, "read_only", 1);
                        if (frm.doc[fieldname]) {
                            const masked = _applyMask(
                                String(frm.doc[fieldname]),
                                rule.mask_pattern
                            );
                            // Show masked value without changing actual doc
                            $(field.$input || field.$wrapper.find(".like-disabled-input"))
                                .val(masked)
                                .text(masked);
                        }
                        break;
                    case "custom":
                        if (rule.custom_handler) {
                            try {
                                // eslint-disable-next-line no-eval
                                eval(rule.custom_handler);
                            } catch (e) {
                                console.warn(`[CAPS] Custom handler error for ${fieldname}:`, e);
                            }
                        }
                        break;
                }
            }

            // ── Action restrictions ─────────────────────────
            const actionRules = _actionRestrictions[dt] || [];
            for (const rule of actionRules) {
                _enforceAction(frm, rule);
            }
        },

        /**
         * Check if current user has a capability.
         */
        async has(capability) {
            if (!_capabilities) _initFromBoot();
            return _capabilities.has(capability);
        },

        /**
         * Check if current user has ANY of the capabilities.
         */
        async hasAny(...capabilities) {
            if (!_capabilities) _initFromBoot();
            return capabilities.some((c) => _capabilities.has(c));
        },

        /**
         * Check if current user has ALL capabilities.
         */
        async hasAll(...capabilities) {
            if (!_capabilities) _initFromBoot();
            return capabilities.every((c) => _capabilities.has(c));
        },

        /**
         * Get restrictions for a specific doctype.
         */
        async getRestrictions(doctype) {
            await _ensureCache();
            return {
                fields: _fieldRestrictions[doctype] || {},
                actions: _actionRestrictions[doctype] || [],
            };
        },

        /**
         * Conditional execution: run callback only if user has capability.
         */
        async ifCan(capability, callback) {
            const can = await this.has(capability);
            if (can && typeof callback === "function") {
                callback();
            }
            return can;
        },

        /**
         * Force-refresh cache from server.
         */
        async bustCache() {
            _capabilities = null;
            _fieldRestrictions = null;
            _actionRestrictions = null;
            _cacheTS = 0;
            try {
                await frappe.xcall("caps.api.bust_cache");
                const r = await frappe.xcall("caps.api.get_all_restrictions");
                if (r) {
                    _fieldRestrictions = r.field_restrictions || {};
                    _actionRestrictions = r.action_restrictions || {};
                    _version = r.version || 0;
                }
                const caps = await frappe.xcall("caps.api.get_my_capabilities");
                if (caps) {
                    _capabilities = new Set(caps);
                }
                _cacheTS = Date.now();
            } catch (e) {
                console.warn("[CAPS] Cache bust failed:", e);
            }
        },

        /**
         * Get current map version (for staleness checks).
         */
        getVersion() {
            return _version;
        },
    };

    // ── Action enforcement helper ─────────────────────────────────

    function _enforceAction(frm, rule) {
        const { action_id, action_type, fallback_behavior, fallback_message } = rule;

        if (action_type === "button" || action_type === "menu_item") {
            // Find and hide/disable the button
            const $btns = frm.$wrapper
                ? frm.$wrapper.find(
                    `.btn-primary-dark:contains("${action_id}"), ` +
                    `.btn-default:contains("${action_id}"), ` +
                    `.dropdown-item:contains("${action_id}")`
                )
                : $();

            if (fallback_behavior === "hide") {
                $btns.closest(".btn, .dropdown-item, li").hide();
            } else if (fallback_behavior === "disable") {
                $btns.prop("disabled", true).addClass("disabled");
                if (fallback_message) {
                    $btns.attr("title", fallback_message);
                }
            }
        }

        if (action_type === "workflow_action") {
            // Hide workflow action buttons
            const $wfBtns = frm.$wrapper
                ? frm.$wrapper.find(
                    `.btn-primary[data-action="${action_id}"], ` +
                    `.workflow-button-area .btn:contains("${action_id}")`
                )
                : $();

            if (fallback_behavior === "hide") {
                $wfBtns.hide();
            } else if (fallback_behavior === "disable") {
                $wfBtns.prop("disabled", true);
                if (fallback_message) {
                    $wfBtns.attr("title", fallback_message);
                }
            }
        }

        if (action_type === "print_format") {
            // Hide print format from the menu
            frm.$wrapper &&
                frm.$wrapper
                    .find(`.dropdown-item:contains("${action_id}")`)
                    .hide();
        }
    }

    // ── Mask helper ───────────────────────────────────────────────

    function _applyMask(value, pattern) {
        if (!pattern) {
            return "●".repeat(Math.min(value.length, 8));
        }
        let result = pattern;

        // {last4} → last N chars
        const lastMatch = pattern.match(/\{last(\d+)\}/);
        if (lastMatch) {
            const n = parseInt(lastMatch[1]);
            result = result.replace(
                lastMatch[0],
                value.length >= n ? value.slice(-n) : value
            );
        }

        // {first2} → first N chars
        const firstMatch = pattern.match(/\{first(\d+)\}/);
        if (firstMatch) {
            const n = parseInt(firstMatch[1]);
            result = result.replace(
                firstMatch[0],
                value.length >= n ? value.slice(0, n) : value
            );
        }

        return result;
    }

    // ── Auto-Enforce on Form Events ──────────────────────────────

    // Initialise capabilities from boot data
    $(document).ready(function () {
        _initFromBoot();
        _showImpersonationBanner();
    });

    // ── Impersonation Banner ─────────────────────────────────────

    function _showImpersonationBanner() {
        const boot = frappe.boot || {};
        const caps = boot.caps || {};
        const target = caps.impersonating;

        // Remove any existing banner first
        $(".caps-impersonation-banner").remove();

        if (!target) return;

        const $banner = $(`
            <div class="caps-impersonation-banner"
                 style="position:fixed;top:0;left:0;right:0;z-index:10000;
                        background:#ff6b35;color:#fff;text-align:center;
                        padding:6px 12px;font-size:13px;font-weight:600;">
                <i class="fa fa-user-secret"></i>
                ${__("CAPS Impersonation Active")} — ${__("Viewing as")}
                <strong>${frappe.utils.escape_html(target)}</strong>
                <button class="btn btn-xs btn-light caps-stop-impersonation"
                        style="margin-left:12px;font-weight:600;">
                    ${__("Stop")}
                </button>
            </div>
        `);
        $banner.find(".caps-stop-impersonation").on("click", function () {
            frappe.call({
                method: "caps.api_impersonation.stop_impersonation",
                callback: function () {
                    $(".caps-impersonation-banner").remove();
                    frappe.show_alert({
                        message: __("Impersonation stopped"),
                        indicator: "green",
                    });
                    // Push body back down
                    $("body").css("margin-top", "");
                    // Reload to get real caps
                    location.reload();
                },
            });
        });
        $("body").prepend($banner);
        // Push body down so banner doesn't overlap navbar
        $("body").css("margin-top", "38px");
    }

    // Hook into every form refresh
    $(document).on("form-refresh", function (event, frm) {
        if (frm && frappe.caps) {
            frappe.caps.enforce(frm);
        }
    });

    // Also hook via frappe.ui.form.on for broader coverage
    if (frappe.ui && frappe.ui.form) {
        const _origTrigger = frappe.ui.form.trigger;
        if (_origTrigger) {
            frappe.ui.form.trigger = function (doctype, event, frm) {
                const result = _origTrigger.apply(this, arguments);
                if (event === "refresh" && frm && frappe.caps) {
                    frappe.caps.enforce(frm);
                }
                return result;
            };
        }
    }
})();


/* === caps_sidebar.js === */
// Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
// Developer Website: https://arkan.it.com
// License: MIT
// For license information, please see license.txt

/**
 * CAPS — Slim Sidebar Navigation
 * ════════════════════════════════════════════════════════════════
 * Icon-only collapsed sidebar, hover-expand, shown only on CAPS routes.
 * Uses frappe_visual icons for consistent styling.
 */
(function () {
	"use strict";

	frappe.provide("frappe.caps_nav");

	const CAPS_ROUTES = [
		"caps", "caps-admin", "caps-graph", "caps-compare", "caps-onboarding",
		"capability", "capability-bundle", "user-capability", "permission-group",
		"role-capability-map", "field-capability-map", "action-capability-map",
		"capability-policy", "capability-request", "caps-audit-log",
		"capability-rate-limit", "caps-integration-pack", "caps-settings",
		"capability-snapshot",
	];

	const NAV_ITEMS = [
		{ icon: "layout-dashboard", label: __("Dashboard"),       route: "/app/caps-admin" },
		{ icon: "chart-dots-3",     label: __("Graph"),           route: "/app/caps-graph" },
		{ icon: "arrows-exchange",  label: __("Compare"),         route: "/app/caps-compare" },
		{ icon: "key",              label: __("Capabilities"),    route: "/app/capability" },
		{ icon: "packages",         label: __("Bundles"),         route: "/app/capability-bundle" },
		{ icon: "users-group",      label: __("Groups"),          route: "/app/permission-group" },
		{ icon: "user-shield",      label: __("User Caps"),       route: "/app/user-capability" },
		{ icon: "map",              label: __("Role Maps"),       route: "/app/role-capability-map" },
		{ icon: "lock",             label: __("Field Maps"),      route: "/app/field-capability-map" },
		{ icon: "bolt",             label: __("Action Maps"),     route: "/app/action-capability-map" },
		{ icon: "gavel",            label: __("Policies"),        route: "/app/capability-policy" },
		{ icon: "hand-stop",        label: __("Requests"),        route: "/app/capability-request" },
		{ icon: "clock-hour-4",     label: __("Rate Limits"),     route: "/app/capability-rate-limit" },
		{ icon: "file-text",        label: __("Audit Log"),       route: "/app/caps-audit-log" },
		{ icon: "settings",         label: __("Settings"),        route: "/app/caps-settings" },
	];

	function is_caps_route() {
		const route = (frappe.get_route_str() || "").toLowerCase().replace(/^\/app\//, "");
		const first = route.split("/")[0];
		return CAPS_ROUTES.some(r => first === r || first.startsWith(r + "/"));
	}

	function build_sidebar() {
		if (document.querySelector(".caps-sidebar")) return;

		const $sidebar = $(`<nav class="caps-sidebar caps-sidebar-collapsed">
			<div class="caps-sidebar-brand">
				<img src="/assets/caps/images/caps-icon-animated.svg" alt="CAPS" class="caps-sidebar-logo">
				<span class="caps-sidebar-title">CAPS</span>
			</div>
			<div class="caps-sidebar-nav"></div>
		</nav>`);

		const $nav = $sidebar.find(".caps-sidebar-nav");
		const current = window.location.pathname;

		NAV_ITEMS.forEach(item => {
			const active = current.startsWith(item.route) ? " caps-nav-active" : "";
			$nav.append(`<a href="${item.route}" class="caps-nav-item${active}" title="${item.label}">
				<i class="ti ti-${item.icon} caps-nav-icon"></i>
				<span class="caps-nav-label">${item.label}</span>
			</a>`);
		});

		// Insert before page-container
		const $body = $("body");
		const $page = $body.find("#page-container, .page-container").first();
		if ($page.length) {
			$page.before($sidebar);
		} else {
			$body.prepend($sidebar);
		}

		// Hover expand/collapse
		$sidebar.on("mouseenter", () => $sidebar.removeClass("caps-sidebar-collapsed"));
		$sidebar.on("mouseleave", () => $sidebar.addClass("caps-sidebar-collapsed"));
	}

	function remove_sidebar() {
		$(".caps-sidebar").remove();
	}

	// ── Route Watcher ────────────────────────────────────────────
	function on_route_change() {
		if (is_caps_route()) {
			build_sidebar();
		} else {
			remove_sidebar();
		}
	}

	// ── Init ─────────────────────────────────────────────────────
	$(document).on("page-change", on_route_change);
	frappe.router && frappe.router.on && frappe.router.on("change", on_route_change);

	// Initial check
	$(function () {
		setTimeout(on_route_change, 300);
	});

	frappe.caps_nav.refresh = on_route_change;
})();


/* === caps_contextual_help.js === */
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


/* === fv_integration.js === */
// Copyright (c) 2024, Arkan Lab — https://arkan.it.com
// License: MIT
// frappe_visual Integration for CAPS

(function() {
    "use strict";

    // App branding registration
    const APP_CONFIG = {
        name: "caps",
        title: "CAPS",
        color: "#059669",
        module: "CAPS",
    };

    // Initialize visual enhancements when ready
    $(document).on("app_ready", function() {
        // Register app color with visual theme system
        if (frappe.visual && frappe.visual.ThemeManager) {
            try {
                document.documentElement.style.setProperty(
                    "--caps-primary",
                    APP_CONFIG.color
                );
            } catch(e) {}
        }

        // Initialize bilingual tooltips for Arabic support
        if (frappe.visual && frappe.visual.bilingualTooltip) {
            // bilingualTooltip auto-initializes — just ensure it's active
        }
    });

    // Route-based visual page rendering
    $(document).on("page-change", function() {
        if (!frappe.visual || !frappe.visual.generator) return;

    // Visual Settings Page
    if (frappe.get_route_str() === 'caps-settings') {
        const page = frappe.container.page;
        if (page && page.main && frappe.visual.generator) {
            frappe.visual.generator.settingsPage(
                page.main[0] || page.main,
                "CAPS Settings"
            );
        }
    }

    // Visual Reports Hub
    if (frappe.get_route_str() === 'caps-reports') {
        const page = frappe.container.page;
        if (page && page.main && frappe.visual.generator) {
            frappe.visual.generator.reportsHub(
                page.main[0] || page.main,
                "CAPS"
            );
        }
    }
    });
})();

