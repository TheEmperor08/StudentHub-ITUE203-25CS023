# Practical 15: StudentHub – Final Integrated Campus Portal

**Course:** ITUE203 - Web Development Frameworks
**Department:** Department of Computer Science & Engineering, CSPIT - CHARUSAT
**Student:** Shreyas (25CS023)
**Academic Year:** 2026-27 | Semester: 3rd

---

## What this folder is
`Practical-15/` is the **final snapshot of the canonical StudentHub application** in `studenthub/` – the single portal into
which Practicals 5–14 were integrated step by step. It is **not** maintained separately: it is produced by

```bash
python tools/sync_practical15.py          # copy every file tracked in studenthub/ and write SNAPSHOT.md
python tools/sync_practical15.py --check  # verify: byte-for-byte identical, SHA-256 manifest matches
```

and verified by `tests/test_snapshot.py`, which also runs the authentication test suite against this folder. The file
`SNAPSHOT.md` lists every file with its SHA-256 hash. The earlier, independently kept copy of Practical 15 is still
available in the Git history.

## What the portal contains (one application, one database `studenthub_db`, one login)
| Practical | Integrated feature (in this snapshot) |
|---|---|
| 5 | Real-time registration validation with regular expressions and a password strength meter (`register.php`) |
| 6 | Campus Data Explorer – JSON files rendered with the Fetch API, search, filter, sort, pagination (`data_explorer.php`) |
| 7 | Help & Contact form – server validation, stored inquiries with reference number (`contact.php`, Admin Console → Inquiries) |
| 8 | Shared database foundation: students – events – registrations with foreign keys, capacity rule in a transaction |
| 9 | Secure self-registration: validation, password policy, bcrypt, account + linked student record in one transaction |
| 10 | Login, hardened sessions, inactivity timeout, POST logout, CSRF protection, roles admin / editor / student |
| 11 | Student management: add, edit, search, filters, soft delete / reactivation, CSV export; inactive students cannot sign in |
| 12 | Event management with secure poster upload (JPEG/PNG/WebP, 2 MB, content checks), registration, capacity, cancellation |
| 13 | Event Finder – Fetch API + JSON API (`api/events.php`) with debounced search, admin CRUD and student registration |
| 14 | Admin dashboard: live statistics, latest registrations, role-based navigation, account status, filtered audit log |

## How to run it
Exactly like the main application (see the root `README.md` and `DEPLOYMENT.md`):

```bash
mysql -u root -e "CREATE DATABASE IF NOT EXISTS studenthub_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
mysql -u root studenthub_db < database/studenthub_demo.sql
php tools/create_demo_user.php --db=studenthub_db --username=admin01 --email=admin01@example.com --role=admin
php -S localhost:8015 -t Practical-15
```

Open `http://localhost:8015/`. Database settings come from the environment (`DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME`).

## Evidence and tests
Genuine Microsoft Edge screenshots of the final portal: `evidence/practical-15-integration/` (end-to-end scenario through
17 critical workflows) and `evidence/practical-05-07-integration/` … `evidence/practical-14-integration/` per practical.
Test results: `TEST_REPORT.md` (section 13 for the final integration).

> **Sample data:** CGPA, SGPA, attendance and timetable figures shown to students are placeholders, labelled
> "Sample / demo data". They are not real academic results.
