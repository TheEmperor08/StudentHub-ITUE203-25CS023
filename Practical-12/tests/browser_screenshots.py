"""StudentHub – Practical 12: browser test + the 13 screenshots (optional; needs  pip install playwright).

Drives the installed Microsoft Edge (headless, via Playwright) through the real application on 127.0.0.1:8612
(start-server.bat) and the demo database studenthub_prac12, checks every step and saves the screenshots.
It ADDS, EDITS and DELETES an event, so re-import studenthub_prac12.sql afterwards and remove posters added to uploads/.
Usage:  set P12_ADMIN_PASSWORD=<the password you set with tools\\set_admin_password.php>
        python tests\\browser_screenshots.py <screenshots folder> <folder with the input posters>
Input posters: hack-the-campus-poster.jpg, workshop-updated-poster.webp, event-poster.svg, sports-meet-poster-large.jpg (> 2 MB).
"""
import os, pathlib, re, sys
from playwright.sync_api import sync_playwright

SHOTS, INPUTS = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
SHOTS.mkdir(parents=True, exist_ok=True)
BASE = "http://127.0.0.1:8612/"
EMAIL, PASSWORD = "admin.demo@example.com", os.environ["P12_ADMIN_PASSWORD"]
results = []


def check(name, ok):
    results.append(ok)
    print(("PASS  " if ok else "FAIL  ") + name)


with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    errors = []

    # 13 – not logged in
    guest = browser.new_context(viewport={"width": 1280, "height": 720})
    page = guest.new_page()
    response = page.goto(BASE + "index.php")
    check("guest: index.php -> HTTP 401 'Access denied', no event data",
          response.status == 401 and "Access denied" in page.inner_text("main") and "Code Sprint" not in page.content())
    page.screenshot(path=str(SHOTS / "unauthorized-access-denied.png"))
    guest.close()

    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    page = ctx.new_page()
    page.on("console", lambda m: errors.append(f"{page.url} :: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))

    def shot(name, full=True):
        page.screenshot(path=str(SHOTS / name), full_page=full)

    # 1 login page
    page.goto(BASE + "login.php")
    page.fill("#email", EMAIL)
    page.fill("#password", PASSWORD)
    shot("admin-login.png", full=False)
    page.click("button:has-text('Log in')")
    page.wait_for_url(BASE + "index.php")
    check("login -> event list with welcome message", "Welcome, Demo Admin" in page.inner_text(".alert-success"))

    # 2 list with posters
    rows = page.locator("tbody tr")
    thumbs_loaded = page.evaluate("Array.from(document.querySelectorAll('img.poster-thumb')).every(i => i.complete && i.naturalWidth > 0)")
    check("list: 12 events, every poster thumbnail loaded", rows.count() == 12 and thumbs_loaded)
    shot("events-list.png")

    # 3 add form, 4 success
    page.goto(BASE + "add.php")
    page.fill("#event_title", "Hack the Campus 2027")
    page.select_option("#category", "Hackathon")
    page.fill("#description", "A 12-hour hackathon where student teams build solutions for real campus problems. Mentors and snacks provided.")
    page.fill("#event_date", "2027-03-13")
    page.fill("#event_time", "09:30")
    page.fill("#venue", "Main Auditorium")
    page.check("#status-open")
    page.set_input_files("#poster", str(INPUTS / "hack-the-campus-poster.jpg"))
    page.wait_for_function("document.getElementById('poster-preview').naturalWidth > 0")
    shot("add-event-form.png")
    page.click("button:has-text('Add event')")
    page.wait_for_url(BASE + "index.php")
    row = page.locator("tr.table-warning")
    check("added: success message and the new event highlighted with its poster",
          "was added successfully" in page.inner_text(".alert-success") and "Hack the Campus 2027" in row.inner_text()
          and page.evaluate("document.querySelector('tr.table-warning img.poster-thumb').naturalWidth > 0"))
    new_id = row.get_attribute("data-event-id")
    shot("successful-event-add.png")

    # 5 poster preview (detail page)
    page.goto(BASE + f"view.php?id={new_id}")
    name = page.inner_text("dd code")
    check("view page shows the uploaded poster under a random name",
          re.fullmatch(r"[a-f0-9]{32}\.jpg", name) is not None and page.evaluate("document.querySelector('img.poster-full').naturalWidth") == 600)
    shot("event-poster-preview.png", full=False)

    # 6 edit form, 7 success (event 2: new title, venue and replacement poster)
    page.goto(BASE + "edit.php?id=2")
    old_src = page.get_attribute("#poster-preview", "src")
    page.fill("#event_title", "Web Frameworks Workshop II")
    page.fill("#event_date", "2026-11-27")
    page.fill("#event_time", "11:00")
    page.fill("#venue", "Computer Lab 4")
    page.set_input_files("#poster", str(INPUTS / "workshop-updated-poster.webp"))
    page.wait_for_function("document.getElementById('poster-preview').src.startsWith('blob:')")
    shot("edit-event-form.png")
    page.click("button:has-text('Save changes')")
    page.wait_for_url(BASE + "index.php")
    row = page.locator("tr.table-warning")
    check("updated: message 'poster was replaced', new details and new poster in the list",
          "poster was replaced" in page.inner_text(".alert-success") and "Web Frameworks Workshop II" in row.inner_text()
          and "Computer Lab 4" in row.inner_text() and row.locator("img").get_attribute("src") != old_src)
    shot("successful-event-update.png")

    # 8 invalid file type (SVG), 9 oversized poster
    for filename, shot_name, expected in (("event-poster.svg", "invalid-file-type.png", "Invalid file type"),
                                          ("sports-meet-poster-large.jpg", "file-size-rejection.png", "maximum size is 2 MB")):
        page.goto(BASE + "add.php")
        page.fill("#event_title", "Annual Sports Meet")
        page.select_option("#category", "Sports")
        page.fill("#description", "Track and field events for all departments, followed by the prize distribution ceremony.")
        page.fill("#event_date", "2027-02-20")
        page.fill("#event_time", "08:00")
        page.fill("#venue", "Main Sports Ground")
        page.set_input_files("#poster", str(INPUTS / filename))
        page.click("button:has-text('Add event')")
        page.wait_for_selector(".alert-danger")
        check(f"{filename}: rejected by the server ('{expected}'), form kept",
              expected in page.inner_text(".alert-danger") and expected in page.inner_text("#poster-error")
              and page.input_value("#event_title") == "Annual Sports Meet")
        shot(shot_name)

    # 10 delete confirmation, 11 success
    page.goto(BASE + f"delete.php?id={new_id}")
    check("delete page asks for confirmation", "Are you sure you want to delete “Hack the Campus 2027”?" in page.inner_text(".alert-danger"))
    shot("delete-confirmation.png", full=False)
    page.click("button:has-text('Yes, delete event')")
    page.wait_for_url(BASE + "index.php")
    check("deleted: message 'deleted together with its poster file', event gone",
          "deleted together with its poster file" in page.inner_text(".alert-success") and page.locator(f"tr[data-event-id='{new_id}']").count() == 0)
    shot("successful-event-delete.png", full=False)

    # 12 category + status filter
    page.select_option("#category", "Hackathon")
    page.select_option("#status", "open")
    page.click("button:has-text('Filter')")
    cats = set(page.locator("tbody td:nth-child(3)").all_inner_texts())
    statuses = set(page.locator("tbody td:nth-child(6)").all_inner_texts())
    check("filter Hackathon + Open -> only open Hackathon events", cats == {"Hackathon"} and statuses == {"Open"} and "category=Hackathon&status=open" in page.url)
    shot("category-status-filter.png", full=False)

    # logout
    page.click("button:has-text('Log out')")
    page.wait_for_url(re.compile(r".*login\.php\?status=logged_out"))
    check("logout -> 'logged out successfully', event list refused afterwards",
          "logged out successfully" in page.inner_text(".alert-success") and page.goto(BASE + "index.php").status == 401)
    check("no JavaScript errors (only the intended HTTP 401/422 responses)",
          all(re.search(r"status of (401|422)", e) for e in errors))
    print(*errors, sep="\n")
    browser.close()

print(f"browser checks: {sum(results)} passed, {len(results) - sum(results)} failed")
