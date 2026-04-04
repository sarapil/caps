// Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
// Developer Website: https://arkan.it.com
// License: MIT
// For license information, please see license.txt

/**
 * CAPS Graph — Full Visual Graph Explorer
 * ══════════════════════════════════════════════════════════════
 * 5 graph modes with frappe_visual GraphEngine + LayoutManager
 */
frappe.pages["caps-graph"].on_page_load = async function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("CAPS Graph Explorer"),
		single_column: true,
	});
	wrapper.caps_graph = new CAPSGraphExplorer(page);
};

frappe.pages["caps-graph"].on_page_show = function (wrapper) {
	if (wrapper.caps_graph && !wrapper.caps_graph._loaded) {
		wrapper.caps_graph.load_graph();
	}
};

class CAPSGraphExplorer {
	constructor(page) {
		this.page = page;
		this.$body = $(page.body);
		this.engine = null;
		this._loaded = false;
		this.current_mode = "hierarchy";

		this.MODES = {
			hierarchy:     { label: __("Capability Hierarchy"),  api: "caps.api_visual.get_capability_hierarchy",  layout: "elk-mrtree",  icon: "🔑" },
			prerequisites: { label: __("Prerequisites"),         api: "caps.api_visual.get_prerequisite_graph",     layout: "fcose",       icon: "🔗" },
			bundles:       { label: __("Bundle Composition"),    api: "caps.api_visual.get_bundle_graph",           layout: "elk-layered", icon: "📦" },
			groups:        { label: __("Group Hierarchy"),       api: "caps.api_visual.get_group_hierarchy",        layout: "elk-mrtree",  icon: "👥" },
			roles:         { label: __("Role → Capability Map"), api: "caps.api_visual.get_role_capability_graph",  layout: "elk-layered", icon: "🛡️" },
		};

		this.init();
	}

	async init() {
		this.$body.html(frappe.render_template("caps_graph"));

		await frappe.visual.engine();
		this._register_caps_types();

		this.setup_toolbar();
		this.bind_events();
		this.load_graph();
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

	setup_toolbar() {
		// Mode selector
		const $select = this.$body.find(".caps-graph-type");
		$select.empty();
		for (const [key, mode] of Object.entries(this.MODES)) {
			$select.append(`<option value="${key}">${mode.icon} ${mode.label}</option>`);
		}
		$select.val(this.current_mode);

		// Layout toolbar + search
		const $toolbar = this.$body.find(".caps-graph-toolbar-extra")[0];
		const $search = this.$body.find(".caps-graph-search-bar")[0];
		if ($toolbar) frappe.visual.LayoutManager.createToolbar($toolbar, null, this.MODES[this.current_mode].layout);
		if ($search) frappe.visual.LayoutManager.createSearchBar($search, null);
	}

	bind_events() {
		this.$body.find(".caps-graph-type").on("change", (e) => {
			this.current_mode = e.target.value;
			this.load_graph();
		});

		this.$body.find(".caps-graph-reset").on("click", () => {
			if (this.engine) this.engine.fit();
		});

		this.$body.find(".caps-graph-export-svg").on("click", () => {
			if (!this.engine) return;
			const svg = this.engine.exportSVG();
			const blob = new Blob([svg], { type: "image/svg+xml" });
			const url = URL.createObjectURL(blob);
			const a = document.createElement("a");
			a.href = url; a.download = `caps-${this.current_mode}-graph.svg`;
			a.click(); URL.revokeObjectURL(url);
		});

		this.$body.find(".caps-graph-export-png").on("click", () => {
			if (!this.engine) return;
			const png = this.engine.exportPNG();
			const a = document.createElement("a");
			a.href = png; a.download = `caps-${this.current_mode}-graph.png`;
			a.click();
		});

		this.$body.find("#btn-caps-graph-help").on("click", () => this.show_help());
	}

	async load_graph() {
		const mode = this.MODES[this.current_mode];
		if (!mode) return;

		const container = this.$body.find(".caps-graph-container")[0];
		if (!container) return;

		// Loading state
		container.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted);">${__("Loading graph...")}</div>`;

		try {
			const r = await frappe.call({ method: mode.api });
			const data = r.message || { nodes: [], edges: [] };

			if (this.engine) { this.engine.destroy(); this.engine = null; }
			container.innerHTML = "";

			if (!data.nodes.length) {
				container.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted);">${__("No data to display for this graph mode")}</div>`;
				this._loaded = true;
				return;
			}

			this.engine = new frappe.visual.GraphEngine({
				container,
				nodes: data.nodes,
				edges: data.edges,
				layout: mode.layout,
				minimap: true,
				contextMenu: true,
				animate: true,
				antLines: true,
				pulseNodes: true,
				expandCollapse: true,
				onNodeClick: (node) => this._on_node_click(node),
				onNodeDblClick: (node) => this._on_node_dblclick(node),
				onEdgeClick: (edge) => this._on_edge_click(edge),
			});

			// Update toolbar references
			const $toolbar = this.$body.find(".caps-graph-toolbar-extra")[0];
			const $search = this.$body.find(".caps-graph-search-bar")[0];
			if ($toolbar) {
				$toolbar.innerHTML = "";
				frappe.visual.LayoutManager.createToolbar($toolbar, this.engine, mode.layout);
			}
			if ($search) {
				$search.innerHTML = "";
				frappe.visual.LayoutManager.createSearchBar($search, this.engine);
			}

			// View controls overlay
			const $viewCtrl = this.$body.find(".caps-graph-view-controls")[0];
			if ($viewCtrl) {
				$viewCtrl.innerHTML = "";
				frappe.visual.LayoutManager.createViewControls($viewCtrl, this.engine);
			}

			this._loaded = true;
			this._update_legend();
		} catch (err) {
			container.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-danger);">${__("Error loading graph")}: ${err.message || err}</div>`;
		}
	}

	_on_node_click(node) {
		new frappe.visual.FloatingWindow({
			title: `${node.icon || ""} ${node.label}`,
			color: "var(--caps-brand)",
			content: this._build_summary(node),
			width: 340, height: 240,
		});
	}

	_on_node_dblclick(node) {
		// Navigate to DocType list based on node type
		const routes = {
			capability: "Capability", capability_inactive: "Capability",
			bundle: "Capability Bundle", group: "Permission Group",
			role: "Role Capability Map", user: "User Capability",
			policy: "Capability Policy", field_map: "Field Capability Map",
			action_map: "Action Capability Map", category_hub: "Capability",
			request: "Capability Request", rate_limit: "Capability Rate Limit",
		};
		const dt = routes[node.type];
		if (dt) frappe.set_route("List", dt);
	}

	_on_edge_click(edge) {
		if (edge.label) {
			frappe.show_alert({ message: `${edge.label}`, indicator: "blue" });
		}
	}

	_build_summary(node) {
		if (!node.summary) return `<p>${node.label}</p>`;
		let h = '<div class="caps-float-summary">';
		for (const [k, v] of Object.entries(node.summary)) {
			h += `<div class="caps-float-row"><span class="caps-float-key">${k}</span><span class="caps-float-val">${v}</span></div>`;
		}
		return h + "</div>";
	}

	_update_legend() {
		const $legend = this.$body.find(".caps-graph-legend");
		const legends = {
			hierarchy: [
				{ color: "var(--caps-brand)", label: __("Active Capability") },
				{ color: "#94a3b8", label: __("Inactive") },
				{ color: "#059669", label: __("Category") },
			],
			prerequisites: [
				{ color: "#ef4444", label: __("Hard Prerequisite"), style: "solid" },
				{ color: "#f59e0b", label: __("Soft Prerequisite"), style: "dashed" },
			],
			bundles: [
				{ color: "#8b5cf6", label: __("Bundle") },
				{ color: "var(--caps-brand)", label: __("Capability") },
			],
			groups: [
				{ color: "#3b82f6", label: __("Group") },
			],
			roles: [
				{ color: "#f59e0b", label: __("Role") },
				{ color: "var(--caps-brand)", label: __("Capability") },
			],
		};
		const items = legends[this.current_mode] || [];
		let h = "";
		items.forEach(i => {
			const border = i.style === "dashed" ? "border-bottom:2px dashed " + i.color : "";
			h += `<span class="legend-item" style="margin-right:16px;"><span style="color:${i.color};${border}">●</span> ${i.label}</span>`;
		});
		$legend.html(h);
	}

	show_help() {
		new frappe.visual.FloatingWindow({
			title: `❓ ${__("Graph Explorer Help")}`,
			color: "var(--caps-brand)", width: 420, height: 350,
			content: `<div style="padding:12px;line-height:1.7;">
				<p><strong>${__("CAPS Graph Explorer")}</strong></p>
				<ul style="padding-left:18px;">
					<li><strong>${__("Hierarchy")}</strong> — ${__("Shows capability parent→child relationships grouped by category")}</li>
					<li><strong>${__("Prerequisites")}</strong> — ${__("Shows hard/soft prerequisite dependencies between capabilities")}</li>
					<li><strong>${__("Bundles")}</strong> — ${__("Shows which capabilities are grouped into bundles")}</li>
					<li><strong>${__("Groups")}</strong> — ${__("Shows permission group hierarchy and membership")}</li>
					<li><strong>${__("Role Map")}</strong> — ${__("Shows Frappe roles mapped to CAPS capabilities")}</li>
				</ul>
				<p>${__("Click a node for details. Double-click to navigate. Use toolbar to switch layouts.")}</p>
			</div>`,
		});
	}

	destroy() {
		if (this.engine) { this.engine.destroy(); this.engine = null; }
		frappe.visual.FloatingWindow.closeAll();
	}
}
