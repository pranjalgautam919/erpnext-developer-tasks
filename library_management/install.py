import frappe


def after_install():
    """Create sample data and the Librarian role after installation."""
    _create_librarian_role()
    _create_sample_data()


def _create_librarian_role():
    """Create a Librarian role if it doesn't exist."""
    if not frappe.db.exists("Role", "Librarian"):
        role = frappe.get_doc({
            "doctype": "Role",
            "role_name": "Librarian",
            "desk_access": 1,
        })
        role.insert(ignore_permissions=True)
        frappe.db.commit()
        print("✓ Librarian role created.")
    else:
        print("  Librarian role already exists, skipping.")


def _create_sample_data():
    """Insert a few sample books and one member for demo purposes."""
    sample_books = [
        {
            "doctype": "Book",
            "title": "The Pragmatic Programmer",
            "author": "David Thomas, Andrew Hunt",
            "isbn": "9780135957059",
            "publisher": "Addison-Wesley",
            "total_copies": 3,
            "available_copies": 3,
            "status": "Available",
            "description": "A classic guide to software craftsmanship.",
        },
        {
            "doctype": "Book",
            "title": "Clean Code",
            "author": "Robert C. Martin",
            "isbn": "9780132350884",
            "publisher": "Prentice Hall",
            "total_copies": 2,
            "available_copies": 2,
            "status": "Available",
            "description": "Principles, patterns, and practices of writing clean code.",
        },
        {
            "doctype": "Book",
            "title": "Design Patterns",
            "author": "Gang of Four",
            "isbn": "9780201633610",
            "publisher": "Addison-Wesley",
            "total_copies": 1,
            "available_copies": 1,
            "status": "Available",
            "description": "Elements of reusable object-oriented software.",
        },
    ]

    for book_data in sample_books:
        if not frappe.db.exists("Book", book_data["isbn"]):
            book = frappe.get_doc(book_data)
            book.insert(ignore_permissions=True)
            print(f"✓ Book '{book_data['title']}' created.")
        else:
            print(f"  Book '{book_data['title']}' already exists, skipping.")

    # Sample member
    from frappe.utils import today, add_years
    if not frappe.db.exists("Library Member", {"email": "demo@library.local"}):
        member = frappe.get_doc({
            "doctype": "Library Member",
            "first_name": "Demo",
            "last_name": "User",
            "email": "demo@library.local",
            "phone": "+91-9000000000",
            "membership_status": "Active",
            "membership_date": today(),
            "membership_expiry_date": add_years(today(), 1),
        })
        member.insert(ignore_permissions=True)
        print("✓ Demo Library Member created.")

    frappe.db.commit()
    print("\nSample data setup complete.")
