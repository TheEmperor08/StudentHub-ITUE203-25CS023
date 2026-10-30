# 🎓 StudentHub – Integrated Campus Portal

**Student:** Shreyas | **Roll No:** 25CS023 | **Email:** 25cs023@charusat.edu.in
**Course:** ITUE203 – Web Development Frameworks | **Institute:** CSPIT, CHARUSAT | **Academic Year:** 2026-27
**Repository:** [https://github.com/TheEmperor08/StudentHub-ITUE203-25CS023](https://github.com/TheEmperor08/StudentHub-ITUE203-25CS023)

> This project was adapted from a classmate's StudentHub project, used as a starting point as permitted by the course. It has been personalised, extended, fixed and redesigned; no other student's personal information is included.

---

## 🌟 Overview
StudentHub is a PHP/MySQL student portal built up across 15 practicals: semantic HTML pages, responsive CSS, JavaScript interactivity, PHP forms, PDO/MySQLi database access, authentication with sessions and role-based access control, CRUD, file uploads, a Fetch-based API and an admin console with audit logging.

## 🚀 Features (main application – `studenthub/`)
* **One authentication system** (`studenthub/includes/auth.php`, Practicals 9 + 10 integrated): login by username or email with `password_verify()` and one generic error message, session ID regeneration at login, hardened session cookie (`STUDENTHUBSESSID`, HttpOnly, SameSite=Strict, Secure on HTTPS), 30-minute inactivity timeout (override with the `STUDENTHUB_SESSION_TIMEOUT` environment variable, in seconds), account re-checked on every request, CSRF tokens on every POST form, logout only by POST.
* **Self-registration** (`studenthub/includes/registration.php`): server-side validation of every field, password policy (8–72 characters with upper- and lower-case letters, a digit and a special character), duplicate username/email refused, role always `student`; the account and its `students` record (next enrollment number of the `YYPPnnn` scheme, linked through `students.user_id`) are created in one transaction.
* **Role-based access:** roles admin, editor and student with explicit permissions; admins land on the Admin Console; anyone else requesting it gets the HTTP 403 page and an audit-log entry. Editors currently hold only the student-portal permission.
* **No fallback database:** if `studenthub_db` is unreachable the portal answers HTTP 503 with a generic message and logs the reason on the server.
* **Student pages:** dashboard, profile (with a working, verified password change), courses, attendance, assignments, results, achievements, notifications, directory and contact.
* **Profile data from the database:** name and roll number come from the logged-in user's `students` record (`studenthub/student_profile.php`).
* **Student management** (Practical 11 integrated; Admin Console → *Student Records*, `admin_dashboard.php?tab=students`, logic in `studenthub/includes/student_management.php`): paginated list of the `students` records with Active/Inactive status and account-link column; add and edit forms with server-side validation (enrollment number format and uniqueness, e-mail, course from the list, semester 1–8, gender); an empty enrollment number gets the next number of the existing `YYPPnnn` scheme; combined search (name, e-mail, enrollment number) and course/semester/status filters; **soft delete** – *Deactivate* (after a confirmation page) sets the status to `Inactive` and keeps the record, its account link and its event registrations; a student account linked to an inactive record cannot sign in, and an open session ends at its next request (generic message, admins and editors unaffected); *Reactivate* restores it; CSV export of the filtered records (UTF-8 with BOM, formula injection neutralised, no account data). Admins only (`students.manage`); every change is a POST with a CSRF token and is audit-logged. No login account is created for an added record.
* **Event management** (Practical 12 integrated; Admin Console → *Campus Events*, logic in `studenthub/includes/event_management.php`): list with search and category / open-closed / upcoming-past filters; add and edit with server-side validation (title, category from `event_categories`, date, time, location, capacity 1–65535 or no limit, open/closed, description); **secure poster upload** – JPEG, PNG or WebP only, at most 2 MB, MIME type of the content must match the extension, real image structure, no embedded PHP, random 32-hex file name, stored in `studenthub/uploads/` (denied over HTTP on Apache, PHP disabled) and delivered only by `poster.php` to signed-in users; the capacity can never be set below the seats taken; events with registrations cannot be deleted (close them instead); registrations view per event; older poster references whose file is missing show a placeholder.
* **Event registration** (Practicals 8 + 12; *Campus Events* page `notifications.php`): students with a linked student record register and cancel; `register_student_for_event()` runs in one transaction and refuses duplicates, full, closed and past events and inactive students (6 simultaneous requests for 3 seats → exactly 3 succeed).
* **Event Finder – Fetch API** (Practical 13 integrated; `events_live.php` + `assets/js/events-live.js`, JSON API `api/events.php`): events are listed, searched (debounced, 300 ms) and filtered without reloading the page; administrators create, edit and delete events in a dialog and students register or cancel – all through `fetch()`. Loading, success, empty and error states; every value inserted with `textContent`. The API uses the portal's own connection, session and event/registration rules and answers JSON with fitting status codes (200, 201, 400, 401, 403, 404, 405, 409, 415, 422, 500, 503); POST requests need `Content-Type: application/json` and the session's CSRF token in `X-CSRF-Token`.
* **Admin Console:** live counters, student records and campus events (above), user list, audit log viewer.
* **Design:** one indigo design system (`assets/css/global.css` + `assets/css/bootstrap-theme.css`), grouped sidebar with icons, mobile drawer with hamburger button, light/dark theme, skip link, visible keyboard focus, reduced-motion support.

> ⚠️ **Sample data:** CGPA, SGPA, attendance and timetable figures in the student pages are **placeholders labelled "Sample / demo data"**, not real academic results.

---

## 📁 Repository Structure
```text
StudentHub/
├── index.php                 # Redirects to studenthub/index.php
├── studenthub/               # Main application
├── Practical-1 … Practical-15/
├── database/studenthub_demo.sql  # Safe demo schema + data (no accounts, no hashes)
├── tools/create_demo_user.php    # CLI: create local accounts (password prompted)
├── tests/                    # Authentication + student-management tests (disposable databases) + optional Edge browser tests
├── evidence/practical-11-integration/  # Genuine Edge screenshots of the integrated student management (fictional records)
├── evidence/practical-12-integration/  # Genuine Edge screenshots of the integrated event management
├── evidence/practical-13-integration/  # Genuine Edge screenshots of the Event Finder (Fetch API)
├── README.md
└── TEST_REPORT.md            # Tests actually executed, with results and limitations
```

---

## 💻 Local Setup
**Requirements:** PHP 8.x with `mysqli` and `pdo_mysql`, MySQL 8 or MariaDB 10.4+.

1. **Main application database**
   ```bash
   mysql -u root -e "CREATE DATABASE IF NOT EXISTS studenthub_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
   mysql -u root studenthub_db < database/studenthub_demo.sql
   ```
   A `studenthub_db` created **before** the Practical 8 integration is upgraded with `database/migrations/001_practical8_foundation.sql` and then `002_unique_enrollment_no.sql` instead (back up first; see `database/README.md`). A database already at migration 001 needs only migration 002.
2. **Create accounts** (no passwords are stored in this repository; you are prompted for one):
   ```bash
   php tools/create_demo_user.php --db=studenthub_db --username=admin01 --email=admin01@example.com --role=admin
   ```
   Students can also self-register at `studenthub/register.php`.
3. **Practical databases** (each practical uses its own database; `studenthub_db` is never touched):
   ```bash
   mysql -u root < Practical-8/schema.sql             # practical8_db
   mysql -u root < Practical-10/user_registration.sql # user_registration (Practicals 9, 10, 14; 11 and 13 log in here)
   mysql -u root < Practical-14/schema.sql
   mysql -u root < Practical-11/schema.sql            # student_db (Practicals 11, 13)
   mysql -u root < Practical-13/schema.sql
   mysql -u root < Practical-12/schema.sql            # event_db
   ```
   Create practical accounts with the same tool, e.g. `--db=user_registration` or `--db=event_db`.
4. **Run**
   ```bash
   php -S localhost:8000
   ```
   Open `http://localhost:8000/` (main portal) or `http://localhost:8000/Practical-N/…`.

Database credentials default to `root` with an empty password on `localhost`; override with the `DB_HOST`, `DB_USER`, `DB_PASS` and `DB_NAME` environment variables. Dates use the `Asia/Kolkata` time zone (the same as MariaDB on the XAMPP server); override with `STUDENTHUB_TIMEZONE`.

---

## 📜 Practical Status
Status reflects what was **actually tested** (see `TEST_REPORT.md`). "Code present" means the feature exists in code but was not verified in a browser.

| # | Topic | Status |
|---|---|---|
| 1 | Planning: roles, sitemap, structure | Partial – text sitemap only; no wireframe image yet |
| 2 | Static semantic HTML pages (12) | Code present |
| 3 | Grid / Flexbox / Bootstrap layout | Code present |
| 4 | DOM: FAQ, modal, slider, banner, hamburger, theme | Code present |
| 5 | Registration validation with regex | Code present |
| 6 | Fetch API, search, filter, sort, pagination | Code present (needs a web server, not `file://`) |
| 7 | PHP POST form → CSV with `flock` | Tested (HTTP) |
| 8 | PDO, prepared statements, 3NF schema | Rebuilt and tested |
| 9 | Secure registration (hashing, duplicates) | Integrated into `studenthub/` and tested (`tests/test_auth.py`) |
| 10 | Login, sessions, RBAC | Integrated into `studenthub/` and tested, including the inactivity timeout (remember-me is not part of the portal) |
| 11 | Student CRUD, search, soft delete, CSV | Integrated into `studenthub/` (Admin Console → Student Records) and tested (`tests/test_students.py`, Edge screenshots in `evidence/practical-11-integration/`) |
| 12 | Event uploads with validation, RBAC | Integrated into `studenthub/` (Admin Console → Campus Events, Campus Events page) and tested (`tests/test_events.py`, Edge screenshots in `evidence/practical-12-integration/`) |
| 13 | Fetch/AJAX CRUD API with RBAC | Integrated into `studenthub/` (Event Finder + `api/events.php`) and tested (`tests/test_api.py`, Edge screenshots in `evidence/practical-13-integration/`) |
| 14 | Admin dashboard, audit logging, 403 | Tested |
| 15 | Integrated portal (copy of `studenthub/`) | Tested via the main application suite |

---

## 🛡️ Security Notes
* Passwords are hashed with bcrypt; no plaintext passwords or hashes are committed.
* The main application and Practicals 8, 9, 10, 11, 13 and 14 use prepared statements (MySQLi or PDO) for queries with user input. Practical 12's event insert/update still uses `mysqli_real_escape_string()` (escaped, but not prepared) – listed as a remaining improvement.
* Output is escaped with `htmlspecialchars()`.
* Student records are never deleted by the portal (soft delete only), and the CSV export prefixes cells that start with `=`, `+`, `-`, `@`, tab or carriage return with an apostrophe so spreadsheets do not run them as formulas.
* The main portal checks a CSRF token on every POST, logs out only by POST, sends `Cache-Control: no-store`, `X-Frame-Options: DENY` and `X-Content-Type-Options: nosniff` on signed-in pages, and redirects only to its own pages.
* Known limitations are listed in `TEST_REPORT.md`.

## 👨‍🎓 Author
**Shreyas** – 25CS023 – Department of Computer Science & Engineering, CSPIT, CHARUSAT
