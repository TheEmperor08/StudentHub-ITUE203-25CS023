"""Corrected report – Practical 7: PHP form processing, as integrated into the portal's Help & Contact page (studenthub/contact.php)."""
from report_lib import corrected_notice

META = {
    "number": 7,
    "title": "PHP Form Processing with Server-Side Validation and Stored Inquiries",
    "tech": "PHP 8 · MySQLi prepared statements · MariaDB 10.4 · HTML5 · CSS3",
    "supersedes": "Practical-7/PRAC_7_ITUE203_25CS023.docx",
    "replaces_note": "The original described the standalone Practical-7 app with a JSON file; the portal's Help & Contact form now "
                     "stores validated inquiries in the inquiries table, with an Admin Console view.",
}

SHOTS = "evidence/practical-05-07-integration/"
FIG_W = 14.0      # cm – lets two screenshots share a page while staying readable


def build(r):
    corrected_notice(
        r, META["supersedes"],
        "The original report described the standalone application in `Practical-7/` (`index.php` and `records.php`, storing "
        "submissions in a JSON file protected by `flock()`). This version describes the same server-side form processing on the "
        "portal's Help & Contact page `studenthub/contact.php`: valid inquiries are stored in the database table `inquiries` "
        "(migration 005) instead of a file, and administrators read and resolve them in the Admin Console.")

    # ------------------------------------------------------------------ 1
    r.heading("1. Aim and Objectives")
    r.para("To process the StudentHub inquiry (Help & Contact) form with PHP: receive the data with the POST method, validate and "
           "sanitise every field on the server, store valid inquiries safely, show clear success and error messages, and let the "
           "administrators work through the stored inquiries.")
    r.bullets([
        "Build an accessible PHP form whose data is sent with POST and processed only on the server.",
        "Validate empty and invalid inputs on the server – name, e-mail address, optional enrollment number, topic and message – "
        "without relying on JavaScript or browser checks.",
        "Sanitise the input and escape every value when it is displayed, so submitted text can never run as HTML.",
        "Store valid inquiries safely, also when several are sent at the same moment (in the portal: a database table instead of a "
        "file).",
        "Show a clear success message with a reference number after saving, and a message next to each invalid field.",
        "Intermediate extension: display the stored records – here as the *Inquiries* tab of the Admin Console.",
        "Advanced extension: protect the form with a CSRF token – here the portal's session token, checked on every POST.",
    ])

    # ------------------------------------------------------------------ 2
    r.heading("2. Problem Definition")
    r.para("Official problem definition: “Process submitted registration/contact form data using PHP. Validate and sanitize inputs "
           "on the server side and store records in CSV or JSON file format. Display success/error messages.”")
    r.para("Practical 7 was first built as a standalone PHP application in `Practical-7/` that appended valid submissions to "
           "`private/submissions.json` under an exclusive `flock()` lock. The integrated portal already had a Help & Contact page, "
           "but according to the audit in `TEST_REPORT.md` (section 12) “inquiries were **not stored** (only an audit line when "
           "signed in)”. The integration, as recorded there, stores validated inquiries in a new table `inquiries` (migration 005), "
           "gives the sender a reference number, adds a honeypot field and adds an *Inquiries* tab to the Admin Console; the "
           "validation and storage functions are in `studenthub/includes/inquiries.php`.")
    r.note("**Storage format.** The practical asks for CSV or JSON file storage. Inside the portal, which already keeps all its data "
           "in `studenthub_db`, the inquiries are stored in a database table instead. `database/README.md` explains the choice: "
           "“Practical 7 kept inquiries in a JSON file protected by `flock()`; in the portal the database provides the same safety "
           "for simultaneous submissions (tested with 8 parallel requests).” The JSON-file version with file locking remains "
           "unchanged in `Practical-7/` and is described in the original report.", fill="EEF4FF")
    r.para("The practical list asks four key questions; the answers for the integrated implementation are:")
    r.table([
        ["Key question", "Answer in the integrated portal"],
        ["Is the form submitted using POST?",
         "Yes. The form has `method=\"POST\"` and `action=\"contact.php\"`; the data is processed only when "
         "`$_SERVER[\"REQUEST_METHOD\"]` is `POST`. A GET request only displays the form."],
        ["Are inputs validated and sanitized server side?",
         "Yes. `validate_inquiry()` accepts only UTF-8 strings, trims every value, collapses spaces in the name, lower-cases the "
         "e-mail and upper-cases the enrollment number, and checks the name pattern and length, the e-mail with `filter_var()`, the "
         "enrollment-number format, the topic list and the message length (10–2000 characters). The form has `novalidate` and no "
         "validation script, so every check is made by PHP."],
        ["Is file writing handled safely?",
         "In the portal no file is written. Each inquiry is one `INSERT` with a prepared statement; the InnoDB table gives every row "
         "its own AUTO_INCREMENT id, so simultaneous inquiries cannot overwrite each other – 8 parallel inquiries were all stored "
         "with different numbers. The table also enforces the topic list (ENUM) and the message length (CHECK)."],
        ["Are success and error responses displayed clearly?",
         "After saving, the page redirects (HTTP 303) and shows, once, a message with the sender's name and the reference number, "
         "e.g. “Thank you, Neha Rao. Your inquiry has been received by the A7 CSE helpdesk (reference #1).” (Figure 2). Invalid "
         "input returns HTTP 422 with “Please correct the highlighted fields. Your "
         "inquiry was not sent.”, a message under each invalid field and the entered values kept."],
    ], [5.0, 11.0])

    # ------------------------------------------------------------------ 3
    r.heading("3. Tools and Technologies")
    r.table([
        ["Tool / technology", "Use in this practical"],
        ["PHP 8.2.12 (XAMPP), MySQLi", "`contact.php`, `includes/inquiries.php`, `admin_dashboard.php`: processing, validation, "
                                       "sessions; prepared statements for INSERT, SELECT and UPDATE"],
        ["MariaDB 10.4.32", "Table `inquiries` in `studenthub_db` (migration `database/migrations/005_inquiries.sql`)"],
        ["HTML5, CSS3", "Form markup with labels and ARIA attributes; `global.css` for field messages and the hidden honeypot field"],
        ["Bootstrap 5.3.2 (CSS)", "Table, badge and button styles of the Admin Console"],
        ["Python 3 (standard library)", "`tests/test_forms.py` (HTTP tests) and `database/tests/test_005_inquiries.py`"],
        ["Playwright + Microsoft Edge (headless)", "`tests/browser_forms.py`: browser checks and the screenshots in Section 8"],
        ["Git / GitHub", "Version control; the integration is commit `938e74f` of the StudentHub repository"],
        ["Operating system", "Windows 11"],
    ], [5.2, 10.8])

    # ------------------------------------------------------------------ 4
    r.heading("4. Place in the Integrated StudentHub Portal")
    r.para("The form is the portal's *Help & Contact* page, linked in the *Campus* group of the sidebar and from the home page "
           "(“Contact Us”). It is public: visitors can send an inquiry without an account. For a signed-in user the name, e-mail "
           "address and enrollment number are filled in from the linked `students` record, and the stored inquiry is linked to the "
           "account.")
    r.table([
        ["File / route", "Role"],
        ["`studenthub/contact.php` (route `contact.php`)", "Form, POST processing, messages; public (`optional_user()`)."],
        ["`studenthub/includes/inquiries.php`", "`INQUIRY_TOPICS`, `validate_inquiry()`, `save_inquiry()`, `list_inquiries()`, "
                                                "`inquiry_counts()`, `resolve_inquiry()`."],
        ["`studenthub/admin_dashboard.php?tab=inquiries`", "Admin Console *Inquiries* tab: list, filter, mark as resolved."],
        ["`studenthub/includes/auth.php`", "CSRF token functions, `e()`, `redirect()` (HTTP 303), the permissions `admin.console` "
                                           "and `inquiries.manage` (administrators only)."],
        ["`database/migrations/005_inquiries.sql` / `.down.sql`", "Creates (or removes) the `inquiries` table."],
        ["`database/studenthub_demo.sql`", "Fresh installation; contains the `inquiries` table and records migrations 001–005."],
    ], [6.2, 9.8])
    r.para("Connections to the other integrated practicals: the CSRF token and sessions come from the integrated login (Practicals "
           "9 and 10); every stored and resolved inquiry is written to the audit log and the Inquiries tab sits in the Admin "
           "Console of Practical 14; the `inquiries` table references `users` in the shared portal database `studenthub_db`, into "
           "which Practicals 8–15 are integrated step by step (`database/README.md`).")

    # ------------------------------------------------------------------ 5
    r.heading("5. Implementation")
    r.heading("5.1 The form", 2)
    r.para("All values are printed with `e()`. The form keeps the field names of the earlier portal form (`name`, `id`, `mail`, "
           "`topic`, `msg`). When a field is invalid, PHP adds `aria-invalid=\"true\"` and `aria-describedby` and prints the message "
           "in a `<span class=\"field-error\">` below it. The last field, `website`, is the honeypot: it is moved off-screen by CSS, "
           "hidden from screen readers (`aria-hidden=\"true\"`) and skipped by the Tab key (`tabindex=\"-1\"`).")
    r.excerpt("studenthub/contact.php", '<form action="contact.php" method="POST" novalidate>', 'inquiry_error($errors, "name")',
              "start of the inquiry form: POST, CSRF token and the first field")
    r.para("The enrollment number, e-mail, topic and message fields follow the same pattern (lines 100–123); the topic options are "
           "generated from `INQUIRY_TOPICS`. The honeypot field is a single line, followed by the two buttons:")
    r.excerpt("studenthub/contact.php", 'class="hp-field"', '<button type="reset">Clear</button>',
              "the honeypot field and the buttons")

    r.heading("5.2 POST processing (Post/Redirect/Get)", 2)
    r.para("When the request is a POST, the CSRF token is checked first (`require_valid_csrf()`, Section 7). The input is then "
           "validated; the submitted strings are kept for redisplay. A valid inquiry is stored, an audit entry is written, the "
           "success message is put into the session (`flash()`) and the browser is redirected back to `contact.php` with HTTP 303, "
           "so refreshing the page cannot send the inquiry again. Invalid input returns HTTP 422 and the form is shown again.")
    r.excerpt("studenthub/contact.php", 'if ($_SERVER["REQUEST_METHOD"] === "POST") {', "http_response_code(422);",
              "processing of the submitted form")

    r.heading("5.3 Server-side validation and sanitising", 2)
    r.excerpt("studenthub/includes/inquiries.php", "function validate_inquiry", "return [$clean, $errors];",
              "validate_inquiry()", max_lines=53)
    r.table([
        ["Field", "Sanitising", "Rule", "Message"],
        ["Your Name (`name`)", "trimmed; runs of white space become one space",
         r"required; 2–100 characters; `/^\p{L}[\p{L}\p{M} .'-]*$/u`",
         "Please enter your name. / The name must be 2–100 characters long. / Use letters, spaces, apostrophes, dots and hyphens only."],
        ["Enrollment Number (`id`, optional)", "trimmed, upper-cased; empty becomes NULL", "`/^[0-9]{2}[A-Z]{2}[0-9]{3}$/`",
         "Use the enrollment number format 2 digits, 2 letters, 3 digits (e.g. 25CS023), or leave it empty."],
        ["Email (`mail`)", "trimmed, lower-cased", "required; at most 100 characters; `filter_var(…, FILTER_VALIDATE_EMAIL)`",
         "Please enter your email address. / Please enter a valid email address, e.g. name@example.com."],
        ["Topic (`topic`)", "trimmed; empty becomes General", "one of General, Academics, Events, Portal access, Other",
         "Please choose a topic from the list."],
        ["Message (`msg`)", "trimmed; CR LF line breaks become LF", "required; 10–2000 characters (`mb_strlen`)",
         "Please enter your message. / The message must be 10–2000 characters long."],
        ["Every field", "–", "must be a string with valid UTF-8 (an array such as `msg[]` is refused)",
         "This field contains characters that are not allowed."],
        ["Honeypot (`website`)", "–", "must be empty", "The inquiry could not be accepted. (shown under the message)"],
    ], [3.0, 3.6, 4.6, 4.8], size=8.5)
    r.para("Sanitising here means normalising the value that is stored; HTML is not removed or encoded before storage. Instead, every "
           "value is escaped at the moment it is printed (Section 7), so the stored text stays exactly what the sender wrote.")

    r.heading("5.4 Storing and reading inquiries", 2)
    r.para("`save_inquiry()` inserts one row with a prepared statement and returns the new id, which is shown to the sender as the "
           "reference number. `user_id` is the id of the signed-in account, or NULL for a visitor. `list_inquiries()` reads the "
           "newest inquiries (at most 100), optionally only those with the status `new` or `resolved`, and joins `users` to show the "
           "account name.")
    r.excerpt("studenthub/includes/inquiries.php", "function save_inquiry", "return (int) $stmt->insert_id;",
              "save_inquiry() (list_inquiries() follows in lines 74–87)")

    r.heading("5.5 Displaying the stored records – Admin Console Inquiries tab (intermediate extension)", 2)
    r.para("The Admin Console (`admin_dashboard.php`) is open only to administrators (`admin.console`). Its *Inquiries* tab shows a "
           "badge with the number of new inquiries, the counts of new and stored inquiries (e.g. “2 new, 2 in total”), a filter "
           "(All / New / Resolved) and a table with "
           "the columns #, Received, From, Topic, Message, Status and Action. Every value is escaped with `e()`; the message keeps "
           "its line breaks (`white-space: pre-wrap`). An open inquiry has a *Resolved* button – a small POST form with the CSRF "
           "token; a resolved one shows the time it was resolved. The markup is the block “INQUIRIES TAB” in `admin_dashboard.php` "
           "(lines 1190–1232); Figures 3 and 4 show it rendered.")
    r.para("Marking an inquiry as resolved is accepted only as a POST with a valid CSRF token and the permission "
           "`inquiries.manage`. `resolve_inquiry()` changes only an inquiry whose status is still `new` (`UPDATE … WHERE id = ? AND "
           "status = 'new'`), so resolving twice gives the message “That inquiry was not found or is already resolved.”")
    r.excerpt("studenthub/admin_dashboard.php", "Help & Contact inquiries (Practical 7): mark as resolved",
              'redirect("admin_dashboard.php?tab=inquiries");', "the resolve action")

    # ------------------------------------------------------------------ 6
    r.heading("6. Database and Relationships")
    r.para("Migration 005 adds one table to `studenthub_db` and changes nothing else:")
    r.excerpt("database/migrations/005_inquiries.sql", "CREATE TABLE IF NOT EXISTS inquiries", ") ENGINE=InnoDB",
              "the inquiries table")
    r.table([
        ["Element", "Meaning"],
        ["`id` INT AUTO_INCREMENT, primary key", "The reference number shown to the sender (#1, #2, …)."],
        ["`user_id` → `users.id`, `fk_inquiries_user`",
         "Optional link to the signed-in account (NULL for visitors). ON DELETE SET NULL: deleting an account keeps its inquiries; "
         "ON UPDATE CASCADE."],
        ["`topic` ENUM", "The same five values as `INQUIRY_TOPICS` in PHP; default General."],
        ["`message` TEXT + CHECK `chk_inquiries_message`", "`CHAR_LENGTH(message) BETWEEN 10 AND 2000` – the PHP rule repeated in "
                                                          "the database."],
        ["`status` ENUM('new', 'resolved')", "Default `new`; `resolved_at` is set when an administrator resolves the inquiry."],
        ["Indexes", "`idx_inquiries_status (status, created_at)` for the filter, `idx_inquiries_user (user_id)` for the foreign key."],
    ], [5.6, 10.4])
    r.para("Relationship: users 1 : 0..n inquiries through the optional `inquiries.user_id`. The table is InnoDB with "
           "`utf8mb4_unicode_ci`, like the other portal tables.")
    r.bullets([
        "**Preconditions:** the script stops with a message if no database is selected, if migration 004 is not recorded, or if a "
        "different `inquiries` table already exists.",
        "**Verification and record:** after creating the table it checks that `fk_inquiries_user` references `users` with the "
        "delete rule SET NULL, and records version `005` in `schema_migrations`.",
        "**Rollback:** `005_inquiries.down.sql` drops the table – and with it every stored inquiry – and removes the `005` record.",
        "**Live database:** according to `database/README.md`, migration 005 was applied to the live database on 31 Oct 2026 after "
        "a verified backup; the read-only check `--verify-live` passed 4 / 4.",
        "**Why PHP validation still matters:** the database README notes that XAMPP runs MariaDB without strict mode, so values "
        "that break no CHECK (for example a too-long text) would be silently adjusted; PHP therefore checks every length first.",
    ])

    # ------------------------------------------------------------------ 7
    r.heading("7. Validation and Security")
    r.heading("7.1 CSRF token (advanced extension)", 2)
    r.para("The portal creates one random token per session (`bin2hex(random_bytes(32))`, renewed at login), puts it into every POST "
           "form with `csrf_field()` and compares it with `hash_equals()`. A POST without a valid token is stopped with HTTP 403 and "
           "written to the audit log as `CSRF_REJECTED` with the status `SECURITY_BLOCK`; nothing is stored.")
    r.excerpt("studenthub/includes/auth.php", "function csrf_is_valid", "studenthub_fail(403",
              "CSRF token check (the token is created by csrf_token(), lines 82–88)")
    r.heading("7.2 Other measures", 2)
    r.bullets([
        "**Escaping on output:** `e()` is `htmlspecialchars()` with `ENT_QUOTES | ENT_SUBSTITUTE` and UTF-8. It is used for the "
        "values shown again in the form, for the success message and for every cell of the Admin Console. Tested with `<b>Bold</b>` "
        "as a name and a stored message containing `<script>alert(1)</script>`: both appear as text.",
        "**SQL injection:** all queries with user input use prepared statements; `inquiry_counts()` runs a fixed query without "
        "input.",
        "**Honeypot:** the hidden `website` field is invisible to people; a simple bot that fills every field is refused with HTTP "
        "422 and nothing is stored.",
        "**Type and encoding checks:** arrays and invalid UTF-8 are refused in every field.",
        "**Access control:** the Admin Console requires `admin.console`, the resolve action `inquiries.manage` (both administrators "
        "only); a GET request with `action=resolve_inquiry` changes nothing; students and editors receive HTTP 403.",
        "**Audit and privacy:** a stored inquiry writes `SUBMIT_INQUIRY` (details: “Inquiry #… stored (topic: …)”) and resolving writes "
        "`RESOLVE_INQUIRY`. The audit entry does not contain the message text. The `inquiries` table stores no IP address; like "
        "every audit entry of the portal, the audit row records the IP address and browser string.",
        "**Post/Redirect/Get:** the success message is stored in the session, shown once after the 303 redirect, and a page "
        "refresh cannot repeat the submission.",
    ])
    r.heading("7.3 Accessibility of the form", 2)
    r.para("Every control has a visible label (`for`/`id`), and the fields are grouped in a `fieldset` with the screen-reader legend "
           "“Inquiry Form”. Invalid fields get `aria-invalid=\"true\"` and `aria-describedby` pointing to their message; the general "
           "error box has `role=\"alert\"` and the success box `role=\"status\"`. The honeypot is hidden from screen readers and from "
           "keyboard navigation.")

    # ------------------------------------------------------------------ 8
    r.heading("8. Output Screenshots")
    r.para("All screenshots are genuine full-page captures in Microsoft Edge (headless, driven by Playwright, viewport 1280 px wide), "
           "made by `tests/browser_forms.py` on 31 October 2026 against the PHP built-in server and a disposable database. The "
           "senders “Neha Rao” (visitor) and “Riya Shah” (student account `riya_shah`) and the administrator `portal_admin` are "
           "fictional test data.")
    r.figure(SHOTS + "08-contact-validation.png",
             "Server-side validation: a visitor submitted name Neha Rao, enrollment number CS-2025, e-mail neha.rao@ and the message "
             "“Help”. The page shows “Please correct the highlighted fields. Your inquiry was not sent.” and a message under the "
             "enrollment number, the e-mail and the message; all entered values are kept. The test confirmed that nothing was stored.", width=FIG_W)
    r.figure(SHOTS + "09-contact-success.png",
             "After correcting the e-mail, leaving the enrollment number empty, choosing the topic Portal access and writing a longer "
             "message: following the 303 redirect the page shows “Thank you, Neha Rao. Your inquiry has been received by the A7 CSE "
             "helpdesk (reference #1).” and an empty form.", width=FIG_W)
    r.figure(SHOTS + "10-admin-inquiries.png",
             "Admin Console, Inquiries tab (badge 2, “2 new, 2 in total”), newest first: #2 from the signed-in student Riya Shah "
             "(riya_shah@example.com · 26IT041, badge “account: riya_shah”, topic Events) and #1 from the visitor Neha Rao (topic "
             "Portal access); both have the status New and a Resolved button.", width=FIG_W)
    r.figure(SHOTS + "11-inquiry-resolved.png",
             "After clicking Resolved for #1: the message “Inquiry #1 was marked as resolved.”, the tab badge shows 1 (“1 new, 2 in "
             "total”), and row #1 shows the status Resolved with the time 2026-10-31 03:20:43 instead of the button.", width=FIG_W)

    # ------------------------------------------------------------------ 9
    r.heading("9. Testing and Results")
    r.para("Environment of the recorded runs (31 October 2026): Windows 11, PHP 8.2.12 (XAMPP) built-in server on 127.0.0.1, MariaDB "
           "10.4.32, Microsoft Edge in headless mode through Playwright. All suites work on disposable databases; `test_forms.py` "
           "confirms at the end that the live `studenthub_db` was not touched, and the migration test reads the live database only "
           "with `--verify-live`. The complete run of all suites (`tests/run_all_output.txt`) passed 841 checks with 0 failures.")
    r.table([
        ["Suite", "Scope", "Result", "Output file"],
        ["`tests/test_forms.py`", "HTTP tests of Practicals 5–7; 19 checks of the contact form and 9 of the Admin Console Inquiries "
                                  "tab concern Practical 7", "**41 / 41 passed**", "`tests/test_forms_output.txt`"],
        ["`tests/browser_forms.py`", "Microsoft Edge checks and screenshots; 4 checks concern Practical 7, two more cover the whole "
                                     "run (no unexpected JavaScript errors, no PHP warnings)", "**15 / 15 passed**",
         "`tests/browser_forms_output.txt`"],
        ["`database/tests/test_005_inquiries.py` (fixture)", "Migration 005 on a fixture with migrations 001–004",
         "**14 / 14 passed**", "`database/tests/test_005_output.txt`"],
        ["`test_005_inquiries.py --source-dump`", "Migration 005 on a real dump in a disposable database (result recorded in "
                                                  "`TEST_REPORT.md` section 12)", "**14 / 14 passed**", "–"],
        ["`test_005_inquiries.py --verify-live`", "Read-only comparison of the live database with the baseline upgraded with 005",
         "**4 / 4 passed**", "`database/tests/test_005_verify_live_output.txt`"],
    ], [4.2, 6.4, 2.4, 3.0])
    r.para("Key checks, summarised from the saved outputs (all PASS):")
    r.bullets([
        "**Form and storage:** contact.php is public with a CSRF token, a topic list and a hidden honeypot field; a valid visitor "
        "inquiry -> 303 back to the form, stored with the e-mail in lower case, the enrollment number in upper case, status new and "
        "no account; the success message names the reference number once; SUBMIT_INQUIRY audit entry without the message text.",
        "**Refused input (HTTP 422 with the matching message):** empty name, name with digits, invalid e-mail, wrong enrollment "
        "format, unknown topic, message under 10 or over 2000 characters, field sent as an array, honeypot filled in; rejected input "
        "is shown again HTML-escaped; nothing was stored; without the CSRF token -> 403, nothing stored.",
        "**Signed-in student and concurrency:** fields prefilled from the linked record and the inquiry linked to the account "
        "(user_id); 8 simultaneous inquiries -> all 8 stored with different reference numbers.",
        "**Admin Console:** newest first with a 'new' badge count; messages HTML-escaped; CSRF token in every POST form; GET or a POST "
        "without token changes nothing (403); mark as resolved stores the time and a RESOLVE_INQUIRY entry; resolving again -> error "
        "message; filter 'Resolved' works; student and editor -> 403.",
        "**Migration 005:** only the new table changes; FK ON DELETE SET NULL; existing rows unchanged; repeatable; CHECK refuses a "
        "short message; deleting an account keeps its inquiry; rollback and re-apply; precondition stop; fresh install identical.",
        "**Edge:** the four steps of Figures 1–4 and no JavaScript errors other than the intended 422 response (the browser's "
        "automatic `/favicon.ico` request got 404 – a known, pre-existing item: the portal has no favicon).",
    ])
    r.heading("9.1 Not tested", 2)
    r.bullets([
        "Running the portal under Apache (all recorded runs used PHP's built-in server).",
        "Screen readers, a physical keyboard, browsers other than Edge and narrow (mobile) widths.",
        "A database failure while an inquiry is being stored.",
    ])

    # ------------------------------------------------------------------ 10
    r.heading("10. Differences from the Original Standalone Practical and Limitations")
    r.table([
        ["Aspect", "Standalone Practical-7 (original report)", "Integrated portal"],
        ["Application", "`index.php` (form + processing) and `records.php`; PHP built-in server on port 8607 with `router.php`",
         "`studenthub/contact.php` in the portal, plus the Admin Console tab"],
        ["Fields", "full name, e-mail, category (5), message 10–1000 characters",
         "name, optional enrollment number, e-mail, topic (5), message 10–2000 characters"],
        ["Storage", "`private/submissions.json` under `flock(LOCK_EX)`; IDs SUB-0001, SUB-0002, …; damaged files backed up",
         "table `inquiries` (migration 005); ids #1, #2, …; prepared INSERT; ENUM, CHECK and foreign key"],
        ["Display of stored records", "`records.php`, a local demonstration page for everyone",
         "Admin Console *Inquiries* tab, administrators only, with a filter and “mark as resolved”"],
        ["CSRF", "own token, renewed after every successful submission; HTTP 400 on failure",
         "the portal's session token (renewed at login); HTTP 403 and an audit entry on failure"],
        ["Bot protection", "none", "honeypot field `website`"],
        ["Signed-in users", "– (no login)", "fields prefilled from the student record; inquiry linked to the account"],
        ["Tests", "63 / 63 checks (`tests/test_form.py`)", "19 + 9 HTTP checks, 4 Edge checks, migration tests 14 / 14, 14 / 14, "
                                                             "4 / 4"],
    ], [3.0, 6.3, 6.7])
    r.heading("10.1 Limitations", 2)
    r.bullets([
        "**Storage format:** the inquiries are stored in a database table, not in a CSV or JSON file as the problem definition "
        "asks; the file-based version remains in `Practical-7/`.",
        "**No e-mail:** the portal sends no e-mail – `DEPLOYMENT.md` states that inquiry answers are not implemented. The helpdesk "
        "can only mark an inquiry as resolved.",
        "**No delete or reopen:** the console offers only “mark as resolved”; it lists at most the newest 100 inquiries.",
        "**Simple bot protection:** the honeypot stops only simple bots; there is no limit on the number of inquiries per sender.",
        "**No client-side checks:** the contact page has HTML5 attributes but `novalidate` and no validation script, so errors are "
        "shown only after the page has been sent to the server.",
        "**Rollback:** undoing migration 005 deletes every stored inquiry; export them first if they are needed.",
    ])

    # ------------------------------------------------------------------ 11
    r.heading("11. Conclusion")
    r.para("The StudentHub Help & Contact form is now processed entirely by PHP inside the integrated portal. Data is sent with POST "
           "and a CSRF token, sanitised and validated on the server, and every valid inquiry is stored in the `inquiries` table of "
           "`studenthub_db` with a prepared statement – 8 simultaneous inquiries were all stored with distinct reference numbers. "
           "Senders see a success message with the reference number after a 303 redirect, or a general message and field-level "
           "messages with their input kept; every displayed value is escaped, and a honeypot field refuses simple bots.")
    r.para("Both extensions are integrated: the stored records are displayed in the Admin Console's Inquiries tab, where "
           "administrators filter them and mark them as resolved (intermediate), and CSRF protection guards both the form and the "
           "resolve action (advanced). The integration passed the HTTP suite (41 / 41), the Edge suite (15 / 15) and the migration "
           "tests (14 / 14, 14 / 14 and 4 / 4). The one deliberate deviation from the problem definition – database storage instead "
           "of a CSV/JSON file – is explained in Section 2 and Section 10.")

    # ------------------------------------------------------------------ 12
    r.heading("12. References")
    r.bullets([
        "ITUE203 Web Development Frameworks – Practical List 2026-27, Practical 7: “PHP Form Processing with Server-Side Validation "
        "and CSV/JSON File Storage”, CSPIT, CHARUSAT.",
        "StudentHub repository: https://github.com/TheEmperor08/StudentHub-ITUE203-25CS023 – folders `studenthub/` (portal), "
        "`database/` (migration 005 and its tests), `Practical-7/` (original standalone version), `tests/`, "
        "`evidence/practical-05-07-integration/`; `TEST_REPORT.md` section 12; `database/README.md`.",
        "PHP Manual – Dealing with forms: https://www.php.net/manual/en/tutorial.forms.php",
        "PHP Manual – filter_var and validate filters: https://www.php.net/manual/en/filter.filters.validate.php",
        "PHP Manual – htmlspecialchars: https://www.php.net/manual/en/function.htmlspecialchars.php",
        "PHP Manual – mysqli prepared statements: https://www.php.net/manual/en/mysqli.quickstart.prepared-statements.php",
        "MariaDB Knowledge Base – CONSTRAINT (CHECK and FOREIGN KEY): https://mariadb.com/kb/en/constraint/",
        "OWASP Cheat Sheet – Cross-Site Request Forgery Prevention: "
        "https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html",
    ])
