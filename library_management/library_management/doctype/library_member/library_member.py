import frappe
from frappe.model.document import Document
from frappe.utils import today, getdate


class LibraryMember(Document):
    """
    Manages library members: validation, auto-fill full name,
    and automatic expiry status update.
    """

    def before_save(self):
        self.set_full_name()
        self.check_membership_expiry()
        self.validate_membership_dates()

    def set_full_name(self):
        """Combine first and last name into full_name."""
        parts = [self.first_name or "", self.last_name or ""]
        self.full_name = " ".join(p for p in parts if p).strip()

    def check_membership_expiry(self):
        """Auto-update status to Expired when expiry date is in the past."""
        if self.membership_expiry_date:
            if getdate(self.membership_expiry_date) < getdate(today()):
                if self.membership_status == "Active":
                    self.membership_status = "Expired"
                    frappe.msgprint(
                        msg=f"Membership for {self.full_name} has been marked as Expired "
                            f"because the expiry date ({self.membership_expiry_date}) has passed.",
                        title="Membership Expired",
                        indicator="orange",
                    )

    def validate_membership_dates(self):
        """Ensure expiry date is after membership start date."""
        if self.membership_date and self.membership_expiry_date:
            if getdate(self.membership_expiry_date) <= getdate(self.membership_date):
                frappe.throw(
                    msg="Membership Expiry Date must be after Membership Date.",
                    title="Invalid Dates",
                )

    def is_membership_valid(self):
        """
        Returns True if this member has an active, non-expired membership.
        Called by Book Transaction before allowing a book to be issued.
        """
        if self.membership_status != "Active":
            return False
        if self.membership_expiry_date:
            if getdate(self.membership_expiry_date) < getdate(today()):
                return False
        return True
