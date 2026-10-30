"""StudentHub - browser test of the Event Finder (Practical 13: Fetch API + JSON API) in Microsoft Edge, with screenshots
(optional; needs  pip install playwright).

An administrator searches, creates, edits and deletes events and a student registers – all through fetch() without a page
reload (the test counts the page navigations). To make the loading state visible in a screenshot, the API responses are
delayed by the test's network layer (the responses themselves are the real ones). Disposable database studenthub_p11_test.
    python tests\\browser_api.py [screenshot folder]      (default: evidence/practical-13-integration)
"""
import json, pathlib, re, secrets, sys, tempfile, time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import test_students as P
from playwright.sync_api import sync_playwright

PORT = 8738
BASE = f"http://127.0.0.1:{PORT}/"
FINDER = BASE + "events_live.php"
SHOTS = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else P.ROOT / "evidence" / "practical-13-integration"
results = []


def check(name, ok):
    results.append(ok)
    print(("PASS  " if ok else "FAIL  ") + name)


def sign_in(page, login, password):
    page.goto(BASE + "login.php")
    page.fill("#login_input", login)
    page.fill("#password", password)
    with page.expect_navigation():
        page.click("button[type=submit]")


def titles(page):
    return [t.strip() for t in page.locator("#event-results article h3").all_inner_texts()]


def main():
    SHOTS.mkdir(parents=True, exist_ok=True)
    P.create_test_db(None)
    admin_pw = secrets.token_urlsafe(12) + "A1!"
    P.create_account("portal_admin", "portal.admin@example.com", "admin", admin_pw)
    students = {}
    for user, name, enr in (("aditi_rao", "Aditi Rao", "26CS051"), ("harsh_patel", "Harsh Patel", "26CS052")):
        students[user] = secrets.token_urlsafe(12) + "A1!"
        uid = P.create_account(user, f"{user}@example.com", "student", students[user])
        P.mysql(f"INSERT INTO students (user_id, enrollment_no, name, email, course, gender, semester, status) VALUES "
                f"({uid}, '{enr}', '{name}', '{user}@example.com', 'Computer Science Engineering', 'Female', 1, 'Active')")
    P.mysql("INSERT INTO events (title, category, event_date, event_time, location, capacity, status, description) VALUES "
            "('Git & GitHub Workshop', 'Workshop', '2026-11-18', '10:00:00', 'Computer Lab 2', 1, 'open', 'Version control for team projects.'), "
            "('Inter-College Quiz', 'Technical', '2026-11-27', '15:00:00', 'Seminar Hall 2', 50, 'open', 'Technical quiz for all branches.'), "
            "('Python for Data Science', 'Workshop', '2026-12-03', '09:30:00', 'Computer Lab 5', 40, 'open', 'Pandas and NumPy basics.'), "
            "('Alumni Talk: Careers in Cloud', 'Seminar', '2026-12-10', '11:00:00', 'Auditorium', NULL, 'closed', 'Registration closed - seats allotted.')")
    server = P.Server(PORT, tempfile.mkdtemp(prefix="browser-p13-"), {"DB_NAME": P.TEST_DB})
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="msedge", headless=True)
            errors = []
            pages = {}
            for who in ("admin", "aditi_rao", "harsh_patel"):
                pages[who] = browser.new_context(viewport={"width": 1280, "height": 900}).new_page()
                pages[who].on("console", lambda m: errors.append(f"{m.text} [{m.location.get('url', '')}]") if m.type == "error" else None)
                pages[who].on("pageerror", lambda e: errors.append(str(e)))
            admin, aditi, harsh = pages["admin"], pages["aditi_rao"], pages["harsh_patel"]
            def shot(page, name):                       # wait until a running list refresh has finished
                if page.url.startswith(FINDER) and page.locator("#live-loading").count():
                    page.wait_for_selector("#live-loading", state="hidden")
                page.screenshot(path=str(SHOTS / name), full_page=True)
            api_calls = []
            admin.on("request", lambda r: api_calls.append(r.url) if "/api/events.php" in r.url else None)

            sign_in(admin, "portal_admin", admin_pw)
            # loading state: hold the first API answer for 1.5 s
            def slow(route):
                time.sleep(1.5)
                route.continue_()
            admin.route("**/api/events.php?action=list*", slow)
            admin.goto(FINDER, wait_until="domcontentloaded")
            admin.wait_for_selector("#live-loading:not([hidden])")
            check("loading state: 'Loading events…' is shown and the list is aria-busy while the API answers",
                  admin.locator("#live-loading").is_visible() and admin.get_attribute("#event-results", "aria-busy") == "true")
            admin.screenshot(path=str(SHOTS / "01-loading-state.png"), full_page=True)
            admin.wait_for_selector("#event-results article")
            admin.unroute("**/api/events.php?action=list*")
            navigations = []
            admin.on("framenavigated", lambda f: navigations.append(f.url) if f == admin.main_frame else None)
            admin.wait_for_selector("#live-loading", state="hidden", timeout=5000)
            check("upcoming events listed from the JSON API (soonest first); the loading indicator disappears again",
                  titles(admin)[:2] == ["Robotics & Automation Exhibition", "Git & GitHub Workshop"] and "events found" in admin.inner_text("#live-summary")
                  and not admin.locator("#live-loading").is_visible() and not admin.locator("#live-message").is_visible())
            shot(admin, "02-event-list.png")

            # debounced search: typing quickly sends one request
            before = len(api_calls)
            admin.locator("#live-q").press_sequentially("workshop", delay=60)
            admin.wait_for_timeout(900)
            want = {r[0] for r in P.mysql("SELECT title FROM events WHERE event_date >= CURDATE() AND (title LIKE '%workshop%' OR location LIKE '%workshop%' OR description LIKE '%workshop%')")}
            check("debounced search: typing 'workshop' quickly sends a single API request; exactly the matching events are shown",
                  len(api_calls) - before == 1 and set(titles(admin)) == want and len(want) >= 1)
            shot(admin, "03-live-search.png")
            admin.fill("#live-q", "")
            admin.select_option("#live-category", "Workshop")
            admin.select_option("#live-status", "open")
            admin.wait_for_timeout(700)
            check("category + status filters (Workshop, open) applied through the API", set(titles(admin)) == {"Robotics & Automation Exhibition", "Git & GitHub Workshop", "Python for Data Science"})
            admin.select_option("#live-category", "")
            admin.select_option("#live-status", "closed")
            admin.wait_for_timeout(700)
            check("status filter 'closed' -> only the closed alumni talk", titles(admin) == ["Alumni Talk: Careers in Cloud"])
            shot(admin, "04-filters.png")
            admin.select_option("#live-status", "")
            admin.wait_for_timeout(700)

            # create with a validation error first (422 from the API), then successfully
            admin.click("#new-event")
            admin.fill("#f-title", "Hackathon Kick-off")
            admin.select_option("#f-category", "Hackathon")
            admin.fill("#f-event_date", "2026-12-15")
            admin.fill("#f-event_time", "09:00")
            admin.fill("#f-location", "")
            admin.fill("#f-capacity", "0")
            admin.fill("#f-description", "Team formation and problem statements.")
            shot(admin, "05-new-event-dialog.png")
            admin.click("#event-save")
            admin.wait_for_selector("#f-location-error:not(:empty)")
            check("API validation (HTTP 422): messages under Location and Capacity, nothing stored",
                  "Please enter the location." in admin.inner_text("#f-location-error") and "1 to 65535" in admin.inner_text("#f-capacity-error")
                  and P.scalar("SELECT COUNT(*) FROM events WHERE title='Hackathon Kick-off'") == "0")
            shot(admin, "06-validation-error.png")
            admin.fill("#f-location", "Innovation Lab, Block A")
            admin.fill("#f-capacity", "80")
            admin.click("#event-save")
            admin.wait_for_selector(".live-message.alert-success")
            admin.wait_for_selector("#event-results article:has-text('Hackathon Kick-off')")
            check("create via fetch (HTTP 201): success message, the new event appears, no page reload",
                  "was published" in admin.inner_text("#live-message") and P.scalar("SELECT COUNT(*) FROM events WHERE title='Hackathon Kick-off'") == "1" and not navigations)
            shot(admin, "07-event-created.png")

            # edit
            admin.click("button[aria-label='Edit Inter-College Quiz']")
            admin.fill("#f-location", "Seminar Hall 2, A7 Building")
            admin.fill("#f-capacity", "60")
            shot(admin, "08-edit-event.png")
            admin.click("#event-save")
            admin.wait_for_selector(".live-message.alert-success:has-text('was updated')")
            admin.wait_for_selector("#event-results article:has-text('60 seats')")
            check("update via fetch: the card shows the new location and capacity, no reload",
                  "Seminar Hall 2, A7 Building" in admin.locator("article", has_text="Inter-College Quiz").inner_text()
                  and P.scalar("SELECT capacity FROM events WHERE title='Inter-College Quiz'") == "60" and not navigations)
            shot(admin, "09-event-updated.png")

            # students register; the second one hits the capacity (409)
            for user, page in (("aditi_rao", aditi), ("harsh_patel", harsh)):
                sign_in(page, user, students[user])
                page.goto(FINDER)
                page.wait_for_selector("#event-results article")
            aditi.locator("article", has_text="Git & GitHub Workshop").locator("button:has-text('Register')").click()
            aditi.wait_for_selector(".live-message.alert-success")
            aditi.wait_for_selector("article:has-text('Git & GitHub Workshop') :text('You are registered')")
            check("student registers via fetch (HTTP 201): success message, 'You are registered', seat count updated",
                  "You are registered for “Git & GitHub Workshop”." in aditi.inner_text("#live-message")
                  and "1 of 1 seats taken" in aditi.locator("article", has_text="Git & GitHub Workshop").inner_text())
            shot(aditi, "10-student-registered.png")
            # Harsh's page was loaded before Aditi took the last seat: his Register button is now stale
            harsh.locator("article", has_text="Git & GitHub Workshop").locator("button:has-text('Register')").click()
            harsh.wait_for_selector(".live-message.alert-error")
            harsh.wait_for_selector("article:has-text('Git & GitHub Workshop') >> text=Event full")    # the list refresh after the error
            check("the stale Register button for the now-full workshop -> API 409 'The event is full.' shown as an error; list refreshed to 'Event full'",
                  "The event is full." in harsh.inner_text("#live-message")
                  and harsh.locator("article", has_text="Git & GitHub Workshop").locator("text=Event full").count() == 1)
            shot(harsh, "11-registration-conflict.png")

            # delete: refused for an event with registrations (409), allowed otherwise
            admin.reload()
            admin.wait_for_selector("#event-results article")
            navigations.clear()
            admin.once("dialog", lambda d: d.accept())
            admin.click("button[aria-label='Delete Git & GitHub Workshop']")
            admin.wait_for_selector(".live-message.alert-error")
            check("deleting an event with a registration -> API 409, message shown, event kept",
                  "cannot be deleted" in admin.inner_text("#live-message") and P.scalar("SELECT COUNT(*) FROM events WHERE title='Git & GitHub Workshop'") == "1")
            shot(admin, "12-delete-conflict.png")
            admin.once("dialog", lambda d: d.accept())
            admin.click("button[aria-label='Delete Hackathon Kick-off']")
            admin.wait_for_selector(".live-message.alert-success:has-text('was deleted')")
            admin.wait_for_function("() => ![...document.querySelectorAll('#event-results h3')].some(h => h.textContent === 'Hackathon Kick-off')")
            check("deleting an event without registrations via fetch -> removed from the list, no reload",
                  P.scalar("SELECT COUNT(*) FROM events WHERE title='Hackathon Kick-off'") == "0" and not navigations)

            # the raw JSON and the 401 for a visitor
            admin.goto(BASE + "api/events.php?action=list&when=upcoming&category=Workshop")
            body = json.loads(admin.locator("body").inner_text())
            check("api/events.php returns JSON {ok, count, events[...]} (shown in the browser)", body["ok"] is True and body["count"] == len(body["events"]) >= 2)
            shot(admin, "13-api-json-response.png")
            visitor = browser.new_context(viewport={"width": 1280, "height": 500}).new_page()
            response = visitor.goto(BASE + "api/events.php?action=list")
            check("a visitor without a session gets HTTP 401 JSON {ok: false}", response.status == 401 and json.loads(visitor.locator("body").inner_text())["ok"] is False)
            shot(visitor, "14-api-unauthorised.png")

            favicon = [e for e in errors if "/favicon.ico" in e]
            unexpected = [e for e in errors if not re.search(r"status of (401|409|422)", e) and "/favicon.ico" not in e]
            check("no JavaScript errors (only the intended 401/409/422 API responses)", not unexpected)
            print(*unexpected, sep="\n")
            if favicon:
                print(f"INFO  known, pre-existing: the portal has no favicon - {len(favicon)} automatic /favicon.ico request(s) got 404")
            browser.close()
    finally:
        server.stop()
        problems = [line for line in server.logged().splitlines() if re.search(r"PHP (Warning|Notice|Fatal|Deprecated)|StudentHub API error", line)]
        check("no PHP warnings or API errors in the server log", not problems)
        P.drop_test_db()
    shown_dir = SHOTS.relative_to(P.ROOT).as_posix() if SHOTS.is_relative_to(P.ROOT) else str(SHOTS)
    print(f"screenshots: {shown_dir}/ ({len(list(SHOTS.glob('*.png')))} PNG files)")
    print(f"browser checks: {sum(results)} passed, {len(results) - sum(results)} failed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
