"""StudentHub – Practical 13: browser test + screenshots 1-9 (optional; needs  pip install playwright).

Drives the installed Microsoft Edge (headless, via Playwright) through the real page on http://127.0.0.1:8613/index.html
(start-server.bat) with the demo database studenthub_prac13. It checks that list, add, update, delete and search work
with Fetch requests to api.php WITHOUT reloading the page, that the search is debounced, and captures the screenshots.
The loading state is captured with real network throttling (DevTools protocol Network.emulateNetworkConditions).
It ADDS, EDITS and DELETES events, so re-import schema.sql afterwards.
Usage:  python tests\\browser_screenshots.py <screenshots folder>
"""
import pathlib, re, sys
from playwright.sync_api import sync_playwright

SHOTS = pathlib.Path(sys.argv[1])
SHOTS.mkdir(parents=True, exist_ok=True)
URL = "http://127.0.0.1:8613/index.html"
results = []


def check(name, ok):
    results.append(ok)
    print(("PASS  " if ok else "FAIL  ") + name)


with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 860})
    api_calls, console_errors, dialogs, navigations = [], [], [], []
    page.on("request", lambda r: api_calls.append((r.method, r.url, r.resource_type)) if "api.php" in r.url else None)
    page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
    page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
    page.on("framenavigated", lambda f: navigations.append(f.url) if f == page.main_frame else None)

    def shot(name, full=False):
        page.screenshot(path=str(SHOTS / name), full_page=full)

    def still_same_page():
        return page.evaluate("window.__pageMarker") == marker and len(navigations) == 1

    # 1 list loaded by fetch
    page.goto(URL)
    page.wait_for_selector("#event-rows tr[data-id]")
    marker = page.evaluate("window.__pageMarker = Math.random()")
    check("page loaded the list with fetch(GET api.php?action=list): 12 rows",
          page.locator("#event-rows tr[data-id]").count() == 12 and any(m == "GET" and "action=list" in u and t == "fetch" for m, u, t in api_calls))
    shot("event-list.png", full=True)

    # 2 add form, 3 added without reload
    page.click("#new-event-btn")
    page.fill("#title", "Hack Night 2027")
    page.select_option("#category", "Hackathon")
    page.fill("#description", "An overnight mini-hackathon: build a small web app with the Fetch API and a JSON back end.")
    page.fill("#event_date", "2027-03-06")
    page.fill("#start_time", "19:00")
    page.fill("#capacity", "80")
    page.fill("#venue", "Innovation Lab, Block A")
    page.select_option("#status", "open")
    shot("add-event-form.png")
    n = len(api_calls)
    page.click("#save-btn")
    page.wait_for_selector(".message-success:has-text('was added')")
    page.wait_for_selector("#event-rows tr.highlight")
    row = page.locator("#event-rows tr.highlight")
    check("add: POST api.php?action=create, success message, new row highlighted, page NOT reloaded",
          any(m == "POST" and "action=create" in u for m, u, _ in api_calls[n:]) and "was added" in page.inner_text("#message")
          and "Hack Night 2027" in row.inner_text() and still_same_page())
    new_id = row.get_attribute("data-id")
    shot("successful-add.png")

    # 4 edit form, 5 updated without reload (event 2: Web Frameworks Workshop)
    page.click('button[aria-label="Edit Web Frameworks Workshop"]')
    check("edit form filled with the event's current values", page.input_value("#title") == "Web Frameworks Workshop" and page.input_value("#capacity") == "60")
    page.fill("#title", "Web Frameworks Workshop (Advanced)")
    page.fill("#venue", "Computer Lab 4")
    page.fill("#capacity", "75")
    shot("edit-event-form.png")
    n = len(api_calls)
    page.click("#save-btn")
    page.wait_for_selector(".message-success:has-text('was updated')")
    page.wait_for_selector('#event-rows tr.highlight[data-id="2"]')
    row = page.locator('#event-rows tr[data-id="2"]')
    check("update: POST api.php?action=update, row shows new title/venue/capacity, page NOT reloaded",
          any(m == "POST" and "action=update" in u for m, u, _ in api_calls[n:]) and "was updated" in page.inner_text("#message")
          and "Web Frameworks Workshop (Advanced)" in row.inner_text() and "Computer Lab 4" in row.inner_text() and "75" in row.inner_text()
          and still_same_page())
    shot("successful-update.png")

    # 6 delete confirmation, 7 deleted without reload
    page.click('button[aria-label="Delete Hack Night 2027"]')
    page.wait_for_selector("#confirm-dialog[open]")
    check("delete asks for confirmation in a dialog", "Hack Night 2027" in page.inner_text("#confirm-dialog"))
    shot("delete-confirmation.png")
    n = len(api_calls)
    page.click("#confirm-yes")
    page.wait_for_selector(".message-success:has-text('was deleted')")
    page.wait_for_function(f"!document.querySelector('#event-rows tr[data-id=\"{new_id}\"]')")
    check("delete: POST api.php?action=delete, row removed, 12 rows again, page NOT reloaded",
          any(m == "POST" and "action=delete" in u for m, u, _ in api_calls[n:]) and page.locator("#event-rows tr[data-id]").count() == 12 and still_same_page())
    shot("successful-delete.png")

    # debounced search: typing "lab" key by key sends one request
    n = len(api_calls)
    page.locator("#search").press_sequentially("lab", delay=90)
    page.wait_for_timeout(900)
    searches = [u for m, u, _ in api_calls[n:] if "action=list" in u]
    check(f"debounced search: typing 'lab' (3 keys) sent {len(searches)} request(s), with q=lab",
          len(searches) == 1 and "q=lab" in searches[0] and "matching “lab”" in page.inner_text("#summary"))

    # 8 loading state with real network throttling
    cdp = page.context.new_cdp_session(page)
    cdp.send("Network.enable")
    cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": 2500, "downloadThroughput": 50000, "uploadThroughput": 50000})
    page.fill("#search", "")
    page.locator("#search").press_sequentially("hackathon", delay=40)
    page.wait_for_selector("#loading:not([hidden])")
    page.wait_for_timeout(600)
    check("loading indicator visible while the throttled request is running", page.is_visible("#loading") and "Searching" in page.inner_text("#loading"))
    shot("loading-state.png")
    page.wait_for_selector("#loading", state="hidden", timeout=20000)
    cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": 0, "downloadThroughput": -1, "uploadThroughput": -1})
    check("after the response the indicator disappears and the results are shown", page.locator("#event-rows tr[data-id]").count() == 2)
    page.fill("#search", "")
    page.wait_for_timeout(800)

    # 9 error state: the API rejects a date after 2100 (passes the browser check, refused by the server)
    page.click("#new-event-btn")
    page.fill("#title", "Future Tech Summit")
    page.select_option("#category", "Seminar")
    page.fill("#description", "A summit about technology trends, planned far in the future.")
    page.fill("#event_date", "2150-06-01")
    page.fill("#start_time", "10:00")
    page.fill("#capacity", "300")
    page.fill("#venue", "Auditorium")
    page.click("#save-btn")
    page.wait_for_selector(".message-error")
    check("server validation error: HTTP 422 message and field error 'Enter a valid date', nothing added",
          "Please correct the highlighted fields." in page.inner_text("#message") and "Enter a valid date" in page.inner_text('[data-error-for="event_date"]')
          and page.locator("#event-rows tr[data-id]").count() == 12)
    shot("error-state.png")
    page.click("#cancel-btn")

    # XSS: an event title with HTML is shown as text and no script runs
    page.evaluate("""fetch('api.php?action=create', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Requested-With': 'fetch'},
                      body: JSON.stringify({title: '<img src=x onerror=alert(1)> Gala', description: 'XSS test event for the browser test.', category: 'Cultural',
                      event_date: '2027-05-01', start_time: '18:00', venue: '<b>Hall</b>', capacity: '10', status: 'open'})})""")
    page.fill("#search", "Gala")
    page.wait_for_selector("#event-rows tr[data-id] >> text=<img src=x onerror=alert(1)> Gala")
    check("HTML in a title is displayed as text, no <img> element created, no alert", page.locator("#event-rows img").count() == 0 and not dialogs)
    check("whole run happened on one page load (no reload)", still_same_page())
    unexpected = [e for e in console_errors if "422" not in e]
    check("no JavaScript errors (only the intended HTTP 422 response is logged)", not unexpected)
    print(*console_errors, sep="\n")
    browser.close()

print(f"browser checks: {sum(results)} passed, {len(results) - sum(results)} failed")
