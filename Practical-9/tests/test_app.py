"""StudentHub – Practical 9: automated end-to-end tests (Python 3, standard library only).

Run from the Practical-9 folder:  python tests\\test_app.py
  1. php -l on every PHP file
  2. tests/test_registration.php (validation, duplicates, hashing, constraints, race condition, rollback)
  3. register.php through XAMPP's PHP built-in server, connected to the disposable database
     studenthub_prac9_test (created from schema.sql and removed at the end): all seven Teams requirements,
     CSRF, SQL injection-style input, audit log, multiple registrations, blocked files
  4. a server whose MySQL port is wrong must answer with a general message only
MySQL must be running. studenthub_prac9 itself is never changed. Test passwords are random and never printed.
"""
import html, http.cookiejar, os, pathlib, re, secrets, subprocess, sys, tempfile, time, urllib.error, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
PHP = r"C:\xampp\php\php.exe" if os.path.exists(r"C:\xampp\php\php.exe") else "php"
MYSQL = r"C:\xampp\mysql\bin\mysql.exe" if os.path.exists(r"C:\xampp\mysql\bin\mysql.exe") else "mysql"
TEST_DB = "studenthub_prac9_test"
PORT, BAD_PORT = 8609, 8619
passed = failed = 0
SECRETS = []                     # every test password and stored hash, to make sure none is ever shown or logged
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def check(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
    else:
        failed += 1
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def sql(query):
    """Runs a fixed test query in the test database and returns the rows (tab-separated)."""
    r = subprocess.run([MYSQL, "-u", "root", "-N", "-B", "-e", query, TEST_DB], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    return [line.split("\t") for line in r.stdout.splitlines()]


def count(table, where="1=1"):
    return int(sql(f"SELECT COUNT(*) FROM {table} WHERE {where}")[0][0])


def password_verify(password, stored_hash):
    env = dict(os.environ, P9_PW=password, P9_HASH=stored_hash)
    r = subprocess.run([PHP, "-r", 'echo password_verify(getenv("P9_PW"), getenv("P9_HASH")) ? "yes" : "no";'],
                       capture_output=True, text=True, env=env)
    return r.stdout == "yes"


def new_password():
    return "Aa1!" + secrets.token_hex(8)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Browser:
    """A client with its own cookie jar (= its own PHP session)."""

    def __init__(self, port=PORT):
        self.port, self.jar = port, http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar), NoRedirect)

    def request(self, path, data=None, method=None):
        body = urllib.parse.urlencode(data, doseq=True).encode() if data is not None else None
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=body, method=method)
        try:
            with self.opener.open(req, timeout=30) as r:
                return r.status, r.headers, r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read().decode("utf-8")

    def token(self):
        # After a registration the first GET shows the one-time confirmation page (no form);
        # like a user clicking "Register another account", load the page again to get the form.
        for _ in range(2):
            status, _, page = self.request("/register.php")
            m = re.search(r'name="csrf_token" value="([0-9a-f]{64})"', page)
            if m:
                return m.group(1)
        return None

    def session_id(self):
        return next((c.value for c in self.jar if c.name == "P9SESSID"), None)

    def register(self, fields, token=True):
        data = dict(fields)
        if token is True:
            data["csrf_token"] = self.token()
        elif token is not None:
            data["csrf_token"] = token
        return self.request("/register.php", data)


def form(n, **override):
    password = override.pop("password", None) or new_password()
    SECRETS.append(password)
    data = {"full_name": "Web Tester", "username": f"web_user_{n}", "email": f"web.user{n}@example.com",
            "password": password, "confirm_password": password, "terms": "1"}
    data.update(override)
    return data


def error_text(page, field):
    m = re.search(rf'<p class="field-error" id="{field}-error">(.*?)</p>', page, re.S)
    return html.unescape(m.group(1)) if m else None


class Server:
    def __init__(self, port, log_dir, env=None):
        self.port, self.log = port, pathlib.Path(log_dir) / f"php-{port}.log"
        self.out = open(pathlib.Path(log_dir) / f"server-{port}.txt", "w")
        environment = {k: v for k, v in os.environ.items() if not k.startswith("P9_DB_")}
        environment.update(env or {})
        self.proc = subprocess.Popen([PHP, "-d", "display_errors=1", "-d", f"error_log={self.log}",
                                      "-S", f"127.0.0.1:{port}", "router.php"],
                                     cwd=ROOT, env=environment, stdout=self.out, stderr=subprocess.STDOUT)
        for _ in range(50):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/assets/css/style.css", timeout=2)
                return
            except Exception:
                time.sleep(0.2)
        raise RuntimeError(f"server on port {port} did not start")

    def logged(self):
        return self.log.read_text(encoding="utf-8", errors="replace") if self.log.exists() else ""

    def stop(self):
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.proc.pid)], capture_output=True)
        self.out.close()


# 1. Syntax check
print("-- php -l")
for f in sorted(ROOT.rglob("*.php")):
    if any(part.startswith(("_tmp", "_backup")) for part in f.relative_to(ROOT).parts):
        continue
    r = subprocess.run([PHP, "-l", str(f)], capture_output=True, text=True)
    check(f"php -l {f.relative_to(ROOT)}", r.returncode == 0 and "No syntax errors" in r.stdout)

# 2. PHP tests
print("-- tests/test_registration.php")
r = subprocess.run([PHP, "tests/test_registration.php"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
summary = re.search(r"Result: (\d+) passed, (\d+) failed", r.stdout)
check("tests/test_registration.php: all checks pass", r.returncode == 0 and bool(summary) and summary.group(2) == "0",
      summary.group(0) if summary else r.stdout[-300:])

subprocess.run([PHP, "tests/test_database.php", "create"], cwd=ROOT, check=True, capture_output=True)
with tempfile.TemporaryDirectory(prefix="p9-tests-") as tmp:
    server = Server(PORT, tmp, {"P9_DB_NAME": TEST_DB})
    try:
        print(f"-- register.php (http://127.0.0.1:{PORT}, database {TEST_DB})")
        b = Browser()
        status, headers, page = b.request("/register.php")
        check("1. form loads: 200 with all six inputs", status == 200 and all(
            f'name="{n}"' in page for n in ("full_name", "username", "email", "password", "confirm_password", "terms")))
        check("form has labels for every input and a 64-character CSRF token",
              all(f'<label for="{n}"' in page for n in ("full_name", "username", "email", "password", "confirm_password", "terms"))
              and re.search(r'name="csrf_token" value="[0-9a-f]{64}"', page) is not None)
        cookie = headers.get("Set-Cookie", "")
        check("session cookie is HttpOnly and SameSite=Strict", "P9SESSID=" in cookie and "HttpOnly" in cookie and "SameSite=Strict" in cookie, cookie)
        check("security headers (CSP, X-Frame-Options, nosniff)", "frame-ancestors 'none'" in headers.get("Content-Security-Policy", "")
              and headers.get("X-Frame-Options") == "DENY" and headers.get("X-Content-Type-Options") == "nosniff")
        check("folder address redirects to register.php", b.request("/")[0] == 302)

        users0, audit0 = count("users"), count("audit_logs")
        status, _, page = b.register({"full_name": "", "username": "", "email": "", "password": "", "confirm_password": ""})
        check("2. empty fields: 422 and a message for each of the six fields", status == 422 and error_text(page, "full_name") == "Full name is required."
              and error_text(page, "username") == "Username is required." and error_text(page, "email") == "Email address is required."
              and error_text(page, "password") == "Password is required." and error_text(page, "confirm_password") == "Please confirm your password."
              and error_text(page, "terms") == "You must accept the terms and conditions.")
        check("   error summary lists 6 fields", "6 fields need attention." in page)

        data = form(1, email="not-an-email")
        status, _, page = b.register(data)
        check("3. invalid email: 422 'Enter a valid email address…'", status == 422 and error_text(page, "email") == "Enter a valid email address, for example name@example.com.")
        check("   entered values kept (name, username, email), terms still ticked", 'value="Web Tester"' in page and 'value="web_user_1"' in page
              and 'value="not-an-email"' in page and re.search(r'id="terms"[^>]*checked', page) is not None)
        check("   password is not sent back in the page", data["password"] not in page and 'type="password" id="password" name="password" required' in page)

        data = form(2)
        data["confirm_password"] = data["password"] + "x"
        status, _, page = b.register(data)
        check("4. password mismatch: 422 'Passwords do not match.'", status == 422 and error_text(page, "confirm_password") == "Passwords do not match.")

        status, _, page = b.register(form(3, password="weakpass"))
        check("   weak password: 422 with the missing rules", status == 422 and "an uppercase letter" in (error_text(page, "password") or ""))

        status, _, page = b.register(form(4, email="asha.demo@example.com"))
        check("5. duplicate email: 422 'An account with this email address already exists.'", status == 422
              and error_text(page, "email") == "An account with this email address already exists." and error_text(page, "username") == "")
        status, _, page = b.register(form(5, email="ASHA.Demo@Example.com"))
        check("   duplicate email in other letter case also refused", status == 422 and "already exists" in (error_text(page, "email") or ""))

        status, _, page = b.register(form(6, username="demo_kabir"))
        check("6. duplicate username: 422 'This username is already taken…'", status == 422
              and error_text(page, "username") == "This username is already taken. Please choose another one." and error_text(page, "email") == "")
        status, _, page = b.register(form(7, username="DEMO_KABIR"))
        check("   duplicate username in other letter case also refused", status == 422 and "already taken" in (error_text(page, "username") or ""))
        check("16. failed attempts created no user and no audit entry", count("users") == users0 and count("audit_logs") == audit0)

        print("-- successful registration")
        session_before = b.session_id()
        data = form(10, full_name="Nisha Example", username="nisha_example", email="nisha.example@example.com")
        status, headers, page = b.register(data)
        check("7. valid form: 303 redirect to register.php?registered=1", status == 303 and headers.get("Location") == "register.php?registered=1", str(status))
        check("   session ID changed after registration (session_regenerate_id)", b.session_id() not in (None, session_before))
        status, _, page = b.request("/register.php?registered=1")
        check("   confirmation page: 'Registration successful' with name, username and email", status == 200 and "Registration successful" in page
              and "Nisha Example" in page and "nisha_example" in page and "nisha.example@example.com" in page)
        check("   no password and no hash in the confirmation page", data["password"] not in page and "$2y$" not in page)
        check("   refreshing shows an empty form again (message shown once)", "Registration successful" not in b.request("/register.php?registered=1")[2])
        rows = sql("SELECT user_id, full_name, username, email, role, password_hash FROM users WHERE username = 'nisha_example'")
        check("8. database insertion: one users row with the submitted values", len(rows) == 1 and rows[0][1:5] == ["Nisha Example", "nisha_example", "nisha.example@example.com", "student"], str(rows and rows[0][:5]))
        stored = rows[0][5] if rows else ""
        SECRETS.append(stored)
        check("9. password_hash column holds a bcrypt hash, not the password", stored.startswith("$2y$10$") and len(stored) == 60 and data["password"] not in stored)
        check("10. password_verify(password, stored hash) is true", password_verify(data["password"], stored))
        check("    password_verify(wrong password, stored hash) is false", not password_verify(data["password"] + "x", stored))
        audit = sql(f"SELECT action FROM audit_logs WHERE user_id = {int(rows[0][0])}") if rows else []
        check("15. audit log: one USER_REGISTERED entry for the new user", audit == [["USER_REGISTERED"]])
        check("    exactly one more user and one more audit entry", count("users") == users0 + 1 and count("audit_logs") == audit0 + 1)

        print("-- CSRF")
        users1, audit1 = count("users"), count("audit_logs")
        c = Browser()
        c.token()
        status, _, page = c.register(form(20), token=None)
        check("13. missing CSRF token: 403 'The form could not be submitted'", status == 403 and "The form could not be submitted" in page)
        status, _, page = c.register(form(21), token="0" * 64)
        check("12. invalid CSRF token: 403", status == 403 and "The form could not be submitted" in page)
        other = Browser()
        status, _, _ = other.register(form(22), token=c.token())
        check("    token from another session: 403", status == 403)
        status, _, page = Browser().register(form(23), token=None)
        check("    request without any session: 403", status == 403)
        status, _, page = c.request("/register.php", {**form(24), "csrf_token[]": [c.token(), "b"]})
        check("    token sent as an array: 403", status == 403)
        check("    rejected requests saved nothing (no user, no audit entry)", count("users") == users1 and count("audit_logs") == audit1)
        check("    rejected form does not echo the attacker's values", "web_user_24" not in page)

        print("-- SQL injection-style and unexpected input")
        status, _, page = b.register(form(30, username="admin' OR '1'='1"))
        check("14. username \"admin' OR '1'='1\": 422 format error", status == 422 and "must start with a letter" in (error_text(page, "username") or ""))
        status, _, page = b.register(form(31, email="x@example.com' OR '1'='1"))
        check("    email with SQL text: 422 invalid email", status == 422 and "valid email" in (error_text(page, "email") or ""))
        status, _, page = b.register(form(32, full_name="Robert'); DROP TABLE users;--"))
        check("    full name with DROP TABLE: 422, and the table still exists", status == 422 and count("users") >= 4)
        tricky = "Aa1!' OR '1'='1"
        data = form(33, username="quote_pw", email="quote.pw@example.com", password=tricky, confirm_password=tricky)
        status, _, _ = b.register(data)
        stored = sql("SELECT password_hash FROM users WHERE username = 'quote_pw'")
        SECRETS.extend(s[0] for s in stored)
        check("    password containing ' OR '1'='1 is just data: registered and verifiable", status == 303 and len(stored) == 1 and password_verify(tricky, stored[0][0]))
        status, _, page = b.register(form(34, full_name="<script>alert(1)</script>"))
        check("    HTML in the name is escaped in the page, not executed", status == 422 and "<script>alert(1)</script>" not in page and "&lt;script&gt;alert(1)&lt;/script&gt;" in page)
        data = form(35)
        del data["username"]
        status, _, page = b.register({**data, "username[]": "x"})
        check("    username sent as an array: 422 'must be sent as text', no PHP warning", status == 422
              and error_text(page, "username") == "This field must be sent as text." and "Warning" not in page and "Fatal" not in page)
        status, _, _ = b.register(form(36, username="role_test", email="role.test@example.com", role="admin"))
        check("    extra field role=admin is ignored: the account is a student", status == 303 and sql("SELECT role FROM users WHERE username = 'role_test'") == [["student"]])
        status, headers, _ = b.request("/register.php", method="PUT")
        check("    PUT request: 405 with Allow: GET, POST", status == 405 and headers.get("Allow") == "GET, POST")

        print("-- multiple registrations")
        ids = []
        for i in range(1, 6):
            data = form(40 + i, username=f"multi_user_{i}", email=f"multi{i}@example.com")
            status, _, _ = b.register(data)
            row = sql(f"SELECT user_id, password_hash FROM users WHERE username = 'multi_user_{i}'")
            ok = status == 303 and len(row) == 1 and password_verify(data["password"], row[0][1])
            SECRETS.extend(r[1] for r in row)
            ids.append(int(row[0][0]) if ok else 0)
        check("18. five registrations in one session all succeed, each with its own hash", 0 not in ids and len(set(ids)) == 5, str(ids))
        check("    one audit entry per new user", count("audit_logs", "action = 'USER_REGISTERED' AND user_id IN (" + ",".join(map(str, ids)) + ")") == 5)
        status, _, _ = b.register(form(46, username="multi_user_3", email="multi.again@example.com"))
        check("17. registering multi_user_3 again is refused", status == 422)
        old = Browser()
        old_token = old.token()
        old.register(form(47, username="replay_user", email="replay@example.com"), token=old_token)
        status, _, _ = old.register(form(48, username="replay_user2", email="replay2@example.com"), token=old_token)
        check("    old token cannot be reused after a successful registration (token rotated)", status == 403)
        check("    every user has exactly one USER_REGISTERED entry", count("users u", "(SELECT COUNT(*) FROM audit_logs a WHERE a.user_id = u.user_id) <> 1") == 0)

        print("-- protected files")
        for path in ("/db.php", "/includes/registration.php", "/includes/security.php", "/tests/test_app.py", "/tests/test_registration.php",
                     "/config.example.php", "/config.local.php", "/router.php", "/start-server.bat", "/.gitignore", "/.htaccess"):
            status, _, page = Browser().request(path)
            check(f"    {path} → 403", status == 403 and "studenthub_prac9" not in page)

        log = server.logged()
        leaked = [s for s in SECRETS if s and s in log]
        check("error log contains no test password and no hash", not leaked and "$2y$" not in log)
        check("no PHP warnings or notices in the error log", not re.search(r"PHP (Warning|Notice|Deprecated|Fatal)", log), log[-300:])
    finally:
        server.stop()

    print(f"-- database unavailable (http://127.0.0.1:{BAD_PORT}, MySQL port 3399)")
    bad = Server(BAD_PORT, tmp, {"P9_DB_NAME": TEST_DB, "P9_DB_PORT": "3399"})
    try:
        b = Browser(BAD_PORT)
        status, _, page = b.request("/register.php")
        check("form still loads without the database", status == 200 and 'name="full_name"' in page)
        data = form(60, username="offline_user", email="offline@example.com")
        status, _, page = b.register(data)
        check("valid form: 503 'Registration is not available right now'", status == 503 and "Registration is not available right now" in page)
        check("page shows no technical details (no mysqli, port, user, SQLSTATE)", not re.search(r"mysqli|3399|root|SQLSTATE|refused|Warning", page, re.I))
        check("entered values kept for a second try", 'value="offline_user"' in page and data["password"] not in page)
        log = bad.logged()
        check("real error written to the PHP error log", "Practical 9 database connection failed" in log)
        check("error log contains no password", data["password"] not in log)
    finally:
        bad.stop()

r = subprocess.run([PHP, "tests/test_database.php", "drop"], cwd=ROOT, capture_output=True, text=True)
check("test database removed again", r.returncode == 0)

print(f"\nResult: {passed} passed, {failed} failed")
sys.exit(0 if failed == 0 else 1)
