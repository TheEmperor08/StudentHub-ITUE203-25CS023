"""StudentHub - tests of the integrated registration, authentication and role-based access (Practicals 9 and 10).
Python 3, standard library only.

    python tests\\test_auth.py                        # disposable DB built from database/studenthub_demo.sql
    python tests\\test_auth.py --source-dump X.sql    # disposable DB restored from a mysqldump of studenthub_db

Creates the disposable database studenthub_auth_test (with a marker table), creates test accounts with
tools/create_demo_user.php (random passwords, never printed) and runs XAMPP's PHP built-in server on the canonical
application (studenthub/) with DB_NAME pointing at the disposable database:
  * a normal server, a server with a 2-second inactivity timeout,
  * two servers whose configured database is unavailable (unknown database / wrong password).
The live studenthub_db is never used. Everything is removed at the end.
"""
import argparse, concurrent.futures, hashlib, html, http.cookiejar, os, pathlib, re, secrets, subprocess, sys, tempfile, threading, time
import urllib.error, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
# STUDENTHUB_APP_DIR runs every suite against another copy of the application (e.g. the Practical-15 snapshot)
APP = pathlib.Path(os.environ["STUDENTHUB_APP_DIR"]) if os.environ.get("STUDENTHUB_APP_DIR") else ROOT / "studenthub"
DEMO = ROOT / "database" / "studenthub_demo.sql"
PHP = r"C:\xampp\php\php.exe" if os.path.exists(r"C:\xampp\php\php.exe") else "php"
MYSQL = r"C:\xampp\mysql\bin\mysql.exe" if os.path.exists(r"C:\xampp\mysql\bin\mysql.exe") else "mysql"
TEST_DB, MARKER, LIVE_DB = "studenthub_auth_test", "zz_auth_test_marker", "studenthub_db"
PORT, PORT_SHORT, PORT_NODB, PORT_BADPW = 8721, 8722, 8723, 8724
PROTECTED = ["dashboard.php", "student_dashboard.php", "profile.php", "courses.php", "attendance.php", "assignments.php",
             "results.php", "achievements.php", "notifications.php", "directory.php", "admin_dashboard.php"]
PUBLIC = ["index.php", "login.php", "register.php", "contact.php"]
GOOD_PW = "Str0ng!Pass"
passed = failed = 0
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def check(name, ok, detail=""):
    global passed, failed
    passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))
    return ok


def info(text):
    print(f"INFO  {text}")


# ---------------------------------------------------------------- database helpers
def mysql(sql, db=TEST_DB):
    r = subprocess.run([MYSQL, "-u", "root", "-N", "-B"] + ([db] if db else []), input=sql, capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        raise RuntimeError(r.stderr.strip())
    return [line.split("\t") for line in r.stdout.splitlines()]


def scalar(sql, db=TEST_DB):
    rows = mysql(sql, db)
    return rows[0][0] if rows else None


def q(value):
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def drop_test_db():
    if mysql(f"SHOW DATABASES LIKE '{TEST_DB}'", None):
        if not mysql(f"SHOW TABLES FROM `{TEST_DB}` LIKE '{MARKER}'", None):
            raise RuntimeError(f"{TEST_DB} exists but was not created by these tests - not dropped")
        mysql(f"DROP DATABASE `{TEST_DB}`", None)


def create_test_db(dump):
    drop_test_db()
    mysql(f"CREATE DATABASE `{TEST_DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; CREATE TABLE `{TEST_DB}`.`{MARKER}` (id INT);", None)
    if dump:
        text = pathlib.Path(dump).read_text(encoding="utf-8")
        text, _ = re.subn(r"^(CREATE DATABASE .*?)`studenthub_db`", rf"\1`{TEST_DB}`", text, flags=re.M)
        text, n = re.subn(r"^USE `studenthub_db`;", f"USE `{TEST_DB}`;", text, flags=re.M)
        assert n == 1
    else:
        text = DEMO.read_text(encoding="utf-8")
    r = subprocess.run([MYSQL, "-u", "root", TEST_DB], input=text, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    # forces the student INSERT to fail AFTER the account INSERT (tests the transaction rollback)
    mysql("DELIMITER //\nCREATE TRIGGER t_fail_student BEFORE INSERT ON students FOR EACH ROW BEGIN "
          "IF NEW.name = 'Trigger Failure' THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'forced test failure'; END IF; END//\nDELIMITER ;\n")


def create_account(username, email, role, password):
    r = subprocess.run([PHP, "tools/create_demo_user.php", f"--db={TEST_DB}", f"--username={username}", f"--email={email}", f"--role={role}"],
                       input=password + "\n", cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return int(scalar(f"SELECT id FROM users WHERE username={q(username)}"))


def password_ok(user_id, password):
    h = scalar(f"SELECT password FROM users WHERE id={user_id}")
    r = subprocess.run([PHP, "-r", "echo password_verify($argv[1], $argv[2]) ? 'yes' : 'no';", password, h], capture_output=True, text=True)
    return r.stdout == "yes"


# ---------------------------------------------------------------- HTTP client and servers
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


class Browser:
    def __init__(self, port=PORT):
        self.port, self.jar = port, http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar), NoRedirect)

    def request(self, path, data=None):
        body = urllib.parse.urlencode(data).encode() if data is not None else None
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/{path}", data=body)
        try:
            with self.opener.open(req, timeout=30) as r:
                return r.status, r.headers, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read().decode("utf-8", "replace")

    def follow(self, path, data=None):
        status, headers, page = self.request(path, data)
        chain = []
        while status in (301, 302, 303) and len(chain) < 5:
            chain.append(headers["Location"])
            status, headers, page = self.request(headers["Location"])
        return status, page, chain

    def token(self, path):
        _, _, page = self.request(path)
        m = re.search(r'name="csrf_token" value="([0-9a-f]{64})"', page)
        return m.group(1) if m else ""

    def sid(self):
        return next((c.value for c in self.jar if c.name == "STUDENTHUBSESSID"), None)

    def set_sid(self, value):
        self.jar.clear()
        self.jar.set_cookie(http.cookiejar.Cookie(0, "STUDENTHUBSESSID", value, None, False, "127.0.0.1", False, False, "/", True,
                                                  False, None, False, None, None, {}))

    def login(self, login_input, password, with_token=True):
        data = {"login_input": login_input, "password": password}
        if with_token:
            data["csrf_token"] = self.token("login.php")
        return self.request("login.php", data)

    def logout(self):
        return self.request("logout.php", {"csrf_token": self.token("dashboard.php")})


class Server:
    def __init__(self, port, log_dir, env):
        self.port, self.log = port, pathlib.Path(log_dir) / f"php-{port}.log"
        self.out = open(pathlib.Path(log_dir) / f"server-{port}.txt", "w")
        e = {k: v for k, v in os.environ.items() if k not in ("DB_HOST", "DB_USER", "DB_PASS", "DB_NAME", "STUDENTHUB_SESSION_TIMEOUT")}
        e.update(env)
        self.proc = subprocess.Popen([PHP, "-d", f"error_log={self.log}", "-d", "log_errors=1", "-S", f"127.0.0.1:{port}"], cwd=APP,
                                     env=e, stdout=self.out, stderr=subprocess.STDOUT)
        for _ in range(50):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/assets/css/auth.css", timeout=2)
                return
            except Exception:
                time.sleep(0.2)
        raise RuntimeError("server did not start")

    def logged(self):
        return self.log.read_text(encoding="utf-8", errors="replace") if self.log.exists() else ""

    def stop(self):
        self.proc.terminate()
        self.proc.wait(10)
        self.out.close()


def audit_count(action, username=None):
    where = f"action={q(action)}" + (f" AND username={q(username)}" if username else "")
    return int(scalar(f"SELECT COUNT(*) FROM audit_logs WHERE {where}"))


def post_forms_without_token(page):
    forms = re.findall(r"<form\b[^>]*method=\"post\"[^>]*>(.*?)</form>", page, re.S | re.I)
    return [f[:80] for f in forms if 'name="csrf_token"' not in f]


# ================================================================ tests
def static_checks():
    print("\n== Static checks")
    php_files = sorted(APP.rglob("*.php")) + sorted((ROOT / "tools").glob("*.php"))
    bad = [p.name for p in php_files if subprocess.run([PHP, "-l", str(p)], capture_output=True).returncode]
    check(f"php -l: no syntax errors in all {len(php_files)} PHP files of studenthub/ and tools/", not bad, ", ".join(bad))
    db = (APP / "db.php").read_text(encoding="utf-8")
    check("db.php has no fallback: no reference to user_registration and only one mysqli connection",
          "user_registration" not in db and db.count("new mysqli(") == 1)
    sources = {p.name: p.read_text(encoding="utf-8") for p in APP.glob("*.php")}
    check("no page starts its own session (only includes/auth.php calls session_start)",
          not [n for n, s in sources.items() if "session_start(" in s])
    check("no GET logout link anywhere (logout is a POST form)", not [n for n, s in sources.items() if 'href="logout.php"' in s])
    unguarded = [p for p in PROTECTED if "require_permission(" not in sources[p]]
    check("every protected page calls require_permission()", not unguarded, str(unguarded))
    check("no message text is read from the URL ($_GET['error'|'success'|'message'])",
          not [n for n, s in sources.items() if re.search(r"\$_GET\[\s*[\"'](error|success|message)[\"']", s)])
    reg = (APP / "includes" / "registration.php").read_text(encoding="utf-8")
    check("registration inserts the role as the literal 'student' (never from the form)",
          "VALUES (?, ?, ?, 'student')" in reg and "$_POST" not in reg)


def registration_tests():
    print("\n== Registration (Practical 9 integrated)")
    b = Browser()
    status, _, page = b.request("register.php")
    years = re.findall(r'<option value="(\d{4})"', page)
    check("register.php: CSRF token, username field, no role field", status == 200 and 'name="csrf_token"' in page
          and 'name="username"' in page and 'name="role"' not in page)

    def form(**over):
        data = {"name": "Asha Patel", "username": "asha_patel", "email": "asha.patel@example.com", "gender": "Female",
                "course": "Computer Science Engineering", "adm_year": years[0], "password": GOOD_PW, "confirm_password": GOOD_PW, "agree": "1"}
        data.update(over)
        return data

    def register(browser, **over):
        data = form(**over)
        data.setdefault("csrf_token", browser.token("register.php"))
        return browser.request("register.php", data)

    prefix = years[0][2:] + "CS"
    before = scalar(f"SELECT IFNULL(MAX(CAST(SUBSTRING(enrollment_no, 5) AS UNSIGNED)), 0) FROM students WHERE enrollment_no REGEXP '^{prefix}[0-9]{{3}}$'")
    expected_no = f"{prefix}{int(before) + 1:03d}"
    users_before = int(scalar("SELECT COUNT(*) FROM users"))
    uid = None
    r = Browser()
    status, headers, _ = register(r, role="admin", csrf_token=r.token("register.php"))
    row = mysql("SELECT u.id, u.role, s.id, s.user_id, s.enrollment_no, s.semester, s.name, s.status, u.password FROM users u "
                "JOIN students s ON s.user_id = u.id WHERE u.username='asha_patel'")
    check("valid registration -> 303 to dashboard.php", status == 303 and headers["Location"] == "dashboard.php", f"{status} {headers.get('Location')}")
    check("account + student record created together, students.user_id = users.id", len(row) == 1 and row[0][0] == row[0][3])
    if row:
        uid = int(row[0][0])
        check("role is 'student' even though the form sent role=admin", row[0][1] == "student")
        check(f"enrollment number follows the scheme, next free number ({expected_no})", row[0][4] == expected_no, row[0][4])
        check(f"semester derived from the admission year {years[0]} -> 1", row[0][5] == "1")
        check("password stored only as a bcrypt hash that password_verify() accepts", row[0][8].startswith("$2y$") and GOOD_PW not in row[0][8]
              and password_ok(uid, GOOD_PW))
    status, page, _ = r.follow("dashboard.php")
    check("registered student is signed in: welcome message with the enrollment number", status == 200 and expected_no in page and "Welcome to StudentHub" in page)
    status, page, _ = r.follow("profile.php")
    check("profile shows the student's own record (through students.user_id)", "Asha Patel" in page and expected_no in page)
    check("USER_REGISTER written to the audit log", audit_count("USER_REGISTER", "asha_patel") == 1)

    r2 = Browser()
    register(r2, name="Bhavin Rao", username="bhavin_rao", email="bhavin.rao@example.com", gender="Male")
    second = scalar("SELECT enrollment_no FROM students WHERE email='bhavin.rao@example.com'")
    check("the next registration gets the following number", second == f"{prefix}{int(before) + 2:03d}", str(second))
    r3 = Browser()
    register(r3, name="Chirag Iyer", username="chirag_iyer", email="chirag.iyer@example.com", course="Data Science", adm_year=years[1])
    third = mysql("SELECT enrollment_no, semester FROM students WHERE email='chirag.iyer@example.com'")
    check(f"other course/year -> own prefix ({years[1][2:]}DS…) and semester 3",
          bool(third) and re.fullmatch(years[1][2:] + r"DS\d{3}", third[0][0]) is not None and third[0][1] == "3", str(third))

    count_before = int(scalar("SELECT COUNT(*) FROM users"))
    cases = [
        ("invalid email", {"email": "not-an-email", "username": "u_bad1"}, "valid email address"),
        ("password too short", {"password": "Ab1!", "confirm_password": "Ab1!", "username": "u_bad2", "email": "b2@example.com"}, "at least 8 characters"),
        ("password without uppercase/number/special", {"password": "weakpassword", "confirm_password": "weakpassword", "username": "u_bad3", "email": "b3@example.com"}, "an uppercase letter"),
        ("password longer than 72 bytes", {"password": "Aa1!" + "x" * 70, "confirm_password": "Aa1!" + "x" * 70, "username": "u_bad4", "email": "b4@example.com"}, "at most 72 characters"),
        ("passwords do not match", {"confirm_password": "Other1!Pass", "username": "u_bad5", "email": "b5@example.com"}, "do not match"),
        ("username starting with a digit", {"username": "1abc", "email": "b6@example.com"}, "Start with a letter"),
        ("username too short", {"username": "ab", "email": "b7@example.com"}, "3–30 characters"),
        ("name with digits / HTML", {"name": "<b>Bob</b>", "username": "u_bad8", "email": "b8@example.com"}, "letters, spaces"),
        ("course not in the list", {"course": "Medicine", "username": "u_bad9", "email": "b9@example.com"}, "course from the list"),
        ("admission year not offered", {"adm_year": "1999", "username": "u_bad10", "email": "b10@example.com"}, "admission year from the list"),
        ("gender not in the list", {"gender": "X", "username": "u_bad11", "email": "b11@example.com"}, "Male, Female or Other"),
        ("terms not accepted", {"agree": "", "username": "u_bad12", "email": "b12@example.com"}, "Terms"),
        ("duplicate email (other case, spaces)", {"email": "  ASHA.PATEL@example.com ", "username": "asha_other"}, "already exists"),
        ("duplicate username (other case)", {"username": "ASHA_PATEL", "email": "asha2@example.com"}, "already taken"),
    ]
    for label, over, expected in cases:
        status, _, page = register(Browser(), **over)
        check(f"{label} -> rejected ('{expected}')", status == 422 and expected in html.unescape(page), str(status))
    check("no account was created by the rejected forms", int(scalar("SELECT COUNT(*) FROM users")) == count_before)
    status, _, page = register(Browser(), name="<script>x</script>", username="u_xss", email="xss@example.com")
    check("rejected input is escaped when the form is shown again", "<script>x</script>" not in page and "&lt;script&gt;" in page)

    mysql("INSERT INTO students (enrollment_no, name, email, course, gender, semester, status) VALUES "
          "('25CS777', 'Admin Created', 'existing.record@example.com', 'Computer Science', 'Female', 3, 'Active')")
    status, _, page = register(Browser(), name="Admin Created", username="existing_rec", email="Existing.Record@example.com")
    check("email of a pre-existing student record (no account) -> refused, 'contact the administrator'",
          status == 422 and "contact the administrator" in page)
    check("... the existing record is not linked or changed and no account is created",
          scalar("SELECT CONCAT(IFNULL(user_id,'NULL'),'|',name) FROM students WHERE email='existing.record@example.com'") == "NULL|Admin Created"
          and scalar("SELECT COUNT(*) FROM users WHERE username='existing_rec'") == "0")

    status, _, page = register(Browser(), csrf_token="0" * 64, username="no_token", email="no.token@example.com")
    check("registration without a valid CSRF token -> refused, nothing stored",
          status == 422 and "form expired" in page and scalar("SELECT COUNT(*) FROM users WHERE username='no_token'") == "0")

    status, _, page = register(Browser(), name="Trigger Failure", username="trigger_fail", email="trigger.fail@example.com")
    check("student INSERT forced to fail after the account INSERT -> general error message, no technical details",
          status == 422 and "Nothing was saved" in page and "forced test failure" not in page and "SQLSTATE" not in page)
    check("... transaction rolled back: neither the account nor the student record exists",
          scalar("SELECT COUNT(*) FROM users WHERE username='trigger_fail' OR email='trigger.fail@example.com'") == "0"
          and scalar("SELECT COUNT(*) FROM students WHERE email='trigger.fail@example.com'") == "0")

    print("\n== Simultaneous registrations (5 at the same moment, same course and year)")
    browsers = [Browser() for _ in range(5)]
    tokens = [br.token("register.php") for br in browsers]
    barrier = threading.Barrier(5)

    def go(i):
        barrier.wait()
        return browsers[i].request("register.php", form(name=f"Parallel Student {chr(65 + i)}", username=f"parallel_{i}",
                                                        email=f"parallel{i}@example.com", course="Web Development", csrf_token=tokens[i]))[0]
    with concurrent.futures.ThreadPoolExecutor(5) as pool:
        statuses = list(pool.map(go, range(5)))
    numbers = [r[0] for r in mysql("SELECT enrollment_no FROM students WHERE email LIKE 'parallel%@example.com' ORDER BY enrollment_no")]
    linked = int(scalar("SELECT COUNT(*) FROM students s JOIN users u ON u.id = s.user_id WHERE s.email LIKE 'parallel%@example.com'"))
    check("all 5 succeed with 5 different, consecutive enrollment numbers, each linked to its account",
          statuses == [303] * 5 and len(set(numbers)) == 5 and linked == 5
          and [int(n[4:]) for n in numbers] == list(range(int(numbers[0][4:]), int(numbers[0][4:]) + 5)), f"{statuses} {numbers}")
    return uid


def login_tests(accounts, student_uid):
    print("\n== Login (Practical 10 integrated)")
    b = Browser()
    status, headers, page = b.request("login.php")
    check("login page: CSRF token; session cookie STUDENTHUBSESSID HttpOnly + SameSite=Strict",
          'name="csrf_token"' in page and re.search(r"STUDENTHUBSESSID=[^;]+;.*HttpOnly.*SameSite=Strict", headers.get("Set-Cookie", ""), re.I) is not None,
          headers.get("Set-Cookie", ""))
    for label, user, pw in (("wrong password", "auth_student", "Wrong!Pass1"), ("unknown account", "nobody_here", GOOD_PW),
                            ("unknown email", "nobody@example.com", GOOD_PW), ("SQL injection", "' OR '1'='1", "' OR '1'='1")):
        status, _, page = b.login(user, pw)
        check(f"{label} -> 401 and the same generic message 'Invalid username/email or password.'",
              status == 401 and "Invalid username/email or password." in page and "not found" not in page.lower())
    check("failed logins are audit-logged (LOGIN_FAILED)", audit_count("LOGIN_FAILED") >= 4)
    status, _, page = b.login("auth_student", accounts["auth_student"], with_token=False)
    check("login without CSRF token -> refused", status == 401 and "form expired" in page)

    before = b.sid()
    status, headers, _ = b.login("auth_student", accounts["auth_student"])
    after = b.sid()
    check("correct username + password -> 303 to dashboard.php", status == 303 and headers["Location"] == "dashboard.php")
    check("session ID regenerated at login (old ID != new ID)", before and after and before != after)
    old = Browser()
    old.set_sid(before)
    check("the pre-login session ID gives no access", old.request("dashboard.php")[0] == 303)
    check("last_login updated and USER_LOGIN audit entry written",
          scalar(f"SELECT last_login IS NOT NULL FROM users WHERE username='auth_student'") == "1" and audit_count("USER_LOGIN", "auth_student") >= 1)
    status, headers, _ = Browser().login("auth.admin@example.com", accounts["auth_admin"])
    check("login with the e-mail address works; admin goes to admin_dashboard.php", status == 303 and headers["Location"] == "admin_dashboard.php")
    st, hd, pg = b.request("dashboard.php")
    check("protected pages send Cache-Control: no-store, X-Frame-Options: DENY, nosniff",
          "no-store" in hd.get("Cache-Control", "") and hd.get("X-Frame-Options") == "DENY" and hd.get("X-Content-Type-Options") == "nosniff")
    for path in ("login.php?next=https://evil.example/", "login.php?status=%3Cscript%3Ealert(1)%3C/script%3E", "logout.php?next=//evil.example"):
        st, hd, pg = Browser().request(path)
        check(f"no open redirect / no reflected text: {path}", "evil.example" not in hd.get("Location", "") and "<script>alert(1)" not in pg)
    return b


def logout_tests(accounts):
    print("\n== Logout")
    b = Browser()
    b.login("auth_student", accounts["auth_student"])
    sid = b.sid()
    status, _, page = b.request("logout.php")
    check("GET logout.php shows a confirmation and does not log out", status == 200 and "Sign out?" in page and b.request("dashboard.php")[0] == 200)
    b.request("logout.php", {"csrf_token": "f" * 64})
    check("POST logout.php with a wrong token does not log out", b.request("dashboard.php")[0] == 200)
    status, headers, _ = b.logout()
    _, page, _ = b.follow(headers.get("Location", "login.php"))
    check("POST logout.php with the token -> login page 'You have been signed out.'",
          status == 303 and headers["Location"] == "login.php?status=logged_out" and "You have been signed out." in page)
    check("after logout every protected page redirects to the login page",
          all(b.request(p)[0] == 303 for p in PROTECTED))
    replay = Browser()
    replay.set_sid(sid)
    check("the old session cookie replayed -> no access (session destroyed on the server)", replay.request("dashboard.php")[0] == 303)
    check("USER_LOGOUT written to the audit log", audit_count("USER_LOGOUT", "auth_student") >= 1)


def access_tests(accounts):
    print("\n== Role-based access control")
    g = Browser()
    for p in PROTECTED:
        status, headers, _ = g.request(p)
        check(f"not signed in: {p} -> login page (status=login_required)", status == 303 and headers["Location"] == "login.php?status=login_required", f"{status} {headers.get('Location')}")
    for p in PUBLIC:
        check(f"public page {p} stays public (200)", g.request(p)[0] == 200)
    check("the public contact form has a CSRF token; a POST without it is refused (403)",
          not post_forms_without_token(g.request("contact.php")[2]) and g.request("contact.php", {"name": "x", "mail": "x@example.com", "msg": "hi"})[0] == 403)

    pages = {}
    for role, user in (("student", "auth_student"), ("editor", "auth_editor"), ("admin", "auth_admin")):
        b = Browser()
        b.login(user, accounts[user])
        pages[role] = b
        bad = [p for p in PROTECTED[:-1] if b.request(p)[0] != 200]
        check(f"{role}: all portal pages load (200)", not bad, str(bad))
        missing = sorted({f for p in PROTECTED[:-1] for f in post_forms_without_token(b.request(p)[2])})
        check(f"{role}: every POST form on the portal pages carries a CSRF token", not missing, str(missing))
    for role in ("student", "editor"):
        b = pages[role]
        denied_before = audit_count("ACCESS_DENIED", f"auth_{role}")
        status, _, page = b.request("admin_dashboard.php")
        check(f"{role} -> admin_dashboard.php: HTTP 403 'Access Denied' page", status == 403 and "Access Denied" in page)
        check(f"... recorded as ACCESS_DENIED in the audit log", audit_count("ACCESS_DENIED", f"auth_{role}") == denied_before + 1)
        token = b.token("dashboard.php")
        n = int(scalar("SELECT COUNT(*) FROM students"))
        status, _, _ = b.request("admin_dashboard.php", {"csrf_token": token, "action": "add_student", "enrollment_no": "X1", "name": "Hacked",
                                                         "email": f"{role}.hack@example.com", "course": "Computer Science", "semester": "3", "gender": "Male"})
        victim = scalar("SELECT id FROM students ORDER BY id LIMIT 1")
        victim_status = scalar(f"SELECT status FROM students WHERE id={victim}")
        status2, _, _ = b.request("admin_dashboard.php", {"csrf_token": token, "action": "deactivate_student", "id": victim})
        check(f"{role} cannot run admin operations (add/deactivate via POST -> 403, nothing changed)",
              status == 403 and status2 == 403 and int(scalar("SELECT COUNT(*) FROM students")) == n
              and scalar(f"SELECT status FROM students WHERE id={victim}") == victim_status)
    a = pages["admin"]
    status, _, page = a.request("admin_dashboard.php")
    check("admin -> Admin Console (200) with the user list and audit log", status == 200 and "Admin Console" in page)
    for tab in ("students", "events", "users", "audits"):
        st, _, pg = a.request(f"admin_dashboard.php?tab={tab}")
        if not check(f"admin console tab '{tab}' loads; all its POST forms carry a CSRF token", st == 200 and not post_forms_without_token(pg)):
            print(post_forms_without_token(pg)[:3])
    print("\n== CSRF and admin operations")
    n = int(scalar("SELECT COUNT(*) FROM students"))
    status, _, page = a.request("admin_dashboard.php", {"action": "add_student", "enrollment_no": "Z1", "name": "No Token", "email": "no.token.admin@example.com",
                                                        "course": "Computer Science", "semester": "3", "gender": "Male"})
    check("admin POST without CSRF token -> 403 'Security check failed', nothing stored",
          status == 403 and "Security check failed" in page and int(scalar("SELECT COUNT(*) FROM students")) == n)
    check("CSRF rejections are audit-logged", audit_count("CSRF_REJECTED") >= 1)
    token = a.token("admin_dashboard.php")
    st, hd, _ = a.request("admin_dashboard.php", {"csrf_token": token, "action": "add_student", "enrollment_no": "26CS900", "name": "Ann O'Neil",
                                                  "email": "quote.test@example.com", "course": "Computer Science", "semester": "4", "gender": "Female"})
    sid_new = scalar("SELECT id FROM students WHERE email='quote.test@example.com'")
    check("admin add student with the token -> stored, message via the session (no text in the URL)",
          sid_new is not None and hd.get("Location") == "admin_dashboard.php?tab=students")
    st, _, pg = a.request("admin_dashboard.php?tab=students")
    added = "was added with enrollment number 26CS900."
    check("the success message appears once, from the session", added in pg and added not in a.request("admin_dashboard.php?tab=students")[2])
    check("a name with a quote is HTML-escaped in the student list", "Ann O&#039;Neil" in pg and "Ann O'Neil" not in pg)
    st, _, _ = a.request(f"admin_dashboard.php?tab=students&action=deactivate_student&id={sid_new}")
    check("a GET link cannot deactivate a student", scalar(f"SELECT status FROM students WHERE id={sid_new}") == "Active")
    st, _, _ = a.request("admin_dashboard.php", {"action": "deactivate_student", "id": sid_new})
    check("POST deactivate without token -> 403, record unchanged", st == 403 and scalar(f"SELECT status FROM students WHERE id={sid_new}") == "Active")
    st, hd, _ = a.request("admin_dashboard.php", {"csrf_token": token, "action": "deactivate_student", "id": sid_new})
    check("POST deactivate with the token -> soft delete (status Inactive, record kept)",
          st == 303 and scalar(f"SELECT CONCAT(COUNT(*), status) FROM students WHERE id={sid_new}") == "1Inactive")
    st, _, page = a.request("admin_dashboard.php", {"csrf_token": token, "action": "add_student", "enrollment_no": "26CS901", "name": "Bad Sem",
                                                    "email": "bad.sem@example.com", "course": "Computer Science", "semester": "12", "gender": "Male"})
    check("admin add student with semester 12 -> refused with a message (no database error page)",
          st == 422 and scalar("SELECT COUNT(*) FROM students WHERE email='bad.sem@example.com'") == "0" and "number from 1 to 8" in page)
    admin_id = int(scalar("SELECT id FROM users WHERE username='auth_admin'"))
    a.request("admin_dashboard.php", {"csrf_token": token, "action": "delete_user", "id": admin_id})
    check("an admin cannot delete the own account", scalar(f"SELECT COUNT(*) FROM users WHERE id={admin_id}") == "1")

    print("\n== Session re-validation (account deleted / role changed while signed in)")
    s = Browser()
    s.login("auth_temp", accounts["auth_temp"])
    temp_id = int(scalar("SELECT id FROM users WHERE username='auth_temp'"))
    mysql(f"UPDATE users SET role='admin' WHERE id={temp_id}")
    check("a role change applies at the next request (promoted to admin -> console allowed)", s.request("admin_dashboard.php")[0] == 200)
    mysql(f"UPDATE users SET role='editor' WHERE id={temp_id}")
    check("... and demotion applies immediately too (editor -> 403)", s.request("admin_dashboard.php")[0] == 403)
    a.request("admin_dashboard.php", {"csrf_token": token, "action": "delete_user", "id": temp_id})
    status, headers, _ = s.request("dashboard.php")
    check("an account deleted while signed in loses access at once (login page 'account_unavailable')",
          status == 303 and headers["Location"] == "login.php?status=account_unavailable", f"{status} {headers.get('Location')}")


def profile_tests(accounts):
    print("\n== Profile: linkage and password change")
    e = Browser()
    e.login("auth_editor", accounts["auth_editor"])
    _, _, page = e.request("profile.php")
    owner = mysql("SELECT name, enrollment_no FROM students WHERE email='25cs023@charusat.edu.in'")
    shows_owner = bool(owner) and owner[0][1] in page
    check("an account without a linked student record sees its own username and no enrollment number (no other person's data)",
          "auth_editor" in page and not shows_owner)
    b = Browser()
    b.login("auth_student", accounts["auth_student"])
    uid = int(scalar("SELECT id FROM users WHERE username='auth_student'"))
    token = b.token("profile.php")
    base = {"form_action": "change_password", "csrf_token": token}
    _, _, page = b.request("profile.php", {**base, "oldpass": "Wrong!Pass1", "newpass": "N3w!Password", "confirm_newpass": "N3w!Password"})
    check("wrong current password -> refused", "Current password is incorrect" in page and password_ok(uid, accounts["auth_student"]))
    _, _, page = b.request("profile.php", {**base, "oldpass": accounts["auth_student"], "newpass": "weakpass", "confirm_newpass": "weakpass"})
    check("weak new password -> refused by the shared password policy", "an uppercase letter" in page and password_ok(uid, accounts["auth_student"]))
    st, _, _ = b.request("profile.php", {"form_action": "change_password", "oldpass": accounts["auth_student"], "newpass": "N3w!Password", "confirm_newpass": "N3w!Password"})
    check("password change without CSRF token -> 403, unchanged", st == 403 and password_ok(uid, accounts["auth_student"]))
    before = b.sid()
    _, _, page = b.request("profile.php", {**base, "oldpass": accounts["auth_student"], "newpass": "N3w!Password", "confirm_newpass": "N3w!Password"})
    check("valid change -> new hash stored, session ID regenerated", "Password changed successfully" in page and password_ok(uid, "N3w!Password") and b.sid() != before)
    accounts["auth_student"] = "N3w!Password"
    check("old password no longer works, new one does",
          Browser().login("auth_student", "Str0ng!Old1")[0] == 401 and Browser().login("auth_student", "N3w!Password")[0] == 303)


def timeout_tests(log_dir, accounts):
    print("\n== Inactivity timeout (second server, STUDENTHUB_SESSION_TIMEOUT=2)")
    server = Server(PORT_SHORT, log_dir, {"DB_NAME": TEST_DB, "STUDENTHUB_SESSION_TIMEOUT": "2"})
    try:
        b = Browser(PORT_SHORT)
        b.login("auth_student", accounts["auth_student"])
        ok1 = b.request("dashboard.php")[0] == 200
        time.sleep(1)
        ok2 = b.request("dashboard.php")[0] == 200
        check("requests within the timeout keep the session alive", ok1 and ok2)
        time.sleep(3.2)
        status, headers, _ = b.request("dashboard.php")
        _, page, _ = b.follow(headers.get("Location", "login.php"))
        check("after 3 s idle -> login page 'Your session ended because you were inactive…'",
              status == 303 and headers["Location"] == "login.php?status=timeout" and "inactive for too long" in page)
        check("... the session is gone and SESSION_TIMEOUT is audit-logged",
              b.request("dashboard.php")[0] == 303 and audit_count("SESSION_TIMEOUT", "auth_student") >= 1)
    finally:
        server.stop()


def database_down_tests(log_dir):
    print("\n== Database unavailable (no fallback, no details for visitors)")
    have_legacy = bool(mysql("SHOW DATABASES LIKE 'user_registration'", None))
    info(f"legacy database user_registration exists on this server: {have_legacy}")
    for port, env, label, secret in ((PORT_NODB, {"DB_NAME": "studenthub_no_such_db"}, "unknown database", None),
                                     (PORT_BADPW, {"DB_NAME": TEST_DB, "DB_PASS": "wr0ng-secret-pw"}, "wrong password", "wr0ng-secret-pw")):
        server = Server(port, log_dir, env)
        try:
            b = Browser(port)
            results = {p: b.request(p) for p in ("index.php", "login.php", "dashboard.php")}
            check(f"{label}: index, login and dashboard -> HTTP 503 'Service temporarily unavailable'",
                  all(r[0] == 503 and "Service temporarily unavailable" in r[2] for r in results.values()), str({p: r[0] for p, r in results.items()}))
            leak = [p for p, r in results.items() if re.search(r"mysqli|Unknown database|Access denied|studenthub_no_such|wr0ng|Stack trace|\.php on line|user_registration", r[2])]
            check(f"{label}: no credentials, database names, SQL or stack traces in the page", not leak, str(leak))
            check(f"{label}: no fallback - no login form or data from another database is served",
                  all('name="csrf_token"' not in r[2] and "Odoo" not in r[2] for r in results.values()))
            time.sleep(0.3)
            log = server.logged()
            check(f"{label}: the real reason is in the server log ('No fallback database is used')",
                  "cannot connect to the configured database" in log and "No fallback database is used" in log)
            if secret:
                check(f"{label}: the password itself is never written to the log", secret not in log)
        finally:
            server.stop()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dump")
    a = ap.parse_args()
    print(f"StudentHub authentication tests (PHP {PHP}, MySQL {MYSQL})")
    info("source: " + (pathlib.Path(a.source_dump).name if a.source_dump else "database/studenthub_demo.sql"))
    live_users_before = scalar("SELECT COUNT(*) FROM users", LIVE_DB)
    live_hash_before = hashlib.sha256("\n".join("|".join(r) for r in mysql("SELECT id, password FROM users ORDER BY id", LIVE_DB)).encode()).hexdigest()
    static_checks()
    create_test_db(a.source_dump)
    log_dir = tempfile.mkdtemp(prefix="auth-tests-")
    accounts = {"auth_admin": secrets.token_urlsafe(12), "auth_editor": secrets.token_urlsafe(12), "auth_student": "Str0ng!Old1",
                "auth_temp": secrets.token_urlsafe(12)}
    try:
        create_account("auth_admin", "auth.admin@example.com", "admin", accounts["auth_admin"])
        create_account("auth_editor", "auth.editor@example.com", "editor", accounts["auth_editor"])
        create_account("auth_student", "auth.student@example.com", "student", accounts["auth_student"])
        create_account("auth_temp", "auth.temp@example.com", "student", accounts["auth_temp"])
        server = Server(PORT, log_dir, {"DB_NAME": TEST_DB})
        try:
            student_uid = registration_tests()
            login_tests(accounts, student_uid)
            logout_tests(accounts)
            access_tests(accounts)
            profile_tests(accounts)
            print("\n== Server log")
            log = server.logged()
            bad = [l for l in log.splitlines() if re.search(r"PHP (Warning|Notice|Deprecated|Fatal|Parse)", l)]
            check("no PHP warnings, notices or fatal errors in the server log", not bad, "\n".join(bad[:3]))
            check("the forced registration failure was logged with details (shown to nobody)", "forced test failure" in log)
            check("no password appears in the server log", "Str0ng!" not in log and "N3w!Password" not in log)
        finally:
            server.stop()
        timeout_tests(log_dir, accounts)
        database_down_tests(log_dir)
    finally:
        drop_test_db()
        check("disposable database removed", not mysql(f"SHOW DATABASES LIKE '{TEST_DB}'", None))
        live_hash_after = hashlib.sha256("\n".join("|".join(r) for r in mysql("SELECT id, password FROM users ORDER BY id", LIVE_DB)).encode()).hexdigest()
        check("the live studenthub_db was not touched (users and password hashes unchanged)",
              scalar("SELECT COUNT(*) FROM users", LIVE_DB) == live_users_before and live_hash_after == live_hash_before)
    print(f"\nResult: {passed} passed, {failed} failed, {passed + failed} checks")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
