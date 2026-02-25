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
		{"fieldname": "booking_no", "label": "Booking No", "fieldtype": "Link", "options": "RE Booking", "width": 140},
		{"fieldname": "booking_date", "label": "Date", "fieldtype": "Date", "width": 100},
		{"fieldname": "customer", "label": "Customer", "fieldtype": "Link", "options": "Customer", "width": 150},
		{"fieldname": "plot", "label": "Plot", "fieldtype": "Link", "options": "RE Plot", "width": 130},
		{"fieldname": "project", "label": "Project", "fieldtype": "Link", "options": "RE Project", "width": 150},
		{"fieldname": "payment_plan_type", "label": "Plan Type", "fieldtype": "Link", "options": "RE Payment Plan Template", "width": 130},
		{"fieldname": "plot_value", "label": "Plot Value", "fieldtype": "Currency", "width": 120},
		{"fieldname": "discount", "label": "Discount", "fieldtype": "Currency", "width": 100},
		{"fieldname": "final_value", "label": "Final Value", "fieldtype": "Currency", "width": 120},
		{"fieldname": "rm_name", "label": "RM Name", "fieldtype": "Data", "width": 130},
		{"fieldname": "booking_status", "label": "Status", "fieldtype": "Data", "width": 120},
	]


def get_data(filters):
	conditions = get_conditions(filters)

	data = frappe.db.sql(
		"""
		SELECT
			b.name AS booking_no,
			b.booking_date,
			b.customer,
			b.plot,
			b.project,
			b.payment_plan_type,
			b.plot_value,
			b.discount,
			b.final_value,
			rm.rm_name AS rm_name,
			b.booking_status
		FROM `tabRE Booking` b
		LEFT JOIN `tabRE Relationship Manager` rm ON rm.name = b.assigned_rm
		WHERE b.docstatus = 1 {conditions}
		ORDER BY b.booking_date DESC, b.name
		""".format(conditions=conditions),
		filters,
		as_dict=True,
	)

	return data


def get_conditions(filters):
	conditions = ""

	if filters.get("project"):
		conditions += " AND b.project = %(project)s"

	if filters.get("assigned_rm"):
		conditions += " AND b.assigned_rm = %(assigned_rm)s"

	if filters.get("from_date"):
		conditions += " AND b.booking_date >= %(from_date)s"

	if filters.get("to_date"):
		conditions += " AND b.booking_date <= %(to_date)s"

	if filters.get("booking_status"):
		conditions += " AND b.booking_status = %(booking_status)s"

	return conditions
