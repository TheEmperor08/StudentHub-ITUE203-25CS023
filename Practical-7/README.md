<div align="center">
  <h1>🎓 Practical 7</h1>
  <h3>PHP Form Processing with Server-Side Validation and JSON File Storage</h3>
</div>

---

### 👨‍🎓 Student Information
- **Name:** Shreyas
- **ID:** 25CS023
- **Course:** ITUE203 - WEB DEVELOPMENT FRAMEWORKS
- **Year:** 2026-27

---

### 🎯 Objective
> Process a student inquiry (contact) form with PHP: submit it with POST, validate and sanitise every field on the server, store valid records in a JSON file with file locking, and show clear success and error messages.

---

### 🚀 How to Run (Windows + XAMPP)
**Requirement:** XAMPP installed in `C:\xampp` (PHP 8.1 or newer; tested with XAMPP's PHP 8.2.12).

**Option A – PHP built-in server (easiest, used for testing)**
1. Double-click **`start-server.bat`** in the `Practical-7` folder. It uses `C:\xampp\php\php.exe` (or `php` from PATH) and opens **http://127.0.0.1:8607/index.php** after about 2 seconds. If the page shows "can't reach this page", press **F5** once.
2. Or, in Command Prompt inside the `Practical-7` folder:
   ```bat
   C:\xampp\php\php.exe -S 127.0.0.1:8607 router.php
   ```
   then open **http://127.0.0.1:8607/index.php**.
3. Keep the window open; stop the server with **Ctrl+C**.

`router.php` makes the built-in server refuse `private/`, `includes/`, `tests/` and hidden files (403), like the `.htaccess` files do on Apache.

**Option B – XAMPP Apache**
1. Copy the whole `Practical-7` folder to `C:\xampp\htdocs\practical7`.
2. Start **Apache** in the XAMPP Control Panel.
3. Open **http://localhost/practical7/index.php**.

`private/.htaccess` and `includes/.htaccess` (`Require all denied`) keep the JSON file and include files from being downloaded. *Option B was not tested for this practical; only Option A was tested.*

**Another computer:** copy the `Practical-7` folder (all paths are relative), install XAMPP, and use Option A or B. The `private/` folder must be writable by PHP; the JSON file is created automatically.

---

### ✅ What It Does
| Requirement | Implementation | File |
|---|---|---|
| PHP form | Student inquiry form: full name, email, category, message | `index.php` |
| POST submission | `<form method="post">` posts to `index.php`; data is processed only when `$_SERVER['REQUEST_METHOD'] === 'POST'` | `index.php` |
| Server-side validation | Required fields; name 2–60 letters (`/^\p{L}[\p{L} .'-]*$/u`); `filter_var(FILTER_VALIDATE_EMAIL)`; category must be in the allowed list; message 10–1000 characters; invalid UTF-8 rejected. The form has `novalidate`, so the browser's own checks do not hide the server validation | `includes/functions.php` |
| Sanitisation | Fields read only as text (arrays rejected); control characters removed; spaces trimmed and tidied; email in lower case; HTML is not trusted – every value is escaped with `htmlspecialchars()` (`e()`) when it is shown | `includes/functions.php` |
| JSON storage | Records appended to `private/submissions.json` (pretty-printed list) under an exclusive `flock()` lock; a missing file/folder is created; a damaged file is backed up as `submissions.corrupt-<time>.json` and a new list is started | `includes/storage.php` |
| Success message | Post/Redirect/Get: after saving, a 303 redirect shows "Inquiry submitted successfully" with the reference (e.g. SUB-0005) once; refreshing cannot submit twice | `index.php` |
| Error messages | HTTP 422; summary "Please correct N fields" with links, a message under each field, `aria-invalid`, entered values kept | `index.php` |
| Display stored records (intermediate extension) | Table of all records + the JSON file contents, all escaped | `records.php` |
| CSRF token (advanced extension) | Random token in the session and a hidden field, checked with `hash_equals()`; a new token after each successful submission | `includes/functions.php` |

**Stored record example**
```json
{ "id": "SUB-0001", "submitted_at": "2026-10-30T14:10:50+05:30", "name": "Eshan Kapoor",
  "email": "eshan.kapoor@example.com", "category": "portal", "message": "I cannot open the attendance page after logging in." }
```
No IP address or browser details are stored.

**Privacy:** real submissions in `private/` are ignored by Git (`Practical-7/.gitignore`) and blocked from browsers. `sample-output/submissions.sample.json` is the file generated during the screenshot run, containing only fictional people with `example.com` addresses.

---

### 📂 Files
```text
Practical-7/
├── index.php                 # form + POST processing (validation, CSRF, storage, messages)
├── records.php               # stored submissions table and JSON view
├── includes/functions.php    # e(), sanitising, validation, CSRF helpers
├── includes/storage.php      # JSON read/append with flock(), missing/damaged file handling
├── assets/css/style.css
├── router.php                # protects private/ and includes/ on PHP's built-in server
├── start-server.bat          # Windows: start XAMPP's PHP server on port 8607
├── private/                  # submissions.json (created at run time, not committed) + .htaccess
├── sample-output/submissions.sample.json
├── screenshots/              # form-ui, validation-error, successful-submission, json-stored-data
└── tests/test_form.py        # automated server-side tests
```

---

### 🧪 Testing
Run the automated tests (Python 3, standard library only; they start XAMPP's PHP themselves and use a separate temporary JSON file, so `private/submissions.json` is never touched):
```bat
python tests\test_form.py
```

**Result: 63 of 63 checks passed** (PHP 8.2.12, Windows 11). Every `.php` file also passes `php -l`.

| # | Test case | Input | Expected and actual result |
|---|---|---|---|
| 1 | Form opens | GET `index.php` | 200, POST form with 4 labelled fields and a CSRF token – **pass** |
| 2 | Empty submission | all fields empty | 422, "Please correct 4 fields", one message per field, nothing stored – **pass** |
| 3 | Invalid email | `abc@`, `name@domain`, `a b@example.com`, `@example.com`, 107-character address | 422, "Please enter a valid email address…", other values kept, nothing stored – **pass** |
| 4 | Invalid input | name `R2D2`, `A`, 61 characters; category `hacker`; message `Too short`, 1001 characters; `name[]` array; invalid UTF-8 | 422 with the matching message, nothing stored – **pass** |
| 5 | Valid submission | Aarohi Menon, valid email, category, message | 303 → success message with reference SUB-0001, shown only once – **pass** |
| 6 | JSON storage | after test 5 | valid pretty JSON list; fields id, submitted_at, name, email, category, message; name spaces tidied, email lower-case – **pass** |
| 7 | Multiple submissions | 3 one after another, then 10 at the same time | 14 records, IDs SUB-0001 to SUB-0014 unique, file still valid (flock) – **pass** |
| 8 | Safe display | name `Anne-Marie O'Neil`; message `<script>alert("XSS")</script> Marks < 40 & "quotes"` | shown as text (`&lt;script&gt;…`), no `<script>` tag in the page; JSON stores `\u003Cscript\u003E` – **pass** |
| 9 | CSRF | no token / wrong token / reused token | 400 with a clear message, nothing stored – **pass** |
| 10 | Storage problems | file deleted; `{ not JSON`; `{"not":"a list"}`; missing folder | handled: "No submissions yet", damaged file backed up and replaced, folder created – **pass** |
| 11 | Private files | `/private/submissions.json`, `/PRIVATE/…`, `/private%5C…`, `/includes/…`, `/tests/…`, `/.gitignore`, `/router.php` | 403 – **pass** |
| 12 | GET does not store | form data in the URL | nothing stored – **pass** |
| 13 | PHP errors | server log | no warnings, notices or errors – **pass** |

**Screenshots** (`screenshots/`, genuine Microsoft Edge 156 renders of the running PHP application; the form was filled in and submitted by a script inside the page):
- `form-ui.png` – the empty form
- `validation-error.png` – server-side errors for name `R2D2`, email `abc@`, no category, message `Hi`
- `successful-submission.png` – success message with reference SUB-0005
- `json-stored-data.png` – `records.php` with 5 stored records and the JSON file contents (including the escaped `<script>` text)

**Not tested:** XAMPP Apache (Option B), other browsers, screen readers, real phones, and a person using a real keyboard and mouse.
