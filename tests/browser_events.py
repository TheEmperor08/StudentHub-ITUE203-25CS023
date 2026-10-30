"""StudentHub - browser test of event management (Practical 12) in Microsoft Edge, with screenshots for the evidence folder
(optional; needs  pip install playwright).

An administrator publishes and edits events with real poster uploads in the Admin Console, an invalid upload is refused,
two students register on the Campus Events page (capacity, cancellation), and the administrator views the registrations
and deletes an event. Disposable database studenthub_p11_test (from database/studenthub_demo.sql) and a temporary poster
folder; the live database and studenthub/uploads are never used. The poster images are fictional (Practical-12/uploads).
    python tests\\browser_events.py [screenshot folder]      (default: evidence/practical-12-integration)
"""
import pathlib, re, secrets, shutil, sys, tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import test_students as P
from playwright.sync_api import sync_playwright

PORT = 8737
BASE = f"http://127.0.0.1:{PORT}/"
EVENTS = BASE + "admin_dashboard.php?tab=events"
LIST = re.compile(re.escape(EVENTS) + r"(#[\w-]*)?$")
SHOTS = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else P.ROOT / "evidence" / "practical-12-integration"
SAMPLES = P.ROOT / "Practical-12" / "uploads"
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


def fill_event(page, title, category, date, time, location, capacity, description):
    page.fill("#event-title", title)
    page.select_option("#event-category", category)
    page.fill("#event-date", date)
    page.fill("#event-time", time)
    page.fill("#event-capacity", capacity)
    page.fill("#event-location", location)
    page.fill("#event-description", description)


def main():
    SHOTS.mkdir(parents=True, exist_ok=True)
    files = pathlib.Path(tempfile.mkdtemp(prefix="p12-files-"))
    # the Practical 12 sample posters show their own titles, so the events below use the same titles
    shutil.copy(SAMPLES / "1a023e38c1e411c26656d6a75e9ede04.jpg", files / "code-sprint-2026.jpg")
    shutil.copy(SAMPLES / "189f38346771ce306b070701ed32a6d7.png", files / "web-frameworks-workshop.png")
    shutil.copy(SAMPLES / "b86f00edf3e60cab8d84782859f1bd6e.webp", files / "ai-healthcare-seminar.webp")
    shutil.copy(SAMPLES / "281eb187b837277bbffdf72095b33ba1.jpg", files / "cultural-night.jpg")
    shutil.copy(SAMPLES / "fa6bfa70286a08f7959899224060da27.png", files / "cricket-cup.jpg")      # PNG content with a .jpg name
    folder = tempfile.mkdtemp(prefix="p12-posters-")
    P.create_test_db(None)
    admin_pw = secrets.token_urlsafe(12) + "A1!"
    P.create_account("portal_admin", "portal.admin@example.com", "admin", admin_pw)
    students = {}
    for i, (user, name, enr) in enumerate((("riya_shah", "Riya Shah", "26IT041"), ("kunal_desai", "Kunal Desai", "26IT042")), 1):
        students[user] = secrets.token_urlsafe(12) + "A1!"
        uid = P.create_account(user, f"{user}@example.com", "student", students[user])
        P.mysql(f"INSERT INTO students (user_id, enrollment_no, name, email, course, gender, semester, status) VALUES "
                f"({uid}, '{enr}', '{name}', '{user}@example.com', 'Information Technology', '{'Female' if i == 1 else 'Male'}', 1, 'Active')")
    P.mysql("UPDATE events SET poster='uploads/odoo_hackathon.jpg' WHERE id=1")            # an older, missing poster reference
    server = P.Server(PORT, tempfile.mkdtemp(prefix="browser-p12-"), {"DB_NAME": P.TEST_DB, "STUDENTHUB_UPLOAD_DIR": folder})
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="msedge", headless=True)
            errors = []
            ctx = {}
            for who in ("admin", "riya_shah", "kunal_desai"):
                ctx[who] = browser.new_context(viewport={"width": 1280, "height": 900}).new_page()
                ctx[who].on("console", lambda m: errors.append(f"{m.text} [{m.location.get('url', '')}]") if m.type == "error" else None)
                ctx[who].on("pageerror", lambda e: errors.append(str(e)))
            admin, riya, kunal = ctx["admin"], ctx["riya_shah"], ctx["kunal_desai"]
            shot = lambda page, name: page.screenshot(path=str(SHOTS / name), full_page=True)

            sign_in(admin, "portal_admin", admin_pw)
            admin.goto(EVENTS)
            check("admin: Campus Events tab lists the events; the missing older poster shows a placeholder",
                  admin.locator("#event-table tbody tr").count() == 5 and "poster file not available" in admin.inner_text("#event-table"))
            shot(admin, "01-event-list.png")

            # add an event with a poster; first a refused upload (PNG content named .jpg)
            admin.click("#add-event")
            admin.wait_for_selector("#event-form")
            fill_event(admin, "Code Sprint 2026", "Hackathon", "2026-11-14", "09:30", "Innovation Lab, Block A", "1",
                       "A 24-hour team coding challenge for B.Tech students.")
            admin.set_input_files("#event-poster", str(files / "cricket-cup.jpg"))
            shot(admin, "02-add-event-form.png")
            admin.click("#event-form button[type=submit]")
            admin.wait_for_selector("#event-form .alert-danger")
            check("a PNG renamed to .jpg is refused on the server ('does not match its content'); nothing stored",
                  "does not match its content" in admin.inner_text("#poster-error") and P.scalar("SELECT COUNT(*) FROM events WHERE title='Code Sprint 2026'") == "0")
            shot(admin, "03-poster-rejected.png")
            admin.set_input_files("#event-poster", str(files / "code-sprint-2026.jpg"))
            admin.click("#event-form button[type=submit]")
            admin.wait_for_url(LIST)
            poster = P.scalar("SELECT poster FROM events WHERE title='Code Sprint 2026'")
            check("valid JPEG poster -> event published, poster stored under a random name and shown from poster.php",
                  "was published" in admin.inner_text(".alert-success") and re.fullmatch(r"[a-f0-9]{32}\.jpg", poster or "") is not None
                  and admin.locator("img[alt='Poster: Code Sprint 2026']").evaluate("i => i.naturalWidth > 0"))
            for title, cat, date, time, loc, cap, desc, f in (
                    ("Web Frameworks Workshop", "Workshop", "2026-11-20", "14:00", "Computer Lab 3", "40", "Hands-on session on modern web frameworks.", "web-frameworks-workshop.png"),
                    ("AI in Healthcare Seminar", "Seminar", "2026-11-25", "11:00", "Seminar Hall 1", "120", "Guest lecture on AI in diagnostics.", "ai-healthcare-seminar.webp"),
                    ("Annual Cultural Night", "Cultural", "2026-12-05", "18:00", "Open-Air Theatre", "", "Music and dance performances.", "cultural-night.jpg")):
                admin.goto(EVENTS + "&view=add_event")
                fill_event(admin, title, cat, date, time, loc, cap, desc)
                admin.set_input_files("#event-poster", str(files / f))
                admin.click("#event-form button[type=submit]")
                admin.wait_for_url(LIST)
            check("PNG and WebP posters accepted too", P.scalar("SELECT COUNT(*) FROM events WHERE poster REGEXP '^[a-f0-9]{32}[.](png|webp)$'") == "2")
            shot(admin, "04-event-created.png")

            # edit
            admin.click("a[aria-label='Edit Web Frameworks Workshop']")
            admin.wait_for_selector("#event-form")
            admin.fill("#event-capacity", "35")
            admin.fill("#event-location", "Computer Lab 3, A7 Building")
            check("Edit opens the form with the current poster", admin.locator("img.event-poster-preview").count() == 1)
            shot(admin, "05-edit-event.png")
            admin.click("#event-form button[type=submit]")
            admin.wait_for_url(LIST)
            check("Save changes -> event updated (capacity 35, new location)", "was updated" in admin.inner_text(".alert-success")
                  and P.scalar("SELECT CONCAT(capacity, '|', location) FROM events WHERE title='Web Frameworks Workshop'") == "35|Computer Lab 3, A7 Building")
            shot(admin, "06-event-updated.png")

            # students register (capacity 1 for the coding sprint)
            for user, page in (("riya_shah", riya), ("kunal_desai", kunal)):
                sign_in(page, user, students[user])
                page.goto(BASE + "notifications.php")
            check("student: Campus Events page lists the upcoming events with posters, seats and Register buttons",
                  riya.locator("article.event-card").count() == 5 and riya.locator("img.event-poster").count() == 4 and riya.locator("button:has-text('Register')").count() == 5)
            shot(riya, "07-student-event-list.png")
            riya.locator("article.event-card", has_text="Code Sprint 2026").locator("button:has-text('Register')").click()
            riya.wait_for_load_state()
            check("Riya registers -> success message and 'You are registered' with a Cancel button",
                  "You are registered for “Code Sprint 2026”." in riya.inner_text(".flash-message")
                  and "You are registered" in riya.locator("article.event-card", has_text="Code Sprint 2026").inner_text())
            shot(riya, "08-registration-success.png")
            kunal.reload()
            card = kunal.locator("article.event-card", has_text="Code Sprint 2026")
            check("capacity 1 reached: Kunal sees 'Event full' and no Register button for it",
                  "Event full" in card.inner_text() and card.locator("button:has-text('Register')").count() == 0 and "1 of 1 seats taken" in card.inner_text())
            shot(kunal, "09-event-full.png")
            kunal.locator("article.event-card", has_text="Web Frameworks Workshop").locator("button:has-text('Register')").click()
            kunal.wait_for_load_state()
            kunal.locator("article.event-card", has_text="Web Frameworks Workshop").locator("button:has-text('Cancel registration')").click()
            kunal.wait_for_load_state()
            check("Kunal registers for the workshop and cancels -> 'was cancelled', row kept as cancelled",
                  "was cancelled" in kunal.inner_text(".flash-message")
                  and P.scalar("SELECT r.status FROM registrations r JOIN events e ON e.id = r.event_id WHERE e.title='Web Frameworks Workshop'") == "cancelled")
            shot(kunal, "10-registration-cancelled.png")

            # registrations view and deletion
            admin.goto(EVENTS)
            admin.click("a[aria-label='Registrations for Code Sprint 2026']")
            admin.wait_for_selector("#event-registrations")
            check("admin: registrations of the event list Riya Shah (26IT041, Registered)", "Riya Shah" in admin.inner_text("#event-registrations")
                  and "26IT041" in admin.inner_text("#event-registrations"))
            shot(admin, "11-event-registrations.png")
            admin.goto(EVENTS)
            admin.click("a[aria-label='Delete Code Sprint 2026']")
            admin.wait_for_selector("#event-confirm")
            check("delete is refused for an event with registrations (history kept)", "cannot be deleted" in admin.inner_text("#event-confirm")
                  and admin.locator("#event-confirm button[type=submit]").count() == 0)
            shot(admin, "12-delete-refused.png")
            admin.goto(EVENTS)
            cultural_poster = pathlib.Path(folder) / P.scalar("SELECT poster FROM events WHERE title='Annual Cultural Night'")
            admin.click("a[aria-label='Delete Annual Cultural Night']")
            admin.wait_for_selector("#event-confirm")
            admin.click("#event-confirm button[type=submit]")
            admin.wait_for_url(LIST)
            check("an event without registrations is deleted after confirmation (poster file removed)",
                  "was deleted" in admin.inner_text(".alert-success") and P.scalar("SELECT COUNT(*) FROM events WHERE title='Annual Cultural Night'") == "0"
                  and not cultural_poster.exists())
            shot(admin, "13-event-deleted.png")

            response = riya.goto(EVENTS)
            check("a student opening the Events tab of the Admin Console -> HTTP 403", response.status == 403 and "Access Denied" in riya.inner_text("main"))
            shot(riya, "14-student-access-denied.png")

            favicon = [e for e in errors if "/favicon.ico" in e]
            unexpected = [e for e in errors if not re.search(r"status of (403|422)", e) and "/favicon.ico" not in e]
            check("no JavaScript errors (only the intended 403/422 responses)", not unexpected)
            print(*unexpected, sep="\n")
            if favicon:
                print(f"INFO  known, pre-existing: the portal has no favicon - {len(favicon)} automatic /favicon.ico request(s) got 404")
            browser.close()
    finally:
        server.stop()
        problems = [line for line in server.logged().splitlines() if re.search(r"PHP (Warning|Notice|Fatal|Deprecated)", line)]
        check("no PHP warnings or errors in the server log", not problems)
        P.drop_test_db()
    shown_dir = SHOTS.relative_to(P.ROOT).as_posix() if SHOTS.is_relative_to(P.ROOT) else str(SHOTS)
    print(f"screenshots: {shown_dir}/ ({len(list(SHOTS.glob('*.png')))} PNG files)")
    print(f"browser checks: {sum(results)} passed, {len(results) - sum(results)} failed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
