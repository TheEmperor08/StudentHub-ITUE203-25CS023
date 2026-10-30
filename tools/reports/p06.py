"""Corrected report – Practical 6: JSON + Fetch API, as integrated into the portal's Campus Data Explorer (studenthub/data_explorer.php)."""
from report_lib import corrected_notice

META = {
    "number": 6,
    "title": "Rendering External JSON Data using Fetch API, Search and Filter",
    "tech": "JavaScript (ES6+) · Fetch API · JSON · HTML5 · CSS3 · PHP 8 (page and access control)",
    "supersedes": "Practical-6/PRAC_6_ITUE203_25CS023.docx",
    "replaces_note": "The original described the standalone Practical-6/directory.html served by Python; the JSON datasets are now "
                     "rendered on the portal's Campus Data Explorer page (studenthub/data_explorer.php).",
}

SHOTS = "evidence/practical-05-07-integration/"
FIG_W = 14.0      # cm – lets two screenshots share a page while staying readable


def build(r):
    corrected_notice(
        r, META["supersedes"],
        "The original report described the standalone page `Practical-6/directory.html` (five ES modules, served by Python's "
        "http.server). This version describes the Campus Data Explorer of the portal – `studenthub/data_explorer.php` with "
        "`studenthub/assets/js/data.js` – which reads the same anonymised Practical 6 datasets (copied into `studenthub/data/`) "
        "but is simpler than the standalone page; every difference is listed in Section 10.")

    # ------------------------------------------------------------------ 1
    r.heading("1. Aim and Objectives")
    r.para("To display students, events and FAQs from external JSON files inside the StudentHub portal using the JavaScript Fetch API, "
           "with dynamic rendering, search, filtering, sorting and pagination, and with clear loading and error states.")
    r.bullets([
        "Load three JSON datasets (students, events, FAQs – Practical 6's sample data, 15 records each) with `fetch()` and render "
        "them as tables.",
        "Implement search, filter, sort and pagination with JavaScript array methods (`filter`, `some`, `includes`, `sort`, `slice`, "
        "`forEach`) and a `Set` for the filter options.",
        "Show a loading message while a file is being fetched and an error message with the reason when loading fails.",
        "Show each file's own “SAMPLE DATA” description, so the user always sees that the records are invented.",
        "Escape every value from the JSON files before it is inserted into the page.",
        "Make the page a normal part of the portal: portal layout and sidebar link, available to signed-in users only.",
    ])
    r.para("The advanced extension of the standalone version (a localStorage cache of the last response) and its ES-module structure "
           "were not carried over; see Section 10.")

    # ------------------------------------------------------------------ 2
    r.heading("2. Problem Definition")
    r.para("Official problem definition: “Display event lists, student profiles, notices, or FAQs from external JSON files using "
           "Fetch API. Implement dynamic rendering, search, filter, sorting, and pagination.”")
    r.para("Practical 6 was first built as the standalone page `Practical-6/directory.html`. In the integrated portal the audit in "
           "`TEST_REPORT.md` (section 12) found that “`assets/js/data.js` and `data/*.json` existed but **no page used them**”. The "
           "integration therefore added the Campus Data Explorer page `data_explorer.php`; at the same time `data.js` was changed to "
           "escape every value, and the artificial 800 ms delay it contained was removed. After the report review the portal's "
           "earlier JSON files were replaced by Practical 6's own anonymised sample datasets (`DEMO-001` … `DEMO-015`), and "
           "`data.js` was extended to read their format and to show each file's description above the table (`TEST_REPORT.md` "
           "section 13).")
    r.para("The practical list asks four key questions; the answers for the integrated implementation are:")
    r.table([
        ["Key question", "Answer in the integrated portal"],
        ["How is JSON fetched, parsed, and rendered?",
         "`fetchData()` calls `fetch()` with the template literal `data/${type}.json`, checks `response.ok`, parses the body with "
         "`response.json()`, keeps the `records` list in `currentData` and shows the file's `description` with `showNote()`. "
         "`renderTable()` builds the table head from the keys of the first record and one row per record, with every value "
         "escaped by `esc()`."],
        ["Which array methods are used for search, filter, sort, and pagination?",
         "`filter()` with `Object.values(item).some()` and `includes()` for the search, `filter()` with equality on `branch` "
         "(students) or `category` (events and FAQs) for the filter, `sort()` with `localeCompare()` for the A–Z / Z–A order, "
         "`slice()` for the 5 rows of the current page, and `forEach()` with a `Set` to build the filter options."],
        ["How are loading and error states handled?",
         "`showLoading()` shows “⏳ Fetching Data from JSON...” in `#status-container` (an `aria-live=\"polite\"` region); "
         "`showError()` shows “Error loading data:” followed by the reason, with `role=\"alert\"`; when nothing matches, “No "
         "records found.” is shown."],
        ["How is modularity maintained in JavaScript files?",
         "All behaviour is in one file, `data.js`, inside a `DOMContentLoaded` handler, split into functions with one task each "
         "(`fetchData`, `populateFilterOptions`, `applyFilters`, `renderTable`, `renderPagination`, `showNote`, `showLoading`, "
         "`showError`). The PHP page contains only the empty containers. Unlike the standalone version, it is not split into ES "
         "modules."],
    ], [5.2, 10.8])

    # ------------------------------------------------------------------ 3
    r.heading("3. Tools and Technologies")
    r.table([
        ["Tool / technology", "Use in this practical"],
        ["HTML5 + PHP 8.2.12 (XAMPP)", "`studenthub/data_explorer.php`: page structure, access check, sidebar"],
        ["CSS3", "`studenthub/assets/css/global.css`: tabs, toolbar, status messages and table of the Data Explorer"],
        ["JavaScript (ES6+)", "`studenthub/assets/js/data.js`: Fetch API, async/await, array methods, template literals"],
        ["JSON", "`studenthub/data/students.json`, `events.json`, `faqs.json` – Practical 6's sample datasets, 15 records each"],
        ["Python 3 (standard library)", "`tests/test_forms.py`: HTTP tests against the PHP built-in server"],
        ["Playwright + Microsoft Edge (headless)", "`tests/browser_forms.py`: browser checks and the screenshots in Section 8"],
        ["Git / GitHub", "Version control; the integration is commit `938e74f` of the StudentHub repository, the later switch to "
                         "the Practical 6 datasets is described in `TEST_REPORT.md` section 13"],
        ["Operating system", "Windows 11"],
    ], [5.2, 10.8])

    # ------------------------------------------------------------------ 4
    r.heading("4. Place in the Integrated StudentHub Portal")
    r.para("The Data Explorer is a normal portal page in the *Campus* group of the sidebar (“Data Explorer”, `sidebar.php` line 23), "
           "next to Notices, the Event Finder, the Directory and Help & Contact. It uses the portal's layout, theme and session.")
    r.table([
        ["File / route", "Role"],
        ["`studenthub/data_explorer.php` (route `data_explorer.php`)",
         "The page: header, “Sample data” note, three dataset buttons, search / filter / sort controls and the containers for "
         "status, table and pagination. Requires the permission `portal.view`."],
        ["`studenthub/assets/js/data.js`", "The Practical 6 script (loaded with `defer`)."],
        ["`studenthub/data/students.json`, `events.json`, `faqs.json`",
         "The external JSON datasets – byte-for-byte copies of `Practical-6/data/*.json`."],
        ["`studenthub/assets/css/global.css`", "Styles under the comment “Campus Data Explorer (Practical 6)”."],
        ["`studenthub/sidebar.php`", "The sidebar link."],
        ["`tests/test_forms.py`, `tests/browser_forms.py`", "Tests of the integration (Section 9)."],
    ], [5.8, 10.2])
    r.para("Access is controlled by the portal's integrated login (Practicals 9 and 10): `require_permission(\"portal.view\")` admits "
           "the roles admin, editor and student and sends a visitor who is not signed in to the login page.")
    r.excerpt("studenthub/data_explorer.php", "Campus Data Explorer (Practical 6 integrated)", 'require_permission("portal.view")',
              "purpose of the page and access check")
    r.para("The note on the page states that the records are sample data and points to the pages with the live database records: "
           "the Directory (students) and the Event Finder (`events_live.php`, Practical 13), which also uses `fetch()` but reads the "
           "database through the portal's JSON API `api/events.php`. The Data Explorer complements it by demonstrating client-side "
           "rendering of static JSON files.")

    # ------------------------------------------------------------------ 5
    r.heading("5. Implementation")
    r.heading("5.1 The page and its containers", 2)
    r.para("The three buttons carry the dataset name in `data-type`. The page itself contains no data: the table, the dataset "
           "description, the status messages and the page buttons are produced by `data.js`. Without JavaScript the `noscript` "
           "message “The Data Explorer needs JavaScript.” is shown.")
    r.excerpt("studenthub/data_explorer.php", '<div class="explorer-tabs"', "</div>", "the three dataset buttons")
    r.para("Between the buttons and the containers (lines 42–47) is the toolbar with three labelled controls: a search box "
           "(`type=\"search\"`, id `searchInput`, with autocomplete switched off), the filter select `#filterSelect` (first option "
           "“All Categories/Branches”) and the sort select `#sortSelect` with the options Default order, Name A–Z and Name Z–A. Then "
           "follow the containers:")
    r.excerpt("studenthub/data_explorer.php", '<div id="status-container"', "<noscript>",
              "status, table and pagination containers and the noscript message")

    r.heading("5.2 JSON datasets", 2)
    r.para("The three files are identical copies of the datasets of the standalone `Practical-6/data/` folder. Each is a JSON object "
           "that labels itself as sample data: `dataset` (its name), `sampleData: true`, `description` (a sentence beginning "
           "“SAMPLE DATA - …”) and `records`, a list of 15 objects. The student file, for example, describes itself as “SAMPLE DATA - "
           "fictional students created for ITUE203 Practical 6. All names, IDs (DEMO-001 to DEMO-015) and CPI values are invented "
           "and do not belong to real people.”")
    r.table([
        ["File", "Records", "Fields", "Filter", "Sorted by"],
        ["`students.json`", "15", "id (DEMO-001 … DEMO-015), name, branch, semester, cpi", "branch (CE, CSE, IT)", "name"],
        ["`events.json`", "15", "id, title, date (yyyy-mm-dd), venue, category",
         "category (Cultural, Hackathon, Seminar, Social, Sports, TechFest, Workshop)", "title"],
        ["`faqs.json`", "15", "id, category, question, answer",
         "category (Academics, Attendance, Campus, Exams, Fees, Hostel, Portal)", "question"],
    ], [2.4, 1.5, 4.6, 5.1, 2.4])

    r.heading("5.3 Fetching and parsing the JSON (Fetch API)", 2)
    r.para("`fetchData()` is an `async` function: it shows the loading state, awaits the response, treats any status outside 200–299 "
           "as an error (`response.ok`) and parses the JSON. It then takes the `records` list (a plain array would be accepted as it "
           "is), shows the file's `description` with `showNote()`, and builds the filter options from the data with a `Set`, so each "
           "branch or category appears once. Any exception – a failed request, a bad status or invalid JSON – is caught and shown as "
           "an error message. The same function is called when the page loads (students) and whenever a dataset button is clicked; "
           "a click also clears the search and resets the sort order.")
    r.excerpt("studenthub/assets/js/data.js", "async function fetchData(type)", "// Filter, Search, and Sort Logic",
              "fetchData() and populateFilterOptions()")

    r.heading("5.4 Search, filter and sorting", 2)
    r.para("`applyFilters()` runs on every key press in the search box and on every change of the filter or sort select. It never "
           "changes `currentData`; it builds `filteredData` from it and always returns to page 1.")
    r.bullets([
        "**Search:** case-insensitive (`toLowerCase()`), matched against every value of a record – including the ID, numbers such "
        "as the semester, and for FAQs the answer text.",
        "**Filter:** equality on `branch` (students) or `category` (events and FAQs).",
        "**Sort:** “Name A–Z” / “Name Z–A” compare the `name`, `title` or `question` field with `localeCompare()`; “Default order” "
        "keeps the order of the file.",
    ])
    r.excerpt("studenthub/assets/js/data.js", "function applyFilters()", "renderTable();", "search, filter and sort")

    r.heading("5.5 Dynamic rendering", 2)
    r.para("`renderTable()` computes the number of pages, takes the 5 records of the current page with `slice()`, and builds the "
           "table: one `<th scope=\"col\">` per key of the first record (upper-cased) and one row per record. Each value passes through "
           "`esc()` before it is placed in the HTML string; a CPI of 9 or more is additionally wrapped in `<mark>`.")
    r.excerpt("studenthub/assets/js/data.js", "function renderTable()", "renderPagination(totalPages);", "renderTable()")

    r.heading("5.6 Pagination", 2)
    r.para("`renderPagination()` creates Previous, one button per page and Next; Previous is disabled on the first page and Next on "
           "the last; the current page button gets the class `active`. When all results fit on one page, no page buttons are shown.")
    r.excerpt("studenthub/assets/js/data.js", "function renderPagination(totalPages)", "// The dataset's own description",
              "renderPagination()")

    r.heading("5.7 Dataset description, loading and error states", 2)
    r.para("`showNote()` creates a `<p id=\"dataset-note\">` above the table once and writes the file's description into it with "
           "`textContent`, so the text can never be interpreted as HTML; the paragraph is hidden when a file has no description. The "
           "loading message is placed in `#status-container`, which is an `aria-live=\"polite\"` region, and the table and page "
           "buttons are cleared while a file is loading. The error message is escaped, because it contains the text of the caught "
           "exception.")
    r.excerpt("studenthub/assets/js/data.js", "// The dataset's own description", 'role="alert"',
              "showNote(), showLoading() and showError()")

    # ------------------------------------------------------------------ 6
    r.heading("6. Database and Relationships")
    r.para("Practical 6 uses no database table. The Data Explorer reads three static JSON files with `fetch()`; nothing is written "
           "and nothing is stored in the browser. The only server-side rule is the access check of `data_explorer.php`: "
           "`require_permission(\"portal.view\")` uses the signed-in session (the role comes from `users.role`).")
    r.para("The live student and event records of the portal remain in the `students` and `events` tables of `studenthub_db` and are "
           "shown on the Directory and the Event Finder pages. The JSON files contain only invented sample records and are not "
           "connected to those tables, which is why the page labels them as sample data and links to the live pages.")

    # ------------------------------------------------------------------ 7
    r.heading("7. Validation and Security")
    r.bullets([
        "**Escaping:** `esc()` replaces `&`, `<`, `>`, `\"` and `'` with HTML entities. It is applied to every table value, every "
        "column heading, every filter option and the error text, so text in a JSON file can never run as HTML; the dataset "
        "description is inserted with `textContent`. The escaping was added during the integration (`TEST_REPORT.md` section 12: "
        "“`data.js` now escapes every value”).",
        "**Response checks:** a status outside 200–299 and invalid JSON both end in the error message instead of a broken page.",
        "**Fixed URLs:** the dataset name in the request comes from the `data-type` attribute of the three buttons in the page, not "
        "from free user input.",
        "**Access:** the page requires sign-in. The JSON files themselves are static files that the server delivers without a "
        "session – the HTTP test fetched them without signing in – so they must never contain private data; they contain only the "
        "invented sample records described in Section 5.2.",
    ])
    r.excerpt("studenthub/assets/js/data.js", "document.addEventListener('DOMContentLoaded'", "const itemsPerPage = 5;",
              "the esc() function and the state of the explorer")

    # ------------------------------------------------------------------ 8
    r.heading("8. Output Screenshots")
    r.para("All screenshots are genuine full-page captures of `studenthub/data_explorer.php` in Microsoft Edge (headless, driven by "
           "Playwright, viewport 1280 × 900 px), made by `tests/browser_forms.py` on 31 October 2026 against the PHP built-in server and "
           "a disposable database, after the switch to the Practical 6 datasets. The signed-in user “Riya Shah” (26IT041) is a "
           "fictional test account created by the test. For the loading screenshot the test holds the request for "
           "`data/students.json` in its own network layer until the screenshot has been taken and then releases it, so the response "
           "is the real file; this capture replaces an earlier one that had been saved only after the data had loaded "
           "(`TEST_REPORT.md` section 13).")
    r.figure(SHOTS + "04-data-explorer-loading.png",
             "Loading state: while the request for data/students.json is still pending, the status area shows “⏳ Fetching Data from "
             "JSON...” below the controls; no table, description or page buttons are shown yet.", width=FIG_W)
    r.figure(SHOTS + "05-data-explorer-students.png",
             "Students dataset loaded: the file's own description (“SAMPLE DATA - fictional students created for ITUE203 Practical "
             "6. All names, IDs (DEMO-001 to DEMO-015) and CPI values are invented …”) above the table; page 1 of 3 with DEMO-001 to "
             "DEMO-005, columns taken from the JSON keys (ID, NAME, BRANCH, SEMESTER, CPI), and the CPI 9.21 highlighted with <mark>.",
             width=FIG_W)
    r.figure(SHOTS + "06-data-explorer-search-filter.png",
             "Search “aar” (a term the test derives from the data) combined with the branch filter CSE: exactly one record remains, "
             "DEMO-003 Aarohi Menon (CSE, semester 3, CPI 8.42); no page buttons are shown because the result fits on one page.",
             width=FIG_W)
    r.figure(SHOTS + "07-data-explorer-events-sorted.png",
             "Events dataset (ID, TITLE, DATE, VENUE, CATEGORY) with its own SAMPLE DATA description, sorted “Name Z–A” by title: Web "
             "Development Bootcamp, Technical Fest Opening, Robotics Expo, Python Workshop, Open Source Contribution Month on page 1 "
             "of 3.", width=FIG_W)

    # ------------------------------------------------------------------ 9
    r.heading("9. Testing and Results")
    r.para("Environment of the recorded runs (31 October 2026): Windows 11, PHP 8.2.12 (XAMPP) built-in server on 127.0.0.1, MariaDB "
           "10.4.32 for the disposable test database, Microsoft Edge in headless mode through Playwright. The complete run of all "
           "suites after these changes (`tests/run_all_output.txt`) passed 841 checks with 0 failures.")
    r.table([
        ["Suite", "Scope", "Result", "Output file"],
        ["`tests/test_forms.py`", "HTTP tests of Practicals 5, 6 and 7 in the portal; 6 checks concern Practical 6",
         "**41 / 41 passed**", "`tests/test_forms_output.txt`"],
        ["`tests/browser_forms.py`", "Microsoft Edge checks and screenshots of Practicals 5–7; 5 checks concern Practical 6, two "
                                     "more cover the whole run (no JavaScript errors, no PHP warnings)",
         "**15 / 15 passed**", "`tests/browser_forms_output.txt`"],
    ], [4.0, 6.6, 2.4, 3.0])
    r.para("Practical 6 checks, copied from the saved outputs:")
    r.bullets([
        "data_explorer.php (signed in) has the tabs, search, filter, sort, status, table and pagination containers and loads data.js "
        "– PASS",
        "not signed in: redirected to the login page – PASS",
        "the sidebar links to the Data Explorer – PASS",
        "data/students.json, events.json and faqs.json are Practical 6's sample datasets (sampleData, description, 15 records each) "
        "– PASS",
        "the student dataset uses invented DEMO-001 … DEMO-015 ids (no real enrollment numbers) – PASS",
        "data.js fetches the JSON, handles errors, escapes every value and paginates (5 per page) – PASS",
        "Edge: Data Explorer: loading state while students.json is fetched (no table yet) – PASS",
        "Edge: the dataset's own 'SAMPLE DATA' description is shown above the table – PASS",
        "Edge: students rendered from JSON: 5 rows per page with pagination – PASS",
        "Edge: search 'aar' + branch filter CSE -> exactly the 1 matching CSE student(s) – PASS",
        "Edge: events tab sorted Z–A – PASS",
        "Edge (whole run): no JavaScript errors; no PHP warnings or errors in the server log – PASS",
    ])
    r.para("Note on the method: the sixth HTTP check searches the source of `data.js` for `fetch`, the use of `data.records`, "
           "`response.ok`, the `catch` block, the escaping of each value and the page size, and confirms that the old 800 ms delay "
           "is gone; the behaviour is checked in Edge.")
    r.heading("9.1 Not tested", 2)
    r.bullets([
        "The error state was not produced in a browser; it is covered only by the source check above, so there is no screenshot of "
        "an error message.",
        "The FAQs dataset (and its category filter) was checked over HTTP but not opened in Edge.",
        "Keyboard-only use, screen readers, browsers other than Edge and narrow (mobile) widths.",
    ])

    # ------------------------------------------------------------------ 10
    r.heading("10. Differences from the Original Standalone Practical and Limitations")
    r.table([
        ["Aspect", "Standalone Practical-6 (original report)", "Integrated portal"],
        ["Page and server", "`directory.html`, Python http.server on port 8606, no login",
         "`data_explorer.php` in the portal; sign-in required"],
        ["Code structure", "five ES modules (config, api, filters, render, main)", "one script, `data.js`, with separate functions"],
        ["Data", "objects labelled as sample data with a `records` list; fictional DEMO-001… IDs",
         "the same three files (byte-identical copies); the description is shown above the table"],
        ["Search", "listed fields only, spaces trimmed, matches highlighted with <mark>",
         "all values of a record, not trimmed, no highlighting"],
        ["Filter", "branch, event category, FAQ category", "the same: branch, event category, FAQ category"],
        ["Sorting", "several fields in both directions, `aria-sort`", "one text field (name / title / question), A–Z or Z–A"],
        ["Pagination", "5, 10 or 15 rows; `aria-current`", "fixed 5 rows per page"],
        ["Loading / errors", "spinner, `aria-busy`, 8-second time-out, Retry button, error simulation panel",
         "text message; error with the reason; no Retry button and no time-out"],
        ["Cache (advanced)", "last response kept in localStorage", "none"],
        ["Fast switching", "request number + AbortController guard", "no guard against a slow, older response"],
        ["Tests", "29 static, 22 contrast and 93 Edge checks", "6 HTTP and 5 Edge checks within the 41 / 41 and 15 / 15 suites"],
    ], [3.0, 6.3, 6.7])
    r.heading("10.1 Limitations", 2)
    r.bullets([
        "**JavaScript required:** without JavaScript the page shows only the notice “The Data Explorer needs JavaScript.”",
        "**Sample data:** the JSON files are static sample files, not the portal's live records, and they are not kept in step with "
        "the database.",
        "**Public files:** the JSON files can be downloaded without signing in, although the page itself requires it; they contain "
        "only invented data.",
        "**No retry or cache:** after a failed request the user must click the dataset button again or reload the page.",
        "**Accessibility:** the dataset buttons are plain buttons in a `role=\"group\"` (not the ARIA tabs pattern of the "
        "standalone version), and the sorted column is not marked with `aria-sort`.",
    ])

    # ------------------------------------------------------------------ 11
    r.heading("11. Conclusion")
    r.para("The StudentHub portal now contains the Campus Data Explorer, `studenthub/data_explorer.php`, which loads Practical 6's "
           "anonymised students, events and FAQs datasets with the Fetch API and renders them as tables with search, filter, A–Z / "
           "Z–A sorting and pagination of 5 rows, all built with array methods. Each file's own “SAMPLE DATA” description is shown "
           "above the table, loading and error states are shown in a live region, every value from the files is HTML-escaped, and "
           "the page is reachable from the sidebar for signed-in users only.")
    r.para("The integrated version is deliberately simpler than the standalone one: the localStorage cache, the ES-module structure, "
           "the time-out and Retry button and the extra accessibility features remain in `Practical-6/`. The integration passed "
           "the HTTP suite (41 / 41) and the Edge suite (15 / 15), and the screenshots show the loading state, the loaded data with "
           "its description, a combined search and filter, and a sorted events list.")

    # ------------------------------------------------------------------ 12
    r.heading("12. References")
    r.bullets([
        "ITUE203 Web Development Frameworks – Practical List 2026-27, Practical 6: “Rendering External JSON Data using Fetch API, "
        "Search and Filter”, CSPIT, CHARUSAT.",
        "StudentHub repository: https://github.com/TheEmperor08/StudentHub-ITUE203-25CS023 – folders `studenthub/` (portal), "
        "`Practical-6/` (original standalone version and its datasets), `tests/`, `evidence/practical-05-07-integration/`; "
        "`TEST_REPORT.md` sections 12 and 13.",
        "MDN – Using the Fetch API: https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch",
        "MDN – Response.ok: https://developer.mozilla.org/en-US/docs/Web/API/Response/ok",
        "MDN – Array.prototype.filter(): https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/filter",
        "MDN – String.prototype.localeCompare(): "
        "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/String/localeCompare",
        "MDN – Node.textContent: https://developer.mozilla.org/en-US/docs/Web/API/Node/textContent",
        "MDN – ARIA live regions: https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/ARIA_Live_Regions",
    ])
