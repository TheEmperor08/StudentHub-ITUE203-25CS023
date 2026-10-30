"""StudentHub - tests of the integrated Practicals 5-7: real-time registration validation (P5), the Campus Data Explorer
with JSON + Fetch (P6) and stored, validated contact inquiries (P7). Python 3, standard library only.

    python tests\\test_forms.py                        # disposable DB built from database/studenthub_demo.sql
    python tests\\test_forms.py --source-dump X.sql    # disposable DB restored from a mysqldump (missing migrations applied)
"""
import argparse, concurrent.futures, html, json, pathlib, re, secrets, subprocess, sys, tempfile, threading

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import test_students as P  # noqa: E402

PORT = 8744
MIGRATIONS = P.ROOT / "database" / "migrations"
check, info, mysql, scalar, q = P.check, P.info, P.mysql, P.scalar, P.q
ACCOUNTS = {}


def login(name):
    b = P.Browser(PORT)
    b.login(name, ACCOUNTS[name])
    return b


def errors_of(page):
    return {m[0]: html.unescape(m[1]) for m in re.findall(r'<span class="field-error" id="(\w+)-error">(.*?)</span>', page)}


def flash_text(page):
    m = re.search(r'<div class="alert-(success|error) flash-message"[^>]*>.*?<p>(.*?)</p>', page, re.S)
    return (m.group(1), html.unescape(m.group(2))) if m else None


def inquiries():
    return int(scalar("SELECT COUNT(*) FROM inquiries"))


GOOD = {"name": "Meera Joshi", "mail": " Meera.Joshi@Example.com ", "id": "25it077", "topic": "Academics", "msg": "When will the semester 3 timetable for the labs be published?"}


def p5_tests():
    print("\n== Practical 5: real-time registration validation")
    js = (P.APP / "assets" / "js" / "register-validation.js").read_text(encoding="utf-8")
    st, _, page = P.Browser(PORT).request("register.php")
    check("register.php loads the validation script (and keeps server-side validation: novalidate form)",
          st == 200 and "assets/js/register-validation.js" in page and 'action="register.php" novalidate' in page)
    check("the script checks every field with regular expressions / rules matching the server (name, username, email, password policy, confirm, gender, course, year, terms)",
          all(k in js for k in ("NAME = /^\\p{L}", "USERNAME = /^[A-Za-z][A-Za-z0-9_]*$/", "EMAIL = /", "an uppercase letter", "a special character",
                                "The passwords do not match.", "Please choose Male, Female or Other.", "Please accept the Terms")))
    check("password strength meter, real-time checks (input/blur) and submit blocking are implemented",
          "strength-label" in js and "addEventListener('blur'" in js and "event.preventDefault()" in js)
    b = P.Browser(PORT)
    st, _, page = b.request("register.php", {"csrf_token": b.token("register.php"), "name": "Js Bypass", "username": "js_bypass", "email": "js.bypass@example.com",
                                             "gender": "Male", "course": "Data Science", "adm_year": re.search(r'<option value="(\d{4})" selected', page).group(1),
                                             "password": "weakpass", "confirm_password": "weakpass", "agree": "1"})
    check("bypassing the browser checks does not help: the server refuses the weak password (422, nothing stored)",
          st == 422 and "an uppercase letter" in page and scalar("SELECT COUNT(*) FROM users WHERE username='js_bypass'") == "0")


def p6_tests():
    print("\n== Practical 6: Campus Data Explorer (JSON + Fetch)")
    s = login("p57_student")
    st, _, page = s.request("data_explorer.php")
    check("data_explorer.php (signed in) has the tabs, search, filter, sort, status, table and pagination containers and loads data.js",
          st == 200 and all(f'id="{i}"' in page for i in ("searchInput", "filterSelect", "sortSelect", "status-container", "data-table-container", "pagination-container"))
          and page.count('class="tab-btn') == 3 and "assets/js/data.js" in page)
    st, hd, _ = P.Browser(PORT).request("data_explorer.php")
    check("not signed in: redirected to the login page", st == 303 and "login.php" in hd.get("Location", ""))
    check("the sidebar links to the Data Explorer", 'href="data_explorer.php"' in s.request("dashboard.php")[2])
    ok = True
    for name in ("students", "events", "faqs"):
        st, hd, body = P.Browser(PORT).request(f"data/{name}.json")
        try:
            data = json.loads(body)
        except ValueError:
            data = {}
        rows = data.get("records") if isinstance(data, dict) else None
        ok = ok and st == 200 and data.get("sampleData") is True and "SAMPLE DATA" in data.get("description", "") and isinstance(rows, list) and len(rows) == 15
    check("data/students.json, events.json and faqs.json are Practical 6's sample datasets (sampleData, description, 15 records each)", ok)
    ids = [r["id"] for r in json.loads((P.APP / "data" / "students.json").read_text(encoding="utf-8"))["records"]]
    check("the student dataset uses invented DEMO-001 … DEMO-015 ids (no real enrollment numbers)", ids == [f"DEMO-{i:03d}" for i in range(1, 16)])
    js = (P.APP / "assets" / "js" / "data.js").read_text(encoding="utf-8")
    check("data.js fetches the JSON, handles errors, escapes every value and paginates (5 per page)",
          "fetch(`data/${type}.json`)" in js and "data.records" in js and "response.ok" in js and "catch (error)" in js and "esc(item[key])" in js and "itemsPerPage = 5" in js
          and "setTimeout(resolve, 800)" not in js)


def p7_tests():
    print("\n== Practical 7: stored contact inquiries")
    g = P.Browser(PORT)
    st, _, page = g.request("contact.php")
    check("contact.php is public, has a CSRF token, a topic list and a hidden honeypot field",
          st == 200 and 'name="csrf_token"' in page and 'id="topic"' in page and 'class="hp-field"' in page)
    token = g.token("contact.php")
    st, hd, _ = g.request("contact.php", {**GOOD, "csrf_token": token})
    row = mysql("SELECT id, IFNULL(user_id,'NULL'), name, email, enrollment_no, topic, message, status FROM inquiries ORDER BY id DESC LIMIT 1")[0]
    check("a valid inquiry from a visitor -> 303 back to the form, stored (e-mail lower case, enrollment upper case, status new, no account)",
          st == 303 and hd.get("Location") == "contact.php" and row[1:] == ["NULL", "Meera Joshi", "meera.joshi@example.com", "25IT077", "Academics", GOOD["msg"], "new"], str(row))
    check("the success message (from the session) names the reference number, once",
          flash_text(g.request("contact.php")[2]) == ("success", f"Thank you, Meera Joshi. Your inquiry has been received by the A7 CSE helpdesk (reference #{row[0]}).")
          and flash_text(g.request("contact.php")[2]) is None)
    check("SUBMIT_INQUIRY audit entry without the message text", scalar("SELECT details FROM audit_logs WHERE action='SUBMIT_INQUIRY' ORDER BY id DESC LIMIT 1") == f"Inquiry #{row[0]} stored (topic: Academics)")
    n = inquiries()
    cases = [("empty name", {"name": ""}, "name", "Please enter your name."), ("name with digits", {"name": "R2D2"}, "name", "letters, spaces"),
             ("invalid e-mail", {"mail": "meera@"}, "mail", "valid email address"), ("wrong enrollment format", {"id": "CS-2025"}, "id", "enrollment number format"),
             ("unknown topic", {"topic": "Gossip"}, "topic", "topic from the list"), ("message under 10 characters", {"msg": "Help!"}, "msg", "10–2000 characters"),
             ("message over 2000 characters", {"msg": "x" * 2001}, "msg", "10–2000 characters"), ("field sent as an array", {"msg[]": "x", "msg": None}, "msg", "not allowed"),
             ("honeypot field filled in (bot)", {"website": "http://spam.example"}, "msg", "could not be accepted")]
    for label, over, field, text in cases:
        data = {k: v for k, v in {**GOOD, **over, "csrf_token": token}.items() if v is not None}
        st, _, page = g.request("contact.php", data)
        check(f"{label} -> 422 '{text}'", st == 422 and text in errors_of(page).get(field, ""), f"{st} {errors_of(page)}")
    st, _, page = g.request("contact.php", {**GOOD, "name": "<b>Bold</b>", "csrf_token": token})
    check("rejected input is shown again HTML-escaped with the general error message", "&lt;b&gt;Bold&lt;/b&gt;" in page and "<b>Bold</b>" not in page
          and "Your inquiry was not sent." in page)
    check("nothing was stored by the rejected forms", inquiries() == n)
    st, _, _ = g.request("contact.php", GOOD)
    check("without the CSRF token -> 403, nothing stored", st == 403 and inquiries() == n)
    s = login("p57_student")
    st, _, page = s.request("contact.php")
    check("a signed-in student finds name, e-mail and enrollment number filled in from the linked record",
          'value="Forms Student"' in page and 'value="p57_student@example.com"' in page and 'value="26DS777"' in page)
    s.request("contact.php", {"name": "Forms Student", "mail": "p57_student@example.com", "id": "26DS777", "topic": "Events", "msg": "Can I still register for the workshop?",
                              "csrf_token": s.token("contact.php")})
    check("the student's inquiry is linked to the account (user_id)", scalar("SELECT u.username FROM inquiries i JOIN users u ON u.id = i.user_id ORDER BY i.id DESC LIMIT 1") == "p57_student")
    mysql("INSERT INTO inquiries (name, email, topic, message) VALUES ('Script Tester', 'xss@example.com', 'Other', '<script>alert(1)</script> please check')")

    browsers = [P.Browser(PORT) for _ in range(8)]
    tokens = [b.token("contact.php") for b in browsers]
    barrier = threading.Barrier(8)

    def send(i):
        barrier.wait()
        return browsers[i].request("contact.php", {**GOOD, "name": f"Parallel Sender {chr(65 + i)}", "msg": f"Parallel inquiry number {i} for the helpdesk.", "csrf_token": tokens[i]})[0]
    before = inquiries()
    with concurrent.futures.ThreadPoolExecutor(8) as ex:
        codes = list(ex.map(send, range(8)))
    check("8 simultaneous inquiries -> all 8 stored with different reference numbers (the database replaces Practical 7's file lock)",
          codes == [303] * 8 and inquiries() == before + 8 and scalar("SELECT COUNT(DISTINCT id) FROM inquiries WHERE name LIKE 'Parallel Sender %'") == "8")

    print("\n== Inquiries in the Admin Console")
    a = login("p57_admin")
    token = a.token("admin_dashboard.php")
    st, _, page = a.request("admin_dashboard.php?tab=inquiries")
    table = re.search(r'id="inquiry-table".*?<tbody>(.*?)</tbody>', page, re.S).group(1)
    ids = re.findall(r'<td class="fw-bold text-muted">#(\d+)</td>', table)
    check("the Inquiries tab lists all stored inquiries, newest first, with a 'new' badge count on the tab",
          st == 200 and ids == [r[0] for r in mysql("SELECT id FROM inquiries ORDER BY id DESC LIMIT 100")] and 'id="inquiries-tab"' in page and '<span class="badge bg-danger">' in page)
    check("message text is HTML-escaped in the console", "&lt;script&gt;alert(1)&lt;/script&gt; please check" in page and "<script>alert(1)</script> please check" not in page)
    check("every POST form in the tab carries a CSRF token", not P.post_forms_without_token(page))
    first = int(ids[-1])
    a.request(f"admin_dashboard.php?tab=inquiries&action=resolve_inquiry&id={first}")
    st, _, _ = a.request("admin_dashboard.php", {"action": "resolve_inquiry", "id": first})
    check("GET with action=resolve_inquiry and a POST without token change nothing (403)", st == 403 and scalar(f"SELECT status FROM inquiries WHERE id={first}") == "new")
    st, _, _ = a.request("admin_dashboard.php", {"csrf_token": token, "action": "resolve_inquiry", "id": first})
    check("mark as resolved -> status resolved, time stored, RESOLVE_INQUIRY audit entry",
          st == 303 and scalar(f"SELECT CONCAT(status, '|', resolved_at IS NOT NULL) FROM inquiries WHERE id={first}") == "resolved|1"
          and scalar("SELECT details FROM audit_logs WHERE action='RESOLVE_INQUIRY' ORDER BY id DESC LIMIT 1") == f"Inquiry #{first} marked as resolved")
    a.request("admin_dashboard.php", {"csrf_token": token, "action": "resolve_inquiry", "id": first})
    st, _, page = a.request("admin_dashboard.php?tab=inquiries")
    check("resolving it again -> error message", "already resolved" in page)
    _, _, page = a.request("admin_dashboard.php?tab=inquiries&inq_status=resolved")
    shown = re.findall(r'<td class="fw-bold text-muted">#(\d+)</td>', re.search(r'id="inquiry-table".*?</table>', page, re.S).group(0))
    check("filter 'Resolved' shows only the resolved inquiry", shown == [str(first)])
    for name in ("p57_student", "p57_editor"):
        b = login(name)
        st1 = b.request("admin_dashboard.php?tab=inquiries")[0]
        st2 = b.request("admin_dashboard.php", {"csrf_token": b.token("dashboard.php"), "action": "resolve_inquiry", "id": ids[0]})[0]
        check(f"{name.split('_')[1]}: Inquiries tab and resolve action -> 403", st1 == 403 and st2 == 403 and scalar(f"SELECT status FROM inquiries WHERE id={ids[0]}") == "new")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dump")
    args = ap.parse_args()
    print(f"StudentHub tests of Practicals 5-7 in the portal (PHP {P.PHP}, MySQL {P.MYSQL})")
    info("source: " + (pathlib.Path(args.source_dump).name if args.source_dump else "database/studenthub_demo.sql"))
    live_before = P.live_fingerprint()
    workdir = tempfile.mkdtemp(prefix="p57-")
    server = None
    try:
        P.create_test_db(args.source_dump)
        for m in sorted(MIGRATIONS.glob("0*.sql")):
            if not m.name.endswith(".down.sql") and scalar(f"SELECT COUNT(*) FROM schema_migrations WHERE version='{m.name[:3]}'") == "0":
                r = subprocess.run([P.MYSQL, "-u", "root", P.TEST_DB], input=m.read_text(encoding="utf-8"), capture_output=True, text=True, encoding="utf-8")
                assert r.returncode == 0, r.stderr
                info(f"{m.name} applied to the disposable copy")
        for name, role in (("p57_admin", "admin"), ("p57_editor", "editor"), ("p57_student", "student")):
            ACCOUNTS[name] = secrets.token_urlsafe(12) + "A1!"
            P.create_account(name, f"{name}@example.com", role, ACCOUNTS[name])
        uid = scalar("SELECT id FROM users WHERE username='p57_student'")
        mysql(f"INSERT INTO students (user_id, enrollment_no, name, email, course, gender, semester, status) VALUES ({uid}, '26DS777', 'Forms Student', 'p57_student@example.com', 'Data Science', 'Female', 1, 'Active')")
        server = P.Server(PORT, workdir, {"DB_NAME": P.TEST_DB})
        p5_tests()
        p6_tests()
        p7_tests()
        problems = [l for l in server.logged().splitlines() if re.search(r"PHP (Warning|Notice|Fatal|Deprecated|Parse)", l)]
        check("no PHP warnings, notices or fatal errors in the server log", not problems, "; ".join(problems[:3]))
    finally:
        if server:
            server.stop()
        P.drop_test_db()
    print("\n== Clean-up")
    check("disposable database removed", not mysql(f"SHOW DATABASES LIKE '{P.TEST_DB}'", None))
    check("the live studenthub_db was not touched", P.live_fingerprint() == live_before)
    print(f"\nResult: {P.passed} passed, {P.failed} failed, {P.passed + P.failed} checks")
    return 1 if P.failed else 0


if __name__ == "__main__":
    sys.exit(main())
