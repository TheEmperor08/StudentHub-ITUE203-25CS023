# Practical 13 – Test Cases and Results

Environment: Windows 11, XAMPP PHP 8.2.12, MariaDB 10.4.32, Microsoft Edge.
Automated API suite: `python tests\test_app.py` → **89 passed, 0 failed** (`test_output.txt`).
Browser test: `tests\browser_screenshots.py` (Edge via Playwright) → **13 passed, 0 failed** (`browser_output.txt`).
Syntax check: `php -l` on all 4 PHP files → no syntax errors.

| ID | Test case | Steps / input | Expected result | Actual result |
|---|---|---|---|---|
| TC01 | Required files | check `db.php`, `api.php`, `index.html`, `script.js`, `schema.sql` | all five exist in `Practical-13/` | Pass |
| TC02 | Database import | import `schema.sql` into a test database | 12 events (9 open, 3 closed), InnoDB, indexes, CHECK constraints enforced | Pass |
| TC03 | List events (API) | `GET api.php?action=list` | 200, `application/json`, `{"ok":true,"count":12,…}`, numeric ids, sorted by date | Pass |
| TC04 | List events (page) | open `index.html` | table filled by a `fetch` GET request, 12 rows | Pass |
| TC05 | Search by title / venue / category | `q=workshop`, `q=LAB`, `q=Robotics` | matching events only, case-insensitive | Pass |
| TC06 | Search edge cases | `q=zzzz`, `q=%`, `q=_` | 0 results; wildcards searched literally | Pass |
| TC07 | Category filter | `category=Sports`; search + category; unknown category | only Sports; combined filter; unknown value ignored | Pass |
| TC08 | Debounced AJAX search | type `lab` key by key in the browser | only **one** request (`q=lab`) after typing stops; results updated | Pass |
| TC09 | Get one event | `get&id=3`; unknown id; missing / `1 OR 1=1` / `-1` / `abc` id | 200 with event; 404; 400 JSON errors | Pass |
| TC10 | Add event (API) | valid JSON to `create` | 200 `{"ok":true,"message":"…was added.","event":{…}}`, row stored, title spaces cleaned | Pass |
| TC11 | Add event without reload (page) | fill the form, *Save event* | POST `create`, success message, new row highlighted, page not reloaded | Pass |
| TC12 | Required fields | empty JSON object | 422 with errors for all 8 fields | Pass |
| TC13 | Invalid values | 2-letter / 121-char title, short description, unknown category, 30 Feb, year 2150, 25:00, venue `X`, capacity 0 / 5001 / `12abc`, status `pending`, title as array | 422 with the field error; nothing stored | Pass |
| TC14 | Update event (API) | valid JSON to `update` | 200, row changed, saved event returned | Pass |
| TC15 | Update without reload (page) | *Edit* → change title, venue, capacity → *Save changes* | POST `update`, row shows new values, page not reloaded | Pass |
| TC16 | Update errors | empty title; unknown id; id `1 OR 1=1` | 422 (row unchanged); 404; 400 | Pass |
| TC17 | Delete confirmation | *Delete* in the page | dialog “Are you sure you want to delete …?” | Pass |
| TC18 | Delete without reload | *Yes, delete* | POST `delete`, 200 `{"ok":true,…,"deleted_id":…}`, row removed, page not reloaded | Pass |
| TC19 | Delete errors | delete again; invalid id | 404 “not found”; 400 | Pass |
| TC20 | Loading state | search with network throttling (2.5 s latency) | “Searching for …” indicator visible, hidden after the response | Pass |
| TC21 | Error state | add an event dated 2150-06-01 | HTTP 422 shown as message and field error “Enter a valid date” | Pass |
| TC22 | Wrong method | GET on `create`; POST on `list` | 405 JSON with `Allow: POST` / `Allow: GET` | Pass |
| TC23 | Wrong body | form-encoded POST; missing `X-Requested-With`; invalid JSON; JSON array; 30 kB body; unknown action | 415; 400; 400; 400; 400; 400 – all JSON | Pass |
| TC24 | SQL injection | `q=' OR '1'='1`, UNION in `q`; title `Robert'); DROP TABLE events;--` | 0 results; stored literally, table intact | Pass |
| TC25 | XSS | title `<script>…`, venue `<img onerror>` | stored as text; JSON escapes `<` as `<`; page shows it as text, no element created, no alert | Pass |
| TC26 | Central JSON error handling | MySQL unreachable | 500 `{"ok":false,"error":"The server could not complete…"}`, no SQL details; real error in PHP log | Pass |
| TC27 | Protected files | `schema.sql`, `README.md`, config, router, tests, `.gitignore`, `db.php`, batch file | 403 | Pass |
| TC28 | Network evidence | Edge DevTools Network panel during list / add / update / delete | `fetch` requests to `api.php`, 200 OK, JSON responses (screenshots 10–12) | Pass |
