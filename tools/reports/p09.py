"""Corrected report – Practical 9: secure student self-registration, integrated into the StudentHub portal (register.php),
creating the login account and its linked student record in one transaction in studenthub_db."""
from report_lib import corrected_notice

META = {
    "number": 9,
    "title": "Secure User Registration with Database Insert, Duplicate Email Check and Password Hashing",
    "tech": "PHP 8 · MySQLi prepared statements and transactions · password_hash() (bcrypt) · CSRF tokens · studenthub_db",
    "supersedes": "Practical-9/PRAC_9_ITUE203_25CS023.docx",
    "replaces_note": "The original describes a standalone registration page with its own database studenthub_prac9; registration "
                     "now runs in the integrated portal and creates the account together with its linked student record.",
}

EV = "evidence/practical-09-10-integration/"
EV15 = "evidence/practical-15-integration/"
RG = "studenthub/includes/registration.php"


def build(r):
    corrected_notice(r, META["supersedes"],
                     "The original report describes a standalone registration page in `Practical-9/` with its own database "
                     "`studenthub_prac9` (tables `users` and `audit_logs`). This corrected version describes registration as it "
                     "now works in the integrated portal (`studenthub/register.php`, database `studenthub_db`): the same security "
                     "requirements, but one transaction now creates the login account **and** its linked student record with the "
                     "next enrollment number, and the new student is signed in through the portal's one authentication system.")

    # ------------------------------------------------------------------ 1
    r.heading("1. Aim and Objectives")
    r.para("To build a secure StudentHub registration page in PHP that validates the input, refuses duplicate e-mail addresses and "
           "usernames, stores the password only as a hash created with `password_hash()` and inserts the new user into MySQL with "
           "MySQLi prepared statements – inside the integrated portal, so that a new student immediately has a working account, "
           "a student record and an enrollment number.")
    r.bullets([
        "Validate every field on the server (the browser can be bypassed); browser checks are only a convenience.",
        "Refuse an e-mail address or username that is already registered – in PHP and with UNIQUE keys in MySQL.",
        "Store passwords only as `password_hash()` hashes; never show, log or save a plaintext password.",
        "Use MySQLi prepared statements for every query with user input, and one transaction for all inserts.",
        "Extensions: CSRF token validation and an audit-log entry for every successful registration.",
        "Integration: create the `students` record linked through `students.user_id`, assign the next enrollment number and "
        "sign the student in; the role is always `student`, never taken from the form.",
    ])

    # ------------------------------------------------------------------ 2
    r.heading("2. Problem Definition")
    r.para("Official title: *“Secure User Registration with Database Insert, Duplicate Email Check, and Password Hashing.”* A "
           "registration form is the first part of a portal an attacker can reach. Without server-side checks it accepts invalid "
           "data; without duplicate checks one e-mail address can own several accounts; plaintext passwords are exposed by any "
           "database leak; and SQL built from user input allows SQL injection.")
    r.para("In the portal one more problem had to be solved: an account alone is not enough. Profile, dashboard and event "
           "registration need a `students` record that belongs to the account. Before the integration, accounts without a record "
           "showed a fixed name and roll number (TEST_REPORT §2). Registration therefore has to create both rows together – or "
           "neither – and must not take over a record that an administrator created for someone else.")
    r.table([
        ["#", "Evaluation requirement", "Where it is shown"],
        ["1", "Successful user registration", "Section 10, Figures 2–3; test \"valid registration -> 303 to dashboard.php\""],
        ["2", "Empty-field validation", "Section 7 (a \"required\" message for every field)"],
        ["3", "Invalid email validation", "Section 7; test \"invalid email -> rejected\""],
        ["4", "Password mismatch validation", "Section 7; test \"passwords do not match -> rejected\""],
        ["5", "Duplicate email / username validation", "Section 8; tests for both, also in another letter case"],
        ["6", "Password stored as a hash", "Section 9; test \"password stored only as a bcrypt hash that password_verify() accepts\""],
        ["7", "Successful database insertion", "Section 10, Figure 5; test \"account + student record created together\""],
    ], [0.8, 5.0, 10.2])

    # ------------------------------------------------------------------ 3
    r.heading("3. Tools and Technologies")
    r.table([
        ["Tool", "Use in this practical"],
        ["PHP 8.2.12 (XAMPP)", "Validation, sessions, CSRF tokens, `password_hash()`; PHP's built-in server for the tests"],
        ["MySQLi (exception mode)", "Prepared statements and the registration transaction"],
        ["MariaDB 10.4.32 (XAMPP)", "Shared portal database `studenthub_db` – tables `users`, `students`, `audit_logs`"],
        ["HTML5, CSS3, JavaScript", "Form (`register.php`, `assets/css/auth.css`); browser checks `assets/js/register-validation.js` (added with Practical 5)"],
        ["Python 3 (standard library)", "`tests/test_auth.py` – HTTP tests on a disposable database"],
        ["Microsoft Edge (headless) + Playwright", "`tests/browser_auth.py`, `tests/browser_e2e.py` – browser checks and screenshots"],
        ["Git / GitHub", "Commit `8011d39` – Practicals 9 and 10 integrated into the portal"],
    ], [4.8, 11.2])

    # ------------------------------------------------------------------ 4
    r.heading("4. Place in the Integrated Portal")
    r.para("Registration is the public page `studenthub/register.php` (linked from the sign-in page as *Create an account*). It "
           "uses the portal's shared connection, authentication and audit log:")
    r.table([
        ["File", "Role in Practical 9"],
        ["`register.php`", "Form and controller: CSRF check, validation, registration, sign-in, audit entry, redirect"],
        ["`includes/registration.php`", "`validate_registration()`, `find_registration_conflicts()`, `next_enrollment_number()`, `register_student_account()`"],
        ["`includes/auth.php`", "`password_problems()` and `PASSWORD_POLICY_TEXT` (shared with the password change), `csrf_field()` / `csrf_is_valid()`, `login_user()`, `e()`"],
        ["`audit_logger.php`, `db.php`", "`log_audit()` (USER_REGISTER); the MySQLi connection `$conn`"],
        ["`assets/js/register-validation.js`", "Real-time browser checks with the same rules (later Practical 5 integration)"],
    ], [5.2, 10.8])

    # ------------------------------------------------------------------ 5
    r.heading("5. Database Design")
    r.para("Registration writes to two tables of `studenthub_db` (InnoDB, `utf8mb4_unicode_ci`). Their current structure in "
           "`database/studenthub_demo.sql`:")
    r.excerpt("database/studenthub_demo.sql", "CREATE TABLE IF NOT EXISTS `users` (", "CONSTRAINT `chk_students_semester`",
              "users and students (current schema)")
    r.bullets([
        "`users.password` holds only the `password_hash()` result (VARCHAR(255) leaves room for longer future algorithms). "
        "`username` and `email` are UNIQUE; because the collation ignores letter case, `Diya_Mehta` counts as a duplicate of "
        "`diya_mehta`. `status` and `chk_users_role` were added later by migration 004 (Practical 14); the columns "
        "`remember_token_hash` / `remember_token_expiry` are legacy columns that the portal does not use.",
        "`students.user_id` (migration 001, Practical 8) links the record to its account: UNIQUE (one account per record) with "
        "`ON DELETE SET NULL`. `students.email` is UNIQUE, `enrollment_no` UNIQUE since migration 002, and `semester` is checked "
        "to be NULL or 1–8.",
        "Registration inserts the role as the literal `'student'` and the status as `'Active'`; neither value can come from the form.",
    ])

    # ------------------------------------------------------------------ 6
    r.heading("6. Registration Form and Browser-side Checks")
    r.para("`register.php` shows one card with these inputs; each has a visible label, a suitable HTML type, length limits and "
           "`autocomplete` hints. A hidden field carries the session's CSRF token. The form has `novalidate`, so the server alone "
           "decides; a field with an error gets `aria-invalid=\"true\"` and `aria-describedby` pointing to its message.")
    r.table([
        ["Field", "Input", "Server rule (validate_registration)"],
        ["Full Name (`name`)", "text, 2–100", "letters (any language), spaces, apostrophes, dots, hyphens; extra spaces collapsed"],
        ["Username", "text, 3–30, pattern", "starts with a letter; then letters, digits, underscore"],
        ["Email Address", "email, max 100", "`FILTER_VALIDATE_EMAIL`; trimmed and stored in lower case"],
        ["Gender / Course / Admission Year", "radio / select / select", "Male, Female or Other; one of 4 courses; the current academic year or one of the two before"],
        ["Password / Confirm Password", "password, 8–72", "policy of `password_problems()`; confirmation equal (`hash_equals()`)"],
        ["Terms (`agree`)", "checkbox value 1", "must be exactly `'1'`"],
    ], [4.4, 3.6, 8.0])
    r.para("With the later Practical 5 integration, `assets/js/register-validation.js` checks every field while typing with the same "
           "rules and messages, shows a password-strength meter and keeps the form from being sent while a rule is broken "
           "(Figure 1). This is only a convenience: `tests/test_forms.py` confirmed that a request bypassing the browser is still "
           "refused by the server (\"the server refuses the weak password (422, nothing stored)\").")

    # ------------------------------------------------------------------ 7
    r.heading("7. Server-side Validation")
    r.para("`validate_registration()` first makes sure every value is a plain UTF-8 string – a request such as `name[]=x` sends an "
           "array and gets \"This field contains characters that are not allowed.\" – and then applies the rules. Every field has "
           "its own \"required\" message (for example \"Please enter your full name.\", \"Please choose a username.\"), which covers "
           "the empty-field requirement. The password policy is shared with the password change in the profile:")
    r.excerpt("studenthub/includes/auth.php", "function password_problems(string $password): array", "const PASSWORD_POLICY_TEXT",
              "password policy: 8–72, upper, lower, digit, special character")
    r.excerpt(RG, "    if (!isset($errors['username'])) {", "$errors['agree'] = 'Please accept the Terms & Conditions.';",
              "username, e-mail, lists, password, confirmation and terms")
    r.para("The maximum of 72 is measured in bytes because bcrypt uses only the first 72 bytes. The semester is not a form field: "
           "it is derived from the admission year (admitted this academic year → 1, last year → 3, two years ago → 5). Extra "
           "fields such as `role=admin` are ignored. When there are errors the page answers HTTP 422 with \"Please correct the "
           "highlighted fields.\", a message under each field and the entered values (never the passwords) shown again through "
           "`htmlspecialchars()`.")

    # ------------------------------------------------------------------ 8
    r.heading("8. Duplicate Email and Username Protection")
    r.para("After validation, `find_registration_conflicts()` runs separate prepared statements, so the user is told exactly which "
           "value is taken. The e-mail is compared trimmed and in lower case. If no account but a **student record** already has "
           "the address (for example one created by an administrator), the registration is refused with a request to contact the "
           "administrator – the record is never linked or changed automatically.")
    r.excerpt(RG, "function find_registration_conflicts(", "return $errors;", "username, account e-mail and student-record e-mail checks")
    r.para("A check in PHP alone is not enough: two requests can both pass it before either inserts. The UNIQUE keys on "
           "`users.username`, `users.email` and `students.email` have the final word – an INSERT that fails with MySQL error 1062 "
           "rolls the transaction back and returns the same friendly message (Section 10).")

    # ------------------------------------------------------------------ 9
    r.heading("9. Password Hashing")
    r.para("A hash is a one-way function: the password can be turned into the hash, but not back. `password_hash($password, "
           "PASSWORD_DEFAULT)` uses bcrypt (`$2y$…`) in PHP 8.2 and includes a random salt, so the same password gives a different "
           "hash every time and precomputed tables are useless. At sign-in (Practical 10) `password_verify()` recomputes the hash "
           "with the stored salt and cost. Only the hash is stored; the error log line of a failed registration contains no "
           "password or hash, and no password appears in this report or the screenshots (the fields are masked). The tests "
           "confirmed that the stored value is a bcrypt hash accepted by `password_verify()` and that no password appears in the "
           "server log.")

    # ------------------------------------------------------------------ 10
    r.heading("10. One Transaction: Account, Student Record and Enrollment Number")
    r.para("Enrollment numbers follow the portal's existing scheme: the last two digits of the admission year, the course code "
           "(IT, CS, DS or WD) and a three-digit counter, e.g. `26IT001`. The next number is computed while the matching rows are "
           "locked with `SELECT … FOR UPDATE`, so two simultaneous registrations never get the same number:")
    r.excerpt(RG, "function next_enrollment_number(", "return $prefix . sprintf('%03d', $max + 1);", "next free number for the prefix")
    r.para("`register_student_account()` checks the conflicts, hashes the password and then creates both rows in **one transaction**: "
           "the account (role always `'student'`) and the student record with `user_id` = the new account's id. On any error the "
           "transaction is rolled back, so an account never exists without its record and vice versa.")
    r.excerpt(RG, "// Creates the account and the linked student record in one transaction.",
              "throw new RuntimeException('Registration could not be completed.');", "account + linked record, commit or rollback")
    r.para("The rollback was tested by a test trigger that makes the student INSERT fail after the account INSERT: the page showed a "
           "general message without technical details, the details went to the server log, and neither the account nor the record "
           "existed afterwards.")

    # ------------------------------------------------------------------ 11
    r.heading("11. CSRF Protection, Sign-in and Audit Log")
    r.para("The controller at the top of `register.php` shows the order of the steps. A POST is processed only if it carries the "
           "token of the session (`csrf_is_valid()` compares with `hash_equals()`); otherwise nothing is validated or saved. After "
           "a successful registration `login_user()` signs the student in – it regenerates the session ID and creates a new CSRF "
           "token (Practical 10) – the audit entry USER_REGISTER is written, and a 303 redirect leads to the dashboard "
           "(Post/Redirect/Get), where a one-time message names the enrollment number.")
    r.excerpt("studenthub/register.php", 'if ($_SERVER["REQUEST_METHOD"] === "POST") {', "http_response_code(422);",
              "controller: CSRF, validation, registration, sign-in, audit entry")
    r.para("A visitor who is already signed in is redirected away from the page. The CSRF token is 32 random bytes from "
           "`random_bytes()` (64 hexadecimal characters) per session; a missing or wrong token gives the message \"The registration "
           "form expired. Please check your details and submit again.\" and stores nothing.")

    # ------------------------------------------------------------------ 12
    r.heading("12. Output Screenshots")
    r.para("Genuine full-page captures from Microsoft Edge (headless, Playwright, window 1280 px wide) of the integrated portal on "
           "PHP's built-in server with a disposable database built from `database/studenthub_demo.sql`; all names and addresses "
           "are fictional and every password field is masked. Figures 1, 3 and 5 come from `tests/browser_auth.py`, Figures 2 and 4 "
           "from the end-to-end test `tests/browser_e2e.py`.")
    r.figure(EV + "register-weak-password.png",
             "Weak password \"weakpass\" (masked) for Diya Mehta: the browser-side check added later with the Practical 5 integration "
             "stops the form – strength \"Very weak\" and \"The password needs an uppercase letter, a number, a special character.\"; "
             "nothing was sent and the values stay in the fields. The server-side refusal of a weak password is tested over HTTP in "
             "tests/test_auth.py", width=12)
    r.figure(EV15 + "01-registration.png",
             "The registration form filled for the fictional student Ishaan Mehta (ishaan_mehta, ishaan.mehta@example.com, "
             "Information Technology, admission year 2026) with a strong password (strength \"Strong\") and the terms accepted, "
             "just before Register Account", width=12)
    r.figure(EV + "registered-dashboard.png",
             "After a successful registration: Diya Mehta is signed in at once and redirected to dashboard.php with \"Welcome to "
             "StudentHub, Diya Mehta! Your enrollment number is 26IT001.\"; sidebar and header show the linked record (26IT001, "
             "B.Tech Information Technology, 1st semester). Attendance and CGPA tiles are labelled sample data", width=10)
    r.figure(EV15 + "03-student-profile.png",
             "My Profile of Ishaan Mehta, read from the student record linked through students.user_id: enrollment number 26IT043, "
             "Information Technology, semester 1 (derived from admission year 2026), e-mail ishaan.mehta@example.com", width=10)
    r.figure(EV + "admin-console.png",
             "Admin Console → Student Records in the same run as Figures 1 and 3: the self-registered Diya Mehta (26IT001, "
             "Information Technology, semester 1) is Active with the account column \"Linked\"; the demo records from "
             "studenthub_demo.sql have no account (\"None\")", width=11)

    # ------------------------------------------------------------------ 13
    r.heading("13. Testing and Results")
    r.para("All tests were executed on 31 October 2026 with PHP 8.2.12 (XAMPP), MariaDB 10.4.32 and PHP's built-in server on Windows 11, "
           "against the disposable database `studenthub_auth_test` (built from `database/studenthub_demo.sql`, dropped afterwards). "
           "Test passwords are random and never printed; the live `studenthub_db` users and password hashes were compared before "
           "and after and were unchanged (TEST_REPORT §6).")
    r.table([
        ["Suite", "Result", "Output"],
        ["`tests/test_auth.py` – HTTP tests of registration, login, sessions and RBAC", "**132 / 132 passed**", "`tests/test_auth_output.txt`"],
        ["`tests/browser_auth.py` – Microsoft Edge (Figures 1, 3, 5)", "**14 / 14 passed**", "`tests/browser_auth_output.txt`"],
        ["`tests/browser_e2e.py` – end-to-end scenario (Figures 2, 4)", "**17 / 17 passed**", "`tests/browser_e2e_output.txt`"],
        ["`tests/run_all.py` – complete run of every suite", "**841 passed, 0 failed**", "`tests/run_all_output.txt`"],
    ], [8.4, 3.6, 4.0])
    r.para("The registration-related checks of `tests/test_auth.py` (the other checks belong to Practical 10):")
    r.table([
        ["Area", "Checks", "Examples (from test_auth_output.txt)"],
        ["Valid registration and linkage", "12", "CSRF token and no role field in the form; 303 to dashboard.php; account and record created together with `students.user_id = users.id`; role `student` although the form sent `role=admin`; numbers 26CS001 and the next one; semester 1 for 2026, 25DS… and semester 3 for 2025; bcrypt hash accepted by `password_verify()`; signed in with welcome message; own profile; USER_REGISTER"],
        ["Invalid input", "12", "invalid e-mail; password too short, without uppercase/number/special, longer than 72 bytes; passwords do not match; username starting with a digit or too short; name with digits/HTML; course, admission year or gender not in the list; terms not accepted"],
        ["Duplicates and existing records", "6", "duplicate e-mail (other case, spaces) and username (other case) refused; no account created by refused forms; input escaped on redisplay; e-mail of a pre-existing student record refused and that record not linked or changed"],
        ["CSRF / rollback / concurrency", "1 + 2 + 1", "no valid token → refused, nothing stored; forced failure → general message, both rows rolled back; 5 simultaneous registrations → 5 different, consecutive enrollment numbers"],
        ["Static checks / server log", "7 + 3", "`php -l` on all 40 PHP files of `studenthub/` and `tools/`; registration inserts the role as the literal `'student'`; no PHP warnings; no password in the server log"],
    ], [4.0, 1.8, 10.2])
    r.para("**Browser checks (Edge):** `browser_auth.py` confirmed that the weak password is stopped in the browser and the values "
           "stay in the fields, that registration leads to the dashboard with the welcome message and enrollment number, that the "
           "sidebar shows the student's own name and number, and that the database contains the account and its linked record. "
           "`browser_e2e.py` step 1: \"registration: account + linked student record with the next enrollment number, signed in\". "
           "Both outputs report one known 404 for `/favicon.ico` (the portal has no favicon). The suite rows of the complete run "
           "are \"Practicals 9/10 – registration, login, sessions, RBAC\" 132 / 0, \"Edge – registration, login, RBAC\" 14 / 0 and "
           "\"Edge – end-to-end (Practical 15)\" 17 / 0.")

    # ------------------------------------------------------------------ 14
    r.heading("14. Problems Found and Fixed")
    r.bullets([
        "**Accounts without a student record** showed a fixed name and roll number (Shreyas / 25CS023) on several pages (TEST_REPORT "
        "§2). Registration now creates the linked record, and an account without one sees only its own username and no enrollment "
        "number (TEST_REPORT §6; test \"an account without a linked student record sees its own username …\").",
        "**Old shared database:** the earlier Practical-9 code used the shared `user_registration` database. The portal uses only "
        "`studenthub_db`; `db.php` has no fallback, and the tests confirmed that an unavailable database gives HTTP 503 on the home, "
        "sign-in and dashboard pages instead of a login form or data from another database.",
        "**Time zone:** PHP used XAMPP's `Europe/Berlin` while MariaDB uses India time, so between midnight and about 04:30 the "
        "academic year used for enrollment numbers and dates could be one day behind; `db.php` now sets `Asia/Kolkata` "
        "(TEST_REPORT §7).",
        "**Browser test after Practical 5:** once the real-time checks were added, the weak-password check in `browser_auth.py` was "
        "changed to expect the browser to stop the form; the server refusal is tested over HTTP (TEST_REPORT §12).",
        "**Taking over existing records:** linking a registration to an existing record with the same e-mail could hand someone "
        "else's record to a new account; such registrations are refused and the administrator is asked to help.",
    ])

    # ------------------------------------------------------------------ 15
    r.heading("15. Differences from the Original Practical and Limitations")
    r.table([
        ["Aspect", "Original report (Practical-9/)", "Integrated portal"],
        ["Database", "Own `studenthub_prac9`: `users` + `audit_logs`", "Shared `studenthub_db`: `users` + linked `students` record"],
        ["Fields", "Full name, username, e-mail, password, confirmation, terms", "+ gender, course, admission year (enrollment number, semester)"],
        ["One transaction", "User row + audit row", "Account + student record; USER_REGISTER logged after the commit"],
        ["After success", "Confirmation page (Post/Redirect/Get)", "Signed in at once; 303 to the dashboard with the enrollment number"],
        ["CSRF failure / hash CHECK", "HTTP 403; CHECK constraint on the hash format", "Message in the form (HTTP 422); no CHECK – only the application writes hashes"],
        ["Tests", "93 / 93 (PHP) and 78 / 78 (Python)", "132 / 132 HTTP, 14 / 14 and 17 / 17 Edge; complete run 841 / 0"],
    ], [3.0, 6.2, 6.8])
    r.bullets([
        "No e-mail verification or password reset (the portal sends no e-mail), no rate limiting and no CAPTCHA – the canvas CAPTCHA "
        "of Practical 5 was not carried into the portal (TEST_REPORT §12–§13).",
        "The duplicate messages reveal that a username or e-mail address is already registered (required by the practical).",
        "Automatic enrollment numbers exist only for the four registration courses, at most 999 per prefix. For a self-registered "
        "student the e-mail is stored in `users` and in `students`.",
        "An all-empty POST is not among the saved checks; empty fields are handled by the \"required\" branches shown in Section 7. "
        "Tested only with PHP's built-in server, MariaDB 10.4.32 and Microsoft Edge.",
    ])

    # ------------------------------------------------------------------ 16
    r.heading("16. Conclusion")
    r.para("All seven evaluation requirements are met in the integrated portal. Every field is validated on the server (with "
           "browser checks only for convenience), duplicate e-mail addresses and usernames are refused in PHP and by UNIQUE keys, "
           "passwords are stored only as bcrypt hashes, and every query with user input is a MySQLi prepared statement. One "
           "transaction creates the account and its linked student record with the next enrollment number, so a new student can "
           "use the dashboard, the profile and event registration immediately, and a failure leaves nothing behind. Both extensions "
           "are implemented: a CSRF token on the form and an audit entry for every registration. 132 HTTP checks, 14 + 17 browser "
           "checks and the complete run of 841 checks passed.")

    # ------------------------------------------------------------------ 17
    r.heading("17. References")
    r.bullets([
        "Project repository: https://github.com/TheEmperor08/StudentHub-ITUE203-25CS023 – `studenthub/register.php`, "
        "`studenthub/includes/registration.php`, `studenthub/includes/auth.php`, `tests/`, `evidence/practical-09-10-integration/`, "
        "`TEST_REPORT.md` §6; commit `8011d39`",
        "PHP Manual – password_hash: https://www.php.net/manual/en/function.password-hash.php",
        "PHP Manual – MySQLi prepared statements: https://www.php.net/manual/en/mysqli.quickstart.prepared-statements.php",
        "PHP Manual – random_bytes and hash_equals: https://www.php.net/manual/en/function.random-bytes.php, "
        "https://www.php.net/manual/en/function.hash-equals.php",
        "PHP Manual – Validate filters (FILTER_VALIDATE_EMAIL): https://www.php.net/manual/en/filter.filters.validate.php",
        "OWASP – Password Storage Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html",
        "OWASP – Cross-Site Request Forgery Prevention Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html",
    ])
