"""StudentHub - browser test: a deactivated student cannot sign in or keep a session, and can again after reactivation
(Practical 11 soft delete + Practical 10 sessions), in Microsoft Edge with screenshots (optional; pip install playwright).

A student registers through register.php (so the account and its linked student record are created by the portal itself),
an administrator deactivates the record in the Admin Console, the student's open session ends, a new sign-in is refused,
the administrator reactivates the record and the student signs in again. Disposable database studenthub_p11_test (from
database/studenthub_demo.sql); the live database is never used.
    python tests\\browser_inactive_login.py [screenshot folder]      (default: evidence/practical-11-integration)
"""
import pathlib, re, secrets, sys, tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import test_students as P
from playwright.sync_api import sync_playwright

PORT = 8736
BASE = f"http://127.0.0.1:{PORT}/"
CONSOLE = BASE + "admin_dashboard.php?tab=students"
LIST = re.compile(re.escape(CONSOLE) + r"(#[\w-]*)?$")
SHOTS = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else P.ROOT / "evidence" / "practical-11-integration"
MESSAGE = "Your access to StudentHub is currently disabled. Please contact the administrator."
STUDENT_PW = "Lina#2026pass"
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
    P.create_test_db(None)
    admin_pw = secrets.token_urlsafe(12) + "A1!"
    P.create_account("portal_admin", "portal.admin@example.com", "admin", admin_pw)
    server = P.Server(PORT, tempfile.mkdtemp(prefix="browser-inactive-"), {"DB_NAME": P.TEST_DB})
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="msedge", headless=True)
            errors = []
            contexts = {}
            for who in ("student", "admin"):
                contexts[who] = browser.new_context(viewport={"width": 1280, "height": 900})
                pg = contexts[who].new_page()
                pg.on("console", lambda m: errors.append(f"{m.text} [{m.location.get('url', '')}]") if m.type == "error" else None)
                pg.on("pageerror", lambda e: errors.append(str(e)))
            student, admin = contexts["student"].pages[0], contexts["admin"].pages[0]
            shot = lambda page, name: page.screenshot(path=str(SHOTS / name), full_page=True)

            # 1. the student registers (account + linked student record) and is signed in
            student.goto(BASE + "register.php")
            student.fill("#name", "Lina Mehra")
            student.fill("#username", "lina_mehra")
            student.fill("#email", "lina.mehra@example.com")
            student.check("input[name=gender][value=Female]")
            student.select_option("#course", "Data Science")
            student.fill("#password", STUDENT_PW)
            student.fill("#confirm_password", STUDENT_PW)
            student.check("#agree")
            student.click("button[type=submit]")
            student.wait_for_url(BASE + "dashboard.php")
            record = P.student("email='lina.mehra@example.com'")
            uid = P.scalar("SELECT id FROM users WHERE username='lina_mehra'")
            check("the student registers and is signed in; the student record is linked to the account (students.user_id)",
                  record is not None and record["user_id"] == uid and record["status"] == "Active")

            # 2. the administrator deactivates the record
            sign_in(admin, "portal_admin", admin_pw)
            admin.goto(CONSOLE + "&q=Lina")
            admin.click("a[aria-label='Deactivate Lina Mehra']")
            admin.wait_for_selector("#student-confirm")
            check("the confirmation says that inactive students cannot sign in", "cannot sign in" in admin.inner_text("#student-confirm"))
            admin.click("#student-confirm button[type=submit]")
            admin.wait_for_url(LIST)
            check("administrator: record deactivated; the message says the linked account can no longer sign in",
                  "can no longer sign in" in admin.inner_text(".alert-success") and P.student(f"id={record['id']}")["status"] == "Inactive")
            admin.goto(CONSOLE + "&q=Lina")
            shot(admin, "14-admin-deactivated-linked-student.png")

            # 3. the student's open session ends at the next request
            student.goto(BASE + "dashboard.php")
            check("the signed-in student's next page request -> sign-in page with the generic access message (session ended)",
                  "login.php?status=access_disabled" in student.url and MESSAGE in student.inner_text("main"))
            shot(student, "15-session-ended-after-deactivation.png")
            student.goto(BASE + "profile.php")
            check("... and the student stays signed out (profile -> sign-in page)", "login.php" in student.url)

            # 4. a new sign-in with the correct password is refused
            sign_in(student, "lina_mehra", STUDENT_PW)
            text = student.inner_text("main")
            check("signing in again with the correct password is refused with the same generic message (no record details)",
                  "login.php" in student.url and MESSAGE in text and "inactive" not in text.lower() and record["enrollment_no"] not in text)
            shot(student, "16-inactive-login-denied.png")
            student.goto(BASE + "dashboard.php")
            check("... no session was started (dashboard -> sign-in page)", "login.php" in student.url)

            # 5. the administrator reactivates the record; the student signs in again
            admin.goto(CONSOLE + "&q=Lina")
            admin.click("button[aria-label='Reactivate Lina Mehra']")
            admin.wait_for_url(LIST)
            check("administrator: record reactivated", "was reactivated" in admin.inner_text(".alert-success") and P.student(f"id={record['id']}")["status"] == "Active")
            sign_in(student, "lina_mehra", STUDENT_PW)
            student.wait_for_url(BASE + "dashboard.php")
            check("after reactivation the student signs in normally: dashboard with welcome message and own name/enrollment number",
                  "Welcome back, lina_mehra." in student.inner_text(".flash-message") and "Lina Mehra" in student.inner_text(".nav-user")
                  and record["enrollment_no"] in student.inner_text(".nav-user"))
            shot(student, "17-login-after-reactivation.png")
            student.goto(BASE + "profile.php")
            check("... and can open the other portal pages (profile)", student.url == BASE + "profile.php")

            check("the administrator's session was never affected", admin.goto(CONSOLE).status == 200)
            favicon = [e for e in errors if "/favicon.ico" in e]
            unexpected = [e for e in errors if not re.search(r"status of 403", e) and "/favicon.ico" not in e]
            check("no JavaScript errors (only the intended 403 response of the refused sign-in)", not unexpected)
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
    print(f"screenshots: {shown_dir}/ (14-17)")
    print(f"browser checks: {sum(results)} passed, {len(results) - sum(results)} failed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
