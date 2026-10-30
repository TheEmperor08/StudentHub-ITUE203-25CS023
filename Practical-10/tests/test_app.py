"""StudentHub – Practical 10: automated tests (Python 3, standard library only).

Run from the Practical-10 folder:  python tests\\test_app.py
Creates the disposable database studenthub_prac10_test from user_registration.sql (only the name changed),
sets random passwords for the demo accounts with tools/set_password.php, starts XAMPP's PHP built-in server
three times (normal, 2-second timeout, MySQL unreachable) and removes the test database at the end.
studenthub_prac10 is never changed. Test passwords are random and never printed.
"""
import http.cookiejar, os, pathlib, re, secrets, subprocess, sys, tempfile, time, urllib.error, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
PHP = r"C:\xampp\php\php.exe" if os.path.exists(r"C:\xampp\php\php.exe") else "php"
MYSQL = r"C:\xampp\mysql\bin\mysql.exe" if os.path.exists(r"C:\xampp\mysql\bin\mysql.exe") else "mysql"
TEST_DB = "studenthub_prac10_test"
ADMIN, STUDENT = "admin.demo@example.com", "student.demo@example.com"
passed = failed = 0
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def check(name, ok, detail=""):
    global passed, failed
    passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def mysql(sql_text, database=None):
    args = [MYSQL, "-u", "root", "-N", "-B"] + ([database] if database else [])
    r = subprocess.run(args, input=sql_text, capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        raise RuntimeError(r.stderr)
    return [line.split("\t") for line in r.stdout.splitlines()]


def test_db_exists():
    return bool(mysql(f"SHOW DATABASES LIKE '{TEST_DB}'"))


def drop_test_db():
    if test_db_exists():
        if not mysql(f"SHOW TABLES FROM {TEST_DB} LIKE 'p10_test_marker'"):
            raise RuntimeError(f"{TEST_DB} exists but was not created by these tests - not dropped")
        mysql(f"DROP DATABASE {TEST_DB}")


def set_password(email, password, env_extra=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("P10_")}
    env.update({"P10_DB_NAME": TEST_DB, **(env_extra or {})})
    return subprocess.run([PHP, "tools/set_password.php", email], input=password + "\n", cwd=ROOT,
                          capture_output=True, text=True, env=env)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Browser:
    def __init__(self, port):
        self.port, self.jar = port, http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar), NoRedirect)

    def request(self, path, data=None, method=None):
        body = urllib.parse.urlencode(data).encode() if data is not None else None
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/{path.lstrip('/')}", data=body, method=method)
        try:
            with self.opener.open(req, timeout=30) as r:
                return r.status, r.headers, r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read().decode("utf-8")

    def follow(self, path, data=None):
        """Like a browser: follows redirects and returns the final status, page and the list of locations."""
        status, headers, page = self.request(path, data)
        chain = []
        while status in (301, 302, 303) and len(chain) < 5:
            chain.append(headers["Location"])
            status, headers, page = self.request(headers["Location"])
        return status, page, chain

    def token(self, page):
        m = re.search(r'name="csrf_token" value="([0-9a-f]{64})"', page)
        return m.group(1) if m else ""

    def sid(self):
        return next((c.value for c in self.jar if c.name == "P10SESSID"), None)

    def set_sid(self, value):
        self.jar.clear()
        self.jar.set_cookie(http.cookiejar.Cookie(0, "P10SESSID", value, None, False, "127.0.0.1", False, False, "/", True,
                                                  False, None, False, None, None, {}))

    def login(self, email, password, extra=None):
        _, _, page = self.request("login.php")
        return self.request("authenticate.php", {"csrf_token": self.token(page), "email": email, "password": password, **(extra or {})})

    def logout(self):
        _, _, page = self.request("dashboard.php")
        return self.request("logout.php", {"csrf_token": self.token(page)})


class Server:
    def __init__(self, port, log_dir, env=None):
        self.port, self.log = port, pathlib.Path(log_dir) / f"php-{port}.log"
        self.out = open(pathlib.Path(log_dir) / f"server-{port}.txt", "w")
        environment = {k: v for k, v in os.environ.items() if not k.startswith("P10_")}
        environment.update({"P10_DB_NAME": TEST_DB, **(env or {})})
        self.proc = subprocess.Popen([PHP, "-d", f"error_log={self.log}", "-S", f"127.0.0.1:{port}", "router.php"],
                                     cwd=ROOT, env=environment, stdout=self.out, stderr=subprocess.STDOUT)
        for _ in range(50):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/style.css", timeout=2)
                return
            except Exception:
                time.sleep(0.2)
        raise RuntimeError(f"server on port {port} did not start")

    def logged(self):
        return self.log.read_text(encoding="utf-8", errors="replace") if self.log.exists() else ""

    def stop(self):
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.proc.pid)], capture_output=True)
        self.out.close()


print("-- php -l")
for f in sorted(ROOT.rglob("*.php")):
    if any(p.startswith(("_tmp", "_backup")) for p in f.relative_to(ROOT).parts):
        continue
    r = subprocess.run([PHP, "-l", str(f)], capture_output=True, text=True)
    check(f"php -l {f.relative_to(ROOT)}", r.returncode == 0 and "No syntax errors" in r.stdout)

print("-- prepared statements (source check)")
app_code = "".join(p.read_text(encoding="utf-8") for p in [*ROOT.glob("*.php"), *ROOT.glob("includes/*.php"), *ROOT.glob("tools/*.php")])
check("no ->query( or multi_query in the application: every SQL statement uses prepare()", "->query(" not in app_code and "multi_query" not in app_code)
check("password checked with password_verify() and stored with password_hash()", "password_verify(" in app_code and "password_hash(" in app_code)

print(f"-- test database {TEST_DB}")
drop_test_db()
dump = (ROOT / "user_registration.sql").read_text(encoding="utf-8").replace("studenthub_prac10", TEST_DB)
mysql(dump)
mysql(f"CREATE TABLE {TEST_DB}.p10_test_marker (id INT)")
rows = mysql("SELECT email, role, LEFT(password_hash, 4), CHAR_LENGTH(password_hash) FROM users ORDER BY user_id", TEST_DB)
check("user_registration.sql imports: 1 admin and 2 students, all with 60-character $2y$ hashes",
      [r[1] for r in rows] == ["admin", "student", "student"] and all(r[2] == "$2y$" and r[3] == "60" for r in rows), str(rows))
admin_pw, student_pw = "Ad1!" + secrets.token_hex(8), "St1!" + secrets.token_hex(8)
check("tools/set_password.php sets the admin and student demo passwords", set_password(ADMIN, admin_pw).returncode == 0
      and set_password(STUDENT, student_pw).returncode == 0)
check("set_password.php refuses a password shorter than 8 characters", set_password(STUDENT, "short").returncode == 1)
check("set_password.php refuses an unknown email", set_password("nobody@example.com", "Long-enough-1").returncode == 1)
stored = dict((r[0], r[1]) for r in mysql("SELECT email, password_hash FROM users", TEST_DB))
check("stored value is a hash, not the password", stored[ADMIN].startswith("$2y$10$") and admin_pw not in stored[ADMIN])
r = subprocess.run([PHP, "-r", 'echo password_verify(getenv("PW"), getenv("H")) ? "yes" : "no";'],
                   env={**os.environ, "PW": student_pw, "H": stored[STUDENT]}, capture_output=True, text=True)
check("password_verify(student password, stored hash) is true", r.stdout == "yes")
check("mysql: duplicate email refused by the UNIQUE key", "Duplicate entry" in subprocess.run(
    [MYSQL, "-u", "root", TEST_DB, "-e", f"INSERT INTO users (name, email, password_hash) VALUES ('X', '{ADMIN}', '{stored[ADMIN]}')"],
    capture_output=True, text=True).stderr)

with tempfile.TemporaryDirectory(prefix="p10-tests-") as tmp:
    server = Server(8610, tmp)
    try:
        P = 8610
        print("-- login page and unauthenticated access")
        b = Browser(P)
        status, headers, page = b.request("login.php")
        check("login.php: 200 with email and password fields and a CSRF token", status == 200 and 'type="email"' in page
              and 'type="password"' in page and b.token(page) != "")
        cookie = headers.get("Set-Cookie", "")
        check("session cookie HttpOnly and SameSite=Strict", "HttpOnly" in cookie and "SameSite=Strict" in cookie, cookie)
        for page_name in ("dashboard.php", "admin_dashboard.php", "student_dashboard.php"):
            status, headers, _ = Browser(P).request(page_name)
            check(f"not logged in: {page_name} → 303 login.php?status=login_required", status == 303
                  and headers["Location"] == "login.php?status=login_required")
        status, page, _ = Browser(P).follow("dashboard.php")
        check("login page then shows 'Please log in to continue.'", "Please log in to continue." in page)

        print("-- invalid logins (generic message)")
        for label, email, pw in (("wrong password", STUDENT, student_pw + "x"), ("unknown email", "nobody@example.com", student_pw),
                                 ("SQL injection text", "' OR '1'='1' -- ", "x' OR '1'='1"), ("empty fields", "", "")):
            b = Browser(P)
            status, headers, _ = b.login(email, pw)
            ok = status == 303 and headers["Location"] == "login.php?status=invalid"
            status, _, page = b.request(headers["Location"]) if ok else (0, None, "")
            check(f"invalid login ({label}) → 'Invalid email or password.'", ok and "Invalid email or password." in page
                  and "dashboard" not in page.lower().split("<main")[1])
        b = Browser(P)
        b.request("login.php")
        status, headers, _ = b.request("authenticate.php", {"email": STUDENT, "password": student_pw})
        check("login without CSRF token refused (login.php?status=expired)", headers["Location"] == "login.php?status=expired")
        check("GET authenticate.php → login page", Browser(P).request("authenticate.php")[1]["Location"] == "login.php")

        print("-- student login, session ID regeneration, role checks")
        s = Browser(P)
        s.request("login.php")
        sid_before = s.sid()
        status, headers, _ = s.login(STUDENT, student_pw, {"role": "admin"})
        check("valid student login → 303 student_dashboard.php", status == 303 and headers["Location"] == "student_dashboard.php")
        sid_after = s.sid()
        check("session ID changed after login (session_regenerate_id)", sid_before and sid_after and sid_before != sid_after)
        old = Browser(P)
        old.set_sid(sid_before)
        check("the pre-login session ID no longer gives access", old.request("dashboard.php")[1].get("Location") == "login.php?status=login_required")
        status, headers, page = s.request("student_dashboard.php")
        check("student_dashboard.php: 200 for the student, shows 'Demo Student'", status == 200 and "Demo Student" in page)
        check("protected page sends Cache-Control: no-store", "no-store" in headers.get("Cache-Control", ""))
        check("role=admin sent by the browser is ignored (role from the database)", "badge-student" in page and "badge-admin" not in page)
        status, _, page = s.request("dashboard.php")
        check("dashboard.php: 200, shows 'Session ID regenerated' Yes and no session ID", status == 200 and "Session ID regenerated" in page
              and '<strong class="ok">Yes</strong>' in page and sid_after not in page and sid_before not in page)
        status, _, page = s.request("admin_dashboard.php")
        check("student → admin_dashboard.php: 403 'Unauthorized Access'", status == 403 and "Unauthorized Access" in page and "admin.demo@example.com" not in page)

        print("-- admin login and role checks")
        a = Browser(P)
        status, headers, _ = a.login(ADMIN, admin_pw)
        check("valid admin login → 303 admin_dashboard.php", status == 303 and headers["Location"] == "admin_dashboard.php")
        status, _, page = a.request("admin_dashboard.php")
        check("admin_dashboard.php: 200 with the user list (3 accounts)", status == 200 and page.count("@example.com") >= 3)
        status, _, page = a.request("student_dashboard.php")
        check("admin → student_dashboard.php: 403 'Unauthorized Access'", status == 403 and "Unauthorized Access" in page)

        print("-- logout")
        sid = s.sid()
        status, headers, _ = s.request("logout.php")
        check("GET logout.php does not log out (redirect to dashboard)", headers["Location"] == "dashboard.php" and s.request("dashboard.php")[0] == 200)
        status, headers, _ = s.request("logout.php", {"csrf_token": "0" * 64})
        check("POST logout.php with a wrong token does not log out", s.request("dashboard.php")[0] == 200)
        status, headers, _ = s.logout()
        check("logout → 303 login.php?status=logged_out", status == 303 and headers["Location"] == "login.php?status=logged_out")
        check("logout expires the session cookie", "P10SESSID=deleted" in headers.get("Set-Cookie", "") or "Max-Age=0" in headers.get("Set-Cookie", ""),
              headers.get("Set-Cookie", ""))
        check("login page shows 'You have been logged out successfully.'", "logged out successfully" in s.request(headers["Location"])[2])
        for page_name in ("dashboard.php", "student_dashboard.php"):
            check(f"after logout: {page_name} → login (access denied)", s.request(page_name)[1].get("Location") == "login.php?status=login_required")
        replay = Browser(P)
        replay.set_sid(sid)
        check("old session cookie replayed after logout → login (session destroyed on the server)",
              replay.request("student_dashboard.php")[1].get("Location") == "login.php?status=login_required")

        print("-- other checks")
        status, headers, _ = a.request("timeout.php")
        check("timeout.php with an active session does not end it (→ dashboard)", headers["Location"] == "dashboard.php" and a.request("admin_dashboard.php")[0] == 200)
        status, _, page = Browser(P).follow("login.php?status=<script>alert(1)</script>")
        check("unknown status text in the address is never shown", "<script>alert(1)</script>" not in page and "alert(1)" not in page)
        for path in ("db.php", "includes/auth.php", "tools/set_password.php", "tests/test_app.py", "config.example.php",
                     "config.local.php", "router.php", "start-server.bat", ".gitignore", ".htaccess"):
            check(f"/{path} → 403", Browser(P).request(path)[0] == 403)
        log = server.logged()
        check("PHP error log: no passwords, no hashes, no warnings", admin_pw not in log and student_pw not in log and "$2y$" not in log
              and not re.search(r"PHP (Warning|Notice|Deprecated|Fatal)", log), log[-300:])
    finally:
        server.stop()

    print("-- session timeout (server with P10_SESSION_TIMEOUT=2)")
    server = Server(8620, tmp, {"P10_SESSION_TIMEOUT": "2"})
    try:
        t = Browser(8620)
        t.login(STUDENT, student_pw)
        status, _, page = t.request("dashboard.php")
        check("protected page refreshes to timeout.php after 3 seconds (meta refresh)", status == 200
              and '<meta http-equiv="refresh" content="3;url=timeout.php">' in page)
        time.sleep(1.2)
        check("activity within the limit keeps the session (request after 1.2 s)", t.request("student_dashboard.php")[0] == 200)
        time.sleep(1.2)
        check("…and again 1.2 s later (inactivity counted from the last request)", t.request("student_dashboard.php")[0] == 200)
        sid = t.sid()
        time.sleep(3)
        status, page, chain = t.follow("student_dashboard.php")
        check("after 3 s of inactivity: → timeout.php → login.php?status=timeout", chain == ["timeout.php", "login.php?status=timeout"], str(chain))
        check("login page: 'Your session expired after 2 seconds of inactivity…'", "Your session expired after 2 seconds of inactivity" in page)
        replay = Browser(8620)
        replay.set_sid(sid)
        check("expired session cannot be reused", replay.request("dashboard.php")[1].get("Location") == "login.php?status=login_required")
    finally:
        server.stop()

    print("-- database unavailable (server with MySQL port 3399)")
    server = Server(8630, tmp, {"P10_DB_PORT": "3399"})
    try:
        d = Browser(8630)
        status, headers, _ = d.login(STUDENT, student_pw)
        check("login while MySQL is unreachable → login.php?status=unavailable", headers.get("Location") == "login.php?status=unavailable")
        page = d.request(headers["Location"])[2]
        check("general message only (no mysqli, port, user, SQLSTATE)", "Login is not available right now" in page
              and not re.search(r"mysqli|3399|root|SQLSTATE|refused", page, re.I))
        check("real error written to the PHP error log, without the password", "Practical 10 database connection failed" in server.logged()
              and student_pw not in server.logged())
    finally:
        server.stop()

drop_test_db()
check("test database removed", not test_db_exists())
print(f"\nResult: {passed} passed, {failed} failed")
sys.exit(0 if failed == 0 else 1)
