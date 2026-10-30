# Practical 12 – Test Cases and Results

Environment: Windows 11, XAMPP PHP 8.2.12 (Fileinfo, no GD), MariaDB 10.4.32, Microsoft Edge.
Automated suite: `python tests\test_app.py` → **153 passed, 0 failed** (full output in `test_output.txt`).
Browser run: `tests\browser_screenshots.py` (Edge via Playwright) → **13 passed, 0 failed** (`browser_output.txt`).
Syntax check: `php -l` on all 15 PHP files → no syntax errors.

Each test case below is covered by one or more of the 153 automated checks.

| ID | Test case | Steps / input | Expected result | Actual result |
|---|---|---|---|---|
| TC01 | Database connection and seed data | import `studenthub_prac12.sql`, open the list | 12 events (8 open, 4 closed), 6 categories, 1 hashed admin; page loads | Pass |
| TC02 | Constraints | unknown category; poster name `../db.php`; two events with one poster; plaintext password | refused by FK, CHECK, UNIQUE and CHECK constraints | Pass |
| TC03 | Admin login | `admin.demo@example.com` + correct password | 303 → event list, “Welcome, Demo Admin”, session ID changed, old ID useless | Pass |
| TC04 | Failed login | wrong password, unknown email, `' OR '1'='1`, empty fields, missing CSRF token | HTTP 401 “Invalid email or password.” / “login form expired”; no session | Pass |
| TC05 | Unauthorized access | open index, add, edit, view, delete, poster without login; POST add/delete | HTTP 401 “Access denied”, no event data, nothing changed | Pass |
| TC06 | Logout | GET logout; POST with wrong token; POST with token; replay old cookie | only the valid POST logs out; afterwards 401, old cookie useless | Pass |
| TC07 | Session timeout | server with 2-second timeout, wait 3 s | redirect to login “Your session expired…”, session gone | Pass |
| TC08 | Event listing | open `index.php` | 12 rows with poster thumbnails, title, category, date & time, venue, Open/Closed badge | Pass |
| TC09 | Poster delivery | `poster.php?file=<stored name>` | exact image bytes, image Content-Type, `nosniff`, sandbox CSP | Pass |
| TC10 | Create with valid JPEG / PNG / WebP | add an event with each format | 303, success message, new row, file stored under `<32 hex>.<ext>` with identical bytes | Pass |
| TC11 | Random file names | three uploads; upload named `../../db.php.jpg` | three different random names; nothing written outside `uploads/` | Pass |
| TC12 | Required-field validation | empty form | HTTP 422, error for title, description, category, date, time, venue and poster | Pass |
| TC13 | Tampered values | category “Music”, 30 Feb, 25:00, status “pending”, 2-letter title | all refused | Pass |
| TC14 | Invalid extension | PNG renamed `.gif`, `poster.php`, `poster.svg` | “Invalid file type. Only JPEG, PNG and WebP…” | Pass |
| TC15 | Disguised files | PHP script as `.jpg`, SVG as `.png`, Windows EXE as `.jpg` | rejected (content is not a JPEG, PNG or WebP image) | Pass |
| TC16 | MIME mismatch | PNG content named `.jpg`; JPEG content named `.webp` | “The file extension does not match its content” | Pass |
| TC17 | Corrupted images | JPEG header + garbage; PNG header only; PNG cut in half; PNG with wrong CRC; JPEG and WebP cut in half | “The poster is not a valid image or is damaged.” | Pass |
| TC18 | Embedded code | valid JPEG + `<?php …` | “rejected because it contains embedded code” | Pass |
| TC19 | Oversized file | 2 MB + 1 byte; 3.5 MB real image (browser) | “The poster is … MB. The maximum size is 2 MB.”; exactly 2 MB is accepted | Pass |
| TC20 | Server limits | POST over `post_max_size`; file over `upload_max_filesize` | clear “too large” messages, not a CSRF error | Pass |
| TC21 | Image dimensions; empty file | PNG 7000 × 1 px; 0-byte file | rejected | Pass |
| TC22 | No abandoned files | every rejected upload; INSERT forced to fail after storing | no new row and no new file in `uploads/` | Pass |
| TC23 | Edit without new poster | change title and venue | “existing poster was kept”, same file name and file | Pass |
| TC24 | Poster replacement | edit with a valid WebP | new random name stored, new file present, old file deleted after the update | Pass |
| TC25 | Rejected replacement | `evil.php`; 2 MB+ JPEG; valid poster + empty title | HTTP 422, “current poster was kept”, nothing changed, no new file | Pass |
| TC26 | Failed update | UPDATE forced to fail after the new poster was stored | 503 general message; new file removed; old poster still in MySQL and on disk | Pass |
| TC27 | Delete confirmation | open `delete.php?id=N` | “Are you sure you want to delete …?”, nothing deleted yet | Pass |
| TC28 | Delete and poster clean-up | POST without/with wrong token; confirmed POST | refused without token; confirmed: row and only its poster file removed | Pass |
| TC29 | Delete edge cases | same ID again; `1 OR 1=1`; `../db.php` | “not found”, nothing deleted | Pass |
| TC30 | Category filter | `category=Workshop` | only Workshop events | Pass |
| TC31 | Open/Closed filter | `status=open`, `status=closed`, Sports + closed | only matching events; filters stay selected | Pass |
| TC32 | Filter tampering | unknown values; `Sports' OR '1'='1` | ignored, all events listed | Pass |
| TC33 | SQL injection | title `Robert'); DROP TABLE events;--`, venue `O'Neill Hall`, `view.php?id=1 OR 1=1` | stored literally, table intact; not found | Pass |
| TC34 | XSS escaping | `<script>` in title, `<img onerror>` in description, `"><b>` in venue | escaped in list, view, edit and delete pages | Pass |
| TC35 | CSRF protection | add without token / with another session's token; edit without token | refused, nothing changed | Pass |
| TC36 | Path traversal | `poster.php?file=` `../db.php`, `..%2Fdb.php`, `..\db.php`, absolute paths, `x.php`, … | HTTP 404, no file content revealed | Pass |
| TC37 | Upload-folder execution protection | `/uploads/<poster>`, `/uploads/shell.php`, `/uploads/.htaccess`; PHP code planted as `<hex>.jpg` | HTTP 403; planted code delivered as raw bytes, never executed | Pass |
| TC38 | Protected files | `db.php`, `includes/`, `tools/`, `tests/`, SQL dump, README, config, `.htaccess`, batch file | HTTP 403 | Pass |
| TC39 | Abandoned-file clean-up tool | orphan poster older than 1 h, recent file, other file | list mode lists it; `--delete` removes only that file | Pass |
| TC40 | Raw database errors hidden | MySQL unreachable | 503 “The event database is not available right now”, details only in the PHP log | Pass |
