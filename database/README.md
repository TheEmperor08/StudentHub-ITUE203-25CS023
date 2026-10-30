# StudentHub database (`studenthub_db`)

The single shared MariaDB/MySQL database of the StudentHub portal (`studenthub/`). Practicals 8–15 are integrated
into this database step by step; the practical folders keep their own historical databases only as evidence.

| File | Purpose |
|---|---|
| `studenthub_demo.sql` | Current schema + fictional demo rows for a **new** installation (no accounts, no password hashes) |
| `migrations/001_practical8_foundation.sql` | Upgrades an **existing** database to the Practical 8 foundation |
| `migrations/001_practical8_foundation.down.sql` | Schema rollback of migration 001 |
| `migrations/002_unique_enrollment_no.sql` | Practical 11: UNIQUE index on `students.enrollment_no` |
| `migrations/002_unique_enrollment_no.down.sql` | Rollback of migration 002 (drops the index only) |
| `tests/test_001_practical8_foundation.py` | Tests of migration 001 (disposable databases only) + read-only live check |
| `tests/test_002_unique_enrollment_no.py` | Tests of migration 002 (disposable databases only) + read-only live check |
| `migrations/003_event_management.sql` / `.down.sql` | Practical 12: `event_categories` + FK, `events.status`, `events.updated_at`, UNIQUE `events.poster` (and rollback) |
| `tests/test_003_event_management.py` | Tests of migration 003 (disposable databases only) + read-only live check |
| `migrations/004_admin_dashboard.sql` / `.down.sql` | Practical 14: menu roles `student`/`editor`/`admin` + integrated links, `users.status`, `chk_users_role` (and rollback) |
| `tests/test_004_admin_dashboard.py` | Tests of migration 004 (disposable databases only) + read-only live check |
| `migrations/005_inquiries.sql` / `.down.sql` | Practical 7: `inquiries` table for the Help & Contact form (and rollback) |
| `tests/test_005_inquiries.py` | Tests of migration 005 (disposable databases only) + read-only live check |
| `tests/fixtures/studenthub_v1_fixture.sql` | The pre-migration structure with fictional rows, used by the tests |

## Tables and relationships (after migrations 001 and 002)

```text
users (id) ─────────1:0..1──────── students (id, user_id → users.id  ON DELETE SET NULL, UNIQUE; enrollment_no UNIQUE)
  │                                    │
  │ 1:n (ON DELETE SET NULL)           │ 1:n (ON DELETE CASCADE)
  ▼                                    ▼
audit_logs (user_id → users.id)    registrations (student_id → students.id, event_id → events.id,
                                                  UNIQUE (student_id, event_id), status registered/attended/cancelled)
                                       ▲
                                       │ 1:n (ON DELETE CASCADE)
                                   events (id, event_time, capacity)
menu_items, schema_migrations: no relationships
```

All keys are signed `INT(11)`, all tables InnoDB with `utf8mb4_unicode_ci`.

## Practical 8 design in the portal database

Practical 8 designed `students`, `events` and `registrations` in its own database `studenthub_prac8`. Migration 001
adds that design to the existing portal tables instead of replacing them, so no page and no existing data breaks:

| Practical 8 | Portal database | Note |
|---|---|---|
| `registrations` (CASCADE FKs, UNIQUE student+event, status ENUM) | `registrations` – same columns and rules | keys are signed `INT(11)` like the portal's primary keys (P8 used UNSIGNED) |
| `students.semester` TINYINT, CHECK 1–8 | `students.semester` `INT(11)`, CHECK `NULL or 1–8` | type and default kept; NULL allowed for legacy rows |
| `events.capacity` NOT NULL, CHECK > 0 | `events.capacity` NULL, CHECK `NULL or > 0` | existing events have no capacity: NULL = no limit set (nothing invented) |
| – | `events.event_time` TIME NULL | event start time; existing events NULL |
| `student_code`, `full_name`, `venue`, `branch` | `enrollment_no`, `name`, `location`, `course` | the portal names are kept (used by 11 / 5 files); course names stay free text |
| procedure `register_student_for_event` (capacity check) | `studenthub/includes/event_registration.php` | the same rule in PHP, inside a real transaction (see below) |
| – | `students.user_id` → `users.id` | links a student record to its login account |
| – | `audit_logs.user_id` → `users.id` | optional link; anonymous entries stay NULL |

Unchanged on purpose: `students.enrollment_no`, `events.location`, the status values (`Active`/`Inactive`), course
names, the roles `admin`, `editor` and `student` (an editor gets no admin rights), password hashes and all rows.

## Setting up

**New database** (fresh installation):
```bat
C:\xampp\mysql\bin\mysql.exe -u root -e "CREATE DATABASE IF NOT EXISTS studenthub_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
C:\xampp\mysql\bin\mysql.exe -u root studenthub_db < database\studenthub_demo.sql
```
The demo file already contains migrations 001 and 002; it refuses to run on a database older than 001 (use the
migrations instead).

**Existing database created before migration 001:**
```bat
C:\xampp\mysql\bin\mysqldump.exe -u root --single-transaction --routines --triggers --events --databases studenthub_db > studenthub_db_before_001.sql
C:\xampp\mysql\bin\mysql.exe -u root studenthub_db < database\migrations\001_practical8_foundation.sql
python database\tests\test_001_practical8_foundation.py --verify-live --baseline-dump studenthub_db_before_001.sql
```
Keep the dump outside the repository – it contains real accounts and password hashes.

**Existing database at migration 001** (Practical 11 student management):
```bat
C:\xampp\mysql\bin\mysqldump.exe -u root --single-transaction --routines --triggers --events --databases studenthub_db > studenthub_db_before_002.sql
C:\xampp\mysql\bin\mysql.exe -u root studenthub_db < database\migrations\002_unique_enrollment_no.sql
python database\tests\test_002_unique_enrollment_no.py --verify-live --baseline-dump studenthub_db_before_002.sql
```

## Migration 002 – unique enrollment numbers (Practical 11)

The Admin Console now adds and edits student records, so two records must never share an enrollment number. The
application checks it, and migration 002 makes the database enforce it too (also for simultaneous requests):

1. **Preconditions** (nothing is changed if one fails): migration 001 is recorded; `students.enrollment_no` exists; no
   enrollment number is used twice. The column collation is case-insensitive, so `25cs011` and `25CS011` count as the
   same number. Duplicates are **not** corrected automatically – list them with
   `SELECT enrollment_no, COUNT(*) FROM students WHERE enrollment_no IS NOT NULL GROUP BY enrollment_no HAVING COUNT(*) > 1;`
2. `UNIQUE KEY uq_students_enrollment_no (enrollment_no)`. `NULL` stays allowed, any number of times (legacy rows).
3. Verification of the index, then the row `002` in `schema_migrations`.

No column, value, status, course name, account link or registration changes. Idempotent; the rollback
(`002_unique_enrollment_no.down.sql`) drops only the index and the `002` row. Applied to the live database on
31 Oct 2026 after a verified backup (9 records, no duplicates).

**Soft delete (Practical 11):** student records are never deleted by the portal. Deactivating a student sets
`students.status` to `Inactive` (the existing status value); the row, its `user_id` link and its `registrations` stay.
Inactive students cannot register for events (`register_student_for_event()` refuses them) and are not listed in the
student directory. A `student` account whose linked record (`students.user_id`) is `Inactive` cannot sign in, and an open
session ends at its next request (`studenthub/includes/auth.php`); admin and editor accounts and accounts without a linked
record are not affected. Reactivation sets the status back to `Active` and restores normal sign-in.

## Migration 001 in detail

1. **Preconditions** (nothing is changed if one fails): the four tables exist and are InnoDB; `users.id`,
   `students.id`, `events.id` and `audit_logs.user_id` are signed `INT(11)`; no audit entry points at a deleted account;
   no semester outside 1–8; no different `registrations` table exists.
2. `students.user_id` (nullable, UNIQUE, FK `ON DELETE SET NULL`) and `chk_students_semester`.
3. **Linking:** a student record gets `user_id` only if its e-mail (trimmed, case-insensitive) belongs to exactly one
   account, that account has the role `student`, exactly one student record has that e-mail and neither side is linked
   yet. Student records without an account, ambiguous e-mails and admin/editor accounts stay unlinked; no account is
   created and nothing is deleted. (Live database: 5 records linked, 4 student records without an account, 1 student
   account without a record.)
4. `events.event_time`, `events.capacity` (both NULL for existing events), `chk_events_capacity`, index `idx_events_date`.
5. Table `registrations` with both CASCADE foreign keys and `UNIQUE (student_id, event_id)`.
6. `fk_audit_logs_user` (`ON DELETE SET NULL`: deleting an account keeps its audit entries and username).
7. Post-verification of every foreign key, CHECK and unique key, then the row `001` in `schema_migrations`.

The script is idempotent: running it again changes nothing.

**Application side:** `studenthub/audit_logger.php` stores an entry with `user_id = NULL` (username kept) if the
account was deleted while its session was still open – otherwise the new foreign key would make that page fail.

## Capacity rule (no overbooking)

`registrations` prevents duplicates by itself. The capacity is enforced by
`register_student_for_event($db, $student_id, $event_id)` in `studenthub/includes/event_registration.php`: in one
transaction it locks the event row (`SELECT … FOR UPDATE`), counts the registrations that are not `cancelled`, and
inserts the registration (or reactivates a cancelled one) only if a seat is free. Concurrent requests for the same event
therefore wait for each other. It throws `EventRegistrationException` with the reason `event_not_found`,
`student_not_found`, `student_inactive`, `duplicate` or `event_full`. `capacity` NULL means no limit. A plain
`INSERT INTO registrations` bypasses the capacity rule, so the portal must always use this function. It is used by the Campus Events page
(`notifications.php`) and the events API (`api/events.php`, Practicals 12 and 13).

## Migration 003 – event management (Practical 12)

1. **Preconditions** (nothing is changed if one fails): migration 002 is recorded; `events.category` is `VARCHAR(50)` and `events.poster`
   `VARCHAR(255)`; no two events share a poster value; no event has an empty category.
2. `event_categories (name PK, description)` with Practical 12's six categories plus **every category already used** (the live
   database keeps *Conference*), and `fk_events_category` (`ON UPDATE CASCADE`, `ON DELETE RESTRICT`).
3. `events.status ENUM('open','closed') NOT NULL DEFAULT 'open'` (existing events: open), `events.updated_at` (set automatically on
   change; existing events NULL), `UNIQUE uq_events_poster`, indexes on status and category.
4. Verification, then the row `003` in `schema_migrations`. Idempotent; `003_event_management.down.sql` removes exactly these changes.

No event value is changed. The four live events whose `poster` points to an older path (`uploads/odoo_hackathon.jpg` etc.) keep that
value: the files do not exist, so the portal shows a placeholder and never opens or deletes anything outside the poster folder
(`poster_path()` accepts only `<32 hex>.<jpg|png|webp>` inside it); uploading a new poster replaces the reference. Events with
registrations cannot be deleted by the portal, so `fk_registrations_event ... ON DELETE CASCADE` never removes registration history
through the interface. Applied to the live database on 31 Oct 2026 after a verified backup.

## Migration 004 – admin dashboard (Practical 14)

1. **Preconditions:** migration 003 is recorded; every account has the role `admin`, `editor` or `student`.
2. `menu_items.min_role` becomes `ENUM('student','editor','admin') NOT NULL DEFAULT 'student'` – the old value `user` (not a portal role)
   becomes `student`. Links to old standalone pages or anchors that do not exist are pointed at the integrated pages
   (`dashboard.php`, `profile.php`, `notifications.php`, `attendance.php`, `events_live.php` instead of `../Practical-13/index.html`).
   The row linking to the non-existent `faculty.php` is kept; the portal hides links to missing pages.
3. `users.status ENUM('active','disabled') NOT NULL DEFAULT 'active'` (every existing account stays active) and
   `chk_users_role CHECK (role IN ('admin','editor','student'))`.
4. Verification, then the row `004`. Idempotent. The rollback removes `users.status` and the check and maps `student` back to `user`;
   the corrected links stay (they point at existing pages). Applied to the live database on 31 Oct 2026 after a verified backup.

## Migration 005 – contact inquiries (Practical 7)

`inquiries (id, user_id → users.id ON DELETE SET NULL, name, email, enrollment_no, topic ENUM, message TEXT CHECK 10–2000 characters,
status new/resolved, created_at, resolved_at)`. Practical 7 kept inquiries in a JSON file protected by `flock()`; in the portal the database
provides the same safety for simultaneous submissions (tested with 8 parallel requests). Preconditions: migration 004 recorded, no different
`inquiries` table. Nothing else changes; the rollback drops the table (and its inquiries). Applied to the live database on 31 Oct 2026
after a verified backup.

## Rollback

1. **Preferred:** restore the dump taken before the migration:
   `C:\xampp\mysql\bin\mysql.exe -u root < studenthub_db_before_001.sql` (the dump recreates `studenthub_db` exactly).
2. **Schema rollback** when the dump is older than data you want to keep:
   `C:\xampp\mysql\bin\mysql.exe -u root studenthub_db < database\migrations\001_practical8_foundation.down.sql`.
   It removes exactly what migration 001 added and **deletes** every registration, event time/capacity value and the
   student–account links; all other data stays. Tested: the structure afterwards is identical to the original.

## MariaDB DDL limitations

- Every `ALTER TABLE` / `CREATE TABLE` commits immediately; DDL cannot be rolled back and the migration is not one
  atomic transaction. If a statement fails half-way, the earlier ones stay applied. The preconditions catch the known
  causes first, and because every step is idempotent, re-running the script after fixing the cause completes it.
- `ADD … IF NOT EXISTS` for foreign keys and CHECK constraints compares only the **name**; the post-verification block
  therefore also checks the referenced tables and delete rules.
- Adding a foreign key rebuilds the table (`ALGORITHM=COPY`) and blocks writes to it meanwhile – a fraction of a second
  for these tables, but noticeable on large tables.
- A foreign-key column must have exactly the type of the referenced key: all keys here are signed `INT(11)`.
- Dropping a foreign key keeps its index; the rollback drops `fk_audit_logs_user`'s index explicitly.
- CHECK constraints are enforced by MariaDB 10.2.1+ independently of `sql_mode`; XAMPP runs without strict mode, so
  other invalid values (e.g. too-long text) are still silently adjusted.
- The scripts use compound statements (`BEGIN NOT ATOMIC`) with `DELIMITER`; they work with the `mysql` client and the
  phpMyAdmin import, not when pasted statement-by-statement into tools that ignore `DELIMITER`.

## Tests

```bat
python database\tests\test_001_practical8_foundation.py                          :: fixture (fictional data)
python database\tests\test_001_practical8_foundation.py --source-dump <dump.sql>  :: a real dump, restored into a disposable DB
```
Each run creates the disposable databases `studenthub_mig001_test`, `studenthub_mig001_pre` and `studenthub_mig001_fresh`
(with a marker table) and drops them at the end. Checked: structure, keys and types; every original value unchanged
(SHA-256 of all original columns, including password hashes); the linking rule; repeated runs; rollback and re-apply;
the precondition stop; registrations, duplicates, capacity, cancelled seats and 8 parallel requests for 3 seats; CHECK and
foreign-key behaviour on delete; the audit-log fallback; all existing portal pages and admin actions through the PHP
built-in server; a fresh install from `studenthub_demo.sql`.

Results (31 Oct 2026, PHP 8.2.12, MariaDB 10.4.32): fixture **87 / 87**, real pre-migration dump **87 / 87**, live
database after migration (`--verify-live`) **24 / 24**. Output of the fixture run: `tests/test_001_output.txt`.
Re-run after migration 002 and the Practical 11 changes: fixture **87 / 87** (the fresh-install comparison now applies
the later migrations to the upgraded copy first), live `--verify-live` **24 / 24**.
Latest run (complete run of Practical 15, after the regression checks added with Practicals 12 and 14): fixture **88 / 88**.

```bat
python database\tests\test_002_unique_enrollment_no.py                          :: fixture + migration 001
python database\tests\test_002_unique_enrollment_no.py --source-dump <dump.sql>  :: a real dump in a disposable DB
```
Checked: the only structural change is the new index; every row of every table unchanged; idempotent; duplicate
(also other letter case) refused, several `NULL` allowed; rollback restores the previous structure and can run twice;
re-apply; precondition stops (duplicates, missing migration 001) change nothing; a fresh install equals 001 + 002; the
demo file adds the index to a database made by its earlier version. Results (31 Oct 2026): fixture **22 / 22**, real
dump **22 / 22**, live database after applying it (`--verify-live`) **4 / 4**. Output: `tests/test_002_output.txt`,
`tests/test_002_verify_live_output.txt`.
