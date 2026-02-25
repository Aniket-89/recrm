import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class REPaymentPlanTemplate(Document):
    def validate(self):
        self._sort_stages()
        self._compute_total_percentage()
        self._validate_total_percentage()

    def _sort_stages(self):
        self.stages.sort(key=lambda s: s.stage_order or 0)

    def _compute_total_percentage(self):
        self.total_percentage = sum(flt(s.percentage) for s in self.stages)

    def _validate_total_percentage(self):
        if abs(self.total_percentage - 100.0) > 0.01:
            frappe.throw(
                _(
                    "Stage percentages must total exactly 100%. "
                    "Current total: {0}%"
                ).format(self.total_percentage),
                title=_("Invalid Payment Plan"),
            )

    def _validate_possession_stage(self):
        possession_stages = [s for s in self.stages if s.is_possession_stage]
        if len(possession_stages) > 1:
            frappe.throw(
                _("Only one stage can be marked as the Possession Stage."),
                title=_("Invalid Payment Plan"),
            )
