// Copyright (c) 2026, Real Estate CRM and contributors
// For license information, please see license.txt

frappe.query_reports["Overdue Payment Report"] = {
	filters: [
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			options: "RE Project",
		},
		{
			fieldname: "rm",
			label: __("Relationship Manager"),
			fieldtype: "Link",
			options: "RE Relationship Manager",
		},
	],
};
