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
						<p><a href="#" onclick="frappe.caps.open_onboarding(); return false;">${__("Full Onboarding Guide →")}</a></p>
					</div>`,
				});
			}
		});
	};

	// ── Onboarding in FloatingWindow ─────────────────────────────
	frappe.caps.open_onboarding = function () {
		frappe.caps.ensure_visual().then(() => {
			const steps = [
				{ title: __("Review Capabilities"), desc: __("Explore the capabilities declared by each installed app in the CAPS workspace.") },
				{ title: __("Map Roles"), desc: __("Assign CAPS capabilities to Frappe roles using the visual mapping interface.") },
				{ title: __("Configure Field Restrictions"), desc: __("Set up field-level visibility rules — hide, mask, or read-only per capability.") },
				{ title: __("Test Permissions"), desc: __("Use the permission simulator to verify access patterns for different user roles.") },
				{ title: __("Monitor & Audit"), desc: __("Review the permission analytics dashboard for usage patterns and potential conflicts.") },
			];
			const stepsHtml = steps.map((s, i) => `
				<div style="display:flex;gap:12px;padding:14px 0;border-bottom:1px solid var(--border-color);">
					<div style="width:32px;height:32px;border-radius:50%;background:rgba(16,185,129,0.12);color:#10B981;display:flex;align-items:center;justify-content:center;font-weight:700;flex-shrink:0;">${i + 1}</div>
					<div><h4 style="margin:0 0 4px;">${s.title}</h4><p style="margin:0;color:var(--text-muted);font-size:0.9rem;">${s.desc}</p></div>
				</div>
			`).join("");

			if (frappe.visual && frappe.visual.FloatingWindow) {
				new frappe.visual.FloatingWindow({
					title: `🚀 ${__("CAPS Onboarding")}`,
					color: "#10B981",
					width: 520,
					height: 480,
					content: `<div style="padding:16px;">
						<p style="color:var(--text-muted);margin-bottom:16px;">${__("Follow these steps to configure capability-based access control.")}</p>
						${stepsHtml}
					</div>`,
				});
			} else {
				// Fallback: open standalone page
				frappe.set_route("caps-onboarding");
			}
		});
	};
})();
