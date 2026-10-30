# Practical 11 – Test Cases and Results

Environment: Windows 11, XAMPP PHP 8.2.12, MariaDB 10.4.32, Microsoft Edge, Microsoft Excel.
Automated suite: `python tests\test_app.py` → **106 passed, 0 failed** (full output in `test_output.txt`).
Browser run: `tests\browser_screenshots.py` (Edge via Playwright) → **13 passed, 0 failed**.
Syntax check: `php -l` on all 9 PHP files → no syntax errors.

The table lists the required test cases; each is covered by one or more of the 106 automated checks.

| ID | Test case | Steps / input | Expected result | Actual result |
|---|---|---|---|---|
| TC01 | Database connection | open `index.php` | page loads (HTTP 200) with data from `studenthub_prac11_test` | Pass |
| TC02 | Seed data | import `studenthub_prac11.sql` | 24 records, 22 active, 2 inactive; UNIQUE email and CHECK constraints work | Pass |
| TC03 | Student list display | open `index.php` | table with ID, name, email, course, semester, status badge, last updated, actions; "Showing 1–10 of 24 students" | Pass |
| TC04 | Successful addition | add *Neha Raval, Neha.Raval@Example.com, Information Technology, 3* | 303 → list, "Student “Neha Raval” was added successfully", row first and highlighted, email stored in lower case, status active | Pass |
| TC05 | Empty-field validation | submit the add form with all fields empty (and with spaces only) | HTTP 422, an error under each of the 4 fields, nothing inserted; in Edge the browser blocks the empty form | Pass |
| TC06 | Invalid email | email `not-an-email` | "Enter a valid email address…", typed values kept, nothing inserted | Pass |
| TC07 | Duplicate email | `DIYA.SHAH@example.com` (existing, other case); email of an inactive student | "This email is already registered to another student.", nothing inserted | Pass |
| TC08 | Tampered values | 1-letter name, course *Medicine*, semester 9 | all three refused by the server | Pass |
| TC09 | Successful update | edit ID 2 → Computer Science, semester 4 | "Student “Diya Shah” was updated successfully.", MySQL row changed, row first | Pass |
| TC10 | Update errors | another student's email; empty name; unknown ID 9999 | error messages, nothing saved; unknown ID → "That student record was not found." | Pass |
| TC11 | Soft-delete confirmation | click *Deactivate* for ID 15 | confirmation page "Are you sure you want to deactivate Rohan Verma?"; GET changes nothing | Pass |
| TC12 | Successful soft delete | press *Yes, deactivate student* | "…was deactivated. The record is kept in the database with status Inactive." | Pass |
| TC13 | Status changed to inactive | check MySQL and the list | `status='inactive'`, `deleted_at` set; red *Inactive* badge, no Deactivate button | Pass |
| TC14 | Inactive record remains | count rows before/after | row count unchanged; no `DELETE FROM` anywhere in the code | Pass |
| TC15 | Soft delete twice / unknown ID | deactivate ID 15 again; POST ID 999999 | "…is already inactive." / "record was not found", nothing changed | Pass |
| TC16 | Search by name | `q=Patel` | only Aarav Patel | Pass |
| TC17 | Search by email | `q=kiara.iyer@example` | only Kiara Iyer | Pass |
| TC18 | Search by course | `q=data science` | all Data Science students (case-insensitive) | Pass |
| TC19 | Search edge cases | `q=zzzz`, `q=%` | "No students found"; `%` searched literally | Pass |
| TC20 | Course filter | course = Information Technology; Electronics & Communication | only that course; `&` escaped as `&amp;` | Pass |
| TC21 | Combined filters | search + course + status | result equals the matching SQL count | Pass |
| TC22 | Pagination | pages 1, 2, 3; `page=99`; `page=abc`; `status=active` | 10 + 10 + 4 rows, each student once; out-of-range pages clamped; page links keep the filter | Pass |
| TC23 | Success and error messages | after add / update / soft delete / errors | green success or red error message; shown once only | Pass |
| TC24 | CSV export | click *Export CSV* | `text/csv` attachment `students_YYYYMMDD_HHMMSS.csv`, UTF-8 BOM, CRLF, header + one row per student, 9 columns | Pass |
| TC25 | CSV contents and filters | export with course/status filter and search text | only matching rows; inactive rows have Status *Inactive* and *Deactivated At* | Pass |
| TC26 | CSV formula injection | names `=HYPERLINK(…)`, `+1+1`, `-2+3`, email `@sum…` | exported as `'=HYPERLINK(…)`, `'+1+1`, … (text, not formulas) | Pass |
| TC27 | Excel compatibility | open the downloaded CSV in Microsoft Excel | 27 rows × 9 columns, readable, `&` and dates correct (`csv-opened-in-excel.png`) | Pass |
| TC28 | CSRF validation | POST without token, with a made-up token, with another session's token; delete/edit without token | refused with "The form could not be processed…", nothing changed | Pass |
| TC29 | Duplicate submission | send the same add form twice; replay a used delete token | first accepted, second refused (one record) | Pass |
| TC30 | SQL injection | `' OR '1'='1`, `UNION SELECT …` in search; injection in course, `id=1 OR 1=1`, `student_id=17 OR 1=1`; `Robert'); DROP TABLE students;--` | treated as text / refused; no extra rows, no change, table intact; `O'Brien` stored literally | Pass |
| TC31 | XSS output escaping | `<script>alert(1)</script>` in search; `<img src=x onerror=alert(1)>` stored as a name | shown escaped (`&lt;…&gt;`) in the list, edit form, confirmation page and re-shown form | Pass |
| TC32 | Raw database errors hidden | MySQL unreachable (port 1) | HTTP 503 "The student database is not available right now", no technical details; real error in the PHP log | Pass |
| TC33 | Protected files | open `db.php`, `includes/`, `tests/`, SQL dump, config, README, batch file | HTTP 403 | Pass |
