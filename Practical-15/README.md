# Practical 15: StudentHub – Integrated Campus Portal

**Course:** ITUE203 - Web Development Frameworks  
**Department:** Department of Computer Science & Engineering, CSPIT - CHARUSAT  
**Student:** Shreyas (25CS023)  
**Academic Year:** 2026-27 | Semester: 3rd  
**Submission Due:** October 29, 2026  

---

## 📌 Overview
Practical 15 is the integrated StudentHub portal. This folder is an exact copy of the main application in `studenthub/` (kept in sync after every change), built with PHP, MySQL (the pages use MySQLi; `db.php` also opens a PDO connection that no page currently uses), HTML, CSS and JavaScript.

> **Sample data:** CGPA, SGPA, attendance and timetable figures shown to students are placeholders, clearly labelled "Sample / demo data". They are not real academic results.

---

## 🧭 Features

### Public pages
- **Home** (`index.php`): announcement banner, hero with sign-in buttons, image slider, FAQ accordion, guidelines modal, a hamburger menu on phones, and latest events from the database.
- **Login** (`login.php`): username **or** email with `password_verify()`; admins go to the Admin Console and students to the dashboard.
- **Register** (`register.php`): creates the user (bcrypt hash) and the student record, then signs the student in.
- **Contact** (`contact.php`): department details and an inquiry form. The inquiry is not stored; when a user is logged in it is recorded in `audit_logs`.

### Student area (login required; sidebar navigation)
- **Dashboard:** welcome header, summary cards (sample data), weekly timetable and upcoming events from the database.
- **Profile:** details from the student's own record. **Password change works**: it verifies the current password and stores a new bcrypt hash. Saving phone and address is not available, and the page says so.
- **Courses**, **Results** (sample data) and **Notices** (events from the database).
- **Attendance** (sample data): the leave form records the request in `audit_logs` only.
- **Assignments** and **Achievements:** file uploads are **not available**, and the file inputs are disabled. Submissions are noted in `audit_logs` only, with no file stored.
- **Directory:** student list rendered by PHP from the database, with an instant client-side JavaScript search over the table (no Fetch API).
- **Light/dark theme** (remembered in the browser) and a mobile navigation drawer.

### Admin Console (`admin_dashboard.php`, role = admin)
- **Above the tabs:** counts of users, students, events and audit logs, plus navigation links from `menu_items`.
- **Overview:** recent system activity (the 6 latest audit entries) and platform information.
- **Students:** add (modal form), search, filter by course, delete, and **CSV export**. There is no edit or status-toggle function in this console (that is in Practical 11).
- **Events:** publish an event with an optional poster. The poster is checked by **file extension** (jpg, jpeg, png, webp, gif) and **size** (≤ 2 MB) and saved under a random name; there is no MIME or image-content check. Deleting an event also removes its poster file.
- **Users:** account list with roles and last login; delete (an admin cannot delete their own account).
- **Audit Logs:** the 50 most recent entries.
- Non-admins who open the console get the **403** page, and an `ACCESS_DENIED` / `SECURITY_BLOCK` entry is written.

### How earlier practicals appear here
| Practical | In this application |
|---|---|
| 1–6 | Semantic pages, responsive layout, theme toggle, slider, FAQ, modal, hamburger menu (home page) |
| 7 | Contact inquiry form (logged in `audit_logs` when signed in; the CSV version is in `Practical-7`) |
| 8–9 | MySQL access and secure registration with duplicate-email check |
| 10 | Login, session regeneration, role-based redirect, logout |
| 11 | Admin student records: add, search, filter, delete, CSV export |
| 12 | Event publishing with validated poster upload |
| 13 | Not used inside this application; the Fetch API single-page app is in `Practical-13` (linked from the admin navigation) |
| 14 | Admin statistics, 403 restriction and audit logging |

---

## 🔒 Security (as implemented)
- Passwords are hashed with bcrypt; `session_regenerate_id(true)` runs after login, registration and password change.
- **Every query that uses user input is a prepared statement** (login, registration, profile, password change, admin add/search/delete, audit logging). Fixed queries without input (counts, lists) use `query()`.
- Output is escaped with `htmlspecialchars()`.
- Role checks happen on the server for every admin request.
- **Known gaps:** admin delete actions are plain links without CSRF tokens; the login error reveals whether an account exists; poster uploads are validated by extension and size only.

---

## 📂 Directory Structure
```
Practical-15/
├── index.php, login.php, register.php, logout.php, 403.php
├── dashboard.php, student_dashboard.php (same page)
├── profile.php, courses.php, attendance.php, assignments.php, results.php, achievements.php
├── notifications.php, directory.php, contact.php
├── admin_dashboard.php        # Admin Console (5 tabs)
├── students.php, events.php, users.php, audit_logs.php   # redirect to the matching admin tab
├── sidebar.php                # shared navigation
├── student_profile.php        # looks up the logged-in student's record
├── audit_logger.php, db.php
├── insert.php                 # disabled demo; reports "not available"
├── test_connection.php        # Practical 8 array demo (no database)
├── schema.sql                 # safe demo database: schema + demo rows, no accounts or password hashes
├── assets/css/                # tokens.css, global.css, auth.css, home.css, bootstrap-theme.css
├── assets/js/                 # theme.js (theme, drawer, tables), script.js (home page)
│                              # auth.js, nav.js, data.js: legacy files, not loaded by the PHP pages
├── data/                      # legacy JSON demo data (not used by the PHP pages)
└── uploads/                   # event posters (.gitkeep)
```

---

## 🚀 Setup
1. **Database** (from the repository root):
   ```bash
   mysql -u root -e "CREATE DATABASE IF NOT EXISTS studenthub_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
   mysql -u root studenthub_db < Practical-15/schema.sql
   ```
2. **Accounts:** none are seeded and no passwords are stored in this repository. You are prompted for each password:
   ```bash
   php tools/create_demo_user.php --db=studenthub_db --username=<name> --email=<email> --role=admin
   ```
   Students can also self-register on `register.php`.
3. **Run** from the repository root:
   ```bash
   php -S localhost:8000
   ```
   Open `http://localhost:8000/Practical-15/index.php` (or the identical main copy at `http://localhost:8000/studenthub/index.php`).

The database connection uses `localhost` / `root` / empty password / `studenthub_db` unless the `DB_HOST`, `DB_USER`, `DB_PASS` or `DB_NAME` environment variables are set.

---

## ✅ Test status
Automated tests were run against `studenthub/`, of which this folder is a byte-for-byte copy (see `TEST_REPORT.md` for details):
- Main application: 95 / 95 checks (personalisation, sample labels, access control, registration and login, password change, honest messages), re-run after the latest redesign.
- Redesign structure: 196 / 196 checks after the latest redesign, including the honest achievement/assignment messages.
- Achievement / assignment forms (validation, attached files not saved, no files written): 21 / 21 checks, run before the latest redesign.
- Fresh install from `schema.sql` with a tool-created admin: passed, run before the latest redesign.

The home page, dashboard, profile, achievements and assignments pages were visually checked in a browser by the student. Other pages, phone widths and dark mode have not been visually verified.

---

## 📸 Screenshots to capture for the lab report
Not captured yet. Take them from a server using demo data only (for example a database created from `schema.sql`), so no real student records appear; do not show typed passwords.

- [ ] Home page (desktop), with the FAQ open and the guidelines modal
- [ ] Login and Register pages
- [ ] Student dashboard (desktop) and the same page at phone width with the menu drawer open
- [ ] Profile, and a successful password change message
- [ ] Results page showing the "Sample / demo data" label
- [ ] Notices and Directory (with a search term typed)
- [ ] Admin Console: Overview, Students (with the add form), Events (with a poster), Users, Audit Logs
- [ ] CSV export opened in a spreadsheet
- [ ] 403 page when a student opens the Admin Console
- [ ] Dark mode on any page

**Lab report:** `PRAC_15_ITUE203_25CS023.docx` has not been created yet.
