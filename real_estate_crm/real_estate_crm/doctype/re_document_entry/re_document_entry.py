import frappe
from frappe.model.document import Document
from frappe.utils import nowdate


class REDocumentEntry(Document):
    def before_save(self):
        """Auto-stamp uploaded_on and uploaded_by on first attachment."""
        if self.file and not self.uploaded_on:
            self.uploaded_on = nowdate()
            self.uploaded_by = frappe.session.user
