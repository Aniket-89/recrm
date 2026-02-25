# Copyright (c) 2026, Real Estate CRM and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, getdate


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"fieldname": "date",
			"label": "Date",
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"fieldname": "payment_entry_no",
			"label": "Payment Entry No",
			"fieldtype": "Link",
			"options": "RE Payment Entry",
			"width": 170,
		},
		{
			"fieldname": "booking_no",
			"label": "Booking No",
			"fieldtype": "Link",
			"options": "RE Booking",
			"width": 160,
		},
		{
			"fieldname": "stage_name",
			"label": "Stage Name",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"fieldname": "amount",
			"label": "Amount",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"fieldname": "payment_mode",
			"label": "Payment Mode",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"fieldname": "reference_no",
			"label": "Reference No",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"fieldname": "balance_after",
			"label": "Balance After",
			"fieldtype": "Currency",
			"width": 140,
		},
	]


def get_data(filters):
	if not filters or not filters.get("customer"):
		return []

	conditions = " AND b.customer = %(customer)s"

	if filters.get("project"):
		conditions += " AND b.project = %(project)s"
	if filters.get("from_date"):
		conditions += " AND pe.posting_date >= %(from_date)s"
	if filters.get("to_date"):
		conditions += " AND pe.posting_date <= %(to_date)s"

	# Get total due for the customer across all their bookings (for running balance)
	total_due_data = frappe.db.sql(
		"""
		SELECT
			IFNULL(SUM(b.final_value), 0) AS total_due
		FROM `tabRE Booking` b
		WHERE b.customer = %(customer)s
			AND b.docstatus = 1
			AND b.status != 'Cancelled'
			{project_condition}
	""".format(
			project_condition=" AND b.project = %(project)s" if filters.get("project") else ""
		),
		filters,
		as_dict=True,
	)
	total_due = flt(total_due_data[0].total_due) if total_due_data else 0

	# Get all payment entries for this customer
	payment_entries = frappe.db.sql(
		"""
		SELECT
			pe.posting_date AS date,
			pe.name AS payment_entry_no,
			pe.booking AS booking_no,
			pe.stage_name AS stage_name,
			pe.amount AS amount,
			pe.payment_mode AS payment_mode,
			pe.reference_no AS reference_no
		FROM
			`tabRE Payment Entry` pe
		INNER JOIN `tabRE Booking` b ON pe.booking = b.name
		WHERE
			pe.docstatus = 1
			{conditions}
		ORDER BY
			pe.posting_date, pe.creation
	""".format(conditions=conditions),
		filters,
		as_dict=True,
	)

	# Calculate cumulative received to derive running balance
	# Get payments before the from_date to compute the opening cumulative received
	cumulative_received_before = 0
	if filters.get("from_date"):
		prior_data = frappe.db.sql(
			"""
			SELECT
				IFNULL(SUM(pe.amount), 0) AS total_received
			FROM `tabRE Payment Entry` pe
			INNER JOIN `tabRE Booking` b ON pe.booking = b.name
			WHERE pe.docstatus = 1
				AND b.customer = %(customer)s
				AND pe.posting_date < %(from_date)s
				{project_condition}
		""".format(
				project_condition=" AND b.project = %(project)s" if filters.get("project") else ""
			),
			filters,
			as_dict=True,
		)
		cumulative_received_before = flt(prior_data[0].total_received) if prior_data else 0

	# Calculate running balance: total_due - cumulative_received
	cumulative_received = cumulative_received_before
	for row in payment_entries:
		cumulative_received += flt(row.amount)
		row["balance_after"] = flt(total_due) - flt(cumulative_received)

	return payment_entries
