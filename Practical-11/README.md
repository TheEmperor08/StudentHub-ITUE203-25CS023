<div align="center">
  <h1>🎓 Practical 11</h1>
  <h3>Student Management CRUD Application with Search, Course Filter, Soft Delete and CSV Export (PHP + MySQLi)</h3>
</div>

---

### 👨‍🎓 Student Information
- **Name:** Shreyas
- **ID:** 25CS023
- **Course:** ITUE203 - WEB DEVELOPMENT FRAMEWORKS
- **Year:** 2026-27

---

### 🎯 Aim and Objectives
> Build a Student Management application in PHP and MySQL that lists student records in a table, adds and updates students with validation, searches by name, email and course, filters by course, **soft-deletes** students after a confirmation (status changes to `inactive`, the record is kept), shows success and error messages, and exports the records to a CSV file that opens correctly in Microsoft Excel. Every database operation uses **MySQLi prepared statements**.

**Problem definition:** an institute keeps student records that must be easy to find and maintain, but records must never be lost by accident. Deleting a student therefore only marks the record *inactive* (soft delete), every change must be validated on the server, and the list must be exportable for spreadsheet work without opening a door to SQL injection, XSS, CSRF or CSV formula injection.

---

### 🛠️ Technologies
PHP 8.2.12 (XAMPP) with **MySQLi**, MariaDB 10.4.32 (XAMPP's MySQL server), HTML5, CSS3, a few lines of JavaScript (optional double-click guard), Microsoft Edge and Microsoft Excel (screenshots), Python 3 (test scripts only).

---

### 🚀 How to Run (Windows + XAMPP)
1. **Start** MySQL (and Apache if you use phpMyAdmin) in the **XAMPP Control Panel**.
2. **Import the database:** open **http://localhost/phpmyadmin** → **Import** → **Choose File** → `Practical-11\studenthub_prac11.sql` → **Import**. The left panel then shows **studenthub_prac11** with the table `students` (24 records).
   *Command line alternative:* `C:\xampp\mysql\bin\mysql.exe -u root < studenthub_prac11.sql`
3. **Start the site:** double-click **`start-server.bat`** (opens **http://127.0.0.1:8611/index.php**), or run `C:\xampp\php\php.exe -S 127.0.0.1:8611 router.php` in the folder.
   *XAMPP Apache alternative (not tested):* copy the folder to `C:\xampp\htdocs\practical11` and open http://localhost/practical11/.

**Settings:** `db.php` uses XAMPP's defaults (`127.0.0.1:3306`, user `root`, empty password, database `studenthub_prac11`). To change them, copy `config.example.php` to `config.local.php` (ignored by Git) and edit the values. No password is stored in the repository.

---

### 🗄️ Database (`studenthub_prac11`, exported in `studenthub_prac11.sql`)
| Column | Type | Notes |
|---|---|---|
| `student_id` | INT UNSIGNED AUTO_INCREMENT | primary key |
| `full_name` | VARCHAR(100) | index `idx_students_full_name` |
| `email` | VARCHAR(254) | **UNIQUE** key `uq_students_email` (case-insensitive collation) |
| `course` | VARCHAR(60) | index `idx_students_course`; one of 5 courses checked by the application |
| `semester` | TINYINT UNSIGNED | CHECK 1–8 |
| `status` | ENUM('active','inactive') DEFAULT 'active' | index `idx_students_status` |
| `created_at` | DATETIME | set when the record is added |
| `updated_at` | DATETIME | changes automatically on every UPDATE |
| `deleted_at` | DATETIME NULL | time of the soft delete; CHECK: `NULL` exactly when status is `active` |

InnoDB, `utf8mb4_unicode_ci`. **24 fictional seed students** (example.com): **22 active, 2 inactive**. One table is enough for this practical, so there are no foreign keys. The dump was exported with `mysqldump`; it creates only `studenthub_prac11`, and importing it again resets the `students` table to the 24 seed records.

---

### 🔧 How It Works
| File | Purpose |
|---|---|
| `index.php` | **READ** – student table, search, course and status filters, pagination (10 per page), messages, Export button |
| `add.php` | **CREATE** – form + server-side validation, duplicate-email check, prepared `INSERT` |
| `edit.php` | **UPDATE** – form filled from MySQL, validation, prepared `UPDATE` |
| `delete.php` | **SOFT DELETE** – GET shows a confirmation page; the confirmed POST runs `UPDATE … SET status='inactive', deleted_at=NOW()` |
| `export.php` | **CSV export** of every record matching the current search/filters |
| `includes/functions.php` | session, security headers, form tokens, messages, validation, the search/filter query, layout |
| `db.php` | settings and the MySQLi connection; errors are logged, never shown |
| `style.css`, `app.js`, `favicon.svg` | responsive layout (the table turns into cards on phones); double-click guard |
| `router.php`, `.htaccess`, `start-server.bat`, `config.example.php`, `.gitignore` | server setup; block `includes/`, `tests/`, the SQL dump and config files (HTTP 403) |

- **Soft delete (no permanent deletion):** the *Deactivate* button opens `delete.php?id=N`, which only shows the student and the question *"Are you sure you want to deactivate …?"*. Nothing changes until **Yes, deactivate student** is pressed (a POST with a form token). The record stays in the table with status **Inactive** and the time in `deleted_at`; the list shows a red *Inactive* badge and greys the row. The application contains no `DELETE` statement. Inactive students keep their email reserved and can still be edited.
- **Search and filter:** one search box matches **name, email and course** with `LIKE ?` (the user's `%` and `_` are escaped and searched literally); the course and status drop-downs only accept values from fixed lists. Search, filters and pagination work together, and the page links keep the filters.
- **Validation:** the form uses HTML5 rules (`required`, `type="email"`, `pattern`, `maxlength`) for early warnings, but only the server check counts: name 2–100 letters (spaces, `.`, `'`, `-` allowed), valid email (stored in lower case), course from the list, semester 1–8, email not used by another student. Errors appear under each field and the typed values are kept.
- **Messages:** after every add, update and soft delete the browser is redirected to the list (Post/Redirect/Get) and a green message names the student; the changed row is shown first and highlighted. Errors are shown in red. Messages are created by the server and kept in the session – no text from the address bar is displayed.
- **CSV export:** `export.php` exports all matching records (all pages) with the columns *Student ID, Full Name, Email, Course, Semester, Status, Created At, Updated At, Deactivated At*. **Inactive records are included** (Status *Inactive* and a *Deactivated At* time) unless the status filter is set to *Active*. The file is UTF-8 with a byte-order mark, comma-separated with CRLF line endings, so Excel opens it directly. **Formula injection:** any cell that starts with `=`, `+`, `-`, `@`, tab or carriage return gets a leading apostrophe, so Excel shows it as text.
- **Security:** MySQLi prepared statements for every query (no `query()`); `htmlspecialchars()` on every output; each form carries a random **one-time token** stored in the session, which works as CSRF protection and stops the same form from being submitted twice; add, update and soft delete accept only POST; MySQL errors go to the PHP error log and the user sees *"The student database is not available right now"*; Content-Security-Policy, `X-Frame-Options: DENY`, `nosniff`, HttpOnly + SameSite=Strict session cookie.

---

### 🧪 Testing
With MySQL running, in the `Practical-11` folder: `python tests\test_app.py`
It creates the disposable database `studenthub_prac11_test` from `studenthub_prac11.sql`, starts two PHP servers (normal, and with MySQL unreachable), runs the checks over HTTP and removes the test database again. `studenthub_prac11` and all other databases are not changed. Full output: [`tests/test_output.txt`](tests/test_output.txt); test cases: [`tests/TEST_CASES.md`](tests/TEST_CASES.md).

**Result: 106 of 106 automated checks passed** (PHP 8.2.12, MariaDB 10.4.32, Windows 11). `php -l` found no syntax errors in any of the 9 PHP files.

| Area | Checks | Result |
|---|---|---|
| Static: `php -l`, prepared statements only, no `DELETE FROM` | 4 | pass |
| Database: 24 seed rows (22/2), InnoDB, indexes, UNIQUE email, CHECK constraints | 8 | pass |
| Connection, student list, badges, security headers, cookie flags | 6 | pass |
| Pagination (3 pages, clamping, filter kept in links) | 6 | pass |
| Add student, success message, highlighted row | 5 | pass |
| Validation: empty fields, invalid email, duplicate email, tampered values | 9 | pass |
| Update student and its errors | 7 | pass |
| Soft delete: confirmation, status → inactive, record kept, already inactive | 9 | pass |
| Search by name / email / course, course filter, combined filters | 10 | pass |
| CSV export: headers, BOM, CRLF, columns, filters, inactive rows, formula injection | 9 | pass |
| CSRF and duplicate submissions | 7 | pass |
| SQL injection | 7 | pass |
| XSS output escaping | 5 | pass |
| Protected files → 403; no PHP warnings in the log | 10 | pass |
| MySQL unreachable → general message only, details in the log; test DB removed | 4 | pass |

**Browser test:** `tests/browser_screenshots.py` drove Microsoft Edge (headless, Playwright) through the real application on `studenthub_prac11` – **13 of 13 browser checks passed** (including: the browser blocks an empty form, no JavaScript errors). It changes data, so the dump was re-imported afterwards.

**Screenshots** (`screenshots/`, genuine captures of the running application, fictional data): `students-list.png`, `add-student.png`, `successful-add.png`, `edit-student.png`, `successful-update.png`, `search-result.png`, `course-filter.png`, `delete-confirmation.png`, `successful-soft-delete.png`, `success-message.png`, `error-message.png`, `csv-export.png`, `csv-opened-in-excel.png`. Screenshots 1–11 come from the browser test. `csv-export.png` is a normal Edge window after clicking *Export CSV* (Edge's Downloads panel shows the file), and `csv-opened-in-excel.png` shows that same downloaded file opened in Microsoft Excel (columns auto-fitted for readability; the file was closed without saving).

---

### 📂 Project Structure
```text
Practical-11/
├── index.php, add.php, edit.php, delete.php, export.php   # the application pages
├── db.php, includes/functions.php                          # connection and shared helpers
├── style.css, app.js, favicon.svg
├── studenthub_prac11.sql                                   # SQL dump: schema + 24 seed records
├── config.example.php, router.php, start-server.bat, .htaccess, .gitignore, .gitattributes
├── tests/test_app.py, tests/test_output.txt, tests/TEST_CASES.md, tests/browser_screenshots.py
├── screenshots/                                            # 13 PNG files
└── PRAC_11_ITUE203_25CS023.docx / .pdf
```

---

### ⚠️ Limitations
- No login: the application is meant for local lab use (login and roles were Practical 10). Anyone who can open the site can change records.
- A deactivated student cannot be reactivated from the interface (only with SQL); this keeps the practical focused on soft deletion.
- The list shows the most recently changed record first using `updated_at`, which has 1-second precision; two changes in the same second are ordered by ID.
- Tested with the PHP built-in server, MariaDB 10.4, Microsoft Edge and Microsoft Excel; XAMPP Apache, MySQL 8 and other browsers were not tested.
