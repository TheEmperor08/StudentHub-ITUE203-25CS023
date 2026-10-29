# Practical 13: StudentHub – Fetch API Student Management & Role-Based Navigation

**Course:** ITUE203 - Web Development Frameworks  
**Department:** Computer Science & Engineering, CSPIT, CHARUSAT  
**Student:** Shreyas (25CS023)  
**Academic Year:** 2026-27 | Semester: 3rd  
**Due Date:** October 24, 2026  

---

## 📌 Overview
A single-page student manager: `index.html` + `script.js` talk to a PHP JSON API (`api.php`) using `fetch()` with `async/await`, so records are listed, added, edited and deleted without reloading the page.

The **role comes only from the server-side login session** (set when you sign in through `Practical-10/login.php`). Any `role` value sent by the browser is ignored, and requests without a session receive HTTP 401.

---

## 🔐 What each role can do

| Session role | Navigation items (`get_menu`) | API: read | API: create / update | API: delete | In the page (UI) |
|---|---|---|---|---|---|
| Not logged in | – | 401 | 401 | 401 | "Please log in first" message with a login link |
| `student` | 3 | ✔ | 403 | 403 | Table with "View Only"; add/edit form hidden |
| `editor` | 5 | ✔ | ✔ | 403 | Edit links shown, but **saving is blocked in the page** (see limitations) |
| `admin` | 9 | ✔ | ✔ | ✔ | Add, edit and delete |

The role drop-down at the top is locked to the session role; it only displays it.

---

## 📂 Files
- **`schema.sql`** – creates `student_db` with `students`, `menu_items` (navigation links with a minimum role) and `items` (sample resource table).
- **`db.php`** – PDO connection; returns a JSON 500 error if the database is unavailable.
- **`api.php`** – JSON API (`whoami`, `get_menu`, `read`, `create`, `update`, `delete`) using PDO prepared statements.
- **`index.html`**, **`script.js`**, **`style.css`** – the single-page interface.

---

## 🚀 Setup

1. **Databases** (run from the repository root):
   ```bash
   mysql -u root < Practical-11/schema.sql            # student_db with sample students (shared with Practical 11)
   mysql -u root < Practical-13/schema.sql            # adds menu_items and items to student_db
   mysql -u root < Practical-10/user_registration.sql # login accounts live here
   ```
   `Practical-13/schema.sql` on its own creates an empty `students` table, so import Practical 11's schema first if you want sample records.
2. **Accounts** (password is prompted; none are stored in the repository):
   ```bash
   php tools/create_demo_user.php --db=user_registration --username=<name> --email=<email> --role=admin
   ```
   Use `--role=student` or `--role=editor` for the other roles.
3. **Run** from the repository root (the login page is in `Practical-10`):
   ```bash
   php -S localhost:8000
   ```
4. Sign in at `http://localhost:8000/Practical-10/login.php`, then open `http://localhost:8000/Practical-13/index.html`.

---

## 📡 API Reference (`api.php`)

| Request | Method | Body (JSON) | Allowed roles | Response |
|---|---|---|---|---|
| `?action=whoami` | GET | – | any logged-in user | `{"status":"success","username":"…","role":"…"}` |
| `?action=get_menu` | GET | – | any logged-in user | menu items for the session role |
| `?action=read&type=students` | GET | – | any logged-in user | list of students |
| `?action=create&type=students` | POST | `name`, `email`, `course`, `gender` | editor, admin | success message; **409** if the email already exists |
| `?action=update&type=students` | POST | `id`, `name`, `email`, `course`, `gender` | editor, admin | success message |
| `?action=delete&type=students` | POST | `id` | admin | success message |

`type=items` works the same way for the `items` table, but only through the API; the page manages students.  
Errors: **401** not logged in, **403** role not allowed, **409** duplicate email.

---

## ✅ Test status
Checked with automated HTTP requests (see `TEST_REPORT.md`): anonymous calls return 401; a student's role is read from the session; a student's create and delete are refused with 403 even when the request says `role=admin`; an admin can create and delete; a duplicate email returns a clean 409; the student menu excludes admin items.

**Not tested:** the page in a browser (rendering, alerts, edit form), API `update`, and the editor role (its permissions above are taken from the code).

## ⚠️ Known limitations
- An **editor** sees Edit links and the form, but `script.js` blocks saving for every non-admin, so in the page only admins can add or edit. The API itself allows editors to create and update.
- Some navigation links are placeholders (`#faculty`, `#attendance`, `#students`, `#settings`).
- `api.php` does not apply Practical 10's 5-minute inactivity timeout.

---

## 📸 Screenshots to capture for the lab report
Not captured yet. Take them from the running site; do not show typed passwords or cookies.

**Part 1 – Interface**
- [ ] 1. Student list loaded after signing in as an admin.
- [ ] 2. Adding a student: green success alert and the new row, without a page reload.
- [ ] 3. Editing a student as admin: form filled with the record, then the success alert.
- [ ] 4. Deleting a student: confirmation prompt, then the row disappears.
- [ ] 5. Role-based view: the same page signed in as a **student** (View Only, 3 menu items, no form) and as an **admin** (9 menu items, form visible).
- [ ] 6. Error feedback: adding a student whose email already exists → "A record with that email already exists."
- [ ] 7. Not logged in (private window): "Please log in first" message with the login link.

**Part 2 – Network tab (DevTools → Network → Fetch/XHR)**
- [ ] 8. `GET api.php?action=read` – 200 with the JSON list
- [ ] 9. `POST api.php?action=create` – 200 with the JSON message
- [ ] 10. `POST api.php?action=update` – 200 with the JSON message
- [ ] 11. `POST api.php?action=delete` – 200 with the JSON message
- [ ] 12. `GET api.php?action=get_menu` – 200 with the role's menu
- [ ] 13. `GET api.php?action=whoami` while logged out – 401

**Lab report:** `PRAC_13_ITUE203_25CS023.docx` has not been created yet.
