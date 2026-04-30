import frappe
from frappe.model.document import Document
from frappe.utils import getdate, today, add_days


class BookTransaction(Document):
    """
    Core business logic for book Issue/Return transactions.

    Issue:
      - Validates member is active and membership is not expired
      - Validates book is Available
      - Sets expected return date (14 days default)
      - Decrements available_copies on the Book
      - Updates Book status to Issued when available_copies reaches 0

    Return:
      - Validates a matching open Issue transaction exists for this member+book
      - Increments available_copies on the Book
      - Updates Book status to Available
      - Records actual return date
    """

    # ------------------------------------------------------------------
    # Frappe lifecycle hooks
    # ------------------------------------------------------------------

    def validate(self):
        """Run all validations before save/submit."""
        self.validate_transaction_date()
        if self.transaction_type == "Issue":
            self.validate_member_active()
            self.validate_book_available()
            self.set_expected_return_date()
        elif self.transaction_type == "Return":
            self.validate_open_issue_exists()

    def before_submit(self):
        """Update Book availability counts on submit."""
        if self.transaction_type == "Issue":
            self._decrement_book_copies()
        elif self.transaction_type == "Return":
            self._increment_book_copies()
            self._close_open_issue()

    def on_cancel(self):
        """Reverse the book copy change on cancel."""
        if self.transaction_type == "Issue":
            self._increment_book_copies()
        elif self.transaction_type == "Return":
            self._decrement_book_copies()

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def validate_transaction_date(self):
        """Transaction date cannot be in the future."""
        if getdate(self.date) > getdate(today()):
            frappe.throw(
                msg="Transaction Date cannot be in the future.",
                title="Invalid Date",
            )

    def validate_member_active(self):
        """Block issue if member is inactive or membership has expired."""
        member = frappe.get_doc("Library Member", self.library_member)

        if member.membership_status == "Inactive":
            frappe.throw(
                msg=f"Member '{member.full_name}' has an Inactive membership. "
                    f"Please renew the membership before issuing a book.",
                title="Inactive Membership",
            )

        if member.membership_expiry_date:
            if getdate(member.membership_expiry_date) < getdate(self.date):
                frappe.throw(
                    msg=f"Member '{member.full_name}' membership expired on "
                        f"{member.membership_expiry_date}. "
                        f"Please renew before issuing a book.",
                    title="Membership Expired",
                )

    def validate_book_available(self):
        """Block issue if all copies of the book are already issued."""
        book = frappe.get_doc("Book", self.book)
        if book.available_copies <= 0 or book.status == "Issued":
            frappe.throw(
                msg=f"Book '{book.title}' is currently not available "
                    f"(all {book.total_copies} copies are issued).",
                title="Book Not Available",
            )

    def set_expected_return_date(self):
        """Default expected return date to 14 days from transaction date."""
        if not self.expected_return_date:
            self.expected_return_date = add_days(self.date, 14)

    def validate_open_issue_exists(self):
        """
        For a Return, verify there is a submitted Issue transaction
        for the same member and book that has not yet been returned.
        """
        open_issue = frappe.db.exists(
            "Book Transaction",
            {
                "library_member": self.library_member,
                "book": self.book,
                "transaction_type": "Issue",
                "docstatus": 1,        # submitted
                "actual_return_date": ("in", (None, "")),
            },
        )
        if not open_issue:
            member_name = frappe.db.get_value(
                "Library Member", self.library_member, "full_name"
            )
            book_title = frappe.db.get_value("Book", self.book, "title")
            frappe.throw(
                msg=f"No open Issue transaction found for member '{member_name}' "
                    f"and book '{book_title}'. Cannot process Return.",
                title="Invalid Return",
            )

    # ------------------------------------------------------------------
    # Book copy management
    # ------------------------------------------------------------------

    def _decrement_book_copies(self):
        """Reduce available_copies by 1 and update status if needed."""
        book = frappe.get_doc("Book", self.book)
        book.available_copies = max(0, (book.available_copies or 1) - 1)
        if book.available_copies == 0:
            book.status = "Issued"
        book.save(ignore_permissions=True)

    def _increment_book_copies(self):
        """Increase available_copies by 1 and update status."""
        book = frappe.get_doc("Book", self.book)
        book.available_copies = min(
            book.total_copies, (book.available_copies or 0) + 1
        )
        book.status = "Available"
        book.save(ignore_permissions=True)

    def _close_open_issue(self):
        """
        Find and cancel the matching open Issue so it cannot be
        returned twice. Also stamp the actual return date on it.
        """
        issue_name = frappe.db.get_value(
            "Book Transaction",
            {
                "library_member": self.library_member,
                "book": self.book,
                "transaction_type": "Issue",
                "docstatus": 1,
                "actual_return_date": ("in", (None, "")),
            },
            "name",
        )
        if issue_name:
            frappe.db.set_value(
                "Book Transaction", issue_name, "actual_return_date", self.date
            )



