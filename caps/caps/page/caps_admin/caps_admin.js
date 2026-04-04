// Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
// Developer Website: https://arkan.it.com
// License: MIT
// For license information, please see license.txt

/**
 * CAPS Admin — Visual Landing Page
 * ══════════════════════════════════════════════════════════════
 * Dashboard KPIs + Module Map + Quick Actions + Onboarding
 * Uses: VisualDashboard, GraphEngine, FloatingWindow
 */
frappe.pages["caps-admin"].on_page_load = async function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("CAPS Administration"),
		single_column: true,
	});
	wrapper.caps_admin = new CAPSAdminVisual(page);
};

frappe.pages["caps-admin"].on_page_show = function (wrapper) {
	if (wrapper.caps_admin) wrapper.caps_admin.refresh();
};

class CAPSAdminVisual {
	constructor(page) {
		this.page = page;
		this.$body = $(page.body);
		this.engine = null;
		this.init();
	}

	async init() {
		this.$body.html(frappe.render_template("caps_admin"));

		this.page.set_secondary_action(__("Refresh"), () => this.refresh(), "refresh-cw");

		// Load visual engine
		await frappe.visual.engine();
		this._register_caps_types();

		this.setup_user_lookup();
		this.bind_actions();
		this.refresh();
	}

	_register_caps_types() {
		const defs = {
			capability:   { palette: "emerald", icon: "🔑", shape: "roundrectangle" },
			capability_inactive: { palette: "slate", icon: "🔒", shape: "roundrectangle" },
			bundle:       { palette: "violet",  icon: "📦", shape: "octagon" },
			group:        { palette: "blue",    icon: "👥", shape: "ellipse" },
			role:         { palette: "amber",   icon: "🛡️", shape: "diamond" },
			user:         { palette: "indigo",  icon: "👤", shape: "ellipse" },
			policy:       { palette: "pink",    icon: "📜", shape: "roundrectangle" },
			field_map:    { palette: "teal",    icon: "📝", shape: "roundrectangle" },
			action_map:   { palette: "orange",  icon: "⚡", shape: "roundrectangle" },
			category_hub: { palette: "emerald", icon: "🏷️", shape: "octagon" },
			request:      { palette: "amber",   icon: "✋", shape: "roundrectangle" },
			rate_limit:   { palette: "red",     icon: "⏱️", shape: "roundrectangle" },
		};
		for (const [name, def] of Object.entries(defs)) {
			frappe.visual.ColorSystem.registerNodeType(name, def);
		}
	}

	async refresh() {
		await Promise.all([
			this.load_dashboard(),
			this.load_module_graph(),
			this.load_policies(),
			this.load_audit_log(),
			this.load_expiring(),
		]);
	}

	// ─── KPI Dashboard ───────────────────────────────────────────
	async load_dashboard() {
		const r = await frappe.call({ method: "caps.api_dashboard.get_dashboard_stats" });
		const d = r.message || {};
		const widgets = [
			{
				label: __("CAPABILITIES"), value: d.total_capabilities || 0,
				icon: "🔑", color: "var(--caps-brand)",
				subtitle: `${d.active_capabilities || 0} ${__("active")}`,
				onClick: () => frappe.set_route("List", "Capability"),
			},
			{
				label: __("USERS"), value: d.total_user_capabilities || 0,
				icon: "👤", color: "#6366f1",
				subtitle: __("with capabilities"),
				onClick: () => frappe.set_route("List", "User Capability"),
			},
			{
				label: __("BUNDLES"), value: d.total_bundles || 0,
				icon: "📦", color: "#8b5cf6",
				onClick: () => frappe.set_route("List", "Capability Bundle"),
			},
			{
				label: __("PENDING REQUESTS"), value: d.pending_requests || 0,
				icon: "✋", color: d.pending_requests > 0 ? "#ef4444" : "#94a3b8",
				onClick: () => frappe.set_route("List", "Capability Request", { status: "Pending" }),
				badges: d.pending_requests > 0 ? [{ label: __("Action needed"), type: "warning" }] : [],
			},
		];
		const el = this.$body.find("#caps-kpi-dashboard")[0];
		if (el) { el.innerHTML = ""; new frappe.visual.VisualDashboard(el, widgets); }
	}

	// ─── Module Map Graph ─────────────────────────────────────────
	async load_module_graph() {
		const r = await frappe.call({ method: "caps.api_visual.get_dashboard_graph" });
		const data = r.message || { nodes: [], edges: [] };
		const el = this.$body.find("#caps-module-graph")[0];
		if (!el) return;

		if (this.engine) { this.engine.destroy(); this.engine = null; }
		el.innerHTML = "";

		this.engine = new frappe.visual.GraphEngine({
			container: el,
			nodes: data.nodes,
			edges: data.edges,
			layout: "elk-radial",
			minimap: false,
			contextMenu: true,
			animate: true,
			antLines: true,
			pulseNodes: true,
			onNodeClick: (node) => {
				if (node.meta && node.meta.route) {
					frappe.set_route(node.meta.route);
				} else {
					new frappe.visual.FloatingWindow({
						title: `${node.icon || ""} ${node.label}`,
						color: "var(--caps-brand)",
						content: this._summary_html(node),
						width: 320, height: 220,
					});
				}
			},
			onNodeDblClick: (node) => {
				if (node.meta && node.meta.route) frappe.set_route(node.meta.route);
			},
		});
	}

	_summary_html(node) {
		if (!node.summary) return `<p>${node.label}</p>`;
		let h = '<div class="caps-float-summary">';
		for (const [k, v] of Object.entries(node.summary)) {
			h += `<div class="caps-float-row"><span class="caps-float-key">${k}</span><span class="caps-float-val">${v}</span></div>`;
		}
		return h + "</div>";
	}

	// ─── User Lookup ──────────────────────────────────────────────
	setup_user_lookup() {
		this.user_field = frappe.ui.form.make_control({
			parent: this.$body.find("#user-lookup-field"),
			df: {
				fieldtype: "Link", options: "User", fieldname: "lookup_user",
				placeholder: __("Select a user..."),
				change: () => {
					const u = this.user_field.get_value();
					if (u) this.lookup_user(u);
					else this.$body.find("#user-capabilities-result").html("");
				},
			},
			render_input: true,
		});
	}

	async lookup_user(user) {
		const $r = this.$body.find("#user-capabilities-result");
		$r.html(`<div class="text-muted">${__("Loading...")}</div>`);
		const r = await frappe.call({ method: "caps.api.get_user_capabilities", args: { user } });
		const caps = (r.message && r.message.capabilities) || [];
		if (!caps.length) { $r.html(`<div class="text-muted">${__("No capabilities found")}</div>`); return; }
		let html = '<div class="caps-user-caps-list">';
		caps.forEach((c) => {
			const nm = c.capability_label || c.capability || c.name;
			html += `<span class="caps-badge-pill" title="${frappe.utils.escape_html(c.category || "")}">${frappe.utils.escape_html(nm)}</span> `;
		});
		$r.html(html + "</div>");
	}

	// ─── Quick Actions ────────────────────────────────────────────
	bind_actions() {
		this.$body.find("#btn-export-config").on("click", () => {
			frappe.call({ method: "caps.api_integrations.export_all_config",
				callback: () => frappe.msgprint(__("Config exported. Check downloads.")) });
		});
		this.$body.find("#btn-import-config").on("click", () => {
			new frappe.ui.FileUploader({ as_dataurl: true, on_success: (f) => {
				frappe.call({ method: "caps.api_integrations.import_config", args: { data: f.dataurl },
					callback: () => { frappe.show_alert({ message: __("Config imported"), indicator: "green" }); this.refresh(); } });
			}});
		});
		this.$body.find("#btn-bust-cache").on("click", () => {
			frappe.call({ method: "caps.api.bust_cache",
				callback: () => frappe.show_alert({ message: __("All CAPS caches cleared"), indicator: "green" }) });
		});
		this.$body.find("#btn-new-capability").on("click", () => frappe.new_doc("Capability"));
		this.$body.find("#btn-caps-onboarding").on("click", () => frappe.set_route("caps-onboarding"));
		this.$body.find("#btn-caps-help").on("click", () => this.show_help());
	}

	show_help() {
		new frappe.visual.FloatingWindow({
			title: `❓ ${__("CAPS Admin Help")}`,
			color: "var(--caps-brand)", width: 400, height: 320,
			content: `<div style="padding:12px;line-height:1.7;">
				<p><strong>${__("CAPS Administration Dashboard")}</strong></p>
				<p>${__("Overview of your Capability-Based Access Control system.")}</p>
				<ul style="padding-left:18px;">
					<li>${__("KPI cards show key metrics — click to drill down")}</li>
					<li>${__("Module map shows CAPS components — click nodes to navigate")}</li>
					<li>${__("User lookup inspects any user's capabilities")}</li>
					<li>${__("Quick actions: export/import config, bust cache")}</li>
				</ul>
				<p><a href="/app/caps-onboarding">${__("Full Onboarding Guide →")}</a></p>
			</div>`,
		});
	}

	// ─── Active Policies ──────────────────────────────────────────
	async load_policies() {
		const $el = this.$body.find("#active-policies-list");
		try {
			const r = await frappe.call({ method: "frappe.client.get_list", args: {
				doctype: "Capability Policy", filters: { is_active: 1 },
				fields: ["name", "policy_label", "policy_type", "modified"],
				order_by: "modified desc", limit_page_length: 5,
			}});
			const items = r.message || [];
			if (!items.length) { $el.html(`<div class="text-muted">${__("No active policies")}</div>`); return; }
			let h = '<div class="list-group list-group-flush">';
			items.forEach(p => {
				h += `<a href="/app/capability-policy/${p.name}" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
					<span>${frappe.utils.escape_html(p.policy_label || p.name)}</span>
					<span class="badge" style="background:var(--caps-brand-light);color:var(--caps-brand);">${p.policy_type || ""}</span>
				</a>`;
			});
			$el.html(h + "</div>");
		} catch { $el.html(`<div class="text-muted">${__("Could not load policies")}</div>`); }
	}

	// ─── Recent Audit Log ─────────────────────────────────────────
	async load_audit_log() {
		const $el = this.$body.find("#recent-audit-log");
		try {
			const r = await frappe.call({ method: "frappe.client.get_list", args: {
				doctype: "CAPS Audit Log", fields: ["name", "action", "user", "capability", "timestamp"],
				order_by: "timestamp desc", limit_page_length: 8,
			}});
			const logs = r.message || [];
			if (!logs.length) { $el.html(`<div class="text-muted">${__("No audit entries")}</div>`); return; }
			let h = '<table class="table table-sm table-borderless caps-audit-table"><tbody>';
			logs.forEach(l => {
				h += `<tr>
					<td><span class="caps-badge-action">${frappe.utils.escape_html(l.action || "")}</span></td>
					<td>${frappe.utils.escape_html(l.user || "")}</td>
					<td class="text-muted">${frappe.utils.escape_html(l.capability || "")}</td>
					<td class="text-muted text-right">${frappe.datetime.prettyDate(l.timestamp)}</td>
				</tr>`;
			});
			$el.html(h + "</tbody></table>");
		} catch { $el.html(`<div class="text-muted">${__("Could not load audit log")}</div>`); }
	}

	// ─── Expiring Capabilities ────────────────────────────────────
	async load_expiring() {
		const $el = this.$body.find("#expiring-capabilities");
		if (!$el.length) return;
		try {
			const r = await frappe.call({ method: "caps.api_dashboard.expiry_forecast" });
			const items = (r.message && r.message.expiring) || [];
			if (!items.length) { $el.html(`<div class="text-muted">${__("No capabilities expiring soon")}</div>`); return; }
			let h = '<ul class="caps-expiry-list">';
			items.forEach(i => {
				h += `<li><strong>${frappe.utils.escape_html(i.capability || i.name)}</strong>
					<span class="text-muted"> — ${frappe.utils.escape_html(i.user || "")}</span>
					<span class="text-warning float-right">${frappe.datetime.prettyDate(i.expiry_date)}</span></li>`;
			});
			$el.html(h + "</ul>");
		} catch { $el.html(`<div class="text-muted">${__("Could not load expiring items")}</div>`); }
	}

	destroy() {
		if (this.engine) { this.engine.destroy(); this.engine = null; }
		frappe.visual.FloatingWindow.closeAll();
	}
}
