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
* **Admin dashboard** (Practical 14 integrated; `admin_dashboard.php`, `includes/dashboard.php`, `includes/navigation.php`): five live counters (students active/inactive, events upcoming/open, registrations active/cancelled/attended, accounts per role and disabled, audit entries and security blocks in 7 days) counted on every page load; latest event registrations, newest accounts and recent activity; **role-based navigation** from `menu_items` (student < editor < admin – an editor never sees an admin link; links to missing pages are hidden; menu values are HTML-escaped); **account status** – administrators disable or enable accounts (a disabled account cannot sign in and loses its open sessions; the own account and the last active administrator are protected); audit log with action / status / user filters; one consistent HTTP 403 page with an audit entry.
* **Real-time registration validation** (Practical 5 integrated; `assets/js/register-validation.js` on `register.php`): every field is checked with regular expressions while typing (the same rules and messages as the server), a password strength meter, and the form is not sent while a rule is broken; the server still validates everything.
* **Campus Data Explorer** (Practical 6 integrated; `data_explorer.php` + `assets/js/data.js`): the sample JSON datasets in `data/` (students, events, FAQs) are loaded with the Fetch API and rendered with search, filter, sorting, pagination and loading / error states (values HTML-escaped).
* **Stored contact inquiries** (Practical 7 integrated; `contact.php`, `includes/inquiries.php`, table `inquiries`): the Help & Contact form is validated and sanitised on the server, valid inquiries are stored with a reference number (signed-in users are linked to their account), a honeypot field stops simple bots; administrators read them and mark them as resolved in the Admin Console (*Inquiries* tab).
* **Admin Console:** student records, campus events, user accounts, inquiries and the audit log (above), plus the dashboard overview.
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
├── tools/sync_practical15.py     # makes / verifies Practical-15/ as the snapshot of studenthub/
├── DEPLOYMENT.md             # Apache / production deployment notes
├── submission-reports/       # Corrected / new practical reports (DOCX + PDF) for manual upload – see INDEX.md
├── tools/reports/            # Generator of those reports (python-docx; code excerpts and screenshots from the repository)
├── tests/                    # Authentication + student-management tests (disposable databases) + optional Edge browser tests
├── evidence/practical-11-integration/  # Genuine Edge screenshots of the integrated student management (fictional records)
├── evidence/practical-12-integration/  # Genuine Edge screenshots of the integrated event management
├── evidence/practical-13-integration/  # Genuine Edge screenshots of the Event Finder (Fetch API)
├── evidence/practical-14-integration/  # Genuine Edge screenshots of the admin dashboard
├── evidence/practical-05-07-integration/  # Genuine Edge screenshots of Practicals 5-7 in the portal
├── evidence/practical-15-integration/     # End-to-end Edge scenario through the final portal (17 workflows)
├── README.md
└── TEST_REPORT.md            # Tests actually executed, with results and limitations
```

---

## 💻 Local Setup (Windows + XAMPP)
**Requirements:** XAMPP with PHP 8.1+ (tested: 8.2.12, extensions `mysqli`, `fileinfo`, `mbstring`) and MariaDB 10.4+ / MySQL 8
(tested: MariaDB 10.4.32). Python 3 is needed only for the tests; Playwright + Microsoft Edge only for the browser tests.

1. **Start MySQL** in the XAMPP Control Panel.
2. **Create the database** (new installation – schema with migrations 001–005 and fictional demo rows, no accounts):
   ```bat
   C:\xampp\mysql\bin\mysql.exe -u root -e "CREATE DATABASE IF NOT EXISTS studenthub_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
   C:\xampp\mysql\bin\mysql.exe -u root studenthub_db < database\studenthub_demo.sql
   ```
   **Existing database:** back it up (`mysqldump`) and apply only the migrations it is missing, in order –
   `database/migrations/001_…` to `005_…` (`SELECT * FROM schema_migrations` shows what is applied; details in `database/README.md`).
3. **Create the first administrator** (no passwords are stored in the repository; you are prompted for one):
   ```bat
   C:\xampp\php\php.exe tools\create_demo_user.php --db=studenthub_db --username=admin01 --email=admin01@example.com --role=admin
   ```
   Use `--role=editor` or `--role=student` for further accounts. Students normally register themselves at `register.php`,
   which creates the account and its linked student record together.
4. **Run** the portal with PHP's built-in server and open `http://localhost:8000/`:
   ```bat
   C:\xampp\php\php.exe -S localhost:8000 -t studenthub
   ```
   (Or serve the repository root and open `http://localhost:8000/studenthub/`; the root `index.php` redirects there.)

**Configuration** (environment variables, all optional):

| Variable | Default | Meaning |
|---|---|---|
| `DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME` | `localhost`, `root`, *(empty)*, `studenthub_db` | database connection (there is no fallback database) |
| `STUDENTHUB_SESSION_TIMEOUT` | `1800` | inactivity timeout in seconds |
| `STUDENTHUB_TIMEZONE` | `Asia/Kolkata` | time zone for dates (should match the database server) |
| `STUDENTHUB_UPLOAD_DIR` | `studenthub/uploads` | folder for event posters (must not be reachable over HTTP) |

**Tests:** `python tests\run_all.py` runs every database and HTTP suite and the Practical 15 snapshot check on disposable
databases; add `--browser <python-with-playwright>` for the Microsoft Edge suites. Deployment on Apache: see `DEPLOYMENT.md`.

**Practical folders:** `Practical-1/` … `Practical-14/` keep the original standalone versions and their own databases as
historical evidence (their READMEs explain how to run them); `Practical-15/` is the verified snapshot of `studenthub/`.

---

## 📜 Practical Status
Status reflects what was **actually tested** (see `TEST_REPORT.md`). "Code present" means the feature exists in code but was not verified in a browser.

| # | Topic | Status |
|---|---|---|
| 1 | Planning: roles, sitemap, structure | Partial – text sitemap only; no wireframe image yet |
| 2 | Static semantic HTML pages (12) | Code present |
| 3 | Grid / Flexbox / Bootstrap layout | Code present |
| 4 | DOM: FAQ, modal, slider, banner, hamburger, theme | Code present |
| 5 | Registration validation with regex | Integrated into `studenthub/register.php` (real-time validation + strength meter) and tested (`tests/test_forms.py`, `tests/browser_forms.py`); the standalone CAPTCHA was not carried over (see TEST_REPORT §12) |
| 6 | Fetch API, search, filter, sort, pagination | Integrated into `studenthub/` (Campus Data Explorer) and tested (`tests/test_forms.py`, `tests/browser_forms.py`) |
| 7 | PHP POST form → CSV with `flock` | Integrated into `studenthub/` (Help & Contact stores validated inquiries in the database; Admin Console Inquiries tab) and tested (`tests/test_forms.py`, `tests/browser_forms.py`) |
| 8 | PDO, prepared statements, 3NF schema | Rebuilt and tested |
| 9 | Secure registration (hashing, duplicates) | Integrated into `studenthub/` and tested (`tests/test_auth.py`) |
| 10 | Login, sessions, RBAC | Integrated into `studenthub/` and tested, including the inactivity timeout (remember-me is not part of the portal) |
| 11 | Student CRUD, search, soft delete, CSV | Integrated into `studenthub/` (Admin Console → Student Records) and tested (`tests/test_students.py`, Edge screenshots in `evidence/practical-11-integration/`) |
| 12 | Event uploads with validation, RBAC | Integrated into `studenthub/` (Admin Console → Campus Events, Campus Events page) and tested (`tests/test_events.py`, Edge screenshots in `evidence/practical-12-integration/`) |
| 13 | Fetch/AJAX CRUD API with RBAC | Integrated into `studenthub/` (Event Finder + `api/events.php`) and tested (`tests/test_api.py`, Edge screenshots in `evidence/practical-13-integration/`) |
| 14 | Admin dashboard, audit logging, 403 | Integrated into `studenthub/` (Admin Console overview, role-based navigation, account status, audit filters) and tested (`tests/test_dashboard.py`, Edge screenshots in `evidence/practical-14-integration/`) |
| 15 | Integrated portal (copy of `studenthub/`) | Final snapshot of `studenthub/` (verified byte-for-byte, `tests/test_snapshot.py`); end-to-end Edge test of 17 workflows (`tests/browser_e2e.py`, `evidence/practical-15-integration/`) |

---

## 📝 Corrected Reports
`submission-reports/` contains corrected reports for Practicals 5–13 and new reports for Practicals 14 and 15 (DOCX and PDF),
describing each practical as part of the integrated portal with genuine screenshots from `evidence/` and the saved test
results. `submission-reports/INDEX.md` lists which original report each file replaces. The original reports in the
`Practical-N/` folders are unchanged; nothing was uploaded to Microsoft Teams – the files are for manual replacement after
checking. Rebuild with `python tools/reports/build_reports.py --pdf` (needs python-docx, Pillow and Microsoft Word).

---

## 🛡️ Security Notes
* Passwords are hashed with bcrypt; no plaintext passwords or hashes are committed.
* The main application (all queries with user input) and Practicals 8–14 use prepared statements (MySQLi or PDO).
* Output is escaped with `htmlspecialchars()`.
* Student records are never deleted by the portal (soft delete only), and the CSV export prefixes cells that start with `=`, `+`, `-`, `@`, tab or carriage return with an apostrophe so spreadsheets do not run them as formulas.
* The main portal checks a CSRF token on every POST, logs out only by POST, sends `Cache-Control: no-store`, `X-Frame-Options: DENY` and `X-Content-Type-Options: nosniff` on signed-in pages, and redirects only to its own pages.
* Known limitations are listed in `TEST_REPORT.md`.

## 👨‍🎓 Author
**Shreyas** – 25CS023 – Department of Computer Science & Engineering, CSPIT, CHARUSAT
