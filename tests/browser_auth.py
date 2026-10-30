"""StudentHub - browser test of registration, login, logout and access control in Microsoft Edge (optional;
needs  pip install playwright). Uses the same disposable database as tests/test_auth.py (studenthub_auth_test, built
from database/studenthub_demo.sql) and XAMPP's PHP built-in server on the canonical application. The live database is
never used.
    python tests\\browser_auth.py [screenshot folder]
"""
import pathlib, re, secrets, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import test_auth as T
from playwright.sync_api import sync_playwright

PORT = 8725
BASE = f"http://127.0.0.1:{PORT}/"
SHOTS = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else None
results = []


def check(name, ok):
    results.append(ok)
    print(("PASS  " if ok else "FAIL  ") + name)


def main():
    T.create_test_db(None)
    admin_pw = secrets.token_urlsafe(12)
    T.create_account("browser_admin", "browser.admin@example.com", "admin", admin_pw)
    import tempfile
    server = T.Server(PORT, tempfile.mkdtemp(prefix="browser-auth-"), {"DB_NAME": T.TEST_DB})
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            errors = []
            page.on("console", lambda m: errors.append(f"{m.text} [{m.location.get('url', '')}]") if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(str(e)))
            shot = lambda name: SHOTS and page.screenshot(path=str(SHOTS / name), full_page=True)

            # weak password: refused by the server (the form has novalidate, so the browser sends it)
            page.goto(BASE + "register.php")
            page.fill("#name", "Diya Mehta")
            page.fill("#username", "diya_mehta")
            page.fill("#email", "diya.mehta@example.com")
            page.check("input[name=gender][value=Female]")
            page.select_option("#course", "Information Technology")
            page.fill("#password", "weakpass")
            page.fill("#confirm_password", "weakpass")
            page.check("#agree")
            page.click("button[type=submit]")
            check("weak password -> the server shows the policy error under the field", "an uppercase letter" in page.inner_text("#password-error"))
            check("entered values are kept (password fields are not)", page.input_value("#username") == "diya_mehta" and page.input_value("#password") == "")
            shot("register-weak-password.png")

            # successful registration
            page.fill("#password", "Diya#2026pass")
            page.fill("#confirm_password", "Diya#2026pass")
            page.check("#agree")
            page.click("button[type=submit]")
            page.wait_for_url(BASE + "dashboard.php")
            flash = page.inner_text(".flash-message")
            m = re.search(r"enrollment number is (\w+)", flash)
            check("registration in Edge -> dashboard with welcome message and enrollment number", m is not None and "Diya Mehta" in flash)
            enrollment = m.group(1) if m else ""
            check("sidebar shows the student's own name and enrollment number (record linked by user_id)",
                  "Diya Mehta" in page.inner_text(".nav-user") and enrollment in page.inner_text(".nav-user"))
            check("database: account + linked student record", T.scalar("SELECT s.user_id = u.id FROM users u JOIN students s ON s.email = u.email WHERE u.username='diya_mehta'") == "1")
            shot("registered-dashboard.png")

            # logout with the sidebar button (POST), then the Back button
            page.click("nav#app-nav button.nav-logout")
            page.wait_for_url(re.compile(r".*login\.php\?status=logged_out"))
            check("sidebar Logout button (POST form) -> 'You have been signed out.'", "You have been signed out." in page.inner_text("main"))
            page.go_back()
            page.wait_for_load_state()
            check("Back button after logout does not show the dashboard (no-store; server redirects to login)", "login.php" in page.url and "Sign in" in page.inner_text("main"))

            # wrong password, then correct login
            page.goto(BASE + "login.php")
            page.fill("#login_input", "diya_mehta")
            page.fill("#password", "Wrong#Pass1")
            page.click("button[type=submit]")
            check("wrong password -> 'Invalid username/email or password.'", "Invalid username/email or password." in page.inner_text("main"))
            shot("login-invalid.png")
            page.fill("#password", "Diya#2026pass")
            page.click("button[type=submit]")
            page.wait_for_url(BASE + "dashboard.php")
            check("correct login -> dashboard", "Welcome back, diya_mehta." in page.inner_text(".flash-message"))

            # student opens the Admin Console
            response = page.goto(BASE + "admin_dashboard.php")
            check("student -> admin_dashboard.php: HTTP 403 'Access Denied' page", response.status == 403 and "Access Denied" in page.inner_text("main"))
            shot("student-admin-denied.png")
            page.click("button:has-text('Sign out & switch account')")
            page.wait_for_url(re.compile(r".*login\.php\?status=logged_out"))

            # admin
            page.fill("#login_input", "browser_admin")
            page.fill("#password", admin_pw)
            page.click("button[type=submit]")
            page.wait_for_url(BASE + "admin_dashboard.php")
            check("admin login -> Admin Console with welcome message", "Admin Console" in page.content() and "signed in as administrator" in page.content())
            page.goto(BASE + "admin_dashboard.php?tab=students")
            # Practical 11: students are deactivated (soft delete) instead of deleted; status changes are POST forms
            status_forms = page.locator("form[action='admin_dashboard.php?tab=students'] input[name=action][value=reactivate_student]").count()
            check("student status changes are POST forms with a CSRF token (no delete/deactivate links that change data)",
                  status_forms > 0 and page.locator("a[href*='action=']").count() == 0
                  and page.locator("form[action='admin_dashboard.php?tab=students']:not(:has(input[name=csrf_token]))").count() == 0)
            shot("admin-console.png")
            page.click("button:has-text('Logout')")
            page.wait_for_url(re.compile(r".*login\.php\?status=logged_out"))
            check("admin Logout button -> signed out", "You have been signed out." in page.inner_text("main"))

            # The portal has no favicon (pre-existing); the browser's automatic /favicon.ico request is reported, not hidden
            favicon = [e for e in errors if "/favicon.ico" in e]
            unexpected = [e for e in errors if not re.search(r"status of (401|403|422)", e) and "/favicon.ico" not in e]
            check("no JavaScript errors (only the intended 401/403/422 responses)", not unexpected)
            print(*unexpected, sep="\n")
            if favicon:
                print(f"INFO  known, pre-existing: the portal has no favicon - {len(favicon)} automatic /favicon.ico request(s) got 404")
            browser.close()
    finally:
        server.stop()
        T.drop_test_db()
    print(f"browser checks: {sum(results)} passed, {len(results) - sum(results)} failed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
