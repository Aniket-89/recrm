"""
Project Dashboard API for Real Estate CRM.

Returns project-scoped metrics: plot inventory, booking stats, revenue,
overdue payments, assigned RMs, and plot status breakdown.
"""

import frappe
from frappe import _
from frappe.utils import nowdate, flt, add_days


@frappe.whitelist()
def get_project_dashboard_data(project):
    """Main API -- returns all project dashboard sections."""
    if not frappe.db.exists("RE Project", project):
        frappe.throw(_("Project {0} not found").format(project))

    data = {}
    data["project_info"] = _get_project_info(project)
    data["kpi_cards"] = _get_kpi_cards(project)
    data["plot_status_breakdown"] = _get_plot_status_breakdown(project)
    data["plot_inventory"] = _get_plot_inventory(project)
    data["assigned_rms"] = _get_assigned_rms(project)
    data["monthly_collections"] = _get_monthly_collections(project)
    data["recent_bookings"] = _get_recent_bookings(project)
    data["overdue_payments"] = _get_overdue_payments(project)
    data["upcoming_dues"] = _get_upcoming_dues(project)
    return data


def _get_project_info(project):
    """Basic project details for the header."""
    return frappe.db.get_value(
        "RE Project", project,
        ["name", "project_name", "status", "location", "city", "state",
         "total_plots", "project_start_date", "expected_possession_date"],
        as_dict=True,
    )


def _get_kpi_cards(project):
    """Project-scoped KPI numbers."""
    total_plots = frappe.db.count("RE Plot", {"project": project})
    available = frappe.db.count("RE Plot", {"project": project, "status": "Available"})
    booked = frappe.db.count("RE Plot", {"project": project, "status": "Booked"})
    registered = frappe.db.count("RE Plot", {"project": project, "status": "Registered"})
    on_hold = frappe.db.count("RE Plot", {"project": project, "status": "On Hold"})

    active_bookings = frappe.db.count(
        "RE Booking",
        {"project": project, "booking_status": ["in", ["Booked", "Payment In Progress", "Possession Due"]]},
    )

    total_revenue = frappe.db.sql(
        """
        SELECT COALESCE(SUM(final_value), 0) as total
        FROM `tabRE Booking`
        WHERE project = %s AND booking_status NOT IN ('Cancelled', 'Draft')
        """,
        (project,), as_dict=True,
    )[0].total

    total_received = frappe.db.sql(
        """
        SELECT COALESCE(SUM(ps.amount_received), 0) as total
        FROM `tabRE Booking Payment Schedule` ps
        JOIN `tabRE Booking` b ON ps.parent = b.name
        WHERE b.project = %s AND b.booking_status NOT IN ('Cancelled', 'Draft')
        """,
        (project,), as_dict=True,
    )[0].total

    total_outstanding = frappe.db.sql(
        """
        SELECT COALESCE(SUM(ps.balance), 0) as total
        FROM `tabRE Booking Payment Schedule` ps
        JOIN `tabRE Booking` b ON ps.parent = b.name
        WHERE b.project = %s AND b.booking_status NOT IN ('Cancelled', 'Draft')
        """,
        (project,), as_dict=True,
    )[0].total

    overdue_amount = frappe.db.sql(
        """
        SELECT COALESCE(SUM(ps.balance), 0) as total
        FROM `tabRE Booking Payment Schedule` ps
        JOIN `tabRE Booking` b ON ps.parent = b.name
        WHERE ps.status = 'Overdue'
          AND b.project = %s AND b.booking_status NOT IN ('Cancelled', 'Draft')
        """,
        (project,), as_dict=True,
    )[0].total

    return {
        "total_plots": total_plots,
        "available": available,
        "booked": booked,
        "registered": registered,
        "on_hold": on_hold,
        "active_bookings": active_bookings,
        "total_revenue": flt(total_revenue),
        "total_received": flt(total_received),
        "total_outstanding": flt(total_outstanding),
        "overdue_amount": flt(overdue_amount),
    }


def _get_plot_status_breakdown(project):
    """Plot counts grouped by status for the donut chart."""
    return frappe.db.sql(
        """
        SELECT status, COUNT(*) as count
        FROM `tabRE Plot`
        WHERE project = %s
        GROUP BY status
        ORDER BY FIELD(status, 'Available', 'Booked', 'Registered', 'On Hold')
        """,
        (project,), as_dict=True,
    ) or []


def _get_plot_inventory(project):
    """All plots in this project with details."""
    return frappe.db.sql(
        """
        SELECT
            pl.name, pl.plot_number, pl.status, pl.sector,
            pl.plot_type, pl.facing, pl.plot_area, pl.area_unit,
            pl.rate_per_unit, pl.total_value, pl.booking,
            b.customer
        FROM `tabRE Plot` pl
        LEFT JOIN `tabRE Booking` b ON pl.booking = b.name
            AND b.booking_status NOT IN ('Cancelled', 'Draft')
        WHERE pl.project = %s
        ORDER BY pl.plot_number
        """,
        (project,), as_dict=True,
    ) or []


def _get_assigned_rms(project):
    """RMs assigned to this project via the RE RM Project child table."""
    return frappe.db.sql(
        """
        SELECT
            rm.name, rm.rm_name, rm.rm_code, rm.mobile, rm.email,
            rm.designation, rm.status,
            (SELECT COUNT(*) FROM `tabRE Booking`
             WHERE assigned_rm = rm.name AND project = %s
               AND booking_status NOT IN ('Cancelled', 'Draft')
            ) as booking_count
        FROM `tabRE RM Project` rmp
        JOIN `tabRE Relationship Manager` rm ON rmp.parent = rm.name
        WHERE rmp.project = %s AND rm.status = 'Active'
        ORDER BY rm.rm_name
        """,
        (project, project), as_dict=True,
    ) or []


def _get_monthly_collections(project):
    """Last 6 months of payment collections for this project."""
    return frappe.db.sql(
        """
        SELECT
            DATE_FORMAT(ps.receipt_date, '%%Y-%%m') as month,
            SUM(ps.amount_received) as collected
        FROM `tabRE Booking Payment Schedule` ps
        JOIN `tabRE Booking` b ON ps.parent = b.name
        WHERE ps.receipt_date IS NOT NULL
          AND ps.amount_received > 0
          AND ps.receipt_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
          AND b.project = %s
          AND b.booking_status NOT IN ('Cancelled', 'Draft')
        GROUP BY DATE_FORMAT(ps.receipt_date, '%%Y-%%m')
        ORDER BY month
        """,
        (project,), as_dict=True,
    ) or []


def _get_recent_bookings(project, limit=10):
    """Recent bookings for this project."""
    return frappe.db.sql(
        """
        SELECT
            b.name, b.booking_date, b.plot,
            b.customer, b.booking_status, b.final_value,
            b.assigned_rm
        FROM `tabRE Booking` b
        WHERE b.project = %s
        ORDER BY b.creation DESC
        LIMIT %s
        """,
        (project, limit), as_dict=True,
    ) or []


def _get_overdue_payments(project, limit=10):
    """Overdue payment stages for this project."""
    today = nowdate()
    return frappe.db.sql(
        """
        SELECT
            ps.parent as booking,
            ps.stage_name,
            ps.due_date,
            ps.amount_due,
            ps.balance,
            b.customer,
            b.plot,
            DATEDIFF(%s, ps.due_date) as days_overdue
        FROM `tabRE Booking Payment Schedule` ps
        JOIN `tabRE Booking` b ON ps.parent = b.name
        WHERE ps.status = 'Overdue'
          AND b.project = %s
          AND b.booking_status NOT IN ('Cancelled', 'Draft')
        ORDER BY ps.due_date ASC
        LIMIT %s
        """,
        (today, project, limit), as_dict=True,
    ) or []


def _get_upcoming_dues(project, limit=5):
    """Payment stages due in the next 7 days for this project."""
    today = nowdate()
    next_week = add_days(today, 7)
    return frappe.db.sql(
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
          AND b.project = %s
          AND b.booking_status NOT IN ('Cancelled', 'Draft')
        ORDER BY ps.due_date ASC
        LIMIT %s
        """,
        (today, next_week, project, limit), as_dict=True,
    ) or []
