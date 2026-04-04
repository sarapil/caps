// Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
// Developer Website: https://arkan.it.com
// License: MIT
// For license information, please see license.txt

frappe.query_reports["User Access Matrix"] = {
	filters: [
		{
			fieldname: "user",
			label: __("User"),
			fieldtype: "Link",
			options: "User",
		},
		{
			fieldname: "capability",
			label: __("Capability"),
			fieldtype: "Link",
			options: "Capability",
		},
		{
			fieldname: "category",
			label: __("Category"),
			fieldtype: "Link",
			options: "Capability Category",
		},
		{
			fieldname: "channel",
			label: __("Channel"),
			fieldtype: "Select",
			options: "\nDirect\nGroup\nRole",
		},
		{
			fieldname: "hide_empty",
			label: __("Hide Empty Rows"),
			fieldtype: "Check",
			default: 1,
		},
	],
};
