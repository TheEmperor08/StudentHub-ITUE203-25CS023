"""Corrected report – Practical 11: student management, integrated into the StudentHub Admin Console (Student Records tab)."""
from report_lib import corrected_notice

META = {
    "number": 11,
    "title": "Student Management in the Admin Console – CRUD, Search, Filters, Soft Delete and CSV Export",
    "tech": "PHP 8 · MySQLi prepared statements · MariaDB (studenthub_db) · Bootstrap 5 Admin Console",
    "supersedes": "Practical-11/PRAC_11_ITUE203_25CS023.docx",
    "replaces_note": "The original describes a standalone app with its own database studenthub_prac11 and no login; "
                     "Practical 11 now runs inside the integrated portal (Admin Console → Student Records).",
}



def build(r):
    corrected_notice(r, META["supersedes"],
                     "The original report describes a standalone application in `Practical-11/` with its own database "
                     "`studenthub_prac11` and no login. This corrected version describes the same requirements as they are now "
                     "implemented in the Student Records tab of the Admin Console of the integrated portal (database `studenthub_db`, "
                     "one login), including the later fix that a deactivated student can no longer sign in.")

    # ------------------------------------------------------------------ 1
    r.heading("1. Aim and Objectives")
    r.para("To implement complete student management with PHP, MySQL and MySQLi that performs all record operations safely "
           "and keeps every record, even after a student is removed from the active list – as part of the one integrated "
           "StudentHub portal, working on the same student records that self-registration, the profile pages and the event "
           "registrations use.")
    r.bullets([
        "Display the student records of the portal database in a paginated table (10 per page) with a clear Active / Inactive "
        "status and whether the record is linked to a login account.",
        "Add and update students with server-side validation, a unique enrollment number and e-mail address, and clear messages.",
        "Search by name, e-mail and enrollment number, and filter by course, semester and status – all combinable.",
        "Soft delete a student only after an explicit confirmation: the status changes from Active to Inactive and the row stays "
        "in MySQL together with its account link and event registrations; a Reactivate button restores it.",
        "Export the filtered records to a CSV file that opens correctly in Microsoft Excel and is protected against formula injection.",
        "Use MySQLi prepared statements for every query with values, a CSRF token on every POST, output escaping, "
        "administrator-only access and an audit-log entry for every change.",
        "Integration requirement: a student account whose linked record is deactivated can no longer sign in, and an open "
        "session of that student ends at its next request.",
    ])

    # ------------------------------------------------------------------ 2
    r.heading("2. Problem Definition")
    r.para("An institute's student list changes constantly: students join, change course or semester, and leave. Staff must be "
           "able to find a student quickly and export the list for spreadsheet work. At the same time a record must never be "
           "lost by a wrong click, so removing a student must be reversible – a soft delete that only marks the student inactive. "
           "Every input comes from the browser and is therefore untrusted: it has to be validated on the server, sent to MySQL "
           "only through prepared statements, and escaped whenever it is shown again.")
    r.para("Inside the integrated portal there is an additional requirement. The table `studenthub_db.students` already holds "
           "the records created by self-registration (Practical 9, linked to the login account through `students.user_id`) and is "
           "referenced by `registrations` (Practical 8 foundation) with `ON DELETE CASCADE`. A separate Practical 11 database would "
           "create a second, diverging student list, and a hard delete would silently remove a student's event-registration "
           "history. Student management therefore had to be built on the existing table: enrollment numbers keep the existing "
           "`YYPPnnn` scheme (e.g. `25CS011`), the existing status values `Active` / `Inactive` are reused, and no student row is "
           "ever deleted by the portal.")

    # ------------------------------------------------------------------ 3
    r.heading("3. Tools and Technologies")
    r.table([
        ["Tool", "Use in this practical"],
        ["PHP 8.2.12 (XAMPP)", "Admin Console page, validation, sessions, CSV generation"],
        ["MySQLi (exception mode)", "Every query with values as a prepared statement (`prepare` / `bind_param` / `execute`)"],
        ["MariaDB 10.4.32 (XAMPP)", "Shared portal database `studenthub_db`; migration 002 (unique enrollment numbers)"],
        ["Bootstrap 5.3.2 + Bootstrap Icons", "Layout of the Admin Console (loaded from the jsDelivr CDN)"],
        ["HTML5 forms (`novalidate`)", "Form fields and messages; the server alone decides whether input is valid"],
        ["Python 3", "`tests/test_students.py` (HTTP tests) and `database/tests/test_002_unique_enrollment_no.py` on disposable databases"],
        ["Microsoft Edge (headless) + Playwright", "`tests/browser_students.py` and `tests/browser_inactive_login.py` – browser checks and the screenshots"],
        ["Git / GitHub", "Commits `0ac2f5d` (integration) and `6420efc` (sign-in fix), pushed to the project repository"],
    ], [5.2, 10.8])

    # ------------------------------------------------------------------ 4
    r.heading("4. Place in the Integrated Portal")
    r.para("Practical 11 is no longer a separate application. It is the **Student Records (CRUD)** tab of the Admin Console "
           "(`studenthub/admin_dashboard.php?tab=students`), which an administrator reaches after signing in at the portal's "
           "single login page. The logic lives in one include file; the console page only calls it.")
    r.table([
        ["File / route", "Role in Practical 11"],
        ["`admin_dashboard.php?tab=students`", "List with search, filters and pagination; `view=add`, `view=edit&id=N` and `view=deactivate&id=N` only *show* the forms (GET never changes data)"],
        ["`admin_dashboard.php` (POST)", "`action=add_student`, `update_student`, `deactivate_student`, `reactivate_student` – CSRF token and permission `students.manage` required"],
        ["`admin_dashboard.php?tab=students&export=csv`", "CSV download of the records matching the current search and filters (read-only)"],
        ["`includes/student_management.php`", "Filters, list, validation, duplicate checks, save, soft delete / reactivation, CSV export"],
        ["`includes/registration.php`", "Course list `REGISTRATION_COURSES` and `next_enrollment_number()`, shared with self-registration"],
        ["`includes/auth.php`, `login.php`", "Login, session, `require_permission()`, CSRF; `account_is_deactivated()` / `account_block_reason()`"],
        ["`includes/event_registration.php`, `directory.php`", "Inactive students cannot register for events and are not listed in the student directory"],
        ["`audit_logger.php`", "`log_audit()`: CREATE_STUDENT, UPDATE_STUDENT, DEACTIVATE_STUDENT, REACTIVATE_STUDENT, EXPORT_CSV"],
        ["`database/migrations/002_unique_enrollment_no.sql`", "UNIQUE index on `students.enrollment_no` (with `.down.sql` rollback)"],
    ], [5.6, 10.4])
    r.para("**Shared services.** The tab uses the portal's one authentication system (session cookie `STUDENTHUBSESSID`, "
           "HttpOnly, SameSite=Strict), the one CSRF token of the session, the common HTTP 403 page and the common audit log "
           "(shown in the console's *Security Audit Trail* tab). The permissions are listed explicitly in `includes/auth.php`: "
           "`admin.console` and `students.manage` belong to the role `admin` only, so students and editors receive HTTP 403 for "
           "the tab, the forms, the export and every POST action, and each refusal is logged as ACCESS_DENIED.")

    # ------------------------------------------------------------------ 5
    r.heading("5. Database Design and Relationships")
    r.para("Practical 11 uses the portal table `students` (InnoDB, `utf8mb4_unicode_ci`). Its structure, as created by "
           "`database/studenthub_demo.sql`, is:")
    r.table([
        ["Column", "Type", "Notes"],
        ["id", "INT(11) AUTO_INCREMENT", "Primary key (record ID)"],
        ["user_id", "INT(11) NULL", "Link to the login account; UNIQUE `uq_students_user_id`, FK `fk_students_user` → `users.id` ON DELETE SET NULL"],
        ["enrollment_no", "VARCHAR(20) NULL", "UNIQUE `uq_students_enrollment_no` (migration 002); NULL allowed for legacy rows"],
        ["name", "VARCHAR(100) NOT NULL", "Full name"],
        ["email", "VARCHAR(100) NOT NULL", "UNIQUE key `email`"],
        ["course", "VARCHAR(50) NOT NULL", "Course name; existing names are kept"],
        ["gender", "VARCHAR(10) NOT NULL", "Male / Female / Other for new records"],
        ["semester", "INT(11) DEFAULT 3", "CHECK `chk_students_semester`: NULL or 1–8"],
        ["status", "VARCHAR(20) DEFAULT 'Active'", "Active / Inactive – the soft-delete flag"],
        ["created_at", "TIMESTAMP", "Default CURRENT_TIMESTAMP"],
    ], [2.8, 4.4, 8.8])
    r.heading("5.1 Relationships", 2)
    r.table([
        ["Relationship", "Rule", "Effect for student management"],
        ["users 1 : 0..1 students", "`students.user_id` UNIQUE, ON DELETE SET NULL", "A record can be linked to one login account; the Admin Console never changes the link"],
        ["students 1 : n registrations", "`fk_registrations_student` ON DELETE CASCADE", "Deleting a student would erase registrations – the portal therefore never deletes students (soft delete)"],
        ["events 1 : n registrations", "`fk_registrations_event` ON DELETE CASCADE; UNIQUE (student_id, event_id)", "A student registers at most once per event"],
        ["users 1 : n audit_logs", "`audit_logs.user_id` ON DELETE SET NULL", "Every change made in the tab is logged with the administrator's account"],
    ], [3.8, 5.4, 6.8])
    r.heading("5.2 Migration 002 – unique enrollment numbers", 2)
    r.para("Because the console now adds and edits records, two records must never share an enrollment number. The application "
           "checks it, and migration 002 makes the database enforce it as well (also for simultaneous requests). The script first "
           "checks its preconditions and changes nothing if one fails: migration 001 is recorded, the column exists and no number "
           "is used twice (the column collation is case-insensitive, so `25cs011` and `25CS011` count as the same number). "
           "It then adds the index, verifies it and records version `002` in `schema_migrations`. It is idempotent; "
           "`002_unique_enrollment_no.down.sql` drops only the index and the `002` row. According to `database/README.md` it was "
           "applied to the live database on 31 Oct 2026 after a verified backup (9 records, no duplicates).")
    r.excerpt("database/migrations/002_unique_enrollment_no.sql", "-- the column collation is case-insensitive",
              "ALTER TABLE students ADD UNIQUE KEY", "duplicate precondition and the UNIQUE index")
    r.para("**Soft delete in the schema.** No column was added for the soft delete. Deactivating a student sets the existing "
           "`status` column to `Inactive`; the row, its `user_id` link and its registrations stay. The time of the deactivation "
           "is recorded in the audit log (DEACTIVATE_STUDENT), not in a column of `students`.")

    # ------------------------------------------------------------------ 6
    r.heading("6. Implementation")
    r.heading("6.1 Search, filters and pagination", 2)
    r.para("`student_filters()` reads the query string and accepts a course, semester or status only if it is one of the known "
           "values (unknown values are ignored, never used in SQL). `student_filter_sql()` builds one WHERE clause with `?` "
           "parameter markers that is shared by the table, the page count and the CSV export. The search text is matched against "
           "name, e-mail and enrollment number; `%` and `_` typed by the user are escaped with `addcslashes()` so they are "
           "searched literally. The list is ordered newest first and shows 10 records per page; page links keep the filters.")
    r.excerpt("studenthub/includes/student_management.php", "function student_filter_sql(array $filters)", "return [$where ? ' WHERE '",
              "one parameterised WHERE clause for list, count and export")
    r.heading("6.2 Add and edit with server-side validation", 2)
    r.para("`validate_student_record()` checks every field: the enrollment number must match `^[0-9]{2}[A-Z]{2}[0-9]{3}$` "
           "(stored in upper case), the name 2–100 letters (spaces, apostrophes, dots and hyphens allowed, spaces collapsed), "
           "a valid e-mail of at most 100 characters (stored in lower case), a course from the list, a semester 1–8 and the gender "
           "Male, Female or Other; a field sent as an array is refused. When a record is edited, an unchanged legacy value (an "
           "old number format, course or gender, or no semester) is kept as it is. `check_student_record()` then adds the "
           "duplicate checks, so a duplicate number is reported together with all other errors in one answer (HTTP 422, the typed "
           "values shown again HTML-escaped).")
    r.excerpt("studenthub/includes/student_management.php", "function check_student_record(", "return $errors;",
              "validation plus duplicate checks (all problems at once)")
    r.para("`save_student_record()` writes the record in a transaction. If the enrollment number was left empty on the add form, "
           "the next free number of the existing scheme is assigned: two digits of the admission year (derived from the semester "
           "and the academic year) plus the course code from `REGISTRATION_COURSES` (IT, CS, DS, WD) and a three-digit counter, "
           "computed by `next_enrollment_number()`, which locks the matching rows with `SELECT … FOR UPDATE` until the commit. "
           "The duplicate checks run again inside the transaction, and a duplicate saved by someone else at the same moment is "
           "caught by the UNIQUE keys (MySQL error 1062) and turned into a field message. Only the form fields are written: "
           "`user_id`, `status`, `created_at` and the registrations are never touched, and no login account is created.")
    r.excerpt("studenthub/includes/student_management.php", "function save_student_record(", "throw $e;", "add / update in one transaction")
    r.heading("6.3 Soft delete and reactivation", 2)
    r.para("The Deactivate button only opens `admin_dashboard.php?tab=students&view=deactivate&id=N`, a confirmation panel that "
           "shows the record, the number of its event registrations and the consequences. Only the button *Yes, deactivate "
           "student* sends a POST with the CSRF token. `set_student_status()` changes nothing but the status; the condition in the "
           "WHERE clause makes a second attempt harmless (\"already inactive\" / \"already active\").")
    r.excerpt("studenthub/includes/student_management.php", "function set_student_status(", "return $text !== ''",
              "status-only soft delete and the CSV cell guard")
    r.para("The POST handler of the console checks the CSRF token first, then the permission, loads the record and calls the "
           "functions above; every successful change is written to the audit log and answered with a redirect (Post/Redirect/Get) "
           "and a one-time success message.")
    r.excerpt("studenthub/admin_dashboard.php", 'if ($_SERVER["REQUEST_METHOD"] === "POST") {', "Student $label is already",
              "POST handler of the Student Records tab")
    r.heading("6.4 CSV export", 2)
    r.para("The *Export CSV* button carries the current search and filters (it reads *Export CSV (filtered)* when a filter is "
           "active). The export calls `student_list()` without a limit, so every matching record of every page is written, "
           "inactive ones included. The file `studenthub_students_<date>_<time>.csv` is UTF-8 with a byte-order mark, comma "
           "separated, with CRLF line endings, so Excel opens it directly. It contains only record fields – the account column "
           "says only *Linked* or *None*; no password hash, role, token or session data is exported. Every cell passes "
           "`csv_safe_cell()` (shown in 6.3): a value starting with `=`, `+`, `-`, `@`, tab or carriage return gets a leading "
           "apostrophe so that a spreadsheet shows it as text instead of running it as a formula. Each export is audit-logged "
           "(EXPORT_CSV with the number of records).")
    r.excerpt("studenthub/includes/student_management.php", "function send_students_csv(", "fclose($out);", "CSV download")
    r.heading("6.5 Deactivated students cannot sign in (fix, commit 6420efc)", 2)
    r.para("After the first integration step a deactivated student could still sign in (listed as a limitation in TEST_REPORT §7). "
           "The fix in `includes/auth.php` and `login.php` treats a `student` account whose linked record is `Inactive` as "
           "blocked. `account_block_reason()` also covers accounts disabled by an administrator (`users.status`, added later with "
           "Practical 14). The account and its record are re-read on every request, so an open session ends at the next request: "
           "the session data is deleted on the server, the visitor gets a new empty session ID and SESSION_REVOKED is logged. Admin "
           "and editor accounts, even if linked to an inactive record, and student accounts without a linked record are not affected.")
    r.excerpt("studenthub/includes/auth.php", "// A student account whose linked student record (students.user_id)",
              "return [['id' => (int) $row['id']", "block rule and per-request re-check")
    r.para("At sign-in the block is checked only **after** `password_verify()` succeeded. The answer is HTTP 403 with one generic "
           "message (*\"Your access to StudentHub is currently disabled. Please contact the administrator.\"*), no session is "
           "started and LOGIN_DENIED is logged; a wrong password still gets the normal *\"Invalid username/email or password.\"* "
           "(HTTP 401), so the status of a record is never revealed to someone who does not know the password.")
    r.excerpt("studenthub/login.php", "// An unknown account is checked against a dummy hash", "http_response_code($denied ? 403 : 401);",
              "sign-in refused after password verification")

    # ------------------------------------------------------------------ 7
    r.heading("7. Validation and Security")
    r.bullets([
        "**Server-side validation:** every field is checked by `validate_student_record()`; the form has `novalidate`, so the "
        "browser never decides. Invalid input is answered with HTTP 422, a message under each field and the general alert "
        "\"Please correct the highlighted fields. Nothing was saved.\"",
        "**Duplicates:** checked before saving (all errors at once), again inside the transaction, and finally by the UNIQUE keys on "
        "`enrollment_no` and `email` – also in another letter case and with extra spaces.",
        "**SQL injection:** all queries with values are prepared statements; filter values are accepted only from fixed lists; the "
        "page number and record IDs are matched against strict patterns; LIKE wildcards are escaped.",
        "**XSS:** every value is printed through `e()` = `htmlspecialchars(…, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8')`.",
        "**CSRF:** every POST form carries the session's 64-character token, compared with `hash_equals()`; a missing, wrong or "
        "modified token (or another session's token) is refused with HTTP 403 \"Security check failed\" and logged as CSRF_REJECTED. "
        "GET requests – even with action parameters and the token – change nothing.",
        "**Authorisation:** `require_permission('students.manage')` on the export and on every action; students, editors and "
        "visitors are refused on the server, not only hidden in the menu.",
        "**CSV export:** formula-injection guard, RFC 4180 quoting by `fputcsv()`, no account or session data.",
        "**Records are never lost:** the code contains no `DELETE FROM students`; deactivation is reversible.",
        "**Headers:** signed-in pages send `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin` "
        "and `Cache-Control: no-store`.",
        "**Deactivated students:** refused at sign-in after password verification and signed out at the next request (section 6.5).",
    ])

    # ------------------------------------------------------------------ 8
    r.heading("8. Output Screenshots")
    r.para("All screenshots are genuine full-page captures from Microsoft Edge (headless, driven by Playwright, window 1280 px wide) "
           "of the integrated portal running on PHP's built-in server with a disposable database built from "
           "`database/studenthub_demo.sql` plus fictional students added by the test. Figures 1–11 were produced by "
           "`tests/browser_students.py` (screenshots 01–13), Figures 12–15 by `tests/browser_inactive_login.py` (screenshots 14–17). "
           "Two further captures of the folder are not reproduced here: `02-add-student-form.png` (the empty add form, the same "
           "form as in Figure 2) and `08-student-updated.png` (the list after saving the edit of Figure 6). The Admin Console "
           "gained further tabs in later integration steps (for example *Inquiries*, Practical 7), which are therefore not "
           "visible in these screenshots.")
    r.figure("evidence/practical-11-integration/01-student-list.png",
             "Student Records tab of the Admin Console (administrator portal_admin): 10 of 12 records on page 1 with enrollment "
             "number, name, e-mail, course, semester, status and account columns; John Doe (25IT056) is Inactive with a greyed "
             "row and a Reactivate button; summary \"11 active, 1 inactive in total\" and pagination", width=12.5)
    r.figure("evidence/practical-11-integration/03-validation-error.png",
             "Server-side validation of the add form: the enrollment number 25IT013 is already used by another student, the "
             "e-mail \"riya.sharma@\" is invalid, no course and no semester were selected; the typed name Riya Sharma is kept "
             "and nothing was saved", width=10)
    r.figure("evidence/practical-11-integration/04-student-created.png",
             "After a valid submission with an empty enrollment number: \"Student “Riya Sharma” was added with enrollment number "
             "26IT001.\" – the number was assigned automatically and the new record is first in the list (13 records)", width=12)
    r.figure("evidence/practical-11-integration/05-search-results.png",
             "Search \"Patel\": 2 matching records (Aarav Patel, Rohan Patel); the export button now reads \"Export CSV (filtered)\" "
             "and a \"Reset filters\" link is shown", width=14)
    r.figure("evidence/practical-11-integration/06-filtered-records.png",
             "Combined filters course \"Web Development\" + status \"Active\": the 3 matching records (Kabir Joshi, Kavya Mehta, "
             "Diya Shah); the selected filters stay in the form", width=14)
    r.figure("evidence/practical-11-integration/07-edit-student.png",
             "Edit form for Kavya Mehta filled from the database: \"Record #4 · Active · no login account · 0 event registration(s)\"; "
             "the e-mail is being changed to kavya.mehta@example.com and the semester to 8", width=10.5)
    r.figure("evidence/practical-11-integration/09-deactivate-confirmation.png",
             "Confirmation before the soft delete of Rohan Patel (25CS104): the panel explains that the record, its account link "
             "and its registrations are kept, that it stays in the list and the CSV export, and that inactive students cannot "
             "sign in or register; nothing has changed yet", width=11)
    r.figure("evidence/practical-11-integration/10-student-inactive.png",
             "After the confirmed deactivation: \"Student “Rohan Patel” (25CS104) was deactivated. The record, its account link and "
             "its event registrations are kept; a linked student account can no longer sign in.\" – the row is still listed, "
             "greyed, with an Inactive badge and a Reactivate button (11 active, 2 inactive, still 13 records)", width=12)
    r.figure("evidence/practical-11-integration/11-student-reactivated.png",
             "Reactivation: \"Student “John Doe” (25IT056) was reactivated.\" – John Doe is Active again (12 active, 1 inactive)", width=12)
    r.figure("evidence/practical-11-integration/12-csv-export.png",
             "The CSV file downloaded by the Export button of Figure 5's filtered view (course Web Development, status Active): "
             "studenthub_students_20261031_012936.csv, 390 bytes, UTF-8 with byte-order mark, CRLF line endings. A headless browser "
             "has no download bar, so the test saved the download (also kept as 12-csv-export-web-development-active.csv) and "
             "displayed its exact content as text and, parsed as CSV, as a table in the browser; Excel was not used", width=16)
    r.figure("evidence/practical-11-integration/13-student-access-denied.png",
             "A signed-in student (demo_student) opening the Student Records tab: HTTP 403 \"Access Denied\" page, role student "
             "\"Not permitted here\", no student data shown; the attempt is recorded in the audit log", width=12.5)
    r.figure("evidence/practical-11-integration/14-admin-deactivated-linked-student.png",
             "Sign-in fix: Lina Mehra registered herself (record 26DS001, account column \"Linked\") and the administrator has "
             "deactivated the record – status Inactive, Reactivate button", width=13.5)
    r.figure("evidence/practical-11-integration/15-session-ended-after-deactivation.png",
             "The student's already open session: her next page request leads to the sign-in page with the generic message "
             "\"Your access to StudentHub is currently disabled. Please contact the administrator.\"", width=12.5)
    r.figure("evidence/practical-11-integration/16-inactive-login-denied.png",
             "Signing in again as lina_mehra with the correct password is refused with the same generic message (no record "
             "details); no session is started", width=12.5)
    r.figure("evidence/practical-11-integration/17-login-after-reactivation.png",
             "After the administrator reactivated the record the student signs in normally: dashboard with \"Welcome back, "
             "Lina Mehra\", enrollment 26DS001 and the message \"Welcome back, lina_mehra.\"", width=12.5)

    # ------------------------------------------------------------------ 9
    r.heading("9. Testing and Results")
    r.para("All tests were executed on 31 October 2026 on Windows 11 with PHP 8.2.12 (XAMPP), MariaDB 10.4.32 and PHP's built-in "
           "server, against disposable databases (built from `database/studenthub_demo.sql` or from a restored copy of the real "
           "database, dropped afterwards). The live `studenthub_db` received only migration 002, after a verified backup, and its "
           "users, password hashes, students, events, registrations and menu items were verified unchanged afterwards. The "
           "numbers below are copied from the saved outputs and from TEST_REPORT.md §7–§8.")
    r.table([
        ["Suite", "Result", "Output"],
        ["`tests/test_students.py` – HTTP tests of the Student Records tab (demo data)", "**170 / 170 passed**", "`tests/test_students_output.txt`"],
        ["The same with `--source-dump` (restored copy of the real database)", "**170 / 170 passed**", "not committed (contains real records)"],
        ["`tests/browser_students.py` – Microsoft Edge + screenshots 01–13", "**16 / 16 passed**", "`tests/browser_students_output.txt`"],
        ["`tests/browser_inactive_login.py` – Edge: register, deactivate, session ended, sign-in refused, reactivate", "**13 / 13 passed**", "`tests/browser_inactive_login_output.txt`"],
        ["`database/tests/test_002_unique_enrollment_no.py` – fixture / real dump", "**22 / 22** and **22 / 22 passed**", "`database/tests/test_002_output.txt`"],
        ["`test_002 … --verify-live` – live database after migration 002 (read-only)", "**4 / 4 passed**", "`database/tests/test_002_verify_live_output.txt`"],
        ["Regression: `tests/test_auth.py` (Practicals 9/10) / `tests/browser_auth.py`", "**132 / 132** / **14 / 14 passed**", "`tests/test_auth_output.txt`, `tests/browser_auth_output.txt`"],
    ], [8.2, 3.4, 4.4])
    r.note("Regression of the Practical 8 migration test (`database/tests/test_001_practical8_foundation.py`): TEST_REPORT §7–§8 "
           "record 87 / 87 (fixture) and 24 / 24 (`--verify-live`) for this step. The saved file `database/tests/test_001_output.txt` "
           "now holds a later re-run (88 / 88).", fill="EEF2FF")
    r.heading("9.1 Checks per area (tests/test_students.py)", 2)
    r.table([
        ["Area", "Checks", "Examples of what is verified"],
        ["Static checks", "5", "`php -l` on all PHP files of studenthub/ and tools/; no `DELETE FROM students`; prepared statements; `students.manage` on the server"],
        ["Database (migration 002)", "4", "UNIQUE index present, `002` recorded, duplicate refused also in another letter case, several NULLs allowed"],
        ["Student listing (admin)", "7", "newest first, columns, summary 6 active / 1 inactive, Inactive marking, CSRF token in every form, empty state"],
        ["Add student", "11", "entered and automatic numbers (26IT102, 25DS001), normalisation, no login account created, CREATE_STUDENT"],
        ["Invalid student details", "14", "empty / digits / HTML / one-letter name, invalid or too long e-mail, unknown course or gender, SQL in the number, array field"],
        ["Duplicates", "5", "same number, lower case, with spaces; e-mail in other case; duplicate reported together with other errors"],
        ["Invalid semester values", "9", "`0`, `9`, `12`, `-1`, `3.5`, `abc`, `1 OR 1=1`, empty – all refused, nothing stored"],
        ["Edit student", "14", "values saved; link, status, number, creation time and registrations unchanged; legacy record editable; unknown IDs"],
        ["Search and filters", "14", "name, e-mail, number prefix, course, semester, status and combinations; `%` and `_` literal"],
        ["SQL injection attempts", "9", "four injection strings in the search; injected course, semester, status and page values ignored"],
        ["Pagination", "5", "24 records → 3 pages of 10; last page; page past the end; filters kept"],
        ["Soft delete and reactivation", "21", "confirmation page, GET / token-less requests change nothing, record and registrations kept, `student_inactive`, reactivation"],
        ["Inactive records elsewhere", "2", "hidden from the student directory, listed again after reactivation"],
        ["CSV export", "14", "BOM, CRLF, header, all 27 records incl. inactive, formula injection, 9 columns, filtered export of all pages, file-name time zone"],
        ["Access control", "7", "students, editors and visitors refused for tab, forms, export and POST actions"],
        ["CSRF and GET requests", "4", "missing, wrong, modified and another admin's token refused and logged"],
        ["Deactivated students cannot sign in", "22", "session ended (new ID, SESSION_REVOKED), old cookie useless, sign-in 403 + LOGIN_DENIED, editors/admins unaffected, reactivation"],
        ["Server log / clean-up", "3", "no PHP warnings; disposable database removed; live database untouched"],
        ["**Total**", "**170**", ""],
    ], [4.2, 1.6, 10.2])
    r.heading("9.2 Browser checks (Microsoft Edge)", 2)
    r.para("`tests/browser_students.py` (16 checks) clicked through the tab as a user would: list and pagination, Inactive badge, "
           "add form, server-side validation messages, successful add with the assigned number, search *Patel*, combined filters, "
           "the CSV download (file name pattern, BOM, header, only the filtered rows), edit and save, deactivation with confirmation, "
           "reactivation, HTTP 403 for a student, no JavaScript errors and no PHP warnings. `tests/browser_inactive_login.py` "
           "(13 checks) registered a new student, deactivated the linked record in a second browser context, and verified that "
           "the student's open session ended, that a new sign-in was refused with the generic message, and that sign-in worked "
           "again after reactivation while the administrator's session was never affected. Both outputs report one known, "
           "pre-existing 404 for `/favicon.ico` (the portal has no favicon).")

    # ------------------------------------------------------------------ 10
    r.heading("10. Problems Found and Fixed During Integration")
    r.bullets([
        "**Time zone of dates:** XAMPP's PHP used the `Europe/Berlin` time zone from php.ini while MariaDB uses the system's India "
        "time, so between midnight and about 04:30 the portal's dates (form defaults, academic year for enrollment numbers, CSV "
        "file name) were one day behind. `studenthub/db.php` now sets `Asia/Kolkata` (override: `STUDENTHUB_TIMEZONE`); a test "
        "checks that the export file name matches the database clock.",
        "**Deactivated students could still sign in:** found after the first integration commit (`0ac2f5d`) and listed as a "
        "limitation; fixed in commit `6420efc` (section 6.5) with 22 new HTTP checks and the Edge test `browser_inactive_login.py`. "
        "The confirmation panel and the success message now say that a linked student account can no longer sign in, and "
        "screenshots 01–13 were regenerated with the new wording.",
        "**All problems reported at once:** field validation needs no database, the duplicate checks do. `check_student_record()` "
        "runs both and merges the results, so a duplicate enrollment number is reported together with the other errors (Figure 2) "
        "instead of only after the other errors have been corrected.",
        "**CSV evidence in a headless browser:** a headless Edge has no download bar, so the test saved the downloaded file and "
        "showed its bytes as text and as a table (Figure 10) instead of a screenshot of Excel.",
    ])

    # ------------------------------------------------------------------ 11
    r.heading("11. Differences from the Original Standalone Practical and Limitations")
    r.table([
        ["Aspect", "Original report (Practical-11/)", "Integrated portal (studenthub/)"],
        ["Database", "Own database `studenthub_prac11`, table `students` (student_id, full_name, …, status ENUM('active','inactive'), deleted_at)", "Shared `studenthub_db.students` – the same rows used by self-registration, profiles and event registrations"],
        ["Access", "Standalone application without a login", "Admin Console behind the portal login; `students.manage` (administrators only)"],
        ["CSRF", "One-time form tokens", "One CSRF token per session on every POST, checked with `hash_equals()`"],
        ["Search / filters", "Name, e-mail and course; course and status filter", "Name, e-mail and enrollment number; course, semester and status filters"],
        ["Soft delete", "status inactive + `deleted_at` time", "status Inactive; time in the audit log; Reactivate button"],
        ["Enrollment numbers", "–", "`YYPPnnn` scheme, automatic next number, UNIQUE index (migration 002)"],
        ["Sign-in effect", "–", "A linked student account cannot sign in while its record is Inactive"],
        ["CSV file", "`students_YYYYMMDD_HHMMSS.csv`, 9 columns incl. Deactivated At", "`studenthub_students_YYYYMMDD_HHMMSS.csv`, 9 columns (Record ID … Login Account, Created At)"],
        ["Tests", "106 / 106 automated, 13 / 13 browser", "170 / 170 automated, 16 / 16 + 13 / 13 browser, migration tests"],
    ], [3.0, 6.3, 6.7])
    r.para("**Limitations** (TEST_REPORT §7): there is no interface to link an added record to an existing login account (links "
           "are created only by self-registration); the soft-delete time is recorded in the audit log, not in a column of "
           "`students`; the add form offers automatic enrollment numbers only for the four registration courses (Information "
           "Technology, Computer Science Engineering, Data Science, Web Development) – other courses need a typed number; the Admin "
           "Console still loads Bootstrap from a CDN; the browser reports one 404 for `/favicon.ico`.")

    # ------------------------------------------------------------------ 12
    r.heading("12. Conclusion")
    r.para("Student management now works on the portal's own student records instead of a separate database. Administrators "
           "list, search and filter the records, add and edit them with full server-side validation and unique enrollment "
           "numbers, soft-delete them only after a confirmation and reactivate them, and export exactly the filtered records to a "
           "CSV file protected against formula injection. Deactivation never destroys data – the record, its account link and its "
           "event registrations stay – and a deactivated student can neither sign in nor keep an open session. Prepared "
           "statements, output escaping, a CSRF token on every POST, server-side permission checks and audit logging protect the "
           "tab. 170 automated checks, 16 + 13 browser checks and the migration tests passed.")

    # ------------------------------------------------------------------ 13
    r.heading("13. References")
    r.bullets([
        "Project repository: https://github.com/TheEmperor08/StudentHub-ITUE203-25CS023 – `studenthub/` (portal), `database/` "
        "(schema and migration 002), `tests/`, `evidence/practical-11-integration/`, `TEST_REPORT.md` §7–§8; commits `0ac2f5d`, `6420efc`",
        "PHP Manual – MySQLi prepared statements: https://www.php.net/manual/en/mysqli.quickstart.prepared-statements.php",
        "PHP Manual – htmlspecialchars: https://www.php.net/manual/en/function.htmlspecialchars.php",
        "PHP Manual – fputcsv: https://www.php.net/manual/en/function.fputcsv.php",
        "PHP Manual – hash_equals: https://www.php.net/manual/en/function.hash-equals.php",
        "PHP Manual – password_verify: https://www.php.net/manual/en/function.password-verify.php",
        "OWASP – CSV Injection: https://owasp.org/www-community/attacks/CSV_Injection",
        "OWASP – Cross-Site Request Forgery Prevention Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html",
        "OWASP – SQL Injection Prevention Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html",
    ])
