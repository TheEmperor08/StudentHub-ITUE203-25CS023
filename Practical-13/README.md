<div align="center">
  <h1>🎓 Practical 13</h1>
  <h3>AJAX Event CRUD with the JavaScript Fetch API and a PHP JSON API (MySQLi)</h3>
</div>

---

### 👨‍🎓 Student Information
- **Name:** Shreyas
- **ID:** 25CS023
- **Course:** ITUE203 - WEB DEVELOPMENT FRAMEWORKS
- **Year:** 2026-27

---

### 🎯 Aim
> List, add, edit/update and delete events stored in MySQL **asynchronously with the Fetch API**, without reloading the page. A PHP API returns **JSON** for every request, handles GET and POST correctly, validates all input before any database operation and reports errors through one central JSON error handler. The page shows loading, success and error states and offers an **AJAX search with debounce**.

---

### 📁 Required Source Files
| File | Purpose |
|---|---|
| `db.php` | MySQLi connection to the isolated database `studenthub_prac13` (errors logged, never shown) |
| `api.php` | JSON API: `list`, `get` (GET) and `create`, `update`, `delete` (POST); validation; prepared statements; central JSON error handling |
| `index.html` | Front end: event table, add/edit form, search box, category filter, loading indicator, messages, delete-confirmation dialog |
| `script.js` | Fetch API implementation: `apiRequest()` wrapper, rendering with `textContent`, debounced search, loading/success/error states |
| `schema.sql` | Importable MySQL schema + 12 fictional seed events (mysqldump export) |

Helper files: `style.css`, `favicon.svg`, `router.php` (PHP built-in server rules), `start-server.bat`, `.htaccess`, `config.example.php`, `.gitignore`, `.gitattributes`.

---

### 🚀 How to Run (Windows + XAMPP)
1. **Start** MySQL (and Apache if you use phpMyAdmin) in the **XAMPP Control Panel**.
2. **Import the database:** phpMyAdmin → **Import** → `Practical-13\schema.sql` → **Import**, or in the `Practical-13` folder:
   `C:\xampp\mysql\bin\mysql.exe -u root < schema.sql`
   This creates **studenthub_prac13** with the table `events` (12 events). Importing again resets the data.
3. **Start the site:** double-click **`start-server.bat`**, or run in the `Practical-13` folder:
   `C:\xampp\php\php.exe -S 127.0.0.1:8613 router.php`
4. **Open http://127.0.0.1:8613/index.html** in Microsoft Edge (F12 → *Network* → *Fetch/XHR* shows the requests to `api.php`).

*XAMPP Apache alternative (not tested):* copy the folder to `C:\xampp\htdocs\practical13` and open http://localhost/practical13/.
**Configuration:** `db.php` uses XAMPP's defaults (`127.0.0.1:3306`, user `root`, empty password). To change them, copy `config.example.php` to `config.local.php` (ignored by Git). No login is needed for this practical.

---

### 🗄️ Database (`studenthub_prac13.events`, InnoDB, utf8mb4)
| Column | Type | Rules |
|---|---|---|
| `event_id` | INT UNSIGNED AUTO_INCREMENT | primary key |
| `title` | VARCHAR(120) | required, 3–120 characters (CHECK ≥ 3); index |
| `description` | VARCHAR(1000) | required, 10–1000 characters |
| `category` | VARCHAR(30) | CHECK: Cultural, Hackathon, Seminar, Sports, Technical, Workshop; index |
| `event_date`, `start_time` | DATE, TIME | valid date 2000–2100, time HH:MM; composite index |
| `venue` | VARCHAR(120) | required, 2–120 characters |
| `capacity` | SMALLINT UNSIGNED | CHECK 1–5000 |
| `status` | ENUM('open','closed') | default `open` |
| `created_at`, `updated_at` | DATETIME | `updated_at` changes on every update |

Seed data: **12 fictional events (9 open, 3 closed)**.

---

### 🔌 JSON API (`api.php`)
| Request | Body | Success (HTTP 200) |
|---|---|---|
| `GET api.php?action=list[&q=text][&category=…]` | – | `{"ok":true,"count":…,"total":…,"events":[…]}` |
| `GET api.php?action=get&id=5` | – | `{"ok":true,"event":{…}}` |
| `POST api.php?action=create` | JSON event | `{"ok":true,"message":"Event “…” was added.","event":{…}}` |
| `POST api.php?action=update` | JSON event + `event_id` | `{"ok":true,"message":"Event “…” was updated.","event":{…}}` |
| `POST api.php?action=delete` | `{"event_id":5}` | `{"ok":true,"message":"Event “…” was deleted.","deleted_id":5}` |

**Errors** are JSON too: `{"ok":false,"error":"…","errors":{"field":"message"}}` with **422** (validation), **404** (unknown event), **405** (wrong method, with `Allow` header), **415** (body not JSON), **400** (invalid JSON / id / action) or **500** (server problem – general message only, details in the PHP log). POST requests must send `Content-Type: application/json` and `X-Requested-With: fetch`, so a plain HTML form on another website cannot change data.

**Search:** `q` is matched against title, venue, category and description with `LIKE ?` (the user's `%` and `_` are searched literally). In the page the search box is **debounced** – the request is sent 350 ms after the last key press, and an older, still-running search is cancelled with an `AbortController`.

---

### 🔐 Security
MySQLi **prepared statements** for every query (no `query()`); server-side validation of every field before any INSERT/UPDATE; JSON encoded with `JSON_HEX_TAG|AMP|APOS|QUOT`; the page inserts all data with **`textContent`** (never `innerHTML`), so HTML in a title is shown as text; Content-Security-Policy in `index.html`; `nosniff` and `no-store` on API responses; central exception handler – no SQL or connection details ever reach the browser; `schema.sql`, `README.md`, config files, tests and screenshots answer HTTP 403.

---

### 🧪 Testing
With MySQL running, in the `Practical-13` folder: **`python tests\test_app.py`** – creates the disposable database `studenthub_prac13_test` from `schema.sql`, starts two PHP servers (normal; MySQL unreachable), tests the API and the source files, and removes the test database. `studenthub_prac13` is not changed.

**Result: 89 of 89 automated checks passed** (PHP 8.2.12, MariaDB 10.4.32, Windows 11); `php -l` found no syntax errors in the 4 PHP files. Output: [`tests/test_output.txt`](tests/test_output.txt), test cases: [`tests/TEST_CASES.md`](tests/TEST_CASES.md).

| Area | Checks |
|---|---|
| Required files, `php -l`, MySQLi + prepared statements, Fetch/debounce/textContent in `script.js`, page structure | 13 |
| Database: 12 events (9/3), InnoDB, indexes, CHECK constraints | 5 |
| GET list (JSON, fields, types, order) | 4 |
| Search and category filter (name/venue/category, case-insensitive, `%`/`_` literal, combined, invalid category) | 9 |
| GET one event (404 / 400 cases) | 6 |
| POST create (valid, empty → 8 field errors, 13 invalid values, nothing stored) | 17 |
| POST update (valid, invalid, unknown id, injected id) | 5 |
| POST delete (valid, again → 404, invalid id) | 3 |
| Methods, headers and JSON errors (405, 415, 400) | 8 |
| SQL injection and XSS | 6 |
| Protected files → 403 | 8 |
| Server log, MySQL unreachable → JSON 500, test database removed | 5 |

**Browser test in Microsoft Edge:** `tests\browser_screenshots.py` (Playwright) – **13 of 13 checks passed** ([`tests/browser_output.txt`](tests/browser_output.txt)): list loaded by fetch; add, update and delete send POST requests and change the table **without reloading the page** (a marker variable survives and the page navigates only once); delete asks for confirmation; typing `lab` key by key sends **one** debounced request; the loading indicator appears with real network throttling; a server 422 error is shown; HTML in a title is displayed as text; no JavaScript errors.

---

### 📸 Screenshots (`screenshots/`, 12 genuine captures, Microsoft Edge)
`event-list.png`, `add-event-form.png`, `successful-add.png`, `edit-event-form.png`, `successful-update.png`, `delete-confirmation.png`, `successful-delete.png`, `loading-state.png` (real throttling: 2.5 s latency via the DevTools protocol), `error-state.png` (HTTP 422 from the API), `network-get-json.png`, `network-post-add.png`, `network-crud-operations.png`.

The first nine come from `tests\browser_screenshots.py`. The three Network screenshots show the **real Edge DevTools**: `tests\network_screenshots.py` opens the app in a headless Edge, connects Edge's own DevTools front end to it (with a live screencast of the page) and presses the app's buttons, so every listed request is a genuine `fetch()` from `script.js` to `api.php`. Each shows the request in the Network panel (method, **200 OK**, `Content-Type: application/json`) and its real JSON response opened with *Open in Sources panel*. Both scripts change data, so `schema.sql` was re-imported afterwards.

Report: `PRAC_13_ITUE203_25CS023.docx` and `PRAC_13_ITUE203_25CS023.pdf`.

---

### ⚠️ Limitations
- No login (not required for this practical) – anyone who can open the page can change events.
- No pagination; the list shows every matching event.
- Tested with the PHP built-in server, MariaDB 10.4 and Microsoft Edge; XAMPP Apache, MySQL 8 and other browsers were not tested.
