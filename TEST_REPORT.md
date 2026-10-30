# StudentHub – Test Report

**Student:** Shreyas | **Roll No:** 25CS023 | **Course:** ITUE203 – Web Development Frameworks
**Date executed:** 29 October 2026
**Environment:** Windows 11, PHP 8.2.12 (XAMPP), MariaDB 10.4.32, PHP built-in server (`php -S localhost:8000`)

This report lists **only tests that were actually executed**. The previous report contained results that could not be reproduced and has been withdrawn. Tests ran against throwaway copies of the main database or the separate practical databases; the working `studenthub_db` was verified unchanged with `CHECKSUM TABLE` before and after.

**How tests were run:** automated shell scripts issuing real requests – either PHP CLI renders of each page with a simulated session, or HTTP requests to the running server with separate cookie jars per role – and asserting on the output and database state. **No browser was used**, so no visual, layout or JavaScript behaviour is claimed as tested.

---

## 1. Syntax checks
`php -l` on every PHP file in `studenthub/`, `Practical-1` … `Practical-15` and `tools/` – **no syntax errors**.

## 2. Main application (`studenthub/`) – 95 / 95 passed
| Area | What was checked |
|---|---|
| Personalisation | Accounts without a student record show Shreyas / 25CS023 on dashboard, profile, results, attendance, achievements, assignments and contact; no other student's name or roll number appears |
| Database-driven profiles | Other students (e.g. Diya Shah 25CE045, semester 5) see their own records; semester shows "5th", not "5rd" |
| Sample labels | Dashboard, results, attendance and achievements show "Sample / demo data" |
| Access control | Results without login renders nothing (redirect); a student opening the Admin Console gets the 403 page |
| Registration + login | New account registered through `register.php`; login with the correct password succeeds, wrong password is rejected |
| Password change | Too short, mismatched and wrong-current-password attempts are rejected and the stored hash is unchanged; a failed attempt is audit-logged; a valid change stores a bcrypt hash, the new password logs in and the old one does not |
| Profile contact form | Reports that saving is unavailable instead of claiming success; phone no longer defaults to the college helpline |
| `insert.php` | Returns "Feature unavailable" (HTTP 410) and writes nothing |
| Rendering | All pages render with no PHP warnings; sidebar, hamburger button, skip link, active-link marker and scrollable table wrappers present in the HTML |

**Achievements / assignments forms (HTTP, throwaway database) – 21 / 21 passed:** file inputs are disabled with an "uploads not available" note; valid submissions show a "noted in the activity log only" message (never "submitted/uploaded successfully"); a file attached anyway is reported as NOT saved; empty event names, impossible dates (2026-02-31) and unknown subjects are rejected with no audit entry; an event name containing `<script>` is HTML-escaped; exactly one audit row per valid submission, worded "no file stored"; no file was written anywhere in the project; the live database was unchanged.

**Redesign (v7) structural checks (HTTP, throwaway database) – 196 / 196 passed:** every sidebar page returns 200 with the new stylesheet, mobile top bar, hamburger button, sidebar brand, user card, active-link marker and page header (hero on the dashboard) and no PHP warnings; dashboard shows the welcome hero, four stat tiles, sample labels, timetable anchor and dated event cards; profile, contact, notices, directory, results, courses and achievements render their new layouts with every original form field name present; login/register/403 use the new split layout (register keeps all 11 fields; a student opening the Admin Console still gets HTTP 403); the home page keeps all 10 element IDs used by `script.js`; the Admin Console loads for an admin; all stylesheets and `theme.js` are served. JavaScript files were not syntax-checked by a tool (Node.js is not installed).

**Fresh-install check:** `database/studenthub_demo.sql` imported into an empty database (twice – idempotent; 0 users, 0 audit logs), an admin created with `tools/create_demo_user.php`, login succeeded, and the Admin Console, dashboard, directory and notifications pages rendered with no PHP warnings.

## 3. Practicals 7–14 (HTTP) – 52 / 52 passed (+ Practical 7 manual run)
| Practical | Checks |
|---|---|
| 7 | Valid POST redirects to `Practical-7/contact.html?success=1` and appends a CSV row; invalid POST redirects with all four validation messages |
| 8 | `db.php` connects via PDO to `practical8_db`; list shows seeded rows; 3-table JOIN returns 5 registrations; bound `?branch=` filter works; SQL-injection string returns 0 rows; valid insert succeeds; duplicate and invalid inputs are rejected |
| 9 | Registration stores a bcrypt hash; duplicate email is not inserted; `users.php` no longer shows full hashes |
| 10 | Admin login → dashboard; wrong password rejected; student blocked from admin dashboard (403); student dashboard loads; `last_login` recorded |
| 11 | Anonymous → redirected to login; student → 403; admin → full CRUD via prepared statements (create, duplicate email rejected, update, soft delete, search, SQL-injection search string matches nothing, CSV export, hard delete) |
| 12 | Admin sees event manager; student does not get the add form; real PNG poster uploaded; non-image file rejected; deleting an event removes the row and the poster file |
| 13 | Anonymous API call → 401; student role read from the session; student create/delete blocked (403) even when sending `role=admin`; admin create/delete succeed; duplicate email → clean 409 JSON; student menu excludes admin items |
| 14 | Admin dashboard loads; student gets 403 and a `SECURITY_BLOCK` audit entry |

---

## 4. Not tested
* **Browser/visual:** page appearance, responsive layout at phone/tablet widths (including stacked mobile tables), hamburger drawer behaviour, dark mode, focus outlines and colour contrast in a real browser (the v7 redesign was verified only by HTML/CSS inspection and HTTP checks).
* **Client-side JavaScript:** Practicals 2–6 (static pages, slider, modal, FAQ, regex validation, fetch/filter/sort/paginate) and the Practical 13 page script.
* **Practical 10:** 5-minute inactivity timeout and remember-me cookie login.
* **Practical 7 on Apache:** `private/.htaccess` blocking (the project is served with `php -S`, which ignores `.htaccess`).
* **Main app:** admin student add/delete, event poster upload/delete and CSV export were not exercised in this run.
* **Practical 1:** no wireframe or sitemap image exists to verify.

## 5. Known limitations
* Profile phone/address, achievement certificates and assignment files are not stored (no database columns or upload handling). Each form says so explicitly: the file inputs are disabled, and submissions are only noted in the activity log with "no file stored".
* All practicals and the main portal share one PHP session on `localhost:8000`, so logging into one app can authorise another that checks only the role.
* Admin delete actions use GET links without CSRF tokens; the login page reveals whether an account exists.
* Practical 12 uses escaped (not prepared) SQL for event insert/update.
* With `php -S`, `Practical-7/private/contacts.csv` can be downloaded directly; it is protected only on Apache and is excluded from the repository.
* The live `studenthub_db` still contains a menu link to a non-existent `faculty.php` (the demo SQL omits it).
* Academic figures are sample data, not real results.

---

## 6. Practicals 9 and 10 integrated into `studenthub/` (31 October 2026)
Executed on the same environment against the disposable database `studenthub_auth_test` (built from `database/studenthub_demo.sql`, dropped afterwards); the live `studenthub_db` users and password hashes were compared before and after and were unchanged. A second run used a restored copy of the real pre-change dump (also disposable) and gave the same result.

| Suite | Result | Output |
|---|---|---|
| `tests/test_auth.py` – HTTP tests against PHP's built-in server | **132 / 132 passed** | `tests/test_auth_output.txt` |
| `tests/browser_auth.py` – Microsoft Edge (headless, Playwright) | **14 / 14 passed** | `tests/browser_auth_output.txt` |
| `database/tests/test_001_practical8_foundation.py` – re-run after the change | **87 / 87 passed** | `database/tests/test_001_output.txt` |
| `php -l` on all 31 PHP files of `studenthub/` and `tools/` | no syntax errors | (part of `test_auth.py`) |

Covered: successful registration, invalid email, weak/short/too-long password, mismatched passwords, duplicate email and username (case and spaces ignored), `role=admin` sent by the form ignored, transaction rollback when the student insert fails, `students.user_id` linkage, five simultaneous registrations (consecutive enrollment numbers), login by username and email, wrong password and unknown account (same generic message, HTTP 401), session ID regeneration, the inactivity timeout (2-second test server), POST logout and replay of the old cookie, unauthenticated direct URLs, student and editor denied the Admin Console (403 + audit entry, admin POST operations refused), admin access, CSRF rejection on every form, role change/deletion while signed in, open-redirect attempts, the database unavailable (unknown database and wrong password → HTTP 503 with no details and no fallback to `user_registration`), and no PHP warnings or passwords in the server log.

Items above that this supersedes: §2 "accounts without a student record show Shreyas / 25CS023" (they now see only their own username and no enrollment number); §4 "Practical 10 inactivity timeout" (tested for the portal); §5 "admin delete actions use GET links without CSRF tokens; the login page reveals whether an account exists" (fixed) and "all practicals and the main portal share one PHP session" (the portal now uses its own `STUDENTHUBSESSID` cookie; the practical folders still share theirs).

Not covered: no limit on repeated login attempts; editors hold only the student-portal permission; `Practical-15/` is still the older copy of the portal; the browser reports one 404 for `/favicon.ico` because the portal has no favicon.

---

## 7. Practical 11 integrated into `studenthub/` – student management (31 October 2026)
Same environment. All write tests ran against disposable databases (`studenthub_p11_test`, `studenthub_mig002_*`, built from `database/studenthub_demo.sql` or from a restored copy of the real dump, dropped afterwards). The live `studenthub_db` received only migration 002 (a UNIQUE index), after a verified backup; its users, password hashes, students, events, registrations and menu items were verified unchanged afterwards.

| Suite | Result | Output |
|---|---|---|
| `tests/test_students.py` – HTTP tests of the Student Records tab (demo data) | **148 / 148 passed** | `tests/test_students_output.txt` |
| `tests/test_students.py --source-dump` – the same on a restored copy of the real database | **148 / 148 passed** | (not committed: contains real records) |
| `tests/browser_students.py` – Microsoft Edge (headless, Playwright) + screenshots | **16 / 16 passed** | `tests/browser_students_output.txt`, `evidence/practical-11-integration/` |
| `database/tests/test_002_unique_enrollment_no.py` – migration 002 (fixture / real dump) | **22 / 22** and **22 / 22 passed** | `database/tests/test_002_output.txt` |
| `test_002_unique_enrollment_no.py --verify-live` – live database after applying 002 | **4 / 4 passed** | `database/tests/test_002_verify_live_output.txt` |
| `tests/test_auth.py` – Practicals 9/10 regression (student deletion checks changed to soft delete) | **132 / 132 passed** | `tests/test_auth_output.txt` |
| `tests/browser_auth.py` – Practicals 9/10 Edge regression | **14 / 14 passed** | `tests/browser_auth_output.txt` |
| `database/tests/test_001_practical8_foundation.py` – Practical 8 regression (fixture) / `--verify-live` | **87 / 87** and **24 / 24 passed** | `database/tests/test_001_output.txt` |
| `php -l` on all 32 PHP files of `studenthub/` and `tools/` | no syntax errors | (part of both suites) |

Covered by `test_students.py`: admin listing (newest first, status and account columns, empty state, pagination with filters kept); adding with an entered and with an automatic enrollment number (next number of the `YYPPnnn` scheme from the semester's admission year and the course code), no login account created; validation of every field (empty/invalid name, HTML in the name, invalid or too long e-mail, unknown course, unknown gender, wrong enrollment format, SQL in the enrollment number, array parameters, all fields empty) with the values shown again HTML-escaped; duplicate enrollment numbers (same, lower case, with spaces) and e-mails refused, also by the database index, and reported together with other errors; semesters `0`, `9`, `12`, `-1`, `3.5`, `abc`, `1 OR 1=1` and empty refused; editing (values saved; account link, status, enrollment number, creation time and registrations unchanged; duplicates and invalid semester refused; legacy records with an old number format, course, gender and no semester editable); search by name, e-mail and enrollment number, `%` and `_` matched literally; course, semester and status filters alone and combined with the search; SQL-injection strings in the search, filters, page number and record ID; soft delete through a confirmation page (status `Inactive`, record, account link and both historical registrations unchanged, GET and token-less requests change nothing); an inactive student refused by `register_student_for_event()` and hidden from the directory; reactivation (and registering again afterwards); CSV export (BOM, CRLF, header without account data, inactive rows included, filtered export of all pages, file name time in the portal time zone, `=`, `+`, `-`, `@`, tab and carriage-return cells prefixed with an apostrophe); students, editors and visitors refused for the tab, the forms, the export and every POST action; CSRF rejection (missing, wrong, modified and another admin's token); audit entries `CREATE_STUDENT`, `UPDATE_STUDENT`, `DEACTIVATE_STUDENT`, `REACTIVATE_STUDENT`, `EXPORT_CSV`; no PHP warnings in the server log.

Screenshots (`evidence/practical-11-integration/`, Edge 1280 px wide, full page, fictional records): student list, add form, validation errors, student created, search results, filtered records, edit form, student updated, deactivation confirmation, inactive record, reactivated record, CSV export, access denied for a student. `12-csv-export.png` shows the downloaded file (`12-csv-export-web-development-active.csv`, also in the folder) rendered as text and as a table in the browser, because a headless browser has no download bar and Excel was not used.

Fixed during this step: PHP used XAMPP's `Europe/Berlin` time zone while MariaDB uses the system's India time, so between midnight and about 04:30 the portal's dates (form defaults, academic year, export file name) were one day behind; `db.php` now sets `Asia/Kolkata` (override: `STUDENTHUB_TIMEZONE`).

Not covered / limitations: inactive students can still sign in (only event registration and the directory treat them as inactive); there is no interface to link an added record to an existing login account; the soft-delete time is recorded in the audit log, not in a column of `students`; the add form offers automatic enrollment numbers only for the four registration courses (others need a typed number); the Admin Console still loads Bootstrap from a CDN; the browser reports one 404 for `/favicon.ico`.
