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
