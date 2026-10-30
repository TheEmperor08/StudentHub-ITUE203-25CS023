"""StudentHub - browser test of the integrated Practicals 5-7 in Microsoft Edge, with screenshots
(optional; needs  pip install playwright).

P5: real-time validation and the password strength meter on the portal's registration page; P6: the Campus Data Explorer
(JSON files + Fetch: loading state, search, filter, sorting, pagination); P7: the Help & Contact form (server validation,
stored inquiry with a reference number) and the Inquiries tab of the Admin Console. To make the P6 loading state visible
the test delays the JSON responses in its own network layer (the responses are the real files). Disposable database.
    python tests\\browser_forms.py [screenshot folder]      (default: evidence/practical-05-07-integration)
"""
import pathlib, re, secrets, sys, tempfile, time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import test_students as P
from playwright.sync_api import sync_playwright

PORT = 8745
BASE = f"http://127.0.0.1:{PORT}/"
SHOTS = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else P.ROOT / "evidence" / "practical-05-07-integration"
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
    pw = {"portal_admin": secrets.token_urlsafe(12) + "A1!", "riya_shah": secrets.token_urlsafe(12) + "A1!"}
    P.create_account("portal_admin", "portal.admin@example.com", "admin", pw["portal_admin"])
    uid = P.create_account("riya_shah", "riya_shah@example.com", "student", pw["riya_shah"])
    P.mysql(f"INSERT INTO students (user_id, enrollment_no, name, email, course, gender, semester, status) VALUES ({uid}, '26IT041', 'Riya Shah', 'riya_shah@example.com', 'Information Technology', 'Female', 1, 'Active')")
    server = P.Server(PORT, tempfile.mkdtemp(prefix="browser-p57-"), {"DB_NAME": P.TEST_DB})
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            errors = []
            pages = {}
            for who in ("visitor", "riya_shah", "portal_admin"):
                pages[who] = browser.new_context(viewport={"width": 1280, "height": 900}).new_page()
                pages[who].on("console", lambda m: errors.append(f"{m.text} [{m.location.get('url', '')}]") if m.type == "error" else None)
                pages[who].on("pageerror", lambda e: errors.append(str(e)))
            visitor, riya, admin = pages["visitor"], pages["riya_shah"], pages["portal_admin"]
            shot = lambda page, name: page.screenshot(path=str(SHOTS / name), full_page=True)
            posts = []
            visitor.on("request", lambda r: posts.append(r.url) if r.method == "POST" else None)

            # ---------------- Practical 5
            visitor.goto(BASE + "register.php")
            for field, value in (("#name", "R2D2"), ("#username", "1student"), ("#email", "riya@"), ("#password", "abc")):
                visitor.fill(field, value)
                visitor.locator(field).blur()
            check("real-time validation: messages appear under name, username, e-mail and password while typing (nothing sent)",
                  "letters, spaces" in visitor.inner_text("#name-error") and "Start with a letter" in visitor.inner_text("#username-error")
                  and "valid email" in visitor.inner_text("#email-error") and "at least 8 characters" in visitor.inner_text("#password-error") and not posts)
            check("password strength meter shows 'Very weak' for 'abc'", "Very weak" in visitor.inner_text(".strength-label"))
            shot(visitor, "01-register-live-validation.png")
            visitor.click("button[type=submit]")
            check("submitting with broken rules is blocked in the browser: every rule is listed, focus on the first field, no request sent",
                  not posts and "Please select a course from the list." in visitor.inner_text("#course-error")
                  and "Please accept the Terms" in visitor.inner_text("#agree-error") and visitor.evaluate("document.activeElement.id") == "name")
            shot(visitor, "02-registration-blocked.png")
            visitor.fill("#name", "Neha Rao")
            visitor.fill("#username", "neha_rao")
            visitor.fill("#email", "neha.rao@example.com")
            visitor.fill("#password", "Abcdef12")
            mid = visitor.inner_text(".strength-label")
            visitor.fill("#password", "Campus#Portal2026")
            visitor.fill("#confirm_password", "Campus#Portal2026")
            visitor.locator("#confirm_password").blur()
            check("the meter grows with the password (Abcdef12 -> " + mid.replace("Password strength: ", "") + ", Campus#Portal2026 -> Strong) and the errors disappear",
                  "Strong" in visitor.inner_text(".strength-label") and visitor.locator("#password-error").is_hidden() and visitor.locator("#name-error").is_hidden())
            shot(visitor, "03-password-strength.png")

            # ---------------- Practical 6
            sign_in(riya, "riya_shah", pw["riya_shah"])

            def slow(route):
                time.sleep(1.2)
                route.continue_()
            riya.route("**/data/students.json", slow)
            riya.goto(BASE + "data_explorer.php", wait_until="domcontentloaded")
            riya.wait_for_selector("#status-container .loading")
            check("Data Explorer: loading state while students.json is fetched", "Fetching Data from JSON" in riya.inner_text("#status-container"))
            shot(riya, "04-data-explorer-loading.png")
            riya.wait_for_selector("#data-table-container table")
            riya.unroute("**/data/students.json")
            check("students rendered from JSON: 5 rows per page with pagination", riya.locator("#data-table-container tbody tr").count() == 5
                  and riya.locator("#pagination-container .page-btn").count() == 3)
            shot(riya, "05-data-explorer-students.png")
            riya.fill("#searchInput", "pa")
            riya.select_option("#filterSelect", "CSE")
            rows = riya.locator("#data-table-container tbody tr").all_inner_texts()
            check("search 'pa' + branch filter CSE -> only matching CSE students", rows and all("CSE" in r and "pa" in r.lower() for r in rows))
            shot(riya, "06-data-explorer-search-filter.png")
            riya.click(".tab-btn[data-type='events']")
            riya.wait_for_selector("#data-table-container th:has-text('TITLE')")
            riya.select_option("#sortSelect", "name_desc")
            titles = [t.split("\t")[1] for t in riya.locator("#data-table-container tbody tr").all_inner_texts()]
            check("events tab sorted Z–A", titles == sorted(titles, key=str.lower, reverse=True) and len(titles) == 5)
            shot(riya, "07-data-explorer-events-sorted.png")

            # ---------------- Practical 7
            visitor.goto(BASE + "contact.php")
            visitor.fill("#name", "Neha Rao")
            visitor.fill("#mail", "neha.rao@")
            visitor.fill("#id", "CS-2025")
            visitor.fill("#msg", "Help")
            visitor.click("form[action='contact.php'] button[type=submit]")
            visitor.wait_for_load_state()
            check("server validation of the inquiry: messages under e-mail, enrollment number and message, values kept, nothing stored",
                  "valid email" in visitor.inner_text("#mail-error") and "enrollment number format" in visitor.inner_text("#id-error")
                  and "10–2000" in visitor.inner_text("#msg-error") and visitor.input_value("#name") == "Neha Rao" and P.scalar("SELECT COUNT(*) FROM inquiries") == "0")
            shot(visitor, "08-contact-validation.png")
            visitor.fill("#mail", "neha.rao@example.com")
            visitor.fill("#id", "")
            visitor.select_option("#topic", "Portal access")
            visitor.fill("#msg", "I registered yesterday but cannot see the Event Finder link. Could you check my account?")
            visitor.click("form[action='contact.php'] button[type=submit]")
            visitor.wait_for_url(BASE + "contact.php")
            ref = P.scalar("SELECT id FROM inquiries ORDER BY id DESC LIMIT 1")
            check("valid inquiry -> stored, success message with the reference number", ref is not None and f"(reference #{ref})" in visitor.inner_text(".flash-message"))
            shot(visitor, "09-contact-success.png")
            riya.goto(BASE + "contact.php")
            riya.fill("#msg", "Is attendance required for the Web Frameworks Workshop?")
            riya.select_option("#topic", "Events")
            riya.click("form[action='contact.php'] button[type=submit]")
            riya.wait_for_url(BASE + "contact.php")
            sign_in(admin, "portal_admin", pw["portal_admin"])
            admin.goto(BASE + "admin_dashboard.php?tab=inquiries")
            check("admin: both inquiries listed (the student's linked to the account), tab shows 2 new",
                  admin.locator("#inquiry-table tbody tr").count() == 2 and "account: riya_shah" in admin.inner_text("#inquiry-table")
                  and admin.inner_text("#inquiries-tab").strip().endswith("2"))
            shot(admin, "10-admin-inquiries.png")
            admin.click(f"button[aria-label='Mark inquiry {ref} as resolved']")
            admin.wait_for_url(re.compile(r".*tab=inquiries"))
            check("mark as resolved -> message, status Resolved", f"Inquiry #{ref} was marked as resolved." in admin.inner_text(".alert-success")
                  and P.scalar(f"SELECT status FROM inquiries WHERE id={ref}") == "resolved")
            shot(admin, "11-inquiry-resolved.png")

            favicon = [e for e in errors if "/favicon.ico" in e]
            unexpected = [e for e in errors if not re.search(r"status of (422)", e) and "/favicon.ico" not in e]
            check("no JavaScript errors (only the intended 422 response of the refused inquiry)", not unexpected)
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
