// Copyright (c) 2026, Real Estate CRM and contributors
// For license information, please see license.txt

frappe.query_reports["Plot Inventory Status"] = {
	filters: [
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			options: "RE Project",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nAvailable\nBooked\nRegistered\nOn Hold",
		},
		{
			fieldname: "facing",
			label: __("Facing"),
			fieldtype: "Select",
			options: "\nNorth\nSouth\nEast\nWest\nCorner\nOther",
		},
		{
			fieldname: "sector",
			label: __("Sector"),
			fieldtype: "Data",
		},
	],
};
