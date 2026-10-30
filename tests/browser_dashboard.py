"""StudentHub - browser test of the admin dashboard (Practical 14) in Microsoft Edge, with screenshots
(optional; needs  pip install playwright).

Two students register for events on the Campus Events page, the administrator opens the dashboard (live statistics,
latest registrations, newest accounts), the navigation differs per role, an editor gets the access-denied page, the
administrator disables and re-enables the editor's account and filters the audit log. Disposable database.
    python tests\\browser_dashboard.py [screenshot folder]      (default: evidence/practical-14-integration)
"""
import pathlib, re, secrets, sys, tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import test_students as P
from playwright.sync_api import sync_playwright

PORT = 8742
BASE = f"http://127.0.0.1:{PORT}/"
CONSOLE = BASE + "admin_dashboard.php"
SHOTS = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else P.ROOT / "evidence" / "practical-14-integration"
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


def sidebar_links(page):
    return page.eval_on_selector_all("nav#app-nav a", "els => els.map(a => a.getAttribute('href'))")


def main():
    SHOTS.mkdir(parents=True, exist_ok=True)
    P.create_test_db(None)
    pw = {name: secrets.token_urlsafe(12) + "A1!" for name in ("portal_admin", "neha_editor", "riya_shah", "kunal_desai")}
    P.create_account("portal_admin", "portal.admin@example.com", "admin", pw["portal_admin"])
    P.create_account("neha_editor", "neha.editor@example.com", "editor", pw["neha_editor"])
    for user, name, enr in (("riya_shah", "Riya Shah", "26IT041"), ("kunal_desai", "Kunal Desai", "26IT042")):
        uid = P.create_account(user, f"{user}@example.com", "student", pw[user])
        P.mysql(f"INSERT INTO students (user_id, enrollment_no, name, email, course, gender, semester, status) VALUES "
                f"({uid}, '{enr}', '{name}', '{user}@example.com', 'Information Technology', 'Female', 1, 'Active')")
    P.mysql("INSERT INTO events (title, category, event_date, event_time, location, capacity, status) VALUES "
            "('Web Frameworks Workshop', 'Workshop', '2026-11-20', '14:00:00', 'Computer Lab 3', 40, 'open'), "
            "('AI in Healthcare Seminar', 'Seminar', '2026-11-25', '11:00:00', 'Seminar Hall 1', 120, 'open')")
    server = P.Server(PORT, tempfile.mkdtemp(prefix="browser-p14-"), {"DB_NAME": P.TEST_DB})
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            errors = []
            pages = {}
            for who in pw:
                pages[who] = browser.new_context(viewport={"width": 1280, "height": 900}).new_page()
                pages[who].on("console", lambda m: errors.append(f"{m.text} [{m.location.get('url', '')}]") if m.type == "error" else None)
                pages[who].on("pageerror", lambda e: errors.append(str(e)))
            admin, editor, riya, kunal = pages["portal_admin"], pages["neha_editor"], pages["riya_shah"], pages["kunal_desai"]
            shot = lambda page, name: page.screenshot(path=str(SHOTS / name), full_page=True)

            # real registrations through the Campus Events page
            for page, user, titles in ((riya, "riya_shah", ("Web Frameworks Workshop", "AI in Healthcare Seminar")), (kunal, "kunal_desai", ("Web Frameworks Workshop",))):
                sign_in(page, user, pw[user])
                for title in titles:
                    page.goto(BASE + "notifications.php")
                    page.locator("article.event-card", has_text=title).locator("button:has-text('Register')").click()
                    page.wait_for_load_state()
            check("three registrations made by two students on the Campus Events page", P.scalar("SELECT COUNT(*) FROM registrations WHERE status='registered'") == "3")

            sign_in(admin, "portal_admin", pw["portal_admin"])
            admin.goto(CONSOLE)
            stats = {name: admin.inner_text(f"[data-stat='{name}'] h2") for name in ("students", "events", "registrations", "user", "audit")}
            check("dashboard: live counters equal the database (students, events, active registrations, accounts, audit entries)",
                  stats == {"students": P.scalar("SELECT COUNT(*) FROM students"), "events": P.scalar("SELECT COUNT(*) FROM events"),
                            "registrations": "3", "user": P.scalar("SELECT COUNT(*) FROM users"), "audit": P.scalar("SELECT COUNT(*) FROM audit_logs")})
            check("latest registrations show the students and events just registered", "Kunal Desai" in admin.inner_text("#latest-registrations")
                  and "AI in Healthcare Seminar" in admin.inner_text("#latest-registrations"))
            shot(admin, "01-admin-dashboard.png")

            # navigation per role
            admin.goto(BASE + "dashboard.php")
            check("admin sidebar: Shortcuts to the Admin Console tabs (from menu_items)",
                  {"admin_dashboard.php", "admin_dashboard.php?tab=students", "admin_dashboard.php?tab=events", "admin_dashboard.php?tab=audits"} <= set(sidebar_links(admin)))
            shot(admin, "02-admin-navigation.png")
            riya.goto(BASE + "dashboard.php")
            check("student sidebar: no admin links", not any(h.startswith("admin_dashboard.php") for h in sidebar_links(riya)))
            shot(riya, "03-student-navigation.png")
            sign_in(editor, "neha_editor", pw["neha_editor"])
            editor.goto(BASE + "dashboard.php")
            check("editor sidebar: no admin links either", not any(h.startswith("admin_dashboard.php") for h in sidebar_links(editor)))
            response = editor.goto(CONSOLE + "?tab=users")
            check("editor opening the Admin Console -> HTTP 403 'Access Denied' (same page as for students)", response.status == 403 and "Access Denied" in editor.inner_text("main"))
            shot(editor, "04-editor-access-denied.png")

            # disable / enable an account
            admin.goto(CONSOLE + "?tab=users")
            shot(admin, "05-user-accounts.png")
            admin.click("button[aria-label='Disable neha_editor']")
            admin.wait_for_url(re.compile(r".*tab=users"))
            check("admin disables the editor account -> message, status Disabled", "was disabled" in admin.inner_text(".alert-success")
                  and P.scalar("SELECT status FROM users WHERE username='neha_editor'") == "disabled")
            shot(admin, "06-account-disabled.png")
            editor.goto(BASE + "profile.php")
            check("the editor's open session ends at the next page (sign-in page with the generic message)",
                  "login.php?status=access_disabled" in editor.url and "Your access to StudentHub is currently disabled" in editor.inner_text("main"))
            sign_in(editor, "neha_editor", pw["neha_editor"])
            check("signing in again with the correct password is refused", "login.php" in editor.url and "currently disabled" in editor.inner_text("main"))
            shot(editor, "07-disabled-login-denied.png")
            admin.goto(CONSOLE + "?tab=users")
            admin.click("button[aria-label='Enable neha_editor']")
            admin.wait_for_url(re.compile(r".*tab=users"))
            sign_in(editor, "neha_editor", pw["neha_editor"])
            check("after Enable the editor signs in again", editor.url == BASE + "dashboard.php")
            shot(admin, "08-account-enabled.png")

            # audit log filter
            admin.goto(CONSOLE + "?tab=audits")
            admin.select_option("#audit-status", "SECURITY_BLOCK")
            admin.click("form[aria-label='Filter the audit log'] button[type=submit]")
            admin.wait_for_load_state()
            actions = set(admin.locator("#audit-table tbody td:nth-child(4)").all_inner_texts())
            check("audit log filtered to SECURITY_BLOCK shows the denied access, revoked session and refused sign-in",
                  {"ACCESS_DENIED", "SESSION_REVOKED", "LOGIN_DENIED"} <= {a.strip() for a in actions})
            shot(admin, "09-audit-log-security.png")
            admin.select_option("#audit-status", "")
            admin.select_option("#audit-action", "USER_DISABLED")
            admin.click("form[aria-label='Filter the audit log'] button[type=submit]")
            admin.wait_for_load_state()
            check("filter by action USER_DISABLED -> the account change with the admin's name", "neha_editor" in admin.inner_text("#audit-table")
                  and "portal_admin" in admin.inner_text("#audit-table"))
            shot(admin, "10-audit-log-account-change.png")

            favicon = [e for e in errors if "/favicon.ico" in e]
            unexpected = [e for e in errors if not re.search(r"status of (401|403)", e) and "/favicon.ico" not in e]
            check("no JavaScript errors (only the intended 403 responses)", not unexpected)
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
