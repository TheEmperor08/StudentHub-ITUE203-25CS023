<div align="center">
  <h1>🎓 Practical 12</h1>
  <h3>Event Management CRUD with Poster Upload and File Validation (PHP + MySQLi + Bootstrap 5)</h3>
</div>

---

### 👨‍🎓 Student Information
- **Name:** Shreyas
- **ID:** 25CS023
- **Course:** ITUE203 - WEB DEVELOPMENT FRAMEWORKS
- **Year:** 2026-27

---

### 🎯 Aim and Objectives
> Build an event management module for administrators: add, view, update and delete events, upload an event poster with genuine server-side validation of file type and size, show success and failure messages, filter events by category and Open/Closed status, and restrict everything to logged-in administrators. Every database operation uses **MySQLi prepared statements**.

**Problem definition:** a file-upload form is one of the most dangerous parts of a web application. A careless poster upload trusts the file name or the browser's `accept` attribute and lets an attacker upload a PHP script, an SVG with JavaScript or a huge file – or delete other files through a crafted name. This module accepts only real JPEG, PNG and WebP images up to 2 MB, stores them under random names in a folder that cannot be opened or executed over HTTP, and never deletes or replaces a poster before the database change has succeeded.

---

### 🛠️ Technologies
PHP 8.2.12 (XAMPP) with **MySQLi** and **Fileinfo**, MariaDB 10.4.32 (XAMPP's MySQL server), **Bootstrap 5.3.3** (stored locally in `assets/vendor/`, no CDN), HTML5, CSS3, a few lines of JavaScript (poster preview only), Microsoft Edge (screenshots), Python 3 (test scripts only).

---

### 🚀 How to Run (Windows + XAMPP)
1. **Start** MySQL (and Apache if you want phpMyAdmin) in the **XAMPP Control Panel**.
2. **Import the database:** open **http://localhost/phpmyadmin** → **Import** → **Choose File** → `Practical-12\studenthub_prac12.sql` → **Import**. The left panel then shows **studenthub_prac12** with the tables `admins`, `event_categories` and `events` (12 events).
   *Command line alternative* (in the `Practical-12` folder): `C:\xampp\mysql\bin\mysql.exe -u root < studenthub_prac12.sql`
3. **Set the demo administrator's password** (no password is stored in the repository). In Command Prompt inside the `Practical-12` folder run the command below and type a password of 8–72 characters when asked; it is saved only as a `password_hash()` hash:
   ```bat
   C:\xampp\php\php.exe tools\set_admin_password.php admin.demo@example.com
   ```
4. **Start the site:** double-click **`start-server.bat`** (opens **http://127.0.0.1:8612/login.php**), or run this in the `Practical-12` folder:
   ```bat
   C:\xampp\php\php.exe -S 127.0.0.1:8612 router.php
   ```
5. **Log in** at **http://127.0.0.1:8612/login.php** with `admin.demo@example.com` and the password from step 3.

*XAMPP Apache alternative (not tested):* copy the folder to `C:\xampp\htdocs\practical12` and open http://localhost/practical12/. The `.htaccess` files block the private files and the upload folder.

**Configuration:** `db.php` uses XAMPP's defaults (`127.0.0.1:3306`, user `root`, empty password, database `studenthub_prac12`), stores posters in `uploads/` and ends a session after **30 minutes** without activity. To change these, copy `config.example.php` to `config.local.php` (ignored by Git) and edit the values (`host`, `port`, `name`, `user`, `pass`, `upload_dir`, `session_timeout`).

---

### 🗄️ Database (`studenthub_prac12`, exported in `studenthub_prac12.sql`)
**`events`** (InnoDB, utf8mb4)

| Column | Type | Notes |
|---|---|---|
| `event_id` | INT UNSIGNED AUTO_INCREMENT | primary key |
| `event_title` | VARCHAR(150) | CHECK at least 3 characters |
| `description` | TEXT | |
| `category` | VARCHAR(40) | **foreign key** → `event_categories.category_name`; index |
| `event_date`, `event_time` | DATE, TIME | composite index `idx_events_date` |
| `venue` | VARCHAR(150) | |
| `poster_filename` | VARCHAR(64) | **UNIQUE** (two events can never share a file); CHECK `^[a-f0-9]{32}[.](jpg\|png\|webp)$` – only safe generated names |
| `status` | ENUM('open','closed') DEFAULT 'open' | index |
| `created_at`, `updated_at` | DATETIME | `updated_at` changes on every update |

**`event_categories`** (`category_name` PK, `description`) – Cultural, Hackathon, Seminar, Sports, Technical, Workshop.
**`admins`** (`admin_id`, `full_name`, `email` UNIQUE, `password_hash` with CHECK `$2y$…`/`$argon2…`, `created_at`, `last_login_at`) – one fictional account, `admin.demo@example.com`.

Seed data: **12 fictional events (8 open, 4 closed)**, two per category, each with a poster in `uploads/` (JPEG, PNG and WebP). The database is separate from all other practicals; importing the dump again resets it.

---

### 🖼️ Poster Upload Rules
Allowed: **JPEG, PNG and WebP images, at most 2 MB** (and at most 6000 × 6000 px). A poster is required when adding an event and optional when editing (empty = keep the current poster). The checks in `includes/upload.php` all run on the server:

1. PHP upload error code (partial upload, server limit, missing temp folder…)
2. `is_uploaded_file()`
3. size 1 byte – 2 MB
4. extension `.jpg`, `.jpeg`, `.png` or `.webp`
5. **Fileinfo** MIME type of the content must be `image/jpeg`, `image/png` or `image/webp` **and match the extension**
6. `getimagesize` must read an image of the same type with valid dimensions
7. complete file structure (PNG chunks + CRC up to IEND, JPEG end marker, WebP RIFF length) – rejects truncated/damaged files
8. no PHP code (`<?php`) inside the file

Rejected examples: `.gif`, `.svg`, `.php`, `.exe`, a PHP script renamed to `.jpg`, PNG content named `.jpg`, damaged or truncated images, a JPEG with embedded PHP code, files over 2 MB.

**Storage:** the original file name is never used. An accepted file gets a random name of 32 hexadecimal characters plus the extension of its detected type (e.g. `1a023e38c1e411c26656d6a75e9ede04.jpg`), and only this name is stored in MySQL. The `uploads/` folder is **not reachable over HTTP** (router + `uploads/.htaccess`: `Require all denied`, PHP engine off, script handlers removed); posters are delivered only by `poster.php`, to logged-in administrators, after the name has passed the strict pattern – so path traversal (`../db.php`) is impossible and nothing in the folder can ever run.

**Replacing and deleting:** a replacement poster is validated and stored first, then the event is updated, and only then is the old file deleted. If the update fails, the new file is removed and the old poster stays. Deleting an event removes its row first and then its poster file. Files are deleted only through `delete_poster_file()`, which accepts nothing but a valid poster name inside `uploads/` that no event uses any more. `tools\cleanup_orphan_posters.php` lists (or with `--delete` removes) abandoned poster files older than one hour.

---

### 🔧 Using the Application (Event CRUD)
| Action | How |
|---|---|
| **Log in** | `login.php` – email + password (`password_verify()`); session ID regenerated after login |
| **View** | `index.php` – table with poster thumbnails, title, category, date & time, venue and Open/Closed badge; *View* opens `view.php` with the full-size poster |
| **Filter** | choose a **Category** and/or **Status** (Open / Closed) and press *Filter*; *Reset* shows all events |
| **Add** | *+ Add event* → fill in title, description, category, date, time, venue, status and choose a poster → *Add event* |
| **Edit** | *Edit* → change any field; choose a new poster only if it should be replaced → *Save changes* |
| **Delete** | *Delete* → confirmation page *“Are you sure you want to delete …?”* → *Yes, delete event* (event and poster file are removed) |
| **Log out** | *Log out* button (POST with CSRF token) |

Every action shows a green success or a red error message. Pages that are opened without logging in answer with **HTTP 401 “Access denied”** and show no data.

---

### 🔐 Security
- **SQL injection:** MySQLi prepared statements for every query (no `query()` in the code); filter values accepted only from fixed lists.
- **XSS:** `htmlspecialchars()` on every output; Content-Security-Policy (`default-src 'self'`), `X-Frame-Options: DENY`, `nosniff`.
- **CSRF:** a random session token in every form; add, edit, delete and logout are POST-only and refuse a missing or wrong token.
- **Sessions:** cookie `P12SESSID` HttpOnly + SameSite=Strict + strict mode, `session_regenerate_id(true)` at login, 30-minute inactivity timeout, logout clears the data, the cookie and the server session; `Cache-Control: no-store`.
- **Login:** same message for every failure (*“Invalid email or password.”*); an unknown email is checked against a dummy hash too.
- **Errors:** MySQL errors are logged; the user only sees *“The event database is not available right now.”*
- **Private files:** `db.php`, `includes/`, `tools/`, `tests/`, `uploads/`, the SQL dump, documents and config files answer HTTP 403. Local credentials belong in the git-ignored `config.local.php`.

---

### 🧪 Testing
With MySQL running, in the `Practical-12` folder: **`python tests\test_app.py`**
It creates the disposable database `studenthub_prac12_test` from the dump and a temporary upload folder, sets a random admin password, starts three PHP servers (normal; 2-second timeout with small upload limits; MySQL unreachable) and removes everything again. `studenthub_prac12` and `uploads/` are not changed. Full output: [`tests/test_output.txt`](tests/test_output.txt); test cases: [`tests/TEST_CASES.md`](tests/TEST_CASES.md).

**Result: 153 of 153 automated checks passed** (PHP 8.2.12, MariaDB 10.4.32, Windows 11). `php -l` found no syntax errors in the 15 PHP files.

| Area | Checks | Result |
|---|---|---|
| Static (`php -l`, prepared statements only, upload code, `uploads/.htaccess`, password tool) | 7 | pass |
| Database (12 events 8/4, 6 categories, InnoDB, indexes, FK, UNIQUE + CHECK on poster names, hashed password) | 10 | pass |
| Login, failed logins, 401 for every protected page, session ID regeneration, cookie flags | 18 | pass |
| Event list and poster delivery | 6 | pass |
| Path traversal (`../db.php`, encoded, absolute paths) and upload-folder protection (403, no PHP execution) | 17 | pass |
| Create with valid JPEG / PNG / WebP, random names, highlight | 9 | pass |
| Field validation | 4 | pass |
| Rejected posters: wrong extension, PHP, SVG, EXE, MIME mismatch, corrupted/truncated images, embedded PHP, > 2 MB, > 6000 px, empty; exactly 2 MB accepted | 19 | pass |
| Failed INSERT leaves no abandoned file | 2 | pass |
| Update, keep / replace poster, rejected replacement keeps the old poster, failed UPDATE keeps the old poster | 10 | pass |
| Delete with confirmation, CSRF, poster file removed, nothing else deleted | 6 | pass |
| Category and Open/Closed filters (alone, combined, invalid values, injection) | 8 | pass |
| XSS, SQL injection, CSRF | 7 | pass |
| Protected files → 403 | 11 | pass |
| Logout (GET / wrong token ignored, session destroyed) | 5 | pass |
| Server log (no warnings; forced failures logged) | 2 | pass |
| Session timeout and server upload limits | 5 | pass |
| Clean-up tool | 3 | pass |
| MySQL unreachable, real `uploads/` unchanged, test data removed | 4 | pass |

**Browser test:** `tests/browser_screenshots.py` drove **Microsoft Edge** (headless, Playwright) through the real application on `studenthub_prac12` – **13 of 13 browser checks passed** ([`tests/browser_output.txt`](tests/browser_output.txt)). It changes data, so the dump was re-imported and `uploads/` restored afterwards.

---

### 📸 Screenshots and Report
`screenshots/` contains 13 genuine captures of the running application (fictional data): `admin-login.png`, `events-list.png`, `add-event-form.png`, `successful-event-add.png`, `event-poster-preview.png`, `edit-event-form.png`, `successful-event-update.png`, `invalid-file-type.png`, `file-size-rejection.png`, `delete-confirmation.png`, `successful-event-delete.png`, `category-status-filter.png`, `unauthorized-access-denied.png`.

Report: `PRAC_12_ITUE203_25CS023.docx` and `PRAC_12_ITUE203_25CS023.pdf`. SQL dump: `studenthub_prac12.sql`.

---

### 📂 Project Structure
```text
Practical-12/
├── login.php, logout.php                     # administrator authentication
├── index.php, view.php, add.php, edit.php, delete.php, poster.php
├── db.php, includes/functions.php, includes/upload.php
├── assets/app.css, assets/app.js, assets/favicon.svg, assets/vendor/bootstrap.min.css
├── uploads/                                  # 12 seed posters + .htaccess (not reachable over HTTP)
├── tools/set_admin_password.php, tools/cleanup_orphan_posters.php
├── studenthub_prac12.sql                     # SQL dump: 3 tables + seed data
├── config.example.php, router.php, start-server.bat, .htaccess, .gitignore, .gitattributes
├── tests/test_app.py, test_output.txt, TEST_CASES.md, browser_screenshots.py, browser_output.txt, fixtures/
├── screenshots/                              # 13 PNG files
└── PRAC_12_ITUE203_25CS023.docx / .pdf
```

---

### ⚠️ Limitations
- No limit on login attempts (brute force is not slowed down) and no administrator management in the interface (accounts are added in MySQL, passwords set with the tool).
- The GD extension is not enabled in this XAMPP installation, so posters are validated but not re-encoded; the structure check and the non-executable, non-public upload folder cover this.
- Tested with the PHP built-in server, MariaDB 10.4 and Microsoft Edge; XAMPP Apache (the `.htaccess` rules), MySQL 8 and other browsers were not tested.
