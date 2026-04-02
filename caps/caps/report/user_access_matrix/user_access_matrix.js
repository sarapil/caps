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
