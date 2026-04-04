// Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
// Developer Website: https://arkan.it.com
// License: MIT
// For license information, please see license.txt

frappe.query_reports["Capability Coverage"] = {
	filters: [
		{
			fieldname: "is_active",
			label: __("Active Only"),
			fieldtype: "Check",
			default: 1,
		},
		{
			fieldname: "category",
			label: __("Category"),
			fieldtype: "Link",
			options: "Capability Category",
		},
	],
};
