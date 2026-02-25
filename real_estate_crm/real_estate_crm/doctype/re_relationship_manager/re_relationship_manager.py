import frappe
from frappe import _
from frappe.model.document import Document


class RERelationshipManager(Document):
    def before_insert(self):
        self._auto_generate_rm_code()

    def validate(self):
        self._auto_generate_rm_code()

    def _auto_generate_rm_code(self):
        """
        Auto-generate rm_code from name initials if the user left it blank.
        e.g. "Rahul Sharma" → "RS", "RS01" if RS already exists.
        """
        if self.rm_code:
            return

        words = (self.rm_name or "").split()
        initials = "".join(w[0].upper() for w in words if w)
        if not initials:
            return

        code = initials
        counter = 1
        # Exclude self when checking uniqueness on subsequent saves
        while frappe.db.exists(
            "RE Relationship Manager", {"rm_code": code, "name": ("!=", self.name or "")}
        ):
            code = f"{initials}{counter:02d}"
            counter += 1

        self.rm_code = code

    @frappe.whitelist()
    def get_performance_stats(self):
        """
        Returns stats rendered in the dashboard section (PRD §6.1).
        Called from JavaScript on form refresh.
        """
        leads = frappe.db.count("Lead", {"re_assigned_rm": self.name})
        bookings = frappe.db.get_all(
            "RE Booking",
            filters={"assigned_rm": self.name},
            fields=["name", "booking_status", "final_value", "plot", "project"],
        )
        total_revenue = sum(b.final_value or 0 for b in bookings if b.booking_status != "Cancelled")
        active_bookings = [
            b for b in bookings if b.booking_status not in ("Completed", "Cancelled")
        ]
        closed_bookings = len(
            [b for b in bookings if b.booking_status == "Completed"]
        )

        return {
            "leads": leads,
            "closed_bookings": closed_bookings,
            "total_revenue": total_revenue,
            "active_bookings": active_bookings,
        }
