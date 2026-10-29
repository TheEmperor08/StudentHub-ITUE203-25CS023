# Practical 14: Admin Dashboard with Role-Based Access, Statistics & Audit Logging

**Course:** ITUE203 - Web Development Frameworks  
**Department:** Department of Computer Science & Engineering, CSPIT - CHARUSAT  
**Student:** Shreyas (25CS023)  
**Academic Year:** 2026-27 | Semester: 3rd  
**Due Date:** October 26, 2026  

---

## 📌 Overview
An administrator dashboard (Bootstrap 5 + PHP/MySQLi) on the `user_registration` database, shared with Practicals 9 and 10.

- **Statistics:** live counts of rows in `users`, `students`, `events` and `audit_logs`.
- **Latest registrations:** the 5 most recent accounts with role badges, plus a link to `Practical-9/users.php`.
- **Navigation hub:** lists **all** rows of `menu_items` (the page is admin-only, so it is not filtered by role) and quick links to Practicals 10, 11, 12 and 13.
- **Audit log table:** the 6 most recent `audit_logs` rows with user, action, details, IP address, status and time.
- **Access control:** only `role = admin` can open `dashboard.php`. Anyone else gets the HTTP 403 page, and the attempt is logged as `ACCESS_DENIED` with status `SECURITY_BLOCK`.

### Audit events written by the code
| Action | When | Status |
|---|---|---|
| `USER_LOGIN` | successful login (`login.php`) | `SUCCESS` |
| `LOGIN_FAILED` | wrong password or unknown email | `FAILED` |
| `VIEW_DASHBOARD` | an admin opens the dashboard | `SUCCESS` |
| `ACCESS_DENIED` | a non-admin opens the dashboard | `SECURITY_BLOCK` |
| `USER_LOGOUT` | logout (`logout.php`) | `SUCCESS` |

### Demo data in `schema.sql`
`schema.sql` inserts **demo rows**: 10 navigation links, 5 sample students, 4 sample events and **6 sample audit-log entries** (`ADMIN_LOGIN`, `VIEW_DASHBOARD`, `RBAC_VERIFY`, `ACCESS_DENIED`, `EVENT_UPDATE`, `STUDENT_QUERY`). The sample audit rows are not real activity; `ADMIN_LOGIN`, `RBAC_VERIFY`, `EVENT_UPDATE` and `STUDENT_QUERY` are never written by the code. No user accounts are seeded.

> ⚠️ `schema.sql` runs `DELETE FROM menu_items` and `DELETE FROM audit_logs`, so **re-importing it erases all recorded audit-log rows**.

---

## 📂 Files
- **`schema.sql`** – creates `users`, `students`, `events`, `menu_items` and `audit_logs` in `user_registration` and loads the demo rows above.
- **`db.php`** – MySQLi connection.
- **`audit_logger.php`** – `log_audit()` helper (prepared INSERT with user, action, details, IP, user agent, status).
- **`login.php`** – login by **email** and password (`password_verify`, `session_regenerate_id`), with audit logging.
- **`dashboard.php`** – the admin dashboard.
- **`logout.php`** – logs `USER_LOGOUT` and destroys the session.
- **`403.php`** – the access-denied page.

---

## 🚀 Setup
1. **Database** (from the repository root):
   ```bash
   mysql -u root < Practical-10/user_registration.sql
   mysql -u root < Practical-14/schema.sql
   ```
2. **Accounts:** none are seeded and no passwords are stored in this repository. Create an admin and a student (for the 403 test); you are prompted for each password:
   ```bash
   php tools/create_demo_user.php --db=user_registration --username=<name> --email=<email> --role=admin
   php tools/create_demo_user.php --db=user_registration --username=<name> --email=<email> --role=student
   ```
3. **Run** from the repository root:
   ```bash
   php -S localhost:8000
   ```
4. Open `http://localhost:8000/Practical-14/login.php` and sign in with an **email address**. Admins go to the dashboard; a student who signs in is also sent to `dashboard.php` and sees the 403 page.

---

## ✅ Test status
Checked with automated HTTP requests (see `TEST_REPORT.md`): the dashboard returns 200 for an admin; a student receives HTTP 403, and an `ACCESS_DENIED` / `SECURITY_BLOCK` row is written for that student.

**Not tested:** `LOGIN_FAILED` and `USER_LOGOUT` logging, and the page in a browser.

## ⚠️ Known limitations
- The navigation hub is not filtered by role; it shows every `menu_items` row to the admin. Several links are placeholders (`#faculty`, `#attendance`, `#audit-logs`, `#settings`).
- `audit_logs` is an ordinary table: anyone with database access can edit or delete rows.

---

## 📸 Screenshots to capture for the lab report
Not captured yet. Take them from the running site; do not show typed passwords. Perform a few real actions first (admin login, a student 403 attempt, logout) so real audit rows appear alongside the demo rows, and label any demo rows as sample data.

- [ ] 1. Admin login page, then the dashboard after signing in as admin.
- [ ] 2. Statistics cards (users, students, events, audit logs).
- [ ] 3. Latest registrations table with role badges.
- [ ] 4. Audit log table showing real `USER_LOGIN`, `VIEW_DASHBOARD` and `ACCESS_DENIED` rows.
- [ ] 5. Navigation hub and StudentHub suite links.
- [ ] 6. Signing in as the **student** account: HTTP 403 page.
- [ ] 7. Database proof from a terminal (no password hashes involved):
  ```bash
  mysql -u root user_registration -e "SELECT id, username, action, status, created_at FROM audit_logs ORDER BY id DESC LIMIT 10;"
  ```

**Lab report:** `PRAC_14_ITUE203_25CS023.docx` has not been created yet.
