// Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
// Developer Website: https://arkan.it.com
// License: MIT
// For license information, please see license.txt

/**
 * CAPS Compare — Visual User Comparison
 * ══════════════════════════════════════════════════════════════
 * Side-by-side comparison with optional graph overlay
 * Uses: GraphEngine, FloatingWindow
 */
frappe.pages["caps-compare"].on_page_load = async function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Compare User Capabilities"),
		single_column: true,
	});
	wrapper.caps_compare = new CAPSCompareVisual(page);
};

class CAPSCompareVisual {
	constructor(page) {
		this.page = page;
		this.$body = $(page.body);
		this.engine = null;
		this.init();
	}

	async init() {
		this.$body.html(frappe.render_template("caps_compare"));
		await frappe.visual.engine();

		// Register types
		const defs = {
			capability: { palette: "emerald", icon: "🔑", shape: "roundrectangle" },
			user:       { palette: "indigo",  icon: "👤", shape: "ellipse" },
		};
		for (const [n, d] of Object.entries(defs)) {
			frappe.visual.ColorSystem.registerNodeType(n, d);
		}

		this.setup_fields();
		this.bind_events();
	}

	setup_fields() {
		this.user_a = frappe.ui.form.make_control({
			parent: this.$body.find(".caps-compare-user-a"),
			df: { fieldtype: "Link", options: "User", fieldname: "user_a", placeholder: __("User A") },
			render_input: true,
		});
		this.user_b = frappe.ui.form.make_control({
			parent: this.$body.find(".caps-compare-user-b"),
			df: { fieldtype: "Link", options: "User", fieldname: "user_b", placeholder: __("User B") },
			render_input: true,
		});
	}

	bind_events() {
		this.$body.find(".caps-compare-btn").on("click", () => this.compare());
		this.$body.find(".caps-compare-toggle-graph").on("click", () => this.toggle_graph());
		this.$body.find("#btn-caps-compare-help").on("click", () => this.show_help());
	}

	async compare() {
		const a = this.user_a.get_value();
		const b = this.user_b.get_value();
		if (!a || !b) {
			frappe.show_alert({ message: __("Please select both users"), indicator: "orange" });
			return;
		}

		this.$body.find(".caps-compare-results").show();
		this.$body.find(".caps-compare-loading").show();

		try {
			// Use visual API for graph data
			const r = await frappe.call({
				method: "caps.api_visual.get_user_comparison_graph",
				args: { user_a: a, user_b: b },
			});
			const data = r.message || {};
			const stats = data.stats || {};

			// Update names
			this.$body.find(".user-a-name").text(a);
			this.$body.find(".user-b-name").text(b);

			// Stats summary
			this.$body.find(".caps-compare-summary").html(`
				<div class="caps-compare-stats">
					<div class="caps-stat-pill" style="--pill-color: #3b82f6;">
						<strong>${stats.total_a || 0}</strong> ${__("total for")} ${frappe.utils.escape_html(a)}
					</div>
					<div class="caps-stat-pill" style="--pill-color: var(--caps-brand);">
						<strong>${stats.common || 0}</strong> ${__("common")}
					</div>
					<div class="caps-stat-pill" style="--pill-color: #f59e0b;">
						<strong>${stats.total_b || 0}</strong> ${__("total for")} ${frappe.utils.escape_html(b)}
					</div>
				</div>
			`);

			// Categorize nodes
			const only_a = [], common = [], only_b = [];
			(data.nodes || []).forEach(n => {
				if (n.type === "user") return;
				const zone = n.summary && n.summary[__("Zone")];
				if (zone && zone.includes(a)) only_a.push(n);
				else if (zone && zone.includes(b)) only_b.push(n);
				else if (zone && zone.includes(__("Common"))) common.push(n);
				else common.push(n); // default to common
			});

			// Render pill lists
			this._render_pills(this.$body.find(".caps-only-a"), only_a, "#3b82f6");
			this._render_pills(this.$body.find(".caps-common"), common, "var(--caps-brand)");
			this._render_pills(this.$body.find(".caps-only-b"), only_b, "#f59e0b");

			// Store data for graph toggle
			this._graph_data = data;
			this.$body.find(".caps-compare-toggle-graph").prop("disabled", false);

		} catch (err) {
			frappe.show_alert({ message: __("Comparison failed"), indicator: "red" });
		} finally {
			this.$body.find(".caps-compare-loading").hide();
		}
	}

	_render_pills($el, items, color) {
		if (!items.length) {
			$el.html(`<div class="text-muted">${__("None")}</div>`);
			return;
		}
		let h = '<div class="caps-pill-grid">';
		items.forEach(n => {
			h += `<span class="caps-compare-pill" style="--pill-color:${color};">${frappe.utils.escape_html(n.label)}</span>`;
		});
		$el.html(h + "</div>");
	}

	toggle_graph() {
		const $graph = this.$body.find(".caps-compare-graph-container");
		if ($graph.is(":visible")) {
			$graph.hide();
			if (this.engine) { this.engine.destroy(); this.engine = null; }
			return;
		}

		if (!this._graph_data) return;
		$graph.show();
		const el = $graph[0];
		el.innerHTML = "";

		this.engine = new frappe.visual.GraphEngine({
			container: el,
			nodes: this._graph_data.nodes,
			edges: this._graph_data.edges,
			layout: "fcose",
			minimap: false,
			contextMenu: true,
			animate: true,
			pulseNodes: true,
			onNodeClick: (node) => {
				new frappe.visual.FloatingWindow({
					title: `${node.icon || ""} ${node.label}`,
					color: "var(--caps-brand)",
					content: this._build_summary(node),
					width: 300, height: 200,
				});
			},
		});
	}

	_build_summary(node) {
		if (!node.summary) return `<p>${node.label}</p>`;
		let h = '<div class="caps-float-summary">';
		for (const [k, v] of Object.entries(node.summary)) {
			h += `<div class="caps-float-row"><span class="caps-float-key">${k}</span><span class="caps-float-val">${v}</span></div>`;
		}
		return h + "</div>";
	}

	show_help() {
		new frappe.visual.FloatingWindow({
			title: `❓ ${__("Compare Help")}`,
			color: "var(--caps-brand)", width: 360, height: 260,
			content: `<div style="padding:12px;line-height:1.7;">
				<p>${__("Select two users and click Compare to see their capability differences.")}</p>
				<ul style="padding-left:18px;">
					<li>${__("Blue pills = Only User A")}</li>
					<li>${__("Green pills = Common")}</li>
					<li>${__("Orange pills = Only User B")}</li>
				</ul>
				<p>${__("Toggle the graph view for a visual network comparison.")}</p>
			</div>`,
		});
	}

	destroy() {
		if (this.engine) { this.engine.destroy(); this.engine = null; }
		frappe.visual.FloatingWindow.closeAll();
	}
}
