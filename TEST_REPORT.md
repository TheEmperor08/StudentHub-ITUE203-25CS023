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

Not covered / limitations: ~~inactive students can still sign in~~ (fixed, see §8); there is no interface to link an added record to an existing login account; the soft-delete time is recorded in the audit log, not in a column of `students`; the add form offers automatic enrollment numbers only for the four registration courses (others need a typed number); the Admin Console still loads Bootstrap from a CDN; the browser reports one 404 for `/favicon.ico`.

---

## 8. Fix: deactivated students can no longer sign in (31 October 2026)
`studenthub/includes/auth.php` and `studenthub/login.php`: an account with the role `student` whose linked student record (`students.user_id`) has the status `Inactive` is refused at sign-in **after** the password has been verified (HTTP 403, no session started, `LOGIN_DENIED` in the audit log), and the account is re-checked together with its record on every request, so an open session ends at the next request (session data deleted on the server, new empty session ID, `SESSION_REVOKED` in the audit log). Both cases show one generic message: *"Your access to StudentHub is currently disabled. Please contact the administrator."* A wrong password still gets the normal *"Invalid username/email or password."*, so the status is never revealed to someone without the password. Admin and editor accounts (even if linked to an inactive record) and student accounts without a linked record are not affected; no link is created and no data is changed. Reactivating the record in the Admin Console restores normal sign-in. The console's deactivation confirmation and message now say that a linked student account can no longer sign in. The live database needed no change (it has no student account linked to an inactive record) and was verified identical to the backup taken before the fix.

| Suite (disposable databases) | Result | Output |
|---|---|---|
| `tests/test_students.py` – Practical 11 suite incl. 22 new sign-in checks (demo data / restored real dump) | **170 / 170** and **170 / 170 passed** | `tests/test_students_output.txt` |
| `tests/browser_inactive_login.py` – Microsoft Edge: register, deactivate, session ended, sign-in refused, reactivate, sign-in | **13 / 13 passed** | `tests/browser_inactive_login_output.txt` |
| `tests/browser_students.py` – Practical 11 Edge regression (screenshots 01–13 regenerated with the new wording) | **16 / 16 passed** | `tests/browser_students_output.txt` |
| `tests/test_auth.py` – Practicals 9/10 regression (demo data / restored real dump) | **132 / 132** and **132 / 132 passed** | `tests/test_auth_output.txt` |
| `tests/browser_auth.py` – Practicals 9/10 Edge regression | **14 / 14 passed** | `tests/browser_auth_output.txt` |
| `database/tests/test_001_practical8_foundation.py` – Practical 8 regression | **87 / 87 passed** | `database/tests/test_001_output.txt` |
| `database/tests/test_002_unique_enrollment_no.py` – migration 002 (fixture / real dump) | **22 / 22** and **22 / 22 passed** | `database/tests/test_002_output.txt` |

New checks: active linked student signs in; after deactivation the open session's next request goes to the sign-in page with `status=access_disabled`, the session ID changes, the old cookie gives no access, a POST with the old form token is not processed, public pages show the visitor as signed out; sign-in with the correct password (username or e-mail) is refused with HTTP 403 and the generic message, no session, `last_login` unchanged, `LOGIN_DENIED` logged, no record details in the message; a wrong password gets the normal message; an editor keeps an open session and signs in normally while linked to an inactive record (and still gets 403 for the Admin Console), an admin linked to an inactive record signs in and opens the console; a student account without a linked record signs in and no link is created; after reactivation the student signs in and opens the dashboard and profile; users (incl. password hashes), student records (all fields except status), links and registrations unchanged.

Screenshots (`evidence/practical-11-integration/`): `14-admin-deactivated-linked-student.png`, `15-session-ended-after-deactivation.png`, `16-inactive-login-denied.png`, `17-login-after-reactivation.png`.

---

## 9. Practical 12 integrated into `studenthub/` – event management and registration (31 October 2026)
Write tests ran against disposable databases and a temporary poster folder (`STUDENTHUB_UPLOAD_DIR`); `studenthub/uploads/` and the live database were not used. The live database then received migration 003 after a verified backup; its users, password hashes, students, registrations, menu and every original event value were verified unchanged.

| Suite | Result | Output |
|---|---|---|
| `tests/test_events.py` – HTTP tests of the Campus Events tab, poster uploads and the Campus Events page | **94 / 94 passed** | `tests/test_events_output.txt` |
| `tests/browser_events.py` – Microsoft Edge + screenshots | **16 / 16 passed** | `tests/browser_events_output.txt`, `evidence/practical-12-integration/` |
| `database/tests/test_003_event_management.py` – migration 003 (fixture / real dump) / `--verify-live` | **27 / 27**, **26 / 26**, **5 / 5 passed** | `database/tests/test_003_output.txt`, `test_003_verify_live_output.txt` |
| Regression: `test_001` (88 / 88; 24 / 24 live), `test_002` (22 / 22; 4 / 4 live), `test_auth` (132 / 132), `test_students` (170 / 170), Edge `browser_auth` (14 / 14), `browser_students` (16 / 16), `browser_inactive_login` (13 / 13) | all passed | outputs in `tests/` and `database/tests/` |

Covered by `test_events.py`: listing, columns and the placeholder for an older poster reference whose file is missing (`poster.php` answers 404, the value is kept); adding with and without a poster; JPEG, PNG and WebP posters stored under a random 32-hex name with identical bytes, original name never used, upper-case extension accepted; `poster.php` sends the image with `nosniff` and a sandbox CSP and only to signed-in users; validation (empty/short title, unknown category, impossible or wrongly formatted date, invalid time, empty location, capacity 0/−5/70000/text, unknown status, description over 2000 characters, SQL in the category, HTML escaped on redisplay); rejected posters: GIF, SVG with script, PHP script, PHP renamed to `.jpg`, `shell.php.jpg`, PNG content named `.jpg`, truncated PNG, JPEG with embedded PHP, a 2.3 MB file, an empty file, a text file with a forged `image/png` type – nothing stored, `UPLOAD_REJECTED` logged; editing (poster kept, replaced with the old file deleted, invalid replacement refused); student registration (success, duplicate refused, capacity 2 → third student refused, closed event, past event, cancel keeps the row and frees the seat, cancel twice, re-register, CSRF, GET, unlinked account, admin), 6 simultaneous registrations for 3 seats → exactly 3; capacity cannot drop below seats taken; registrations view; delete refused for an event with registrations, confirmed delete removes the event and its poster; search and category/status/upcoming/past filters and SQL-injection strings; students and editors refused (403) for the tab and every POST action; no PHP warnings; live database and `studenthub/uploads` unchanged.

Note: Windows security software blocks reading an uploaded file that contains a well-known web-shell signature; the portal then rejects it with "could not be read as an image" instead of the content-type message – it is rejected either way.

Not covered / limitations: registrations cannot be marked `attended` from the interface; there is no waiting list; the Campus Events page shows all upcoming events on one page.

---

## 10. Practical 13 integrated into `studenthub/` – Fetch API and JSON API (31 October 2026)
No schema change. Tests ran against disposable databases; a second test server pointed at a database that does not exist.

| Suite | Result | Output |
|---|---|---|
| `tests/test_api.py` – HTTP tests of `api/events.php` and `events_live.php` | **72 / 72 passed** | `tests/test_api_output.txt` |
| `tests/browser_api.py` – Microsoft Edge + screenshots | **16 / 16 passed** | `tests/browser_api_output.txt`, `evidence/practical-13-integration/` |
| Regression: `test_events` 94 / 94, `test_students` 170 / 170, `test_auth` 132 / 132, `test_001` 88 / 88; Edge `browser_events` 16 / 16, `browser_students` 16 / 16, `browser_inactive_login` 13 / 13, `browser_auth` 14 / 14 | all passed | outputs in `tests/` and `database/tests/` |

Covered by `test_api.py`: 401 JSON (never a redirect) without a session and for a student whose record was deactivated; list response shape and exact event fields (posters only as `poster.php?event=` URLs); role flags; search/category/status/upcoming/past filters and combinations; `%`, `_` and SQL-injection strings as text; HTML in titles escaped in the JSON (`\u003C`); get / 404 for unknown and malformed ids; 405 with `Allow` for the wrong method; 400 for an unknown action, malformed JSON, a JSON array and a body over 20 kB; 403 for a missing, wrong or modified `X-CSRF-Token` (audit-logged); 415 for a form-encoded POST; create 201, eight invalid bodies → 422 with `errors` per field, update 200 / 404 / 422, delete 200 / 404 and 409 for an event with registrations; register 201, duplicate / full / closed / past → 409, unknown event → 404, cancel 200 / 409, missing token 403, unlinked account and admin 403; 6 simultaneous API registrations for 3 seats → three 201 and three 409; capacity below seats taken → 422; students and editors 403 for create/update/delete (ACCESS_DENIED logged); the page per role; database unavailable → HTTP 503 JSON with a general message only; no PHP warnings or API errors in the log.

The Edge test delays the API answers in its own network layer to make the loading state visible for screenshot 01; the answers themselves are the real ones. It also counts page navigations: create, update and delete happened without a page reload. A bug found by the browser test was fixed: the page's `display: flex` rules overrode the `hidden` attribute, so the loading indicator stayed visible after loading.

Limitations: posters are uploaded only in the Admin Console (the API handles JSON, not files); the Event Finder lists at most 100 events per request.

---

## 11. Practical 14 integrated into `studenthub/` – admin dashboard, role-based navigation, account status (31 October 2026)
Write tests ran against disposable databases. The live database then received migration 004 after a fresh verified backup; its accounts (incl. password hashes), students, events, registrations and categories were verified unchanged, every account is active and the menu equals the migrated baseline.

| Suite | Result | Output |
|---|---|---|
| `tests/test_dashboard.py` – HTTP tests of the overview, navigation, 403 page, account status and audit filters | **36 / 36 passed** | `tests/test_dashboard_output.txt` |
| `tests/browser_dashboard.py` – Microsoft Edge + screenshots | **15 / 15 passed** | `tests/browser_dashboard_output.txt`, `evidence/practical-14-integration/` |
| `database/tests/test_004_admin_dashboard.py` – migration 004 (fixture / real dump) / `--verify-live` | **18 / 18**, **18 / 18**, **5 / 5 passed** | `database/tests/test_004_output.txt`, `test_004_verify_live_output.txt` |
| Live checks of the earlier migrations after 004: `test_001` 24 / 24, `test_002` 4 / 4, `test_003` 5 / 5 (they now compare the live database with the baseline upgraded by the same migrations, because 004 corrects menu data on purpose) | all passed | `database/tests/*_verify_live_output.txt` |
| Regression: `test_api` 72 / 72, `test_events` 94 / 94, `test_students` 170 / 170, `test_auth` 132 / 132, `test_001` 88 / 88, `test_002` 22 / 22, `test_003` 27 / 27; Edge `browser_api` 16 / 16, `browser_events` 16 / 16, `browser_students` 16 / 16, `browser_inactive_login` 13 / 13, `browser_auth` 14 / 14 | all passed | outputs in `tests/` and `database/tests/` |

Covered by `test_dashboard.py`: the five counters and their breakdowns equal the database; latest event registrations (student + event, newest first); newest accounts; recent activity; sidebar navigation per role (student and editor: no admin links; admin: Admin Console shortcuts from `menu_items`; never `faculty.php` or `../` links); HTML in a menu title or icon is escaped; the console's navigation box lists only existing pages; every console tab gives students and editors the same HTTP 403 page and an `ACCESS_DENIED` entry, and their POST actions are refused; disable/enable with CSRF (GET and token-less requests change nothing), `USER_DISABLED`/`USER_ENABLED` entries, the disabled editor's open session ends (`SESSION_REVOKED: the account is disabled`), sign-in refused with the generic message (`LOGIN_DENIED`), a wrong password still gets the normal message, the own account cannot be disabled, a disabled student account is refused too, re-enabled accounts sign in again; unknown account ids; deleting another account is audit-logged with its name; audit filters by action, status, user and combined, unknown values ignored, SQL in the user filter treated as text; no PHP warnings; live database untouched.

The sidebar printed its link values without escaping; this was harmless while they were fixed in the code, but they now come from `menu_items`, so they are escaped.

Limitations: there is no form to edit `menu_items` (rows are changed in the database or by migrations); the "last active administrator" protection is a defence in depth – it cannot be reached through the interface because an administrator cannot disable or delete their own account.

---

## 12. Practicals 5–7 checked and integrated into `studenthub/` (31 October 2026)
Audit of Practicals 1–7 against the integrated portal:

| Practical | Requirement (from its README / report) | Found in the portal before | Action |
|---|---|---|---|
| 1 | Planning: roles, sitemap, wireframes | documents only (`Practical-1/`) | none – planning documents, nothing to integrate |
| 2 | Semantic HTML pages | all portal pages use semantic HTML5 (header/nav/main/section/footer) | none |
| 3 | Grid / Flexbox / responsive layout | `assets/css/global.css` grid shell, responsive breakpoints, mobile drawer | none |
| 4 | DOM: FAQ, modal, slider, banner, hamburger, theme | home page `index.php` + `assets/js/script.js`, `theme.js` | none |
| 5 | Registration form with JavaScript regex validation, error messages, password strength checker, real-time validation, Canvas CAPTCHA | server-side validation only (no client-side checks) | **integrated**: real-time regex validation, messages, strength meter and submit blocking on `register.php`; the CAPTCHA was **not** integrated (a client-side canvas CAPTCHA gives no real protection on a live form; the standalone `Practical-5/` keeps it) |
| 6 | JSON files rendered with Fetch: search, filter, sort, pagination, loading/error states | `assets/js/data.js` and `data/*.json` existed but **no page used them** | **integrated**: Campus Data Explorer `data_explorer.php`; `data.js` now escapes every value and the artificial 800 ms delay was removed |
| 7 | Inquiry form: POST, server validation and sanitising, stored with locking, success/error messages | form existed but inquiries were **not stored** (only an audit line when signed in) | **integrated**: validated inquiries stored in the `inquiries` table (migration 005), reference number, honeypot, Admin Console Inquiries tab |

| Suite | Result | Output |
|---|---|---|
| `tests/test_forms.py` – HTTP tests of Practicals 5, 6 and 7 in the portal | **41 / 41 passed** | `tests/test_forms_output.txt` |
| `tests/browser_forms.py` – Microsoft Edge + screenshots | **15 / 15 passed** | `tests/browser_forms_output.txt`, `evidence/practical-05-07-integration/` |
| `database/tests/test_005_inquiries.py` – migration 005 (fixture / real dump) / `--verify-live` | **14 / 14**, **14 / 14**, **4 / 4 passed** | `database/tests/test_005_output.txt`, `test_005_verify_live_output.txt` |
| Live checks of migrations 001–004 after 005 | 24 / 24, 4 / 4, 5 / 5, 5 / 5 | `database/tests/*_verify_live_output.txt` |
| Regression: `test_dashboard` 36 / 36, `test_api` 72 / 72, `test_events` 94 / 94, `test_students` 170 / 170, `test_auth` 132 / 132, `test_001` 88 / 88, `test_002` 22 / 22, `test_003` 27 / 27, `test_004` 18 / 18; Edge `browser_auth` 14 / 14 (its weak-password check now expects the browser to stop the form – the server refusal is tested over HTTP), `browser_students` 16 / 16, `browser_inactive_login` 13 / 13, `browser_events` 16 / 16, `browser_api` 16 / 16, `browser_dashboard` 15 / 15 | all passed | outputs in `tests/` and `database/tests/` |

Covered: the registration page loads the validation script with rules matching the server; a request that bypasses the browser is still refused by the server; the Data Explorer page, its sidebar link, the three JSON files and the escaping in `data.js`; the inquiry form (public, CSRF, topics, honeypot), a stored visitor inquiry with normalised e-mail/enrollment, the reference number shown once, an audit entry without the message text, nine invalid cases (incl. array parameters and the honeypot) with escaped redisplay, CSRF refusal, prefilled fields and account link for a signed-in student, 8 simultaneous inquiries all stored with distinct ids, the Inquiries tab (newest first, new-count badge, escaped messages, CSRF forms, resolve with audit entry, resolve twice, filter), students and editors refused (403). In Edge: live messages and the strength meter while typing, submit blocked with focus on the first field, the meter reaching "Strong"; the Data Explorer loading state (JSON response delayed by the test's network layer), 5 rows per page, search + filter, events sorted Z–A; server validation of the contact form, success with the reference number, the admin list and resolving.

---

## 13. Practical 15 – final integration, snapshot and complete test run (31 October 2026)
`Practical-15/` was refreshed from the canonical `studenthub/` with `tools/sync_practical15.py`: 56 application files copied byte for byte, the stale files of the old independent copy (e.g. its own `schema.sql`) removed – the old copy stays in the Git history – and `Practical-15/SNAPSHOT.md` lists the SHA-256 of every file. `tests/test_snapshot.py` verifies the copy and runs the authentication suite (132 / 132) and the events API suite (72 / 72) against `Practical-15/` itself.

**Complete run** – `python tests/run_all.py --browser <python with Playwright>` (output: `tests/run_all_output.txt`), every suite on its own disposable database:

| Suite | Passed | Failed |
|---|---|---|
| Practical 8 – migration 001 and portal | 88 | 0 |
| Migrations 002 / 003 / 004 / 005 | 22 / 27 / 18 / 14 | 0 |
| Practicals 9/10 – registration, login, sessions, RBAC | 132 | 0 |
| Practical 11 – student management | 170 | 0 |
| Practical 12 – events, posters, registration | 94 | 0 |
| Practical 13 – JSON API, Event Finder | 72 | 0 |
| Practical 14 – admin dashboard | 36 | 0 |
| Practicals 5–7 – validation, Data Explorer, inquiries | 41 | 0 |
| Practical 15 – snapshot (incl. 132 + 72 checks against the snapshot) | 5 | 0 |
| Microsoft Edge: auth 14, students 16, inactive login 13, events 16, Event Finder 16, dashboard 15, Practicals 5–7 15, end-to-end 17 | 122 | 0 |
| **Total** | **841** | **0** |

After the report review the Data Explorer was switched to Practical 6's own anonymised sample datasets (`DEMO-001` … `DEMO-015`, each file with a `sampleData` flag and a description, now shown above the table) instead of the portal's earlier JSON files, and the loading-state screenshot was retaken: the earlier one had been saved after the data had loaded. The test now holds the JSON request until the screenshot is taken. The complete run above is the run after these changes.

The first complete run showed one failure in the Event Finder browser test: the check for "Event full" ran before the list refresh that follows the API's 409 answer had finished (a timing race in the test; it had passed in every earlier run). The test now waits for the refreshed card; the second complete run above passed completely. `run_all.py` was also corrected to read each suite's own last summary line.

**End-to-end scenario** (`tests/browser_e2e.py`, Edge, 17 / 17, screenshots `evidence/practical-15-integration/`): student registration; logout and login by e-mail; profile; editor and student refused by the Admin Console (403); admin adds a student (automatic enrollment number) and edits it; deactivation ends the open session and refuses the sign-in, reactivation restores it; a PHP file disguised as `.jpg` is refused and a real JPEG poster is stored under a random name; event edited; registration, duplicate refused ("already registered"), capacity reached for a second student ("The event is full."); cancellation keeps the row; Event Finder debounced search and registration through the JSON API without a reload; student search + status filter; dashboard counters equal the database; audit log shows ACCESS_DENIED, LOGIN_DENIED, SESSION_REVOKED and UPLOAD_REJECTED; a forged form without the CSRF token is refused and the API answers 401 to a visitor.

**Database evidence for Practical 8** (`tests/browser_database_evidence.py`, 6 / 6): phpMyAdmin screenshots of a disposable copy built from `database/studenthub_demo.sql` with fictional registrations (tables, `registrations` structure and foreign keys, `students` structure, the designer view, a three-table JOIN) in `evidence/practical-08-integration/`; Practicals 9/10 screenshots from `tests/browser_auth.py` in `evidence/practical-09-10-integration/`.

**Live database:** migrations 001–005 applied, each after a verified backup; the read-only live checks pass (001 24 / 24, 002 4 / 4, 003 5 / 5, 004 5 / 5, 005 4 / 4).

Remaining limitations (whole project): no limit on repeated sign-in attempts; no e-mail (password reset, inquiry answers); posters are uploaded only in the Admin Console (the JSON API handles no files); `menu_items` has no editing form; the Admin Console loads Bootstrap from a CDN; the portal has no favicon (one 404 per browser session); the canvas CAPTCHA of Practical 5 was not carried into the portal; academic figures on the student pages are sample data; the standalone `Practical-1/` … `Practical-14/` folders are historical and not updated.
