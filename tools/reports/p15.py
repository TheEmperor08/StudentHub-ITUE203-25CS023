"""New report – Practical 15: the final integrated StudentHub portal (studenthub/ and its verified snapshot Practical-15/).

No Word/PDF report existed for Practical 15, so this module writes its own notice box instead of corrected_notice().
Every number below is copied from tests/run_all_output.txt, tests/browser_e2e_output.txt, tests/test_snapshot_output.txt,
TEST_REPORT.md section 13, Practical-15/SNAPSHOT.md or the documentation files named in the text.
"""
from report_lib import corrected_notice  # noqa: F401  (not called: there is no original report to replace)
from report_lib import test_run

META = {
    "number": 15,
    "title": "StudentHub – Final Integrated Campus Portal",
    "tech": "PHP 8 · MariaDB · HTML5 / CSS3 / JavaScript · Fetch API · sessions, RBAC and CSRF · Python + Playwright tests",
    "supersedes": None,
    "replaces_note": "new report – no earlier Word/PDF report existed",
}


def build(r):
    SUITES, PASSED, FAILED = test_run()          # the saved complete run tests/run_all_output.txt
    RUN = {name: ok for name, ok, _, _ in SUITES}
    r.note("**New report.** No Word or PDF report existed for Practical 15. Practical 15 is the final integrated portal: "
           "Practicals 5–14 were integrated step by step into the one canonical application `studenthub/` (one application, "
           "one database `studenthub_db`, one login), and `Practical-15/` is now a verified byte-for-byte snapshot of it "
           "(`Practical-15/README.md`, `Practical-15/SNAPSHOT.md`, `tools/sync_practical15.py`). This report covers the "
           "architecture, the database (migrations 001–005), where each practical lives in the portal, installation, "
           "configuration and deployment, the snapshot process, the complete test run and the end-to-end scenario. All "
           "screenshots were taken from the canonical application `studenthub/` with Microsoft Edge (headless, Playwright) on "
           "disposable test databases with fictional records; all test results are copied from the saved test outputs of the "
           "repository. The commit that records the snapshot is not named here – see the repository history.")

    # ------------------------------------------------------------------ 1
    r.heading("1. Problem Definition and Objectives")
    r.para("Topic (root `README.md`, practical status table): *Integrated portal (copy of studenthub/)*; title of "
           "`Practical-15/README.md`: *StudentHub – Final Integrated Campus Portal*.")
    r.para("Practicals 1–14 were first built as standalone applications in `Practical-N/` folders, several of them with their own "
           "database. Practicals 5–14 were then integrated one by one into the portal `studenthub/`. Until this step, "
           "`Practical-15/` was an older, independently kept copy of the portal with its own `schema.sql` (TEST_REPORT §6 noted "
           "that it was “still the older copy of the portal”). Practical 15 closes the project:")
    r.bullets([
        "One application (`studenthub/`), one database (`studenthub_db`) and one login for every feature of Practicals 5–14.",
        "`Practical-15/` becomes an exact, verified snapshot of `studenthub/` instead of a separately maintained copy.",
        "Installation, configuration, account creation and deployment are documented (`README.md`, `DEPLOYMENT.md`).",
        "Every test suite runs on disposable databases in one complete run, and one continuous Microsoft Edge scenario walks "
        "through the critical workflows with screenshots.",
        "The remaining limitations are stated openly.",
    ])

    # ------------------------------------------------------------------ 2
    r.heading("2. Tools and Technologies")
    r.table([
        ["Tool / technology", "Use in the final portal"],
        ["PHP 8.2.12 (XAMPP) with `mysqli`, `fileinfo`, `mbstring`", "All pages, the JSON API and the business rules "
                                                                    "(README requirement: PHP 8.1+)"],
        ["MariaDB 10.4.32", "The database `studenthub_db` (README: MariaDB 10.4+ or MySQL 8)"],
        ["HTML5, CSS3, JavaScript", "Semantic pages, the design system `assets/css/global.css`, Fetch API front ends "
                                    "(`events-live.js`, `data.js`), real-time validation (`register-validation.js`)"],
        ["Bootstrap 5.3.2, Bootstrap Icons 1.11.1 (CDN)", "Layout of the Admin Console"],
        ["Python 3, Playwright, Microsoft Edge (headless)", "`tests/run_all.py`, the HTTP suites and the Edge suites"],
        ["phpMyAdmin", "Database screenshots of Practical 8 (`tests/browser_database_evidence.py`)"],
        ["Git / GitHub", "Version history; `tools/sync_practical15.py` copies the files tracked by Git"],
        ["Windows 11, PHP built-in server", "Test environment of 31 October 2026"],
    ], [5.8, 10.2])

    # ------------------------------------------------------------------ 3
    r.heading("3. Integrated Architecture")
    r.para("Every page of the portal lives in `studenthub/` and loads the same two foundations: `db.php` opens one MySQLi "
           "connection to the database named by the environment (default `studenthub_db`; there is **no** fallback database – if "
           "it is unreachable the portal answers HTTP 503 with a general message and logs the reason on the server), and "
           "`includes/auth.php` provides the one session, permission and CSRF system:")
    r.excerpt("studenthub/includes/auth.php", "the one authentication and authorisation system", "// Roles stay exactly admin",
              "the single authentication and authorisation layer")
    r.table([
        ["Layer", "Files", "Responsibility"],
        ["Pages and front end", "`*.php` pages, `sidebar.php`, `assets/css/`, `assets/js/`",
         "HTML5 pages, forms, the grouped sidebar, Fetch API front ends"],
        ["Access control", "`includes/auth.php`, `403.php`",
         "Session cookie `STUDENTHUBSESSID`, 30-minute inactivity timeout, roles admin / editor / student with explicit "
         "permissions, CSRF tokens, security headers, the shared HTTP 403 page"],
        ["Business rules", "`includes/registration.php`, `student_management.php`, `event_management.php`, "
                           "`event_registration.php`, `dashboard.php`, `navigation.php`, `inquiries.php`; `api/events.php`",
         "Validation, transactions, capacity rule, soft delete, statistics – used by the pages and by the JSON API alike"],
        ["Data and audit", "`db.php`, `audit_logger.php` → `studenthub_db`",
         "One connection; one audit log for security and data events"],
        ["Files", "`poster.php`, `uploads/`", "Event posters, stored under random names and delivered only to signed-in users"],
    ], [3.0, 6.2, 6.8])

    r.heading("3.1 Folder and file map", 2)
    r.table([
        ["Path", "Content"],
        ["`studenthub/`", "The canonical application (56 files tracked by Git)"],
        ["`Practical-15/`", "Verified snapshot of `studenthub/` plus its own `README.md` and `SNAPSHOT.md`"],
        ["`Practical-1/` … `Practical-14/`", "The original standalone versions, kept as historical evidence"],
        ["`database/`", "`studenthub_demo.sql` (new installation), `migrations/001`–`005` with rollbacks, migration tests"],
        ["`tests/`", "HTTP and Microsoft Edge suites, `run_all.py`, saved outputs"],
        ["`tools/`", "`create_demo_user.php` (accounts), `sync_practical15.py` (snapshot)"],
        ["`evidence/`", "Genuine screenshots of every integration step"],
        ["`README.md`, `TEST_REPORT.md`, `DEPLOYMENT.md`, `index.php`", "Documentation; the root `index.php` redirects to the portal"],
    ], [5.4, 10.6])
    r.para("The 56 application files (the list with SHA-256 hashes is `Practical-15/SNAPSHOT.md`):")
    r.table([
        ["Group", "Files"],
        ["Public and account pages", "`index.php` (home portal), `login.php`, `register.php`, `logout.php`, `contact.php`, `403.php`"],
        ["Student pages", "`dashboard.php` (`student_dashboard.php` has identical content), `profile.php`, `courses.php`, "
                          "`attendance.php`, `assignments.php`, `results.php`, `achievements.php`, `notifications.php` (Campus "
                          "Events), `events_live.php` (Event Finder), `data_explorer.php`, `directory.php`"],
        ["Administration", "`admin_dashboard.php`; `students.php`, `events.php`, `users.php`, `audit_logs.php` redirect to its tabs"],
        ["API and files", "`api/events.php`, `poster.php`, `uploads/.htaccess`, `uploads/.gitkeep`"],
        ["Shared PHP", "`db.php`, `audit_logger.php`, `sidebar.php`, `student_profile.php`, `includes/auth.php`, `registration.php`, "
                       "`student_management.php`, `event_management.php`, `event_registration.php`, `navigation.php`, "
                       "`dashboard.php`, `inquiries.php`"],
        ["Front end", "`assets/css/` (`tokens`, `global`, `home`, `auth`, `bootstrap-theme`), `assets/js/` (`nav`, `theme`, "
                      "`script`, `auth`, `register-validation`, `data`, `events-live`), `data/` (`students`, `events`, `faqs` JSON)"],
        ["Older pages", "`insert.php` (answers HTTP 410 “Feature unavailable”), `test_connection.php` (Practical 8 array demo)"],
    ], [3.6, 12.4])

    # ------------------------------------------------------------------ 4
    r.heading("4. Database")
    r.para("All modules share `studenthub_db` (InnoDB, `utf8mb4_unicode_ci`, signed `INT(11)` keys). A new installation imports "
           "`database/studenthub_demo.sql`, which already contains migrations 001–005, fictional demo rows and no accounts or "
           "password hashes. An existing database is backed up with `mysqldump` and receives the missing migrations in order; "
           "`schema_migrations` records which ones are applied. Every migration checks its preconditions first, is idempotent "
           "and has a `.down.sql` rollback (`database/README.md`).")
    r.table([
        ["Migration", "Practical", "Changes", "Tests (complete run; live)"],
        ["001", "8", "`students.user_id` (UNIQUE, FK `ON DELETE SET NULL`), semester check, `events.event_time` / `capacity` "
                     "(+ check), table `registrations` (CASCADE FKs, UNIQUE student + event, status), `fk_audit_logs_user`",
         "88; live 24 / 24"],
        ["002", "11", "UNIQUE `students.enrollment_no`", "22; live 4 / 4"],
        ["003", "12", "`event_categories` + `fk_events_category`, `events.status`, `events.updated_at`, UNIQUE `events.poster`",
         "27; live 5 / 5"],
        ["004", "14", "`menu_items.min_role` student / editor / admin + integrated links, `users.status`, `chk_users_role`",
         "18; live 5 / 5"],
        ["005", "7", "Table `inquiries` (FK to `users` `ON DELETE SET NULL`, topic ENUM, message CHECK 10–2000 characters, "
                     "status new / resolved)", "14; live 4 / 4"],
    ], [1.8, 1.7, 9.0, 3.5])
    r.table([
        ["Relationship", "Rule"],
        ["`users` 1 : 0..1 `students` (`students.user_id` UNIQUE)", "`ON DELETE SET NULL` – the record stays, only the link goes"],
        ["`students` 1 : n `registrations`", "`ON DELETE CASCADE` (the portal never deletes students – soft delete only)"],
        ["`events` 1 : n `registrations`, UNIQUE (`student_id`, `event_id`)",
         "`ON DELETE CASCADE` (the portal refuses to delete an event with registrations)"],
        ["`event_categories` 1 : n `events`", "`ON UPDATE CASCADE`, `ON DELETE RESTRICT`"],
        ["`users` 1 : n `audit_logs`; `users` 1 : n `inquiries`", "`ON DELETE SET NULL` – entries and inquiries are kept"],
        ["`menu_items`, `schema_migrations`", "No relationships"],
    ], [7.6, 8.4])
    r.para("The capacity rule is enforced in PHP by `register_student_for_event()` (`includes/event_registration.php`): in one "
           "transaction it locks the event row with `SELECT … FOR UPDATE`, counts the registrations that are not cancelled and "
           "inserts (or reactivates) a registration only if a seat is free. Six simultaneous requests for three seats give "
           "exactly three registrations (README); the JSON API uses the same function.")
    r.figure("evidence/practical-08-integration/01-database-tables.png",
             "phpMyAdmin: the portal tables of a disposable copy built from studenthub_demo.sql (zz_report_demo_marker is the "
             "test's marker table)", width=9.6)

    # ------------------------------------------------------------------ 5
    r.heading("5. How Each Practical Lives in the Portal")
    r.table([
        ["P", "Feature in the portal", "Files / route", "Verified by (checks)", "Commit"],
        ["1", "Planning: roles, sitemap, structure", "documents in `Practical-1/` (nothing to integrate)", "audit (TEST_REPORT §12)", "–"],
        ["2", "Semantic HTML5 pages", "all portal pages (header / nav / main / section / footer)", "audit (TEST_REPORT §12)", "–"],
        ["3", "Grid / Flexbox / responsive layout", "`assets/css/global.css`, mobile drawer", "audit (TEST_REPORT §12)", "–"],
        ["4", "DOM: FAQ, modal, slider, banner, hamburger, theme", "`index.php`, `assets/js/script.js`, `theme.js`",
         "audit (TEST_REPORT §12)", "–"],
        ["5", "Real-time regex validation, strength meter", "`register.php`, `assets/js/register-validation.js`",
         f"`test_forms` {RUN['Practicals 5–7 – validation, Data Explorer, inquiries']} (P5–7), Edge {RUN['Edge – Practicals 5–7']}", "`938e74f`"],
        ["6", "Campus Data Explorer (Fetch, search, filter, sort, pages)", "`data_explorer.php`, `assets/js/data.js`, `data/*.json`",
         "as P5", "`938e74f`"],
        ["7", "Stored Help & Contact inquiries", "`contact.php`, `includes/inquiries.php`, `?tab=inquiries`, migration 005",
         "as P5; migration 005: 14", "`938e74f`"],
        ["8", "Database foundation, capacity rule in a transaction", "migration 001, `includes/event_registration.php`",
         "`test_001` 88", "`37b35e6`"],
        ["9", "Secure self-registration (account + record in one transaction)", "`register.php`, `includes/registration.php`",
         "`test_auth` 132, Edge 14", "`8011d39`"],
        ["10", "Login, sessions, timeout, POST logout, CSRF, roles", "`login.php`, `logout.php`, `includes/auth.php`",
         "as P9", "`8011d39`"],
        ["11", "Student management, soft delete, CSV; inactive students cannot sign in",
         "`?tab=students`, `includes/student_management.php`, migration 002",
         "`test_students` 170, migration 002: 22, Edge 16 + 13", "`0ac2f5d`, fix `6420efc`"],
        ["12", "Events with secure poster upload, registration, capacity, cancellation",
         "`?tab=events`, `includes/event_management.php`, `poster.php`, `notifications.php`, migration 003",
         "`test_events` 94, migration 003: 27, Edge 16", "`ba11795`"],
        ["13", "Event Finder (Fetch API) + JSON API", "`events_live.php`, `assets/js/events-live.js`, `api/events.php`",
         "`test_api` 72, Edge 16", "`a9d4e22`"],
        ["14", "Admin dashboard, role-based navigation, account status, audit filters",
         "`admin_dashboard.php`, `includes/dashboard.php`, `navigation.php`, `sidebar.php`, migration 004",
         "`test_dashboard` 36, migration 004: 18, Edge 15", "`05927b3`"],
        ["15", "Final snapshot and end-to-end test", "`Practical-15/`, `tools/sync_practical15.py`, `tests/browser_e2e.py`",
         "snapshot 5, Edge end-to-end 17", "see the repository history"],
    ], [0.8, 4.4, 4.9, 3.9, 2.0], size=8.5)
    r.para("The Admin Console routes are `admin_dashboard.php?tab=…`. Not carried into the portal: the canvas CAPTCHA of "
           "Practical 5 (a client-side CAPTCHA gives no real protection on a live form; the standalone `Practical-5/` keeps it). "
           "Practicals 11–14 are shown in the end-to-end scenario (Section 9); three practicals that the scenario does not "
           "touch are shown here:")
    r.figure("evidence/practical-05-07-integration/01-register-live-validation.png",
             "Practical 5 in the portal: messages and the strength meter appear while typing on register.php", width=7.6)
    r.figure("evidence/practical-05-07-integration/05-data-explorer-students.png",
             "Practical 6 in the portal: the Campus Data Explorer renders data/students.json with search, filter, sort and pages",
             width=8.2)
    r.figure("evidence/practical-05-07-integration/10-admin-inquiries.png",
             "Practical 7 in the portal: stored inquiries in the Admin Console (Inquiries tab, new-count badge)", width=8.2)

    # ------------------------------------------------------------------ 6
    r.heading("6. Installation, Configuration, Accounts and Deployment")
    r.heading("6.1 Local setup (Windows + XAMPP)", 2)
    r.numbered([
        "Requirements: XAMPP with PHP 8.1+ (tested 8.2.12) and MariaDB 10.4+ / MySQL 8 (tested 10.4.32); Python 3 only for "
        "the tests, Playwright + Microsoft Edge only for the browser tests. Start MySQL in the XAMPP Control Panel.",
        "Create the database: `mysql -u root -e \"CREATE DATABASE IF NOT EXISTS studenthub_db CHARACTER SET utf8mb4 COLLATE "
        "utf8mb4_unicode_ci\"`, then `mysql -u root studenthub_db < database\\studenthub_demo.sql`. An existing database: back "
        "it up and apply only the missing migrations (`SELECT * FROM schema_migrations` shows what is applied).",
        "Create the first administrator: `php tools\\create_demo_user.php --db=studenthub_db --username=admin01 "
        "--email=admin01@example.com --role=admin` – the password is prompted and stored only as a bcrypt hash.",
        "Run `php -S localhost:8000 -t studenthub` and open `http://localhost:8000/` (or serve the repository root; its "
        "`index.php` redirects to `studenthub/`). The snapshot runs the same way: `php -S localhost:8015 -t Practical-15`.",
    ])
    r.heading("6.2 Configuration and accounts", 2)
    r.table([
        ["Environment variable", "Default", "Meaning"],
        ["`DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME`", "`localhost`, `root`, (empty), `studenthub_db`",
         "Database connection – there is no fallback database"],
        ["`STUDENTHUB_SESSION_TIMEOUT`", "`1800`", "Inactivity timeout in seconds"],
        ["`STUDENTHUB_TIMEZONE`", "`Asia/Kolkata`", "Time zone for dates (should match the database server)"],
        ["`STUDENTHUB_UPLOAD_DIR`", "`studenthub/uploads`", "Folder for event posters (must not be reachable over HTTP)"],
    ], [5.2, 4.8, 6.0])
    r.para("No account and no password is stored in the repository. Administrators and editors are created with "
           "`tools/create_demo_user.php` (`--role=admin`, `--role=editor`, `--role=student`). Students normally register "
           "themselves at `register.php`, which creates the account (role always `student`) and its linked student record with "
           "the next enrollment number in one transaction. Administrators can disable, enable and delete accounts in the Admin "
           "Console; the own account and the last active administrator are protected.")
    r.heading("6.3 Deployment on Apache (DEPLOYMENT.md)", 2)
    r.bullets([
        "PHP 8.1+ with `mysqli`, `fileinfo`, `mbstring`; `AllowOverride All` so that `studenthub/uploads/.htaccess` denies HTTP "
        "access to the poster folder and switches PHP off there; HTTPS (the session cookie becomes `Secure` automatically).",
        "`studenthub/` is the document root; `database/`, `tests/`, `tools/`, `Practical-*` and `evidence/` must not be served. "
        "The web server user may write only to the poster folder (ideally outside the document root via "
        "`STUDENTHUB_UPLOAD_DIR`). `display_errors = Off`, `log_errors = On`.",
        "A dedicated database user with only `SELECT, INSERT, UPDATE, DELETE` on `studenthub_db`; schema and migrations are run "
        "with an administrative account; connection settings as `SetEnv` variables, never in a file inside the document root.",
        "Operation: regular `mysqldump --single-transaction` backups outside the web root (they contain password hashes), review "
        "of the audit log and the PHP error log, and before an update: back up, apply new migrations, run "
        "`python tests/run_all.py` against a copy, then deploy.",
    ])
    r.para("These steps were written for the project but were **not** carried out on a real public server; the application was "
           "tested with PHP's built-in server.")

    # ------------------------------------------------------------------ 7
    r.heading("7. The Practical 15 Snapshot")
    r.para("`Practical-15/` is not maintained by hand. `python tools/sync_practical15.py` copies every file tracked by Git in "
           "`studenthub/` (`git ls-files`) byte for byte, removes application files that no longer exist in `studenthub/` – the "
           "stale files of the old copy, such as its own `schema.sql`, were removed this way and remain in the Git history – and "
           "writes `Practical-15/SNAPSHOT.md` with the SHA-256 hash of every file and the base commit. Uploaded posters are never "
           "copied; `README.md` and `SNAPSHOT.md` are the only files of the folder that are not application files. "
           "`python tools/sync_practical15.py --check` only verifies and exits with code 1 if anything differs:")
    r.excerpt("tools/sync_practical15.py", "def differences(files):", "    return problems",
              "byte comparison and detection of extra files")
    r.para("The manifest lists 56 files and records as base commit `938e74f` (the Practicals 5–7 integration); the copied files "
           "may include changes committed together with the manifest. `tests/test_snapshot.py` checks the snapshot in five steps:")
    r.table([
        ["#", "Check in `tests/test_snapshot_output.txt`", "Result"],
        ["1", "`tools/sync_practical15.py --check`: `Practical-15/` is byte-for-byte identical to `studenthub/` and "
              "`SNAPSHOT.md` matches", "PASS"],
        ["2", "`SNAPSHOT.md` lists all 56 tracked application files", "PASS"],
        ["3", "The snapshot folder has no separate database or configuration of its own (no `schema.sql`, no config files)", "PASS"],
        ["4", "`tests/test_auth.py` against `Practical-15/`: 132 passed, 0 failed", "PASS"],
        ["5", "`tests/test_api.py` against `Practical-15/`: 72 passed, 0 failed", "PASS"],
    ], [0.8, 13.0, 2.2])

    # ------------------------------------------------------------------ 8
    r.heading("8. Security Summary")
    r.table([
        ["Area", "Control in the portal", "Verified by"],
        ["Passwords", "`password_hash()` (bcrypt); policy 8–72 characters with upper- and lower-case letter, digit and special "
                      "character; no passwords or hashes in the repository", "`test_auth`"],
        ["Sign-in", "One generic message; unknown accounts are checked against a dummy hash; session ID regenerated at login",
         "`test_auth`, Edge"],
        ["Sessions", "Cookie `STUDENTHUBSESSID` (HttpOnly, SameSite=Strict, Secure on HTTPS, strict mode); 30-minute timeout; "
                     "account re-read on every request; logout only by POST", "`test_auth`"],
        ["Access control", "Explicit permissions per role; HTTP 403 page + `ACCESS_DENIED`; the API answers 401 / 403 in JSON",
         "`test_dashboard`, `test_api`, end-to-end 4 and 17"],
        ["Blocked accounts", "Disabled accounts and student accounts with an inactive record cannot sign in; open sessions end "
                             "(`SESSION_REVOKED`)", "`test_students`, `test_dashboard`, end-to-end 6/7"],
        ["CSRF", "Token on every POST form; `X-CSRF-Token` header for the API; refusals logged as `CSRF_REJECTED`",
         "`test_auth` and the module suites, end-to-end 17"],
        ["SQL injection", "Prepared statements for user input; `%` and `_` escaped in searches",
         "`test_students`, `test_events`, `test_api`, `test_dashboard`"],
        ["Cross-site scripting", "`htmlspecialchars()` / `e()` on output; `textContent` in JavaScript; HTML escaped in JSON",
         "`test_students`, `test_events`, `test_api`, `test_forms`, `test_dashboard`"],
        ["File uploads", "JPEG / PNG / WebP up to 2 MB; content type must match; real image; no embedded PHP; random 32-hex "
                         "name; `uploads/.htaccess`; `poster.php` with `nosniff` and a sandbox CSP for signed-in users",
         "`test_events`, end-to-end 8/9"],
        ["Data rules", "Capacity in a locking transaction; duplicates refused; soft delete of students; events with "
                       "registrations cannot be deleted", "`test_events`, `test_api`, `test_students`, end-to-end 10–12"],
        ["Headers and errors", "`X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, `no-store` on private pages; errors only "
                               "in the server log; HTTP 503 without details", "`test_auth`"],
        ["Audit and export", "One filterable audit log; CSV cells starting with `=`, `+`, `-`, `@`, tab or CR are prefixed "
                             "with an apostrophe", "`test_dashboard`, `test_students`, end-to-end 16"],
    ], [3.0, 9.0, 4.0], size=9)

    # ------------------------------------------------------------------ 9
    r.heading("9. End-to-End Scenario")
    r.para("`tests/browser_e2e.py` drives one continuous scenario in Microsoft Edge (1280 × 900 window, full-page screenshots) "
           "on the disposable database `studenthub_p11_test` and a temporary poster folder; the live database is never used. "
           "Five browser contexts play a new student (Ishaan Mehta), the administrator (`portal_admin`), an editor "
           "(`neha_editor`), a second student (Kunal Desai) and a visitor. Result: **17 / 17 passed** "
           "(`tests/browser_e2e_output.txt`).")
    f = lambda *shots: ", ".join(str(base + k) for k in shots)        # figure numbers of e2e screenshots 01-17
    base = r.figure_no
    r.table([
        ["Check", "Workflow and assertion", "Figure"],
        ["1", "Registration: account + linked student record with the next enrollment number, signed in", f(1)],
        ["2", "Logout (POST) and login with the e-mail address", f(2)],
        ["3", "The profile shows the student's own record", f(3)],
        ["4", "Editor and student opening the Admin Console → HTTP 403 “Access Denied”", f(4)],
        ["5", "Admin adds a student (automatic enrollment number) and edits the semester", f(5)],
        ["6/7", "Deactivation: the signed-in student loses access; a new sign-in is refused with the generic message", f(6)],
        ["6", "Reactivation restores sign-in", f(7)],
        ["8/9", "A PHP file disguised as `.jpg` is refused; a real JPEG poster is stored under a random name; the event is edited",
         f(8, 9)],
        ["10/11", "Registration succeeds; a second attempt → “already registered”; another student on a stale page → "
                  "“The event is full.”", f(10, 11)],
        ["12", "Cancellation keeps the row as `cancelled` and frees the seat", f(12)],
        ["13", "Event Finder: debounced search and registration through the JSON API without a page reload", f(13)],
        ["14", "Student search + status filter", f(14)],
        ["15", "Dashboard counters equal the database", f(15)],
        ["16", "Audit log: denied access, refused sign-in, revoked session and rejected upload are recorded", f(16)],
        ["17", "A forged form without the CSRF token → “Security check failed” (403), nothing changed; the API answers 401 to "
               "a visitor", f(17)],
        ["–", "No JavaScript errors (only the intended 401 / 403 / 422 responses); no PHP warnings or errors in the server log",
         "–"],
    ], [1.4, 12.8, 1.8])
    r.para("The run also reported the known 404 for `/favicon.ico` as information (the portal has no favicon).")
    r.figure("evidence/practical-15-integration/01-registration.png",
             "Step 1 – the registration form filled in for Ishaan Mehta (password strength “Strong”)", width=8.6)
    r.figure("evidence/practical-15-integration/02-login-dashboard.png",
             "Step 2 – signed in again with the e-mail address: dashboard with enrollment number 26IT043", width=5.8)
    r.figure("evidence/practical-15-integration/03-student-profile.png",
             "Step 3 – the profile shows the student's own record", width=5.8)
    r.figure("evidence/practical-15-integration/04-editor-access-denied.png",
             "Step 4 – the editor opening the Admin Console gets the HTTP 403 page", width=7.6)
    r.figure("evidence/practical-15-integration/05-student-created-edited.png",
             "Step 5 – student “Tanvi Kulkarni” added with the automatic number 25DS001 and updated (semester 4)", width=7.8)
    r.figure("evidence/practical-15-integration/06-inactive-login-denied.png",
             "Steps 6/7 – after deactivation the student's sign-in is refused with the generic message", width=7.6)
    r.figure("evidence/practical-15-integration/07-student-reactivated.png",
             "Step 6 – the record reactivated; sign-in works again", width=5.6)
    r.figure("evidence/practical-15-integration/08-poster-rejected.png",
             "Step 8 – a PHP file named .jpg is refused: “The file content is not a JPEG, PNG or WebP image.”, nothing saved",
             width=6.0)
    r.figure("evidence/practical-15-integration/09-event-with-poster.png",
             "Step 9 – event “Code Sprint 2026” (capacity 1) with its stored poster, after editing", width=7.2)
    r.figure("evidence/practical-15-integration/10-event-registration.png",
             "Step 10 – the student is registered for “Code Sprint 2026” (1 of 1 seats taken)", width=5.0)
    r.figure("evidence/practical-15-integration/11-event-full.png",
             "Step 11 – the second student gets “The event is full.”", width=5.0)
    r.figure("evidence/practical-15-integration/12-registration-cancelled.png",
             "Step 12 – the registration is cancelled; the row is kept and the seat is free again", width=5.0)
    r.figure("evidence/practical-15-integration/13-fetch-api-registration.png",
             "Step 13 – Event Finder: search “code sprint” and registration through the JSON API without a reload", width=8.6)
    r.figure("evidence/practical-15-integration/14-search-filters.png",
             "Step 14 – student search “Patel” combined with the status filter Active", width=8.6)
    r.figure("evidence/practical-15-integration/15-dashboard-statistics.png",
             "Step 15 – dashboard counters and the latest registrations (registered and cancelled)", width=7.4)
    r.figure("evidence/practical-15-integration/16-audit-log.png",
             "Step 16 – audit log filtered to SECURITY_BLOCK: refused sign-in, revoked session and two denied console accesses "
             "(the rejected upload has the status FAILED and is checked in the database)", width=8.2)
    r.figure("evidence/practical-15-integration/17-csrf-rejected.png",
             "Step 17 – a forged form without the CSRF token: “Security check failed”, nothing was changed", width=6.8)

    # ------------------------------------------------------------------ 10
    r.heading("10. Test Cases and Results")
    r.para("Complete run on 31 October 2026 – `python tests/run_all.py --browser <python with Playwright>` – with PHP 8.2.12 "
           "(XAMPP), MariaDB 10.4.32, Windows 11 and Microsoft Edge (headless, Playwright). Every suite uses its own disposable "
           "database (and a temporary poster folder); the live `studenthub_db` is only read. Output: `tests/run_all_output.txt`.")
    rows = [["Suite", "Passed", "Failed", "Time"]]
    for name, ok, bad, secs in SUITES:
        label = name + (" (incl. 132 + 72 checks against the snapshot)" if name == "Practical 15 – snapshot" else "")
        rows.append([label, str(ok), str(bad), f"{secs} s"])
    rows.append([f"**Total ({len(SUITES)} suites)**", f"**{PASSED}**", f"**{FAILED}**", ""])
    r.table(rows, [10.4, 1.9, 1.9, 1.8])
    edge = [x for x in SUITES if x[0].startswith("Edge")]
    r.para(f"{len(SUITES) - len(edge)} database and HTTP suites contribute {PASSED - sum(x[1] for x in edge)} checks and "
           f"{len(edge)} Microsoft Edge suites {sum(x[1] for x in edge)} checks. `run_all.py` reads "
           "each suite's own last summary line and counts a suite that exits with an error as failed.")
    r.para("**Live database:** migrations 001–005 were applied to the working `studenthub_db`, each after a verified backup; the "
           "read-only live checks pass (001 24 / 24, 002 4 / 4, 003 5 / 5, 004 5 / 5, 005 4 / 4). **Database evidence for "
           "Practical 8:** `tests/browser_database_evidence.py` 6 / 6 (phpMyAdmin screenshots of a disposable copy).")

    # ------------------------------------------------------------------ 11
    r.heading("11. Problems Encountered and Fixes")
    r.table([
        ["Problem", "Fix"],
        ["`Practical-15/` was an older, independently kept copy of the portal (with its own `schema.sql`) that no longer matched "
         "`studenthub/`", "Replaced by the generated snapshot; the old copy stays in the Git history; `tests/test_snapshot.py` "
                         "detects any difference"],
        ["The first complete run showed one failure in the Event Finder browser test: the check for “Event full” ran before the "
         "list refresh after the API's 409 answer had finished (a timing race in the test; it had passed in every earlier run)",
         "The test now waits for the refreshed card; the second complete run passed completely"],
        ["Summary of the complete run", "`run_all.py` was corrected to read each suite's own last summary line "
                                        "(TEST_REPORT §13)"],
        ["Earlier integration steps (TEST_REPORT §7–§12): PHP used XAMPP's `Europe/Berlin` time zone; deactivated students "
         "could still sign in; the Event Finder's loading indicator stayed visible (`display: flex` overrode `hidden`); "
         "sidebar links from `menu_items` were not escaped; `data.js` inserted values unescaped and had an artificial 800 ms delay",
         "Fixed in their steps (`Asia/Kolkata`, sign-in and session check, CSS fix, escaping, delay removed) – the complete run "
         "confirms all of them together"],
    ], [8.6, 7.4])

    # ------------------------------------------------------------------ 12
    r.heading("12. Known Limitations")
    r.bullets([
        "No limit on repeated sign-in attempts; no e-mail (password reset, answers to inquiries).",
        "Posters are uploaded only in the Admin Console (the JSON API handles no files); `menu_items` has no editing form.",
        "The Admin Console loads Bootstrap from a CDN; the portal has no favicon (one 404 per browser session).",
        "The canvas CAPTCHA of Practical 5 was not carried into the portal.",
        "Academic figures on the student pages (CGPA, SGPA, attendance, timetable) are sample data, labelled “Sample / demo data”.",
        "The standalone `Practical-1/` … `Practical-14/` folders are historical and not updated.",
        "The deployment steps of `DEPLOYMENT.md` were not carried out on a public server.",
    ])

    # ------------------------------------------------------------------ 13
    r.heading("13. Conclusion")
    r.para("StudentHub is now one application with one database and one login: the validation of Practical 5, the Data "
           "Explorer of Practical 6, the inquiries of Practical 7, the database foundation of Practical 8, the registration, "
           "login and sessions of Practicals 9 and 10, the student management of Practical 11, the events and posters of "
           "Practical 12, the Fetch API of Practical 13 and the admin dashboard of Practical 14 all run in `studenthub/` on "
           "`studenthub_db` through migrations 001–005. `Practical-15/` is a generated, hash-verified snapshot of exactly this "
           f"application. The complete run passed all {PASSED} checks of {len(SUITES)} suites, the snapshot itself passed the authentication "
           "and API suites, and the end-to-end scenario carried students, an editor and the administrator through 17 critical workflows "
           "in Microsoft Edge with genuine screenshots. The remaining limitations are listed above.")

    # ------------------------------------------------------------------ 14
    r.heading("14. References")
    r.bullets([
        "PHP Manual – MySQLi prepared statements: https://www.php.net/manual/en/mysqli.quickstart.prepared-statements.php",
        "PHP Manual – password_hash: https://www.php.net/manual/en/function.password-hash.php",
        "MDN – Using the Fetch API: https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch",
        "OWASP – Session Management Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html",
        "OWASP – File Upload Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html",
        "MariaDB Knowledge Base – SELECT … FOR UPDATE: https://mariadb.com/kb/en/for-update/",
        "Apache HTTP Server – .htaccess files: https://httpd.apache.org/docs/2.4/howto/htaccess.html",
        "Playwright for Python: https://playwright.dev/python/",
        "Project files: `README.md`, `DEPLOYMENT.md`, `TEST_REPORT.md` (section 13), `database/README.md`, "
        "`Practical-15/README.md`, `Practical-15/SNAPSHOT.md`",
        "Project repository: https://github.com/TheEmperor08/StudentHub-ITUE203-25CS023",
    ])
