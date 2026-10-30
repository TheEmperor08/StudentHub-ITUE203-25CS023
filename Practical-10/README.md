<div align="center">
  <h1>🎓 Practical 10</h1>
  <h3>PHP Login System with Role-Based Access Control, Session Management and Secure Logout</h3>
</div>

---

### 👨‍🎓 Student Information
- **Name:** Shreyas
- **ID:** 25CS023
- **Course:** ITUE203 - WEB DEVELOPMENT FRAMEWORKS
- **Year:** 2026-27

---

### 🎯 Aim and Objectives
> Build a StudentHub login system in PHP and MySQL that checks passwords with `password_verify()`, protects the session against fixation, sends Admin and Student users to their own dashboards, refuses access to the other role's dashboard, ends inactive sessions automatically and logs out securely.

**Problem definition:** after registration (Practical 9) users must be able to log in safely. A login system must not reveal whether an email is registered, must not let a stolen pre-login session ID be reused, must decide access on the server (not by hiding links), must end forgotten sessions, and must make sure that a dashboard cannot be reopened after logout, not even with the Back button.

---

### 🛠️ Technologies
PHP 8.2.12 (XAMPP) with **MySQLi**, MariaDB 10.4.32 (XAMPP's MySQL server), phpMyAdmin 5.2.1, HTML5, CSS3, Microsoft Edge (screenshots), Python 3 (test script only). No JavaScript is needed.

---

### 🚀 How to Run (Windows + XAMPP)
1. **Start** Apache and MySQL in the **XAMPP Control Panel**.
2. **Import the database:** open **http://localhost/phpmyadmin** → **Import** tab → **Choose File** → `Practical-10\user_registration.sql` → **Import**. phpMyAdmin reports *"Import has been successfully finished"* and the left panel shows **studenthub_prac10** with the table `users`.
   *Command line alternative:* `C:\xampp\mysql\bin\mysql.exe -u root < user_registration.sql`
3. **Choose the demo passwords** (they are not stored in the repository). In Command Prompt inside the `Practical-10` folder, run each command and type a password of 8–72 characters when asked:
   ```bat
   C:\xampp\php\php.exe tools\set_password.php admin.demo@example.com
   C:\xampp\php\php.exe tools\set_password.php student.demo@example.com
   ```
   The password is saved only as a `password_hash()` hash.
4. **Start the site:** double-click **`start-server.bat`** (opens **http://127.0.0.1:8610/login.php**), or run `C:\xampp\php\php.exe -S 127.0.0.1:8610 router.php` in the folder.
   *XAMPP Apache alternative (not tested):* copy the folder to `C:\xampp\htdocs\practical10` and open http://localhost/practical10/login.php.

**Demo accounts (fictional):**

| Email | Role | Dashboard after login |
|---|---|---|
| `admin.demo@example.com` | Admin | `admin_dashboard.php` |
| `student.demo@example.com` | Student | `student_dashboard.php` |
| `student2.demo@example.com` | Student | `student_dashboard.php` |

**Settings:** `db.php` uses XAMPP's defaults (`127.0.0.1:3306`, user `root`, empty password, database `studenthub_prac10`) and an **inactivity timeout of 300 seconds (5 minutes)**. To change them, copy `config.example.php` to `config.local.php` (ignored by Git) and edit the values, e.g. `'session_timeout' => 600`.

---

### 🗄️ Database (`studenthub_prac10`, exported in `user_registration.sql`)
| Column | Type | Notes |
|---|---|---|
| `user_id` | INT UNSIGNED AUTO_INCREMENT | primary key |
| `name` | VARCHAR(100) | |
| `email` | VARCHAR(254) | UNIQUE key `uq_users_email` (login name); CHECK email format |
| `password_hash` | VARCHAR(255) | output of `password_hash()`; CHECK that it is a bcrypt/Argon2 hash, so plaintext is refused |
| `role` | ENUM('admin','student') DEFAULT 'student' | index `idx_users_role` |
| `created_at` | DATETIME | |

InnoDB, `utf8mb4_unicode_ci`, all columns NOT NULL. The file was exported with `mysqldump`; it creates only `studenthub_prac10`, and importing it again replaces the `users` table.

---

### 🔐 How It Works
| File | Purpose |
|---|---|
| `db.php` | settings and the MySQLi connection (`get_db()`); errors are logged, never shown |
| `includes/auth.php` | secure session, CSRF token, timeout check, `require_login()` / `require_role()`, security headers, page layout |
| `login.php` | login form (email + password); fixed messages selected by a code (no text from the address is shown) |
| `authenticate.php` | prepared `SELECT … WHERE email = ?`, `password_verify()`, `session_regenerate_id(true)`, stores ID, name, email and role from the database |
| `dashboard.php` | main dashboard for both roles; shows the session-security information |
| `admin_dashboard.php` / `student_dashboard.php` | only for Admin / Student; the other role gets **HTTP 403 "Unauthorized Access"** |
| `timeout.php` | ends an expired session and redirects to the login page |
| `logout.php` | POST + CSRF token; clears `$_SESSION`, expires the cookie, `session_destroy()` |
| `style.css` | shared styling |
| `tools/set_password.php` | command-line tool to set a demo password (stored as a hash) |

- **Login:** the email is looked up with a MySQLi prepared statement and the password is checked with `password_verify()`. Every failure shows the same message, *"Invalid email or password."*; an unknown email is checked against a dummy hash so it takes about as long as a wrong password.
- **Session fixation:** right after a successful login `session_regenerate_id(true)` gives the session a new ID and deletes the old one. The dashboard shows short SHA-256 fingerprints of the old and new ID as evidence – never the IDs themselves.
- **Role-based access:** the role is read from the `users` table at login and kept in the server-side session; a `role` field sent by the browser is ignored. Every protected page calls `require_login()` or `require_role()` before output. Not logged in → login page; wrong role → 403 *Unauthorized Access*.
- **Session cookie:** `P10SESSID`, `HttpOnly`, `SameSite=Strict`, `Secure` on HTTPS, strict mode.
- **Timeout:** each protected request stores the time; after 300 s without a request the next request goes to `timeout.php`, which destroys the session and shows *"Your session expired after 5 minutes of inactivity."* A `<meta http-equiv="refresh">` sends an idle page there by itself.
- **Logout and Back button:** logout needs a POST with the CSRF token (another site cannot log you out). Protected pages send `Cache-Control: no-store`, so after logout the Back button asks the server again and gets the login page.
- **Login CSRF:** the login form carries a CSRF token too.

---

### 🧪 Testing
With MySQL running, in the `Practical-10` folder: `python tests\test_app.py`
It creates the disposable database `studenthub_prac10_test` from `user_registration.sql`, sets random demo passwords with `tools\set_password.php`, runs three PHP servers (normal, 2-second timeout, MySQL unreachable) and removes the test database again. `studenthub_prac10` is not changed.

**Result: 76 of 76 checks passed** (PHP 8.2.12, MariaDB 10.4.32, Windows 11).

| Test | Result |
|---|---|
| `php -l` on every PHP file; every SQL statement uses `prepare()` (no `query()` in the application) | pass |
| SQL import: 1 admin + 2 students with 60-character `$2y$` hashes; duplicate email refused by the UNIQUE key | pass |
| `password_verify()` true for the set password; stored value is not the password | pass |
| Not logged in: all three dashboards → login page *"Please log in to continue."* | pass |
| Invalid login (wrong password, unknown email, `' OR '1'='1`, empty) → *"Invalid email or password."*; missing CSRF token refused | pass |
| Valid Student login → `student_dashboard.php`; valid Admin login → `admin_dashboard.php` | pass |
| Session ID changes at login; the old ID no longer gives access; no session ID in any page | pass |
| `role=admin` sent with a student login is ignored | pass |
| Student → `admin_dashboard.php` and Admin → `student_dashboard.php`: HTTP 403 *Unauthorized Access* | pass |
| Logout: GET or wrong token does nothing; POST with token → *"You have been logged out successfully."*, cookie expired | pass |
| After logout: dashboards → login; the old session cookie replayed → login (session destroyed on the server) | pass |
| Timeout (2 s): requests within the limit keep the session; after 3 s idle → `timeout.php` → *"Your session expired…"*; expired ID unusable; meta refresh present | pass |
| `Cache-Control: no-store` on protected pages; Back button after logout shows the login page (checked in Edge) | pass |
| MySQL unreachable → *"Login is not available right now…"*, no technical details; real error in the PHP log | pass |
| Protected files (`db.php`, `includes/`, `tools/`, `tests/`, config, router, batch file) → 403 | pass |
| PHP error logs: no passwords, no hashes, no warnings; Edge console: only the expected 403 responses | pass |

**Screenshots** (`screenshots/`, genuine Microsoft Edge renders of the running application, fictional accounts):
`successful-student-login.png`, `successful-admin-login.png`, `invalid-login.png`, `student-admin-denied.png`, `admin-student-denied.png`, `successful-logout.png`, `access-denied-after-logout.png`, `session-timeout.png` (taken on a server started with a 5-second timeout for the demonstration), `session-id-regeneration.png` (fingerprints only, no session ID).

---

### 📂 Project Structure
```text
Practical-10/
├── db.php, login.php, authenticate.php, dashboard.php, admin_dashboard.php, student_dashboard.php,
│   logout.php, timeout.php, style.css, user_registration.sql      # the 10 required files
├── includes/auth.php        # session, CSRF, timeout, role checks, layout
├── tools/set_password.php   # sets a demo password (command line)
├── index.php, favicon.svg, config.example.php, router.php, start-server.bat, .htaccess, .gitignore
├── tests/test_app.py
├── screenshots/             # 9 PNG files
└── PRAC_10_ITUE203_25CS023.docx / .pdf
```

---

### ⚠️ Limitations
- No limit on login attempts (brute force is not slowed down) and no "remember me" (the old remember-me cookie was removed because it bypassed the inactivity timeout).
- A role changed in the database takes effect at the next login.
- Tested with the PHP built-in server, MariaDB 10.4 and Microsoft Edge; XAMPP Apache, MySQL 8 and other browsers were not tested.
