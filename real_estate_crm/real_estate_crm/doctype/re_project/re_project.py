import frappe
from frappe import _
from frappe.model.document import Document


class REProject(Document):
    def validate(self):
        self._validate_dates()

    def _validate_dates(self):
        if self.project_start_date and self.expected_possession_date:
            if self.expected_possession_date < self.project_start_date:
                frappe.throw(
                    _("Expected Possession Date cannot be before Project Start Date."),
                    title=_("Invalid Date"),
                )
