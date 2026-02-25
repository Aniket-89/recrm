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
		{
			"fieldname": "rm_name",
			"label": "RM Name",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"fieldname": "rm_code",
			"label": "RM Code",
			"fieldtype": "Link",
			"options": "RE Relationship Manager",
			"width": 140,
		},
		{
			"fieldname": "status",
			"label": "Status",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"fieldname": "leads_assigned",
			"label": "Leads Assigned",
			"fieldtype": "Int",
			"width": 130,
		},
		{
			"fieldname": "opportunities",
			"label": "Opportunities",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"fieldname": "bookings_closed",
			"label": "Bookings Closed",
			"fieldtype": "Int",
			"width": 130,
		},
		{
			"fieldname": "total_revenue",
			"label": "Total Revenue",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"fieldname": "outstanding_collection",
			"label": "Outstanding Collection",
			"fieldtype": "Currency",
			"width": 170,
		},
	]


def get_data(filters):
	conditions = ""
	if filters and filters.get("rm"):
		conditions += " AND rm.name = %(rm)s"

	# Get all RMs
	rm_data = frappe.db.sql(
		"""
		SELECT
			rm.name AS rm_code,
			rm.rm_name,
			rm.status
		FROM
			`tabRE Relationship Manager` rm
		WHERE
			1=1
			{conditions}
		ORDER BY
			rm.rm_name
	""".format(conditions=conditions),
		filters,
		as_dict=True,
	)

	project_condition = ""
	if filters and filters.get("project"):
		project_condition = " AND project = %(project)s"

	data = []
	for rm in rm_data:
		row = {
			"rm_name": rm.rm_name,
			"rm_code": rm.rm_code,
			"status": rm.status,
		}

		# Count leads assigned to this RM
		lead_count = frappe.db.sql(
			"""
			SELECT COUNT(*) AS cnt
			FROM `tabLead`
			WHERE re_assigned_rm = %(rm_code)s
		""",
			{"rm_code": rm.rm_code},
			as_dict=True,
		)
		row["leads_assigned"] = lead_count[0].cnt if lead_count else 0

		# Count opportunities assigned to this RM
		opp_count = frappe.db.sql(
			"""
			SELECT COUNT(*) AS cnt
			FROM `tabOpportunity`
			WHERE re_assigned_rm = %(rm_code)s
		""",
			{"rm_code": rm.rm_code},
			as_dict=True,
		)
		row["opportunities"] = opp_count[0].cnt if opp_count else 0

		# Count bookings closed (status = Completed) and total revenue
		booking_data = frappe.db.sql(
			"""
			SELECT
				COUNT(*) AS cnt,
				SUM(final_value) AS total_revenue
			FROM `tabRE Booking`
			WHERE assigned_rm = %(rm_code)s
				AND docstatus = 1
				AND status = 'Completed'
				{project_condition}
		""".format(project_condition=project_condition),
			{"rm_code": rm.rm_code, "project": filters.get("project") if filters else None},
			as_dict=True,
		)
		row["bookings_closed"] = booking_data[0].cnt if booking_data else 0

		# Total revenue from all non-cancelled bookings
		revenue_data = frappe.db.sql(
			"""
			SELECT
				IFNULL(SUM(final_value), 0) AS total_revenue
			FROM `tabRE Booking`
			WHERE assigned_rm = %(rm_code)s
				AND docstatus = 1
				AND status != 'Cancelled'
				{project_condition}
		""".format(project_condition=project_condition),
			{"rm_code": rm.rm_code, "project": filters.get("project") if filters else None},
			as_dict=True,
		)
		row["total_revenue"] = flt(revenue_data[0].total_revenue) if revenue_data else 0

		# Outstanding collection from payment schedules
		outstanding_data = frappe.db.sql(
			"""
			SELECT
				IFNULL(SUM(ps.balance), 0) AS outstanding
			FROM `tabRE Booking Payment Schedule` ps
			INNER JOIN `tabRE Booking` b ON ps.parent = b.name
			WHERE b.assigned_rm = %(rm_code)s
				AND b.docstatus = 1
				AND ps.status NOT IN ('Paid', 'Cancelled')
				{project_condition}
		""".format(project_condition=project_condition.replace("project", "b.project") if project_condition else ""),
			{"rm_code": rm.rm_code, "project": filters.get("project") if filters else None},
			as_dict=True,
		)
		row["outstanding_collection"] = flt(outstanding_data[0].outstanding) if outstanding_data else 0

		data.append(row)

	return data
