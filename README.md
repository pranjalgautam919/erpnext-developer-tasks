# Library Management System – ERPNext Custom App

A Frappe/ERPNext custom app implementing a **Library Management System** with three DocTypes:
`Library Member`, `Book`, and `Book Transaction`.

---

## Table of Contents
1. [What Was Built](#what-was-built)
2. [Installation](#installation)
3. [DocType Reference](#doctype-reference)
4. [Validation Logic](#validation-logic)
5. [Testing Scenarios](#testing-scenarios)
6. [Git Log Summary](#git-log-summary)

---

## What Was Built

| DocType | Purpose |
|---|---|
| **Library Member** | Stores member details, membership status and dates |
| **Book** | Catalog of books with ISBN, copies count, and status |
| **Book Transaction** | Records Issue / Return events, enforces all rules |

---

## Installation

### Prerequisites
- ERPNext v14 or v15 running (Docker or bare-metal)
- `bench` CLI available

### Steps

```bash
# 1. Navigate to your bench directory
cd frappe-bench

# 2. Get the app
bench get-app https://github.com/<your-username>/library_management
# OR copy the folder manually:
cp -r /path/to/library_management apps/library_management

# 3. Install on your site
bench --site library.localhost install-app library_management

# 4. Migrate (creates the DB tables)
bench --site library.localhost migrate

# 5. (Docker users) run inside the backend container:
docker-compose -f pwd.yml exec backend \
  bench --site library.localhost install-app library_management
docker-compose -f pwd.yml exec backend \
  bench --site library.localhost migrate
```

After migration the app seeds **3 sample books** and **1 demo member** automatically.

---

## DocType Reference

### Library Member

**Auto-name**: `LM-.####` (e.g., `LM-0001`)

| Field | Type | Required | Notes |
|---|---|---|---|
| first_name | Data | ✅ | |
| last_name | Data | | |
| full_name | Data | | Auto-computed (read-only) |
| email | Data (Email) | | Validated as email |
| phone | Data (Phone) | | |
| membership_status | Select | ✅ | Active / Inactive / Expired |
| membership_date | Date | ✅ | |
| membership_expiry_date | Date | ✅ | Must be after membership_date |

**Validations:**
- `full_name` is auto-set from `first_name + last_name`
- `membership_expiry_date` must be strictly after `membership_date`
- If `membership_expiry_date` is in the past, status is auto-updated to `Expired`

---

### Book

**Auto-name**: by `isbn` field (ISBN is the unique key)

| Field | Type | Required | Notes |
|---|---|---|---|
| title | Data | ✅ | |
| author | Data | ✅ | |
| isbn | Data | ✅ | Unique; 10 or 13 digits |
| status | Select | ✅ | Available / Issued |
| publisher | Data | | |
| published_date | Date | | |
| total_copies | Int | ✅ | Min 1 |
| available_copies | Int | | Auto-managed; read-only |
| description | Small Text | | |

**Validations:**
- ISBN must contain only digits (hyphens allowed) and be 10 or 13 digits long
- `total_copies` must be ≥ 1
- `available_copies` initialised to `total_copies` on creation
- `status` auto-syncs: `Available` when `available_copies > 0`, else `Issued`

---

### Book Transaction

**Auto-name**: `BT-.####` (e.g., `BT-0001`)  
**Submittable**: Yes (Draft → Submitted → Cancelled)

| Field | Type | Required | Notes |
|---|---|---|---|
| library_member | Link → Library Member | ✅ | |
| book | Link → Book | ✅ | |
| transaction_type | Select | ✅ | Issue / Return |
| date | Date | ✅ | Defaults to today |
| expected_return_date | Date | | Auto-set to date + 14 days on Issue |
| actual_return_date | Date | | Shown only on Return |
| remarks | Small Text | | |

**Validations (on validate):**
- Transaction date cannot be in the future
- **Issue**: member must be Active and membership not expired
- **Issue**: book `available_copies` must be > 0
- **Return**: a matching submitted Issue transaction must exist for this member+book

**On Submit:**
- **Issue**: decrements `Book.available_copies`; sets `Book.status = "Issued"` if 0
- **Return**: increments `Book.available_copies`; sets `Book.status = "Available"`;
  cancels the original Issue transaction and stamps `actual_return_date`

**On Cancel:**
- Reverses the copy change (re-increments for Issue, re-decrements for Return)

---

## Validation Logic

### Issue Flow
```
User creates Book Transaction (type=Issue)
    │
    ├─ validate_transaction_date()   → date ≤ today
    ├─ validate_member_active()      → status=Active AND expiry_date >= today
    ├─ validate_book_available()     → available_copies > 0
    └─ set_expected_return_date()    → today + 14 days (if not set)
    │
    [Submit]
    └─ _decrement_book_copies()      → available_copies -= 1
                                       if 0 → Book.status = "Issued"
```

### Return Flow
```
User creates Book Transaction (type=Return)
    │
    ├─ validate_transaction_date()       → date ≤ today
    └─ validate_open_issue_exists()      → submitted Issue for same member+book
    │
    [Submit]
    ├─ _increment_book_copies()          → available_copies += 1
    │                                      Book.status = "Available"
    └─ _close_open_issue()               → cancel original Issue doc
                                           stamp actual_return_date on it
```

---

## Testing Scenarios

### ✅ Happy Path – Issue a Book
1. Create a **Library Member** with status `Active` and future expiry date → Save
2. Create a **Book** with 1 copy → Save (status = Available)
3. Create **Book Transaction** type=`Issue`, pick member + book, submit
4. Expected: Transaction submits; Book `available_copies` = 0; Book `status` = Issued

### ✅ Happy Path – Return a Book
1. Using the issued book above, create a new **Book Transaction** type=`Return`
2. Same member and book, submit
3. Expected: Transaction submits; Book `available_copies` = 1; Book `status` = Available
4. Original Issue transaction is now Cancelled with `actual_return_date` filled

### ❌ Error – Issue to Inactive Member
1. Set a member's status to `Inactive`
2. Try to create + submit a Book Transaction (Issue) for that member
3. Expected: Error *"Member has an Inactive membership"*

### ❌ Error – Issue to Member with Expired Membership
1. Set `membership_expiry_date` to a past date (e.g., 2020-01-01)
2. Try to issue a book
3. Expected: Error *"membership expired on ..."*

### ❌ Error – Issue an Already Issued Book (all copies out)
1. Issue all copies of a book (bring available_copies to 0)
2. Try to issue the same book again
3. Expected: Error *"Book is currently not available"*

### ❌ Error – Return Without Matching Issue
1. Create a Return transaction for a book that was never issued to that member
2. Expected: Error *"No open Issue transaction found"*

### ❌ Error – Future Transaction Date
1. Set transaction date to tomorrow
2. Expected: Error *"Transaction Date cannot be in the future"*

### ❌ Error – Invalid ISBN
1. Create a book with ISBN `ABC12345`
2. Expected: Error *"ISBN must contain only digits"*

---

## Time Spent

| Task | Time |
|---|---|
| Environment Setup | ~2h |
| Library Member DocType | ~1.5h |
| Book DocType | ~1.5h |
| Book Transaction DocType + logic | ~3h |
| Testing & Documentation | ~1h |
| **Total** | **~9h** |
