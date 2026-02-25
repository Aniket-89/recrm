import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class REPlot(Document):
    def validate(self):
        self._compute_total_value()
        self._validate_status_change()

    def _compute_total_value(self):
        """total_value = plot_area × rate_per_unit (PRD §4.2)"""
        self.total_value = flt(self.plot_area) * flt(self.rate_per_unit)

    def _validate_status_change(self):
        """
        Only RE Admin / System Manager may change plot status manually.
        All other status changes must flow through the RE Booking workflow
        (which uses db_set to bypass this guard). (PRD §4.2)
        """
        if self.is_new():
            return

        old_status = frappe.db.get_value("RE Plot", self.name, "status")
        if old_status == self.status:
            return

        if frappe.session.user == "Administrator":
            return
        if frappe.has_role("RE Admin") or frappe.has_role("System Manager"):
            return

        frappe.throw(
            _(
                "Plot status can only be changed through the booking workflow. "
                "Contact RE Admin for manual overrides."
            ),
            exc=frappe.PermissionError,
            title=_("Status Change Not Allowed"),
        )
