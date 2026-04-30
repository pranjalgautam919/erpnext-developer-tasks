import frappe
from frappe.model.document import Document


class Book(Document):
    """
    Manages book catalog. Tracks available copies and validates
    ISBN format. Status is updated automatically by Book Transaction.
    """

    def before_save(self):
        self.validate_isbn()
        self.validate_copies()
        self.sync_status()

    def validate_isbn(self):
        """Validate that ISBN contains only digits and hyphens, 10 or 13 digits."""
        if not self.isbn:
            return
        digits = self.isbn.replace("-", "").replace(" ", "")
        if not digits.isdigit():
            frappe.throw(
                msg="ISBN must contain only digits (and optional hyphens).",
                title="Invalid ISBN",
            )
        if len(digits) not in (10, 13):
            frappe.throw(
                msg=f"ISBN must be 10 or 13 digits long. You entered {len(digits)} digits.",
                title="Invalid ISBN",
            )

    def validate_copies(self):
        """Ensure total copies is at least 1."""
        if self.total_copies < 1:
            frappe.throw(
                msg="Total Copies must be at least 1.",
                title="Invalid Copies",
            )
        # On a new book, available_copies should match total_copies
        if self.is_new():
            self.available_copies = self.total_copies

    def sync_status(self):
        """Keep status in sync with available_copies count."""
        if self.available_copies and self.available_copies > 0:
            self.status = "Available"
        else:
            self.status = "Issued"
