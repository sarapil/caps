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
