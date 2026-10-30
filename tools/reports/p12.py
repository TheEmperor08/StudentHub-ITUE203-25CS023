"""Corrected report – Practical 12: event management with secure poster upload and event registration, integrated into
the StudentHub portal (Admin Console → Campus Events, Campus Events page)."""
from report_lib import corrected_notice

META = {
    "number": 12,
    "title": "Event Management with Secure Poster Upload and Event Registration",
    "tech": "PHP 8 · MySQLi prepared statements · PHP Fileinfo · MariaDB (studenthub_db) · Bootstrap 5",
    "supersedes": "Practical-12/PRAC_12_ITUE203_25CS023.docx",
    "replaces_note": "The original describes a standalone app with its own database studenthub_prac12 and its own admin login; "
                     "Practical 12 now runs inside the integrated portal (Admin Console → Campus Events, Campus Events page).",
}



def build(r):
    corrected_notice(r, META["supersedes"],
                     "The original report describes a standalone application in `Practical-12/` with its own database "
                     "`studenthub_prac12`, its own `admins` table and session. This corrected version describes event management as "
                     "it is now implemented in the integrated portal: the Campus Events tab of the Admin Console works on the "
                     "portal's own `events` table (extended by migration 003), uses the portal login, and students register for "
                     "events on the Campus Events page.")

    # ------------------------------------------------------------------ 1
    r.heading("1. Aim and Objectives")
    r.para("To build the event module of StudentHub in which administrators publish campus events with a poster image, "
           "safely, inside the integrated portal – and in which students register for these events without overbooking.")
    r.bullets([
        "Add, view, update and delete events (title, category, date, optional start time, location, optional capacity, "
        "Open/Closed status, optional description, optional poster) in the Admin Console.",
        "Upload event posters and validate the file type (JPEG, PNG, WebP) and file size (max 2 MB) on the server – from the "
        "file content, not from the name or the browser.",
        "Show clear success and failure messages for every action.",
        "Restrict event management to administrators (permission `events.manage`) through the portal's single login.",
        "Intermediate extension: event categories from a database table, an Open/Closed filter, an upcoming/past filter and a search.",
        "Let students with a linked student record register for an event and cancel the registration (Practicals 8 and 12); "
        "the capacity is never exceeded, also for simultaneous requests.",
        "Use MySQLi prepared statements, output escaping and a CSRF token on every POST throughout.",
    ])

    # ------------------------------------------------------------------ 2
    r.heading("2. Problem Definition")
    r.para("Uploading files is one of the most dangerous features of a web application: if the server trusts the file name, the "
           "extension or the browser's `accept` attribute, an attacker can upload a PHP script and run it, an SVG file with "
           "JavaScript, a disguised executable or a huge file. A carelessly built edit or delete function can also destroy the "
           "wrong file, follow a path such as `../db.php`, or lose the old poster when an update fails. The module must therefore "
           "validate every poster on the server, store it safely, change files only after the database change succeeded, and let "
           "only authorised administrators manage events.")
    r.para("The integrated portal adds three constraints. (1) The portal already has an `events` table that the Campus Events "
           "page shows; some existing events store an older poster path (for example `uploads/odoo_hackathon.jpg`) whose file "
           "does not exist. (2) The `registrations` table (Practical 8 foundation) references `events` with `ON DELETE CASCADE`, "
           "so deleting an event would silently remove its registration history. (3) Registrations must respect the capacity even "
           "when several students click *Register* at the same moment. The standalone design of the original report (own database "
           "and own administrator login) could not be copied; its rules had to be brought into the existing tables and login.")

    # ------------------------------------------------------------------ 3
    r.heading("3. Tools and Technologies")
    r.table([
        ["Tool", "Use in this practical"],
        ["PHP 8.2.12 (XAMPP)", "Admin Console, Campus Events page, upload handling, `poster.php`"],
        ["MySQLi (exception mode)", "Every query with values as a prepared statement; transactions with row locks"],
        ["PHP Fileinfo (`finfo`) + `getimagesizefromstring()`", "Real MIME type and image type detected from the file content"],
        ["MariaDB 10.4.32 (XAMPP)", "Shared database `studenthub_db`; migration 003 (event categories, status, unique poster)"],
        ["Bootstrap 5.3.2 + Bootstrap Icons", "Admin Console layout (CDN); the Campus Events page uses the portal's `global.css`"],
        ["Python 3", "`tests/test_events.py` (HTTP and multipart upload tests) and `database/tests/test_003_event_management.py`"],
        ["Microsoft Edge (headless) + Playwright", "`tests/browser_events.py` – browser checks and the screenshots"],
        ["Git / GitHub", "Commit `ba11795`, pushed to the project repository"],
    ], [5.6, 10.4])

    # ------------------------------------------------------------------ 4
    r.heading("4. Place in the Integrated Portal")
    r.para("Event management is the **Campus Events** tab of the Admin Console; event registration is part of the students' "
           "**Campus Events** page (`notifications.php`, menu entry *Notices*). Both use the same include files.")
    r.table([
        ["File / route", "Role in Practical 12"],
        ["`admin_dashboard.php?tab=events`", "Event list with search and filters; `view=add_event`, `view=edit_event&id=N`, `view=delete_event&id=N`, `view=event_registrations&id=N` (GET only shows them)"],
        ["`admin_dashboard.php` (POST, multipart)", "`action=add_event`, `update_event`, `delete_event` – CSRF token and permission `events.manage` required"],
        ["`includes/event_management.php`", "`event_filters()`, `validate_event()`, `save_event()`, `delete_event()`, `validate_poster()`, `poster_structure_ok()`, `store_poster()`, `poster_path()`, `delete_poster_file()`, `discard_new_poster()`"],
        ["`includes/event_registration.php`", "`register_student_for_event()` (transaction), `cancel_event_registration()`, `linked_student()`"],
        ["`notifications.php`", "Campus Events page: upcoming events with poster, seats and Register / Cancel buttons; past events"],
        ["`poster.php?event=N`", "The only way to view a poster; signed-in users only"],
        ["`uploads/` + `uploads/.htaccess`", "Poster folder (`STUDENTHUB_UPLOAD_DIR` overrides it); denied over HTTP and PHP disabled on Apache"],
        ["`database/migrations/003_event_management.sql`", "`event_categories` + foreign key, `events.status`, `events.updated_at`, UNIQUE `events.poster` (with rollback)"],
        ["`audit_logger.php`", "CREATE_EVENT, UPDATE_EVENT, DELETE_EVENT, UPLOAD_REJECTED, EVENT_REGISTER, EVENT_REGISTRATION_CANCEL"],
    ], [5.4, 10.6])
    r.para("**Permissions** (`includes/auth.php`): `events.manage` belongs to the role `admin` only; `portal.view` (Campus Events "
           "page and posters) to admin, editor and student. Only a `student` account with a linked student record "
           "(`students.user_id`) can register – administrators cannot register as students. Students and editors get the common "
           "HTTP 403 page for the Campus Events tab and every event POST, logged as ACCESS_DENIED. The tab shares the portal's "
           "session, CSRF token and audit log with all other pages.")

    # ------------------------------------------------------------------ 5
    r.heading("5. Database Design and Relationships")
    r.para("Practical 12 extends the portal's existing `events` table instead of creating a new one. After migration 003 its "
           "structure (from `database/studenthub_demo.sql`) is:")
    r.table([
        ["Column", "Type", "Notes"],
        ["id", "INT(11) AUTO_INCREMENT", "Primary key"],
        ["title", "VARCHAR(150) NOT NULL", "3–150 characters (application)"],
        ["event_date / event_time", "DATE NOT NULL / TIME NULL", "Index `idx_events_date`; the start time is optional"],
        ["location", "VARCHAR(150) NOT NULL", "2–150 characters (application)"],
        ["capacity", "SMALLINT UNSIGNED NULL", "CHECK `chk_events_capacity`: NULL (no limit) or > 0"],
        ["status", "ENUM('open','closed') NOT NULL DEFAULT 'open'", "Migration 003; closed = no new registrations; index"],
        ["description", "TEXT NULL", "Optional, at most 2000 characters (application)"],
        ["category", "VARCHAR(50) NOT NULL", "FK `fk_events_category` → `event_categories.name` (ON UPDATE CASCADE, ON DELETE RESTRICT)"],
        ["poster", "VARCHAR(255) NULL", "UNIQUE `uq_events_poster` (migration 003): two events can never share a poster file"],
        ["created_at / updated_at", "TIMESTAMP", "`updated_at` set automatically on every change (migration 003)"],
    ], [3.4, 5.2, 7.4])
    r.table([
        ["Table / relationship", "Rule", "Effect"],
        ["event_categories 1 : n events", "`fk_events_category`, ON DELETE RESTRICT", "Category drop-downs come from the table; a used category cannot be deleted"],
        ["events 1 : n registrations", "`fk_registrations_event` ON DELETE CASCADE", "The portal refuses to delete events with registrations, so history is never lost through the interface"],
        ["students 1 : n registrations", "`fk_registrations_student` ON DELETE CASCADE; UNIQUE (student_id, event_id)", "One registration per student and event; status registered / attended / cancelled"],
        ["users 1 : 0..1 students", "`students.user_id`", "Decides which student record a signed-in student registers with"],
    ], [4.0, 5.2, 6.8])
    r.heading("5.1 Migration 003 – event management", 2)
    r.para("The migration first checks its preconditions (migration 002 recorded, the expected column types, no two events with "
           "the same poster value, no empty category) and changes nothing if one fails. It creates `event_categories` with the "
           "six categories of the original Practical 12 **plus every category already used** (the live database keeps "
           "*Conference*), adds `status`, `updated_at`, the unique poster key, two indexes and the category foreign key, verifies "
           "them and records version `003`. No event value is changed; it is idempotent and `003_event_management.down.sql` "
           "removes exactly these changes. According to `database/README.md` it was applied to the live database on 31 Oct 2026 "
           "after a verified backup; the read-only live check lists the categories Conference, Cultural, Hackathon, Seminar, "
           "Sports, Technical and Workshop.")
    r.excerpt("database/migrations/003_event_management.sql", "CREATE TABLE IF NOT EXISTS event_categories (",
              "ON UPDATE CASCADE ON DELETE RESTRICT;", "categories, new columns, unique poster and foreign key")

    # ------------------------------------------------------------------ 6
    r.heading("6. Implementation")
    r.heading("6.1 Event list, search and filters", 2)
    r.para("The Campus Events tab lists the events 10 per page with a poster thumbnail (or a generic image icon), title, category, date "
           "and time, location, seats (*taken / capacity* or *no limit*), the Open/Closed badge and the actions Edit, "
           "Registrations (with the number of registrations) and Delete. `event_filters()` accepts a category only from "
           "`event_categories`, a status only `open`/`closed` and a date filter only `upcoming`/`past`; `event_filter_sql()` builds a "
           "WHERE clause with `?` parameter markers; the search text is matched against title, location and description with `%` and "
           "`_` escaped. The same functions are later reused by the Practical 13 JSON API.")
    r.heading("6.2 Add and edit with server-side validation", 2)
    r.para("`validate_event()` checks every field on the server: title 3–150 characters, a category from the table, a real date "
           "in `YYYY-MM-DD` between 2000 and 2100, an optional time `HH:MM`, location 2–150 characters, capacity a whole number "
           "1–65535 or empty for no limit, status Open or Closed and a description of at most 2000 characters. Invalid input is "
           "answered with HTTP 422, a message under each field and the typed values (HTML-escaped). When an event is edited, the "
           "capacity can never be set below the seats already taken – `save_event()` re-checks this while the event row is locked, "
           "so a registration arriving at the same moment cannot slip through.")
    r.excerpt("studenthub/includes/event_management.php", "// lock the event, then re-check the capacity", "$old_poster = $poster !== null ? $row['poster'] : null;",
              "update inside a transaction with the capacity re-check")
    r.heading("6.3 Poster upload and validation", 2)
    r.para("All checks run on the server in `validate_poster()`; the `accept` attribute of the file field is only a convenience. "
           "The checks are applied in this order, and the first failure ends the check with a clear message:")
    r.table([
        ["Step", "Check", "Rejects for example"],
        ["1", "PHP upload error code", "file above the server limit (\"too large\"), partial upload, missing temp folder"],
        ["2", "`is_uploaded_file()`", "a path that was not uploaded in this request"],
        ["3", "Size: not empty, at most 2 MB (`POSTER_MAX_BYTES`)", "an empty file; a 2.3 MB PNG"],
        ["4", "Extension `.jpg` / `.jpeg` / `.png` / `.webp` (any letter case)", "GIF, SVG with JavaScript, a PHP script"],
        ["5", "The whole file can be read", "a file blocked by security software (\"could not be read as an image\")"],
        ["6", "Fileinfo MIME type of the content is JPEG, PNG or WebP", "a PHP script renamed to `.jpg`, `shell.php.jpg`, a text file sent with a forged `image/png` type"],
        ["7", "MIME type matches the extension", "PNG content named `.jpg` (\"does not match its content\")"],
        ["8", "`getimagesizefromstring()` + structure check `poster_structure_ok()` (PNG chunks with CRC up to IEND, JPEG start/end markers, WebP RIFF length)", "a truncated PNG (\"not a valid image or is damaged\")"],
        ["9", "Width and height 1–6000 px", "gigantic dimensions"],
        ["10", "No `<?php` or `<?=` inside the file", "a valid JPEG with embedded PHP code"],
    ], [1.2, 7.6, 7.2])
    r.excerpt("studenthub/includes/event_management.php", "$tmp = (string) ($file['tmp_name'] ?? '');", "return ['ok' => true, 'tmp' => $tmp",
              "content-based checks of validate_poster()")
    r.heading("6.4 Safe storage, replacement and delivery", 2)
    r.para("The original file name is never used. `store_poster()` names the file with 32 random hexadecimal characters "
           "(`random_bytes(16)`) plus the extension of the *detected* type and moves it with `move_uploaded_file()`; only this name "
           "is stored in `events.poster`. `poster_path()` accepts only names matching `^[a-f0-9]{32}\\.(jpg|png|webp)$` that really "
           "lie inside the upload folder, so older values such as `uploads/odoo_hackathon.jpg` or a value like `../db.php` can "
           "never reach another file – such events simply show a generic image icon.")
    r.excerpt("studenthub/includes/event_management.php", "function store_poster(array $valid)", "return ($path !== false && dirname($path) === $dir",
              "random names and the path check")
    r.para("The console's POST handler keeps files and database consistent: the poster is validated together with the fields, "
           "stored only when everything is valid, then the event is saved; if saving fails the new file is removed again "
           "(`discard_new_poster()`), and only after a successful update is the old poster deleted (`delete_poster_file()`, which "
           "also checks that no event still uses it). A rejected poster is logged as UPLOAD_REJECTED.")
    r.excerpt("studenthub/admin_dashboard.php", "// Campus events (Practical 12): add, edit and delete", "discard_new_poster($stored);",
              "POST handler of the Campus Events tab")
    r.para("The poster folder is never served directly. On Apache, `uploads/.htaccess` denies every request (`Require all denied`), "
           "switches the PHP engine off, removes the PHP handlers and types and disables CGI and directory listings. Posters are "
           "delivered only by `poster.php`, which takes an **event ID** – never a file name – and requires a signed-in user.")
    r.excerpt("studenthub/poster.php", 'require_permission("portal.view");', "readfile($path);",
              "poster delivery with nosniff and a sandbox CSP")
    r.heading("6.5 Deleting events", 2)
    r.para("The Delete action first opens a confirmation panel. For an event **with** registrations the panel explains that it "
           "cannot be deleted and offers *Edit the event* (to close it) instead of a delete button; a forged POST is refused by "
           "`delete_event()` as well, which counts the registrations while the event row is locked. An event without registrations "
           "is deleted after confirmation, and its poster file is removed.")
    r.excerpt("studenthub/includes/event_management.php", "function delete_event(mysqli $db, int $id)", "return ['ok' => true, 'poster' => $row['poster']];",
              "delete only without registrations")
    r.heading("6.6 Event registration for students", 2)
    r.para("On the Campus Events page a student with a linked student record sees every upcoming event with its poster, the seats "
           "(*n of capacity seats taken* or *no seat limit*) and a Register button – or *You are registered* with *Cancel "
           "registration*, *Event full* or *Registration closed*. Each button is a POST form with the CSRF token. "
           "`register_student_for_event()` runs in one transaction: it locks the event row (`SELECT … FOR UPDATE`), refuses closed "
           "and past events, inactive students and duplicates, counts the seats that are not cancelled only after the lock is held, "
           "and then inserts the registration or reactivates a cancelled one. Concurrent requests for the same event therefore "
           "wait for each other, and the capacity is never exceeded. Cancelling sets the status to `cancelled`: the row is kept "
           "as history and the seat is freed. The registrations of an event are listed for the administrator in the console "
           "(enrollment number, student, course, registration status, time).")
    r.excerpt("studenthub/includes/event_registration.php", "function register_student_for_event(", "return $registration_id;",
              "registration transaction without overbooking", max_lines=62)

    # ------------------------------------------------------------------ 7
    r.heading("7. Validation and Security")
    r.bullets([
        "**Uploads:** ten server-side checks (section 6.3), random names, a folder that is not reachable over HTTP and not "
        "executable on Apache, delivery only through `poster.php` with `Content-Security-Policy: default-src 'none'; sandbox` "
        "and `X-Content-Type-Options: nosniff`; files are replaced or deleted only after the database change succeeded.",
        "**Event data:** every field validated on the server (`validate_event()`), HTTP 422 with field messages; the capacity "
        "cannot drop below the seats taken.",
        "**SQL injection:** every query with values is a prepared statement (checked by a static test); filter values only from "
        "fixed lists; IDs matched against strict patterns.",
        "**XSS:** every value is printed through `e()` (`htmlspecialchars` with `ENT_QUOTES`).",
        "**CSRF:** every POST form (add, edit, delete, register, cancel) carries the session token; GET requests never change data.",
        "**Authorisation:** `events.manage` for the tab and every event action, `portal.view` for posters and the Campus Events page; "
        "only a linked student account can register.",
        "**Integrity:** transactions with row locks for registrations, capacity edits and deletions; UNIQUE (student_id, event_id); "
        "UNIQUE poster; category foreign key; events with registrations are never deleted.",
        "**Audit log:** every create, update, delete, rejected upload, registration and cancellation.",
    ])

    # ------------------------------------------------------------------ 8
    r.heading("8. Output Screenshots")
    r.para("All screenshots are genuine full-page captures from Microsoft Edge (headless, driven by Playwright, window 1280 px wide) "
           "taken by `tests/browser_events.py` while the portal ran on PHP's built-in server with a disposable database built "
           "from `database/studenthub_demo.sql` and a temporary poster folder. The poster images are fictional sample posters from "
           "`Practical-12/uploads`. To show this case, the test gave the first demo event the older poster reference "
           "`uploads/odoo_hackathon.jpg` whose file does not exist (as for four events of the live database). Captures 02, 06, 07 "
           "and 09 of the folder are not reproduced: they show the filled add form before submission, the list after the edit, "
           "the student's event list before registering and the *Event full* state, which is also visible in Figure 6.")
    r.figure("evidence/practical-12-integration/01-event-list.png",
             "Campus Events tab of the Admin Console: the 5 demo events with category, date, location, seats (0 / no limit) and "
             "Open status; \"Odoo Hackathon 2026\" shows a generic image icon and \"poster file not available\" for its older, missing "
             "poster reference", width=14)
    r.figure("evidence/practical-12-integration/03-poster-rejected.png",
             "Publishing \"Code Sprint 2026\" with the file cricket-cup.jpg (a PNG image saved with a .jpg name): the server "
             "refuses it – \"The file extension does not match its content (.jpg file containing image/png).\" – nothing was "
             "saved and the other values are kept", width=11)
    r.figure("evidence/practical-12-integration/04-event-created.png",
             "After four valid uploads (JPEG, PNG, WebP and JPEG posters): \"Event “Annual Cultural Night” was published.\" – the "
             "new events show their poster thumbnails delivered by poster.php and the seats 0 / no limit, 0 / 120, 0 / 40 and 0 / 1",
             width=12.5)
    r.figure("evidence/practical-12-integration/05-edit-event.png",
             "Editing \"Web Frameworks Workshop\" (event #7, 0 / 40 seats taken): capacity changed to 35, location to \"Computer "
             "Lab 3, A7 Building\"; the current poster is shown and kept when no new file is chosen", width=9.5)
    r.figure("evidence/practical-12-integration/08-registration-success.png",
             "Campus Events page of the student Riya Shah (26IT041) after registering: success message for \"Code Sprint 2026\" "
             "and \"You are registered\" with a Cancel registration button (capacity 1)", width=8.5)
    r.figure("evidence/practical-12-integration/10-registration-cancelled.png",
             "The same page for the second student Kunal Desai (26IT042): \"Code Sprint 2026\" shows 1 of 1 seats taken and "
             "\"Event full\" without a Register button; after registering for and cancelling \"Web Frameworks Workshop\" the "
             "message \"Your registration … was cancelled.\" appears and the card shows \"Registration cancelled\" with Register "
             "available again", width=8.5)
    r.figure("evidence/practical-12-integration/11-event-registrations.png",
             "Registrations view in the console for \"Code Sprint 2026\" (seats taken 1 / 1): Riya Shah, 26IT041, Information "
             "Technology, Registered, with the registration time; the list shows 1 registration for \"Web Frameworks Workshop\" "
             "(the cancelled one, kept as history) and 0 / 35 seats taken", width=11.5)
    r.figure("evidence/practical-12-integration/12-delete-refused.png",
             "Delete refused: \"Code Sprint 2026 has 1 registration(s) and cannot be deleted, so that the registration history is "
             "kept. Set its registration to Closed instead.\" – only \"Edit the event\" and \"Back\" are offered", width=11.5)
    r.figure("evidence/practical-12-integration/13-event-deleted.png",
             "An event without registrations deleted after confirmation: \"Event “Annual Cultural Night” was deleted.\" – 8 events "
             "remain; its poster file was removed from the poster folder (checked by the test)", width=12.5)
    r.figure("evidence/practical-12-integration/14-student-access-denied.png",
             "The student Riya Shah opening the Campus Events tab of the Admin Console: HTTP 403 \"Access Denied\"", width=12.5)

    # ------------------------------------------------------------------ 9
    r.heading("9. Testing and Results")
    r.para("All tests were executed on 31 October 2026 on Windows 11 with PHP 8.2.12 (XAMPP), MariaDB 10.4.32 and PHP's built-in "
           "server. Write tests used disposable databases and a temporary poster folder (`STUDENTHUB_UPLOAD_DIR`); "
           "`studenthub/uploads/` and the live database were not used. The live database then received migration 003 after a "
           "verified backup; its users, password hashes, students, registrations, menu and every original event value were "
           "verified unchanged. The numbers are copied from the saved outputs and from TEST_REPORT.md §9.")
    r.table([
        ["Suite", "Result", "Output"],
        ["`tests/test_events.py` – Campus Events tab, poster uploads, Campus Events page", "**94 / 94 passed**", "`tests/test_events_output.txt`"],
        ["`tests/browser_events.py` – Microsoft Edge + screenshots", "**16 / 16 passed**", "`tests/browser_events_output.txt`"],
        ["`database/tests/test_003_event_management.py` – fixture / real dump / `--verify-live`", "**27 / 27**, **26 / 26**, **5 / 5 passed**", "`database/tests/test_003_output.txt`, `test_003_verify_live_output.txt`"],
        ["Regression: `test_001` (88 / 88; 24 / 24 live), `test_002` (22 / 22; 4 / 4 live), `test_auth` (132 / 132), `test_students` (170 / 170)", "all passed", "outputs in `tests/` and `database/tests/`"],
        ["Regression in Edge: `browser_auth` (14 / 14), `browser_students` (16 / 16), `browser_inactive_login` (13 / 13)", "all passed", "outputs in `tests/`"],
    ], [8.6, 3.6, 3.8])
    r.heading("9.1 Checks per area (tests/test_events.py)", 2)
    r.table([
        ["Area", "Checks", "Examples of what is verified"],
        ["Static checks", "4", "`php -l`; no `->query()` with values; original file name never used; `uploads/.htaccess` content"],
        ["Database (migration 003)", "2", "`003` recorded; status, updated_at, event_categories and the foreign key exist"],
        ["Event listing (admin)", "5", "5 events, columns, generic icon for a missing older poster, `poster.php` 404 for it, CSRF tokens"],
        ["Add event", "9", "with and without poster; JPEG, PNG and WebP stored under 32-hex names with identical bytes; nosniff + sandbox CSP; visitors redirected; `.PNG` accepted"],
        ["Invalid event details", "16", "empty / short title, unknown category, impossible date 2027-02-30, time 25:00, capacity 0 / −5 / 70000 / text, description over 2000"],
        ["Poster upload validation", "14", "GIF, SVG with script, PHP, PHP renamed `.jpg`, `shell.php.jpg`, PNG named `.jpg`, truncated PNG, JPEG with PHP, 2.3 MB file, empty file, forged type; UPLOAD_REJECTED"],
        ["Edit event", "5", "poster kept; replaced with the old file deleted; invalid replacement refused; UPDATE_EVENT"],
        ["Student registration", "14", "success, duplicate, capacity 2 → third refused, closed, past, cancel and re-register, CSRF, GET, unlinked account, admin"],
        ["Simultaneous registrations", "1", "6 students for 3 seats at once → exactly 3 succeed"],
        ["Capacity, registrations view, deletion", "7", "capacity below seats taken refused; delete refused with registrations; confirmed delete removes event and poster"],
        ["Search and filters", "10", "search, category, status, upcoming / past, combinations; SQL-injection strings as text"],
        ["Access control", "3", "students and editors 403 for tab, forms and POST; visitors to the login page"],
        ["Storage, server log, clean-up", "4", "only used posters remain in the folder; no PHP warnings; live database and `studenthub/uploads` unchanged"],
        ["**Total**", "**94**", ""],
    ], [4.2, 1.6, 10.2])
    r.para("The Edge test (16 checks) published events with real JPEG, PNG and WebP posters, saw the server refuse a PNG renamed "
           "to `.jpg`, edited an event, registered two students until the capacity of 1 was reached, cancelled a registration, "
           "opened the registrations view, saw a delete refused for an event with registrations and an event without "
           "registrations deleted together with its poster, confirmed HTTP 403 for a student and found no JavaScript errors and "
           "no PHP warnings (apart from the known, pre-existing 404 for `/favicon.ico`).")

    # ------------------------------------------------------------------ 10
    r.heading("10. Problems Found and Handled During Integration")
    r.bullets([
        "**Windows security software:** for an uploaded test file that contains a well-known web-shell signature, the security "
        "software blocks reading the file. The portal then rejects it with \"could not be read as an image\" instead of the "
        "content-type message – the file is rejected either way (TEST_REPORT §9). `validate_poster()` reads the file once and "
        "rejects an unreadable file cleanly.",
        "**Older poster references:** existing events store paths such as `uploads/odoo_hackathon.jpg` whose files do not exist. "
        "Instead of broken images or file access outside the poster folder, `poster_path()` accepts only stored random names; "
        "these events show a generic image icon, `poster.php` answers 404, and the value is kept until a new poster is uploaded.",
        "**Registration history and CASCADE:** because `registrations` references `events` with `ON DELETE CASCADE`, deleting an "
        "event would erase its registrations. Deletion is therefore refused for events with registrations (closing the event "
        "is offered instead), both in the panel and inside `delete_event()`.",
        "**Concurrent registrations:** a plain INSERT would bypass the capacity rule; all registrations go through "
        "`register_student_for_event()`, verified with 6 simultaneous requests for 3 seats (exactly 3 succeed).",
    ])

    # ------------------------------------------------------------------ 11
    r.heading("11. Differences from the Original Standalone Practical and Limitations")
    r.table([
        ["Aspect", "Original report (Practical-12/)", "Integrated portal (studenthub/)"],
        ["Database", "Own `studenthub_prac12` with `events`, `event_categories`, `admins`", "Portal `studenthub_db.events` extended by migration 003; categories table with FK"],
        ["Login", "Own administrator table and session cookie `P12SESSID`", "Portal login (`STUDENTHUBSESSID`); role admin with `events.manage`"],
        ["Event fields", "event_title, required description (10–2000), venue, required time and poster", "title, location, optional time, description and poster; capacity 1–65535 or no limit"],
        ["Poster column", "`poster_filename` VARCHAR(64), UNIQUE + CHECK REGEXP", "`poster` VARCHAR(255), UNIQUE; name pattern enforced by `poster_path()` (older values kept)"],
        ["poster.php", "Validated file name, administrators only", "Event ID, every signed-in user (`portal.view`)"],
        ["Delete", "Event and poster after confirmation", "Only events without registrations; otherwise close the event"],
        ["Registration", "–", "Students register and cancel on the Campus Events page (transaction, capacity, duplicates)"],
        ["Orphan clean-up", "`tools\\cleanup_orphan_posters.php`", "No separate tool; new files are removed again when saving fails and old files after a replacement"],
        ["Tests", "153 / 153 automated, 13 / 13 browser", "94 / 94 automated, 16 / 16 browser, migration 003 tests"],
    ], [2.8, 6.4, 6.8])
    r.para("**Limitations** (TEST_REPORT §9): registrations cannot be marked *attended* from the interface; there is no waiting "
           "list; the Campus Events page shows all upcoming events on one page. The `.htaccess` protection of the poster folder takes "
           "effect only on Apache (`DEPLOYMENT.md` recommends placing the folder outside the document root via "
           "`STUDENTHUB_UPLOAD_DIR`); the portal was tested with PHP's built-in server, which ignores `.htaccess`, so the tests "
           "checked the file's content. The Admin Console loads Bootstrap from a CDN.")

    # ------------------------------------------------------------------ 12
    r.heading("12. Conclusion")
    r.para("Event management now works on the portal's own events. Administrators publish, edit, filter and delete events in the "
           "Admin Console; posters are accepted only after ten server-side checks of the upload and its content, stored under "
           "random names in a folder that is never served or executed, delivered only by `poster.php`, and replaced or removed only "
           "after the database change succeeded. Students register for events and cancel on the Campus Events page; one "
           "transaction with row locks prevents duplicates and overbooking, and events with registrations are never deleted, so "
           "the registration history is kept. Prepared statements, output escaping, CSRF tokens, server-side permissions and the "
           "audit log protect the module; 94 automated checks, 16 browser checks and the migration 003 tests passed.")

    # ------------------------------------------------------------------ 13
    r.heading("13. References")
    r.bullets([
        "Project repository: https://github.com/TheEmperor08/StudentHub-ITUE203-25CS023 – `studenthub/`, `database/` (migration "
        "003), `tests/`, `evidence/practical-12-integration/`, `TEST_REPORT.md` §9, `DEPLOYMENT.md`; commit `ba11795`",
        "PHP Manual – Handling file uploads: https://www.php.net/manual/en/features.file-upload.php",
        "PHP Manual – Fileinfo (finfo): https://www.php.net/manual/en/book.fileinfo.php",
        "PHP Manual – getimagesizefromstring: https://www.php.net/manual/en/function.getimagesizefromstring.php",
        "PHP Manual – random_bytes: https://www.php.net/manual/en/function.random-bytes.php",
        "PHP Manual – MySQLi prepared statements: https://www.php.net/manual/en/mysqli.quickstart.prepared-statements.php",
        "MariaDB Knowledge Base – SELECT … FOR UPDATE: https://mariadb.com/kb/en/for-update/",
        "OWASP – File Upload Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html",
        "OWASP – Cross-Site Request Forgery Prevention Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html",
    ])
