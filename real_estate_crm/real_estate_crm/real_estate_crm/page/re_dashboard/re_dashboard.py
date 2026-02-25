"""
Dashboard API for Real Estate CRM homepage.

Returns aggregated metrics: plot counts, booking stats, revenue,
overdue payments, recent bookings, and plot status breakdown.
"""

import frappe
from frappe import _
from frappe.utils import nowdate, flt, getdate, add_days


@frappe.whitelist()
def get_dashboard_data():
    """Main API — returns all dashboard sections in one call."""
    data = {}
    data["kpi_cards"] = _get_kpi_cards()
    data["plot_status_breakdown"] = _get_plot_status_breakdown()
    data["recent_bookings"] = _get_recent_bookings()
    data["overdue_payments"] = _get_overdue_payments()
    data["upcoming_dues"] = _get_upcoming_dues()
    data["project_summary"] = _get_project_summary()
    data["monthly_collections"] = _get_monthly_collections()
    return data


def _get_kpi_cards():
    """Top-level KPI numbers."""
    total_projects = frappe.db.count("RE Project")
    total_plots = frappe.db.count("RE Plot")
    available_plots = frappe.db.count("RE Plot", {"status": "Available"})
    booked_plots = frappe.db.count("RE Plot", {"status": "Booked"})

    active_bookings = frappe.db.count(
        "RE Booking",
        {"booking_status": ["in", ["Booked", "Payment In Progress", "Possession Due"]]},
    )

    total_revenue = frappe.db.sql(
        """
        SELECT COALESCE(SUM(final_value), 0) as total
        FROM `tabRE Booking`
        WHERE booking_status NOT IN ('Cancelled', 'Draft')
        """,
        as_dict=True,
    )[0].total

    total_received = frappe.db.sql(
        """
        SELECT COALESCE(SUM(ps.amount_received), 0) as total
        FROM `tabRE Booking Payment Schedule` ps
        JOIN `tabRE Booking` b ON ps.parent = b.name
        WHERE b.booking_status NOT IN ('Cancelled', 'Draft')
        """,
        as_dict=True,
    )[0].total

    total_outstanding = frappe.db.sql(
        """
        SELECT COALESCE(SUM(ps.balance), 0) as total
        FROM `tabRE Booking Payment Schedule` ps
        JOIN `tabRE Booking` b ON ps.parent = b.name
        WHERE b.booking_status NOT IN ('Cancelled', 'Draft')
        """,
        as_dict=True,
    )[0].total

    overdue_amount = frappe.db.sql(
        """
        SELECT COALESCE(SUM(ps.balance), 0) as total
        FROM `tabRE Booking Payment Schedule` ps
        JOIN `tabRE Booking` b ON ps.parent = b.name
        WHERE ps.status = 'Overdue'
          AND b.booking_status NOT IN ('Cancelled', 'Draft')
        """,
        as_dict=True,
    )[0].total

    total_customers = frappe.db.count("Customer")

    return {
        "total_projects": total_projects,
        "total_plots": total_plots,
        "available_plots": available_plots,
        "booked_plots": booked_plots,
        "active_bookings": active_bookings,
        "total_revenue": flt(total_revenue),
        "total_received": flt(total_received),
        "total_outstanding": flt(total_outstanding),
        "overdue_amount": flt(overdue_amount),
        "total_customers": total_customers,
    }


def _get_plot_status_breakdown():
    """Plot counts grouped by status — for the donut chart."""
    result = frappe.db.sql(
        """
        SELECT status, COUNT(*) as count
        FROM `tabRE Plot`
        GROUP BY status
        ORDER BY FIELD(status, 'Available', 'Booked', 'Registered', 'On Hold')
        """,
        as_dict=True,
    )
    return result or []


def _get_recent_bookings(limit=10):
    """Most recent bookings for the activity feed."""
    bookings = frappe.db.sql(
        """
        SELECT
            b.name, b.booking_date, b.project, b.plot,
            b.customer, b.booking_status, b.final_value,
            b.assigned_rm
        FROM `tabRE Booking` b
        ORDER BY b.creation DESC
        LIMIT %s
        """,
        (limit,),
        as_dict=True,
    )
    return bookings or []


def _get_overdue_payments(limit=10):
    """Top overdue payment stages — sorted by days overdue."""
    today = nowdate()
    overdues = frappe.db.sql(
        """
        SELECT
            ps.parent as booking,
            ps.stage_name,
            ps.due_date,
            ps.amount_due,
            ps.balance,
            b.customer,
            b.plot,
            b.project,
            DATEDIFF(%s, ps.due_date) as days_overdue
        FROM `tabRE Booking Payment Schedule` ps
        JOIN `tabRE Booking` b ON ps.parent = b.name
        WHERE ps.status = 'Overdue'
          AND b.booking_status NOT IN ('Cancelled', 'Draft')
        ORDER BY ps.due_date ASC
        LIMIT %s
        """,
        (today, limit),
        as_dict=True,
    )
    return overdues or []


def _get_upcoming_dues(limit=5):
    """Payment stages due in the next 7 days."""
    today = nowdate()
    next_week = add_days(today, 7)
    upcoming = frappe.db.sql(
        """
        SELECT
            ps.parent as booking,
            ps.stage_name,
            ps.due_date,
            ps.amount_due,
            ps.balance,
            b.customer,
            b.plot
        FROM `tabRE Booking Payment Schedule` ps
        JOIN `tabRE Booking` b ON ps.parent = b.name
        WHERE ps.status = 'Pending'
          AND ps.due_date BETWEEN %s AND %s
          AND b.booking_status NOT IN ('Cancelled', 'Draft')
        ORDER BY ps.due_date ASC
        LIMIT %s
        """,
        (today, next_week, limit),
        as_dict=True,
    )
    return upcoming or []


def _get_project_summary():
    """Per-project plot breakdown."""
    summary = frappe.db.sql(
        """
        SELECT
            p.name as project,
            p.project_name,
            COUNT(pl.name) as total_plots,
            SUM(CASE WHEN pl.status = 'Available' THEN 1 ELSE 0 END) as available,
            SUM(CASE WHEN pl.status = 'Booked' THEN 1 ELSE 0 END) as booked,
            SUM(CASE WHEN pl.status = 'Registered' THEN 1 ELSE 0 END) as registered,
            SUM(CASE WHEN pl.status = 'On Hold' THEN 1 ELSE 0 END) as on_hold
        FROM `tabRE Project` p
        LEFT JOIN `tabRE Plot` pl ON pl.project = p.name
        GROUP BY p.name, p.project_name
        ORDER BY p.project_name
        """,
        as_dict=True,
    )
    return summary or []


def _get_monthly_collections():
    """Last 6 months of payment collections for the bar chart."""
    data = frappe.db.sql(
        """
        SELECT
            DATE_FORMAT(ps.receipt_date, '%%Y-%%m') as month,
            SUM(ps.amount_received) as collected
        FROM `tabRE Booking Payment Schedule` ps
        JOIN `tabRE Booking` b ON ps.parent = b.name
        WHERE ps.receipt_date IS NOT NULL
          AND ps.amount_received > 0
          AND ps.receipt_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
          AND b.booking_status NOT IN ('Cancelled', 'Draft')
        GROUP BY DATE_FORMAT(ps.receipt_date, '%%Y-%%m')
        ORDER BY month
        """,
        as_dict=True,
    )
    return data or []
