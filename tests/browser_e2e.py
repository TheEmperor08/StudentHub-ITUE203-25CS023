"""StudentHub - end-to-end test of the final integrated portal (Practical 15) in Microsoft Edge, with screenshots
(optional; needs  pip install playwright).

One continuous scenario through the critical workflows: registration, login/logout, profile, admin/editor access control,
student creation/editing, deactivation/reactivation, inactive login denial, event creation/editing with a secure poster
upload, event registration, duplicate and capacity restrictions, cancellation, Fetch API operations, search and filters,
dashboard statistics, audit logging and CSRF / unauthorised-access rejection. Disposable database studenthub_p11_test and a
temporary poster folder; the live database is never used. Poster images: fictional Practical 12 samples.
    python tests\\browser_e2e.py [screenshot folder]      (default: evidence/practical-15-integration)
"""
import json, pathlib, re, secrets, shutil, sys, tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import test_students as P
from playwright.sync_api import sync_playwright

PORT = 8747
BASE = f"http://127.0.0.1:{PORT}/"
CONSOLE = BASE + "admin_dashboard.php"
SHOTS = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else P.ROOT / "evidence" / "practical-15-integration"
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


def main():
    SHOTS.mkdir(parents=True, exist_ok=True)
    files = pathlib.Path(tempfile.mkdtemp(prefix="e2e-files-"))
    shutil.copy(SAMPLES / "1a023e38c1e411c26656d6a75e9ede04.jpg", files / "code-sprint-2026.jpg")
    (files / "shell.jpg").write_bytes(b"<?php echo 'not an image'; ?>")
    folder = tempfile.mkdtemp(prefix="e2e-posters-")
    P.create_test_db(None)
    pw = {name: secrets.token_urlsafe(12) + "A1!" for name in ("portal_admin", "neha_editor", "kunal_desai")}
    P.create_account("portal_admin", "portal.admin@example.com", "admin", pw["portal_admin"])
    P.create_account("neha_editor", "neha.editor@example.com", "editor", pw["neha_editor"])
    uid = P.create_account("kunal_desai", "kunal.desai@example.com", "student", pw["kunal_desai"])
    P.mysql(f"INSERT INTO students (user_id, enrollment_no, name, email, course, gender, semester, status) VALUES ({uid}, '26IT042', 'Kunal Desai', 'kunal.desai@example.com', 'Information Technology', 'Male', 1, 'Active')")
    student_pw = "Ishaan#Portal2026"
    server = P.Server(PORT, tempfile.mkdtemp(prefix="browser-e2e-"), {"DB_NAME": P.TEST_DB, "STUDENTHUB_UPLOAD_DIR": folder})
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            errors = []
            pages = {}
            for who in ("student", "admin", "editor", "kunal", "visitor"):
                pages[who] = browser.new_context(viewport={"width": 1280, "height": 900}).new_page()
                pages[who].on("console", lambda m: errors.append(f"{m.text} [{m.location.get('url', '')}]") if m.type == "error" else None)
                pages[who].on("pageerror", lambda e: errors.append(str(e)))
            student, admin, editor, kunal, visitor = (pages[k] for k in ("student", "admin", "editor", "kunal", "visitor"))
            shot = lambda page, name: page.screenshot(path=str(SHOTS / name), full_page=True)

            # 1. registration
            student.goto(BASE + "register.php")
            for field, value in (("#name", "Ishaan Mehta"), ("#username", "ishaan_mehta"), ("#email", "ishaan.mehta@example.com"),
                                 ("#password", student_pw), ("#confirm_password", student_pw)):
                student.fill(field, value)
            student.select_option("#course", "Information Technology")
            student.check("#agree")
            shot(student, "01-registration.png")
            student.click("button[type=submit]")
            student.wait_for_url(BASE + "dashboard.php")
            rec = P.student("email='ishaan.mehta@example.com'")
            check("1. registration: account + linked student record with the next enrollment number, signed in",
                  rec is not None and rec["user_id"] != "NULL" and re.fullmatch(r"\d\dIT\d{3}", rec["enrollment_no"]) and "Welcome to StudentHub" in student.inner_text(".flash-message"))

            # 2. logout and login
            student.click("nav#app-nav button.nav-logout")
            student.wait_for_url(re.compile(r".*status=logged_out"))
            sign_in(student, "ishaan.mehta@example.com", student_pw)
            check("2. logout (POST) and login with the e-mail address", student.url == BASE + "dashboard.php" and "Welcome back, ishaan_mehta." in student.inner_text(".flash-message"))
            shot(student, "02-login-dashboard.png")

            # 3. profile
            student.goto(BASE + "profile.php")
            check("3. profile shows the student's own record", "Ishaan Mehta" in student.inner_text("main") and rec["enrollment_no"] in student.inner_text("main"))
            shot(student, "03-student-profile.png")

            # 4. access control
            sign_in(editor, "neha_editor", pw["neha_editor"])
            r_editor = editor.goto(CONSOLE)
            r_student = student.goto(CONSOLE)
            check("4. editor and student opening the Admin Console -> HTTP 403 'Access Denied'",
                  r_editor.status == 403 and r_student.status == 403 and "Access Denied" in editor.inner_text("main"))
            shot(editor, "04-editor-access-denied.png")

            # 5. student creation and editing
            sign_in(admin, "portal_admin", pw["portal_admin"])
            admin.goto(CONSOLE + "?tab=students&view=add")
            admin.fill("#name", "Tanvi Kulkarni")
            admin.fill("#email", "tanvi.kulkarni@example.com")
            admin.select_option("#course", "Data Science")
            admin.select_option("#semester", "3")
            admin.check("input[name=gender][value=Female]")
            admin.click("#student-form button[type=submit]")
            admin.wait_for_url(re.compile(r".*tab=students"))
            tanvi = P.student("email='tanvi.kulkarni@example.com'")
            admin.goto(CONSOLE + f"?tab=students&view=edit&id={tanvi['id']}")
            admin.select_option("#semester", "4")
            admin.click("#student-form button[type=submit]")
            admin.wait_for_url(re.compile(r".*tab=students"))
            check("5. admin adds a student (automatic enrollment number) and edits the semester",
                  re.fullmatch(r"25DS\d{3}", tanvi["enrollment_no"]) is not None and P.student(f"id={tanvi['id']}")["semester"] == "4")
            shot(admin, "05-student-created-edited.png")

            # 6 + 7. deactivation, inactive login denial, reactivation
            admin.goto(CONSOLE + f"?tab=students&view=deactivate&id={rec['id']}")
            admin.click("#student-confirm button[type=submit]")
            admin.wait_for_url(re.compile(r".*tab=students"))
            student.goto(BASE + "dashboard.php")
            ended = "status=access_disabled" in student.url
            sign_in(student, "ishaan_mehta", student_pw)
            check("6/7. deactivation: the signed-in student loses access and a new sign-in is refused with the generic message",
                  ended and "currently disabled" in student.inner_text("main") and P.student(f"id={rec['id']}")["status"] == "Inactive")
            shot(student, "06-inactive-login-denied.png")
            admin.goto(CONSOLE + "?tab=students&status=Inactive")
            admin.click(f"button[aria-label='Reactivate Ishaan Mehta']")
            admin.wait_for_url(re.compile(r".*tab=students"))
            sign_in(student, "ishaan_mehta", student_pw)
            check("6. reactivation restores sign-in", student.url == BASE + "dashboard.php")
            shot(admin, "07-student-reactivated.png")

            # 8 + 9. event with a secure poster upload
            admin.goto(CONSOLE + "?tab=events&view=add_event")
            admin.fill("#event-title", "Code Sprint 2026")
            admin.select_option("#event-category", "Hackathon")
            admin.fill("#event-date", "2026-11-14")
            admin.fill("#event-time", "09:30")
            admin.fill("#event-capacity", "1")
            admin.fill("#event-location", "Innovation Lab, Block A")
            admin.set_input_files("#event-poster", str(files / "shell.jpg"))
            admin.click("#event-form button[type=submit]")
            admin.wait_for_selector("#poster-error")
            rejected = P.scalar("SELECT COUNT(*) FROM events WHERE title='Code Sprint 2026'") == "0"
            shot(admin, "08-poster-rejected.png")
            admin.set_input_files("#event-poster", str(files / "code-sprint-2026.jpg"))
            admin.click("#event-form button[type=submit]")
            admin.wait_for_url(re.compile(r".*tab=events"))
            ev = P.scalar("SELECT id FROM events WHERE title='Code Sprint 2026'")
            admin.goto(CONSOLE + f"?tab=events&view=edit_event&id={ev}")
            admin.fill("#event-description", "24-hour team coding challenge for B.Tech students.")
            admin.click("#event-form button[type=submit]")
            admin.wait_for_url(re.compile(r".*tab=events"))
            check("8/9. event: a PHP file disguised as .jpg is refused, a real JPEG poster is stored under a random name, the event is edited",
                  rejected and re.fullmatch(r"[a-f0-9]{32}\.jpg", P.scalar(f"SELECT poster FROM events WHERE id={ev}") or "") is not None
                  and P.scalar(f"SELECT description FROM events WHERE id={ev}").startswith("24-hour"))
            shot(admin, "09-event-with-poster.png")

            # 10 + 11. registration, duplicate and capacity
            sign_in(kunal, "kunal_desai", pw["kunal_desai"])
            kunal.goto(BASE + "notifications.php")                       # loaded before the last seat is taken
            student.goto(BASE + "notifications.php")
            stale = student.context.new_page()
            stale.goto(BASE + "notifications.php")
            student.locator("article.event-card", has_text="Code Sprint 2026").locator("button:has-text('Register')").click()
            student.wait_for_load_state()
            ok_reg = "You are registered for “Code Sprint 2026”." in student.inner_text(".flash-message")
            shot(student, "10-event-registration.png")
            stale.locator("article.event-card", has_text="Code Sprint 2026").locator("button:has-text('Register')").click()
            stale.wait_for_load_state()
            dup = "already registered" in stale.inner_text(".flash-message")
            kunal.locator("article.event-card", has_text="Code Sprint 2026").locator("button:has-text('Register')").click()
            kunal.wait_for_load_state()
            full = "The event is full." in kunal.inner_text(".flash-message")
            check("10/11. registration succeeds; a second attempt -> 'already registered'; another student on a stale page -> 'The event is full.'",
                  ok_reg and dup and full and P.scalar(f"SELECT COUNT(*) FROM registrations WHERE event_id={ev} AND status<>'cancelled'") == "1")
            shot(kunal, "11-event-full.png")
            stale.close()

            # 12. cancellation
            student.goto(BASE + "notifications.php")
            student.locator("article.event-card", has_text="Code Sprint 2026").locator("button:has-text('Cancel registration')").click()
            student.wait_for_load_state()
            check("12. cancellation keeps the row as 'cancelled' and frees the seat", "was cancelled" in student.inner_text(".flash-message")
                  and P.scalar(f"SELECT COUNT(*) FROM registrations WHERE event_id={ev} AND status='cancelled'") == "1")
            shot(student, "12-registration-cancelled.png")

            # 13. Fetch API operations
            kunal.goto(BASE + "events_live.php")
            kunal.wait_for_selector("#event-results article")
            navs = []
            kunal.on("framenavigated", lambda f: navs.append(f.url) if f == kunal.main_frame else None)
            kunal.locator("#live-q").press_sequentially("code sprint", delay=40)
            kunal.wait_for_timeout(800)
            kunal.locator("article", has_text="Code Sprint 2026").locator("button:has-text('Register')").click()
            kunal.wait_for_selector(".live-message.alert-success")
            check("13. Event Finder: debounced search and registration through the JSON API without a page reload",
                  "You are registered for “Code Sprint 2026”." in kunal.inner_text("#live-message") and not navs
                  and P.scalar(f"SELECT COUNT(*) FROM registrations WHERE event_id={ev} AND status='registered'") == "1")
            kunal.wait_for_selector("#live-loading", state="hidden")
            shot(kunal, "13-fetch-api-registration.png")

            # 14. search and filters
            admin.goto(CONSOLE + "?tab=students&q=Patel&status=Active")
            names = [n.strip() for n in admin.locator("#student-table tbody td:nth-child(2)").all_inner_texts()]
            check("14. student search + status filter", names and all("Patel" in n for n in names))
            shot(admin, "14-search-filters.png")

            # 15. dashboard statistics
            admin.goto(CONSOLE)
            check("15. dashboard counters equal the database",
                  admin.inner_text("[data-stat='students'] h2") == P.scalar("SELECT COUNT(*) FROM students")
                  and admin.inner_text("[data-stat='registrations'] h2") == P.scalar("SELECT COUNT(*) FROM registrations WHERE status='registered'")
                  and "Kunal Desai" in admin.inner_text("#latest-registrations"))
            shot(admin, "15-dashboard-statistics.png")

            # 16. audit log
            admin.goto(CONSOLE + "?tab=audits&audit_status=SECURITY_BLOCK")
            actions = {a.strip() for a in admin.locator("#audit-table tbody td:nth-child(4)").all_inner_texts()}
            check("16. audit log: denied access, refused sign-in, revoked session and rejected upload are recorded",
                  {"ACCESS_DENIED", "LOGIN_DENIED", "SESSION_REVOKED"} <= actions and P.scalar("SELECT COUNT(*) FROM audit_logs WHERE action='UPLOAD_REJECTED'") == "1")
            shot(admin, "16-audit-log.png")

            # 17. CSRF and unauthorised access
            response = visitor.goto(BASE + "api/events.php?action=list")
            unauth = response.status == 401 and json.loads(visitor.locator("body").inner_text())["ok"] is False
            admin.set_content(f'<form method="post" action="{CONSOLE}"><input name="action" value="deactivate_student"><input name="id" value="{tanvi["id"]}"></form>')
            with admin.expect_navigation():
                admin.evaluate("document.forms[0].submit()")
            check("17. a forged form without the CSRF token -> 'Security check failed' (403), nothing changed; the API answers 401 to a visitor",
                  unauth and "Security check failed" in admin.inner_text("body") and P.student(f"id={tanvi['id']}")["status"] == "Active")
            shot(admin, "17-csrf-rejected.png")

            favicon = [e for e in errors if "/favicon.ico" in e]
            unexpected = [e for e in errors if not re.search(r"status of (401|403|422)", e) and "/favicon.ico" not in e]
            check("no JavaScript errors (only the intended 401/403/422 responses)", not unexpected)
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
