<div align="center">
  <h1>🎓 Practical 6</h1>
  <h3>Rendering External JSON Data using Fetch API, Search and Filter</h3>
</div>

---

### 👨‍🎓 Student Information
- **Name:** Shreyas
- **ID:** 25CS023
- **Course:** ITUE203 - WEB DEVELOPMENT FRAMEWORKS
- **Year:** 2026-27

---

### 🎯 Objective
> Display students, events and FAQs from external JSON files using the Fetch API, with dynamic rendering, search, filter, sorting, pagination, loading and error handling, written as modular JavaScript.

---

### 🚀 How to Run (Windows)
The page loads its data with `fetch()` and uses JavaScript modules, which browsers block for pages opened by double-clicking (`file://`). It must be opened through a local web server. Python's built-in server is enough; no PHP or internet connection is needed.

**Requirement:** Python 3 ([python.org](https://www.python.org/downloads/); during installation tick **"Add python.exe to PATH"**). Check it in Command Prompt with `python --version`.

**Option A – double-click (easiest)**
1. Open the `Practical-6` folder and double-click **`start-server.bat`**.
2. A black window opens and the browser opens **http://127.0.0.1:8606/directory.html** after about 2 seconds. If the page shows "can't reach this page", press **F5** once.
3. Keep the black window open while using the page. To stop the server, click the black window and press **Ctrl+C** (or close it).

**Option B – Command Prompt**
1. Open Command Prompt in the `Practical-6` folder: in File Explorer, click the address bar, type `cmd` and press **Enter**.
2. Run:
   ```bat
   python -m http.server 8606 --bind 127.0.0.1
   ```
   If `python` is not recognised, try `py -3 -m http.server 8606 --bind 127.0.0.1`.
3. Open **http://127.0.0.1:8606/directory.html** in Edge or Chrome.
4. Stop the server with **Ctrl+C**.

**Notes**
- Port **8606** is used so the page does not clash with other local servers, for example a XAMPP/PHP server on port 8000. If 8606 is busy, use another number in both the command and the address (for example `8607`).
- Use `127.0.0.1` in the address, not `localhost`, so the request always reaches this Python server.
- **Copying to another computer:** copy the whole `Practical-6` folder (all paths are relative; nothing outside the folder is needed), install Python 3, then use Option A or B.
- If the page is opened by double-clicking `directory.html`, it shows these instructions instead of a broken page.

---

### 🗂️ Sample Data
`data/students.json`, `data/events.json` and `data/faqs.json` each contain **15 records** inside an object like this:
```json
{ "dataset": "students", "sampleData": true, "description": "SAMPLE DATA - ...", "records": [ ... ] }
```
- **All three datasets are sample data.** Student names, IDs (`DEMO-001` to `DEMO-015`) and CPI values are fictional, and no real roll numbers or classmates' details are used.
- Events are example events, not an official calendar. FAQ answers are general guidance; the HOD answer is role-based, without naming anyone.

---

### ✅ Features
| Feature | How it works | File |
|---|---|---|
| Fetch API | `fetch()` → checks `response.ok` → `response.json()` → checks that a `records` list exists; 8-second time limit | `assets/js/api.js` |
| Dynamic rendering | Table built with `createElement`/`textContent` (never `innerHTML`); readable column labels, formatted dates and CPI; table caption | `assets/js/render.js` |
| Search | Case-insensitive, in the text fields of each dataset (e.g. Student ID, name, branch); matches highlighted with `<mark>` | `assets/js/filters.js` |
| Filter | Branch (students) or category (events, FAQs); options built from the data | `filters.js`, `main.js` |
| Sorting | Students: name, CPI, semester · Events: date, title · FAQs: question, category; sorted column marked with `aria-sort` | `config.js`, `filters.js` |
| Pagination | 5, 10 or 15 rows per page; Previous / page numbers / Next with `aria-current`; resets to page 1 when the search, filter or sort changes | `filters.js`, `render.js` |
| Loading and errors | Loading message with spinner; error message with the reason and a **Retry** button; empty-result message with **Clear search and filter** | `main.js`, `render.js` |
| localStorage cache (advanced extension) | Each successful response is saved; if a later load fails, the saved copy is shown with a notice and the time it was saved | `api.js`, `main.js` |
| Race-condition guard | Switching tabs cancels the previous request (`AbortController`) and ignores any older response | `main.js` |
| Modular JavaScript | ES modules: `config.js` (dataset settings), `api.js` (fetch and cache), `filters.js` (search/filter/sort/paginate), `render.js` (DOM), `main.js` (connects them) | `assets/js/` |
| Accessibility | Tabs with `role="tab"` and arrow/Home/End keys; labelled controls; live regions for status and results; visible focus outline | `directory.html`, `main.js` |

**Testing tools** (bottom of the page, for demonstrating loading and errors):
- **Simulate a loading error:** requests a file that does not exist (a real 404 error).
- **Simulate a slow network:** adds a 3-second delay.
- **Clear saved copies:** empties the localStorage cache.

To show the error message: open *Testing tools* → **Clear saved copies** → tick **Simulate a loading error**. To show the saved-copy fallback instead, tick the error option without clearing.

---

### 📂 Files
```text
Practical-6/
├── directory.html            # page structure (no inline CSS or JS)
├── start-server.bat          # Windows: starts python -m http.server 8606 and opens the page
├── assets/css/style.css      # styles, system fonts, card layout on phones
├── assets/js/
│   ├── main.js               # entry module: tabs, controls, loading/error states
│   ├── config.js             # dataset definitions (URL, columns, search, filter, sort options)
│   ├── api.js                # fetchDataset() and the localStorage cache
│   ├── filters.js            # search, filter, sort, paginate (pure functions)
│   ├── render.js             # table, pagination and status messages
│   └── file-check.js         # shows the server instructions when opened as a file
├── data/students.json, events.json, faqs.json   # 15 sample records each
├── screenshots/              # Edge screenshots (see below)
└── source/check_page.py, contrast_check.py
```

---

### 🧪 Test Results
| Test | How | Result |
|---|---|---|
| Static checks: no inline CSS/JS, no external URLs, every module import resolves, ids and ARIA references exist, labelled controls, JSON files labelled as sample data with ≥15 records, fictional IDs only, no named individuals, fetch/cache/race-guard code present, no `innerHTML`, no `var` | [`source/check_page.py`](source/check_page.py) | 29 of 29 pass |
| Colour contrast (WCAG 2.1: 4.5:1 text, 3:1 borders and focus outline) | [`source/contrast_check.py`](source/contrast_check.py) | 22 of 22 pass |
| Features in Microsoft Edge 156 (headless), page served by Python's `http.server` | Real clicks, typing and select changes dispatched to the page; DOM, focus and localStorage checked; page errors, unhandled promise rejections and `console.error` recorded in every case | **93 of 93 checks pass**, no console errors |

The Edge tests covered:
- **All three datasets:** rendered with readable labels, 15 records each.
- **Search:**
  - match highlighting;
  - case-insensitive search, with extra spaces ignored;
  - search by Student ID;
  - the no-match message and its Clear button.
- **Filter:**
  - branch, events category and FAQ category;
  - filter combined with search.
- **Sorting:** by CPI (both directions), name (both directions), semester, event date (both directions) and FAQ question.
- **Pagination:**
  - Next, page numbers and Previous;
  - 10 and 15 rows per page;
  - reset to page 1 after a search;
  - focus stays on the pagination controls.
- **Loading:** loading message, busy state and the slow-network option.
- **Errors:**
  - a 404 with Retry;
  - a saved localStorage copy shown when loading fails;
  - Clear saved copies;
  - malformed JSON, JSON without a `records` list and a server 500 error;
  - the 8-second time-out.
- **Tab switching:** a slow, older response is ignored when switching tabs quickly.
- **Keyboard:** arrow/Home/End keys move between the tabs.
- **375px layout:** no horizontal scrolling.
- **Opened as a file (`file://`):** the server instructions are shown.

**Screenshots** ([`screenshots/`](screenshots/)):
| Teams requirement | File |
|---|---|
| JSON data displayed | `json-data.png` (students), `events-data.png`, `faqs-data.png` |
| Search result | `search.png` – students matching "an", highlighted |
| Filter result | `filter.png` – events in the Seminar category |
| Sorting result | `sort.png` – students by CPI, high to low |
| Pagination | `pagination.png` – students, page 2 of 3 |
| Loading / error message | `loading.png`, `error.png` (404 with Retry), `cached-copy.png` (saved localStorage copy shown after a failed load) |
| Extra | `mobile-375.png` – card layout on a 375px screen |

**Not tested:**
- A person using a real mouse and keyboard; events were dispatched by script, and real Tab-key movement was not simulated.
- Screen readers.
- Browsers other than Edge.
- Real phones.
- The W3C validator.
- `start-server.bat` was tested on this PC with its `nobrowser` option (server started and the files were served); the automatic browser opening was not tested.

```bat
python source\check_page.py
python source\contrast_check.py
```
