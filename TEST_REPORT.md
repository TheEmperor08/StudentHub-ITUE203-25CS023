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
