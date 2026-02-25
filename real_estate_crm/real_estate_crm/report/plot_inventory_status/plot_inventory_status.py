# Copyright (c) 2026, Real Estate CRM and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"fieldname": "plot_number", "label": "Plot Number", "fieldtype": "Data", "width": 120},
		{"fieldname": "project", "label": "Project", "fieldtype": "Link", "options": "RE Project", "width": 150},
		{"fieldname": "sector", "label": "Sector", "fieldtype": "Data", "width": 100},
		{"fieldname": "plot_type", "label": "Plot Type", "fieldtype": "Data", "width": 100},
		{"fieldname": "facing", "label": "Facing", "fieldtype": "Data", "width": 80},
		{"fieldname": "plot_area", "label": "Area", "fieldtype": "Float", "width": 80},
		{"fieldname": "area_unit", "label": "Area Unit", "fieldtype": "Data", "width": 80},
		{"fieldname": "rate_per_unit", "label": "Rate", "fieldtype": "Currency", "width": 100},
		{"fieldname": "total_value", "label": "Total Value", "fieldtype": "Currency", "width": 120},
		{"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 90},
		{"fieldname": "booking", "label": "Booking", "fieldtype": "Link", "options": "RE Booking", "width": 130},
		{"fieldname": "customer_name", "label": "Customer Name", "fieldtype": "Data", "width": 150},
		{"fieldname": "rm_name", "label": "RM Name", "fieldtype": "Data", "width": 130},
		{"fieldname": "booking_date", "label": "Booking Date", "fieldtype": "Date", "width": 110},
	]


def get_data(filters):
	conditions = get_conditions(filters)

	data = frappe.db.sql(
		"""
		SELECT
			p.plot_number,
			p.project,
			p.sector,
			p.plot_type,
			p.facing,
			p.plot_area,
			p.area_unit,
			p.rate_per_unit,
			p.total_value,
			p.status,
			p.booking,
			b.customer AS customer_name,
			rm.rm_name AS rm_name,
			b.booking_date
		FROM `tabRE Plot` p
		LEFT JOIN `tabRE Booking` b ON b.name = p.booking AND b.docstatus = 1
		LEFT JOIN `tabRE Relationship Manager` rm ON rm.name = b.assigned_rm
		WHERE 1=1 {conditions}
		ORDER BY p.project, p.sector, p.plot_number
		""".format(conditions=conditions),
		filters,
		as_dict=True,
	)

	return data


def get_conditions(filters):
	conditions = ""

	if filters.get("project"):
		conditions += " AND p.project = %(project)s"

	if filters.get("status"):
		conditions += " AND p.status = %(status)s"

	if filters.get("facing"):
		conditions += " AND p.facing = %(facing)s"

	if filters.get("sector"):
		conditions += " AND p.sector LIKE CONCAT('%%', %(sector)s, '%%')"

	return conditions
