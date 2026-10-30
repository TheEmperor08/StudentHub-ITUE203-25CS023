"""StudentHub – Practical 12: automated tests (Python 3, standard library only).

Run from the Practical-12 folder:  python tests\\test_app.py
Creates the disposable database studenthub_prac12_test from studenthub_prac12.sql (only the name changed) and a
temporary upload folder with copies of the seed posters, sets a random administrator password with
tools/set_admin_password.php, starts XAMPP's PHP built-in server three times (normal; 2-second timeout with a 1 MB
POST limit; MySQL unreachable) and removes the test database and folder at the end. studenthub_prac12 and the real
uploads folder are never changed. The test password is random and never printed.
"""
import http.cookiejar, os, pathlib, re, secrets, shutil, struct, subprocess, sys, tempfile, time, urllib.error, urllib.parse, urllib.request, uuid, zlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures"
PHP = r"C:\xampp\php\php.exe" if os.path.exists(r"C:\xampp\php\php.exe") else "php"
MYSQL = r"C:\xampp\mysql\bin\mysql.exe" if os.path.exists(r"C:\xampp\mysql\bin\mysql.exe") else "mysql"
TEST_DB = "studenthub_prac12_test"
ADMIN = "admin.demo@example.com"
PASSWORD = secrets.token_urlsafe(18)
PORT, PORT_SHORT, PORT_DOWN = 8692, 8693, 8694
NAME_RE = re.compile(r"^[a-f0-9]{32}\.(jpg|png|webp)$")
passed = failed = 0
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def check(name, ok, detail=""):
    global passed, failed
    passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))


# ---------------------------------------------------------------- database helpers
def mysql(sql_text, database=TEST_DB):
    args = [MYSQL, "-u", "root", "-N", "-B"] + ([database] if database else [])
    r = subprocess.run(args, input=sql_text, capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        raise RuntimeError(r.stderr)
    return [line.split("\t") for line in r.stdout.splitlines()]


def scalar(sql_text):
    rows = mysql(sql_text)
    return rows[0][0] if rows else None


def count(where="1=1"):
    return int(scalar(f"SELECT COUNT(*) FROM events WHERE {where}"))


def drop_test_db():
    if mysql(f"SHOW DATABASES LIKE '{TEST_DB}'", None):
        if not mysql(f"SHOW TABLES FROM {TEST_DB} LIKE 'p12_test_marker'", None):
            raise RuntimeError(f"{TEST_DB} exists but was not created by these tests - not dropped")
        mysql(f"DROP DATABASE {TEST_DB}", None)


def create_test_db():
    sql = (ROOT / "studenthub_prac12.sql").read_text(encoding="utf-8").replace("`studenthub_prac12`", f"`{TEST_DB}`")
    assert "`studenthub_prac12`" not in sql and f"USE `{TEST_DB}`;" in sql
    mysql(sql + f"\nCREATE TABLE {TEST_DB}.p12_test_marker (id INT);\n", None)
    # Triggers that make one INSERT/UPDATE fail AFTER the poster was stored (to test the clean-up paths)
    body = "FOR EACH ROW BEGIN IF NEW.venue = 'Trigger Failure Hall' THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'forced test failure'; END IF; END//"
    mysql("DELIMITER //\nCREATE TRIGGER t_fail_insert BEFORE INSERT ON events " + body + "\n"
          "CREATE TRIGGER t_fail_update BEFORE UPDATE ON events " + body + "\nDELIMITER ;\n")


# ---------------------------------------------------------------- files
def png_bytes(width, height, rgb=(30, 64, 175)):
    """A real, valid PNG made with the standard library (zlib)."""
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


JPG, PNG, WEBP = ((FIX / f"valid-poster.{e}").read_bytes() for e in ("jpg", "png", "webp"))


def upload_files(folder):
    return {p.name for p in pathlib.Path(folder).iterdir() if p.is_file()}


# ---------------------------------------------------------------- HTTP client
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def multipart(fields, files):
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    for name, (filename, content, ctype) in files.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
                     f'Content-Type: {ctype}\r\n\r\n'.encode() + content + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


class Browser:
    def __init__(self, port=PORT):
        self.port, self.jar = port, http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar), NoRedirect)

    def request(self, path, data=None, files=None):
        headers = {}
        body = None
        if files is not None:
            body, headers["Content-Type"] = multipart(data or {}, files)
        elif data is not None:
            body = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/{path.lstrip('/')}", data=body, headers=headers)
        try:
            with self.opener.open(req, timeout=60) as r:
                return r.status, r.headers, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read()

    def get(self, path):
        s, h, b = self.request(path)
        return s, h, b.decode("utf-8", "replace")

    def post(self, path, data, files=None):
        s, h, b = self.request(path, data, files)
        return s, h, b.decode("utf-8", "replace")

    def follow(self, status, headers, page):
        return self.get(headers["Location"]) if status in (302, 303) else (status, headers, page)

    @staticmethod
    def token(page):
        m = re.search(r'name="csrf_token" value="([0-9a-f]{64})"', page)
        return m.group(1) if m else ""

    def sid(self):
        return next((c.value for c in self.jar if c.name == "P12SESSID"), None)

    def set_sid(self, value):
        self.jar.clear()
        self.jar.set_cookie(http.cookiejar.Cookie(0, "P12SESSID", value, None, False, "127.0.0.1", False, False, "/", True,
                                                  False, None, False, None, None, {}))

    def login(self, email=ADMIN, password=PASSWORD, token=True):
        _, _, page = self.get("login.php")
        data = {"email": email, "password": password}
        if token:
            data["csrf_token"] = self.token(page)
        return self.post("login.php", data)

    def csrf(self):
        _, _, page = self.get("index.php")
        return self.token(page)


def event_fields(**overrides):
    data = {"event_title": "Spring Coding Marathon", "description": "A full-day coding marathon for all students.",
            "category": "Hackathon", "event_date": "2027-03-20", "event_time": "09:30", "venue": "Seminar Hall 2", "status": "open"}
    data.update(overrides)
    return data


def flash(page):
    m = re.search(r'<div class="alert (alert-\w+)" role="\w+">(.*?)</div>', page, re.S)
    return (m.group(1), re.sub(r"<[^>]+>", "", m.group(2))) if m else (None, "")


def add_event(b, filename="poster.jpg", content=JPG, ctype="image/jpeg", token=None, **fields):
    files = {"poster": (filename, content, ctype)} if filename is not None else {"poster": ("", b"", "application/octet-stream")}
    data = event_fields(**fields)
    data["csrf_token"] = b.csrf() if token is None else token
    return b.post("add.php", data, files)


def edit_event(b, event_id, filename=None, content=b"", ctype="image/jpeg", token=None, **fields):
    stored = dict(zip(["event_title", "description", "category", "event_date", "event_time", "venue", "status"],
                      mysql(f"SELECT event_title, description, category, event_date, LEFT(event_time,5), venue, status FROM events WHERE event_id={event_id}")[0]))
    stored.update(fields)
    stored["event_id"] = str(event_id)
    stored["csrf_token"] = b.csrf() if token is None else token
    files = {"poster": (filename, content, ctype)} if filename else {"poster": ("", b"", "application/octet-stream")}
    return b.post(f"edit.php?id={event_id}", stored, files)


def table_ids(page):
    return re.findall(r'<tr class="[^"]*" data-event-id="(\d+)">', page)


# ---------------------------------------------------------------- servers
class Server:
    def __init__(self, port, log_dir, env, php_ini=()):
        self.port, self.log = port, pathlib.Path(log_dir) / f"php-{port}.log"
        self.out = open(pathlib.Path(log_dir) / f"server-{port}.txt", "w")
        environment = {k: v for k, v in os.environ.items() if not k.startswith("P12_")}
        environment.update(env)
        args = [PHP, "-d", f"error_log={self.log}"]
        for setting in php_ini:
            args += ["-d", setting]
        self.proc = subprocess.Popen(args + ["-S", f"127.0.0.1:{port}", "router.php"], cwd=ROOT, env=environment,
                                     stdout=self.out, stderr=subprocess.STDOUT)
        for _ in range(50):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/assets/app.css", timeout=2)
                return
            except Exception:
                time.sleep(0.2)
        raise RuntimeError(f"server on port {port} did not start")

    def logged(self):
        return self.log.read_text(encoding="utf-8", errors="replace") if self.log.exists() else ""

    def stop(self):
        self.proc.terminate()
        self.proc.wait(10)
        self.out.close()


def env_for(upload_dir, **extra):
    return {"P12_DB_NAME": TEST_DB, "P12_UPLOAD_DIR": str(upload_dir), **extra}


# ================================================================ tests
def static_checks():
    print("\n== Static checks")
    php_files = sorted(ROOT.rglob("*.php"))
    bad = [p.name for p in php_files if subprocess.run([PHP, "-l", str(p)], capture_output=True, text=True).returncode]
    check(f"php -l: no syntax errors in all {len(php_files)} PHP files", not bad, ", ".join(bad))
    source = "\n".join(p.read_text(encoding="utf-8") for p in php_files if p.name not in ("router.php", "config.example.php"))
    check("no ->query() / mysqli_query() / multi_query (prepared statements only)",
          not re.search(r"->query\(|mysqli_query|multi_query|real_query", source))
    check("SQL goes through prepare() + execute()", source.count("->prepare(") >= 12 and source.count("->execute()") >= 12)
    upload = (ROOT / "includes" / "upload.php").read_text(encoding="utf-8")
    check("upload validation uses finfo, getimagesize, is_uploaded_file, move_uploaded_file and random_bytes",
          all(x in upload for x in ("new finfo(FILEINFO_MIME_TYPE)", "getimagesize(", "is_uploaded_file(", "move_uploaded_file(", "random_bytes(16)")))
    check("move_uploaded_file / unlink only in includes/upload.php (and the clean-up tool)",
          all(("move_uploaded_file(" not in p.read_text(encoding="utf-8") and "unlink(" not in p.read_text(encoding="utf-8"))
              for p in php_files if p.name not in ("upload.php", "cleanup_orphan_posters.php")))
    ht = (ROOT / "uploads" / ".htaccess").read_text(encoding="utf-8")
    check("uploads/.htaccess: Require all denied, php engine off, script handlers removed",
          "Require all denied" in ht and "php_flag engine off" in ht and "RemoveHandler .php" in ht)


def database_checks(upload_dir):
    print("\n== Database (studenthub_prac12.sql imported into studenthub_prac12_test)")
    check("12 seed events: 8 open, 4 closed", count() == 12 and count("status='open'") == 8 and count("status='closed'") == 4)
    check("6 categories, every event has a valid category (foreign key)",
          int(scalar("SELECT COUNT(*) FROM event_categories")) == 6
          and int(scalar("SELECT COUNT(*) FROM events e JOIN event_categories c ON c.category_name = e.category")) == 12)
    check("1 administrator, password stored as a bcrypt hash", scalar("SELECT COUNT(*) FROM admins WHERE password_hash LIKE '$2y$%'") == "1")
    engines = {r[0] for r in mysql(f"SELECT ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA='{TEST_DB}' AND TABLE_NAME<>'p12_test_marker'")}
    check("all tables are InnoDB", engines == {"InnoDB"}, str(engines))
    idx = {r[0] for r in mysql(f"SELECT INDEX_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA='{TEST_DB}' AND TABLE_NAME='events'")}
    check("indexes on category, status, date and a UNIQUE poster_filename",
          {"idx_events_category", "idx_events_status", "idx_events_date", "uq_events_poster_filename"} <= idx, str(idx))
    names = [r[0] for r in mysql("SELECT poster_filename FROM events")]
    check("every seed poster name has the random format and the file exists", all(NAME_RE.match(n) and (ROOT / "uploads" / n).is_file() for n in names))
    for sql, constraint, label in [
        ("INSERT INTO events (event_title,description,category,event_date,event_time,venue,poster_filename) VALUES ('Bad Cat','xxxxxxxxxx','Music','2027-01-01','10:00','Hall','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.jpg')", "fk_events_category", "unknown category refused by the foreign key"),
        ("UPDATE events SET poster_filename='../db.php' WHERE event_id=1", "chk_events_poster_filename", "CHECK refuses a poster name like ../db.php"),
        (f"UPDATE events SET poster_filename='{scalar('SELECT poster_filename FROM events WHERE event_id=2')}' WHERE event_id=1", "uq_events_poster_filename", "UNIQUE refuses two events sharing one poster file"),
        ("INSERT INTO admins (full_name,email,password_hash) VALUES ('X','x@example.com','plaintext')", "chk_admins_password_hash", "CHECK refuses a plaintext admin password")]:
        try:
            mysql(sql)
            check(label, False)
        except RuntimeError as e:
            check(label, constraint in str(e) or ("Duplicate" in str(e) and constraint.startswith("uq")), str(e)[:120])


def auth_checks(server):
    print("\n== Administrator authentication and access control")
    guest = Browser()
    for path in ["index.php", "add.php", "edit.php?id=1", "view.php?id=1", "delete.php?id=1", "poster.php?file=" + scalar("SELECT poster_filename FROM events WHERE event_id=1")]:
        status, _, page = guest.get(path)
        check(f"not logged in: GET {path.split('?')[0]} -> 401 'Access denied', no event data",
              status == 401 and "Access denied" in page and "Code Sprint" not in page, str(status))
    before = count()
    status, _, _ = guest.post("add.php", event_fields(csrf_token="x"), {"poster": ("p.jpg", JPG, "image/jpeg")})
    status2, _, _ = guest.post("delete.php", {"event_id": "1", "csrf_token": "x"})
    check("not logged in: POST add.php / delete.php -> 401, nothing changed", status == 401 and status2 == 401 and count() == before)

    b = Browser()
    status, headers, page = b.get("login.php")
    check("login page 200 with CSRF token; cookie HttpOnly + SameSite=Strict",
          status == 200 and b.token(page) and re.search(r"P12SESSID=.*HttpOnly.*SameSite=Strict", headers.get("Set-Cookie", ""), re.I) is not None)
    for label, email, password in [("wrong password", ADMIN, "wrong-password-123"), ("unknown email", "nobody@example.com", PASSWORD),
                                   ("SQL injection ' OR '1'='1", "' OR '1'='1", "' OR '1'='1"), ("empty fields", "", "")]:
        status, _, page = b.login(email, password)
        check(f"failed login ({label}) -> 401 'Invalid email or password.'", status == 401 and "Invalid email or password." in page and current_session_ok(b) is False)
    status, _, page = b.login(token=False)
    check("login without CSRF token refused", status == 401 and "login form expired" in page)

    before_sid = b.sid()
    status, headers, _ = b.login()
    after_sid = b.sid()
    _, _, page = b.get("index.php")
    check("valid login -> 303 to index.php with welcome message", status == 303 and headers["Location"] == "index.php" and "Welcome, Demo Admin" in page)
    check("session ID regenerated at login", before_sid and after_sid and before_sid != after_sid)
    old = Browser()
    old.set_sid(before_sid)
    check("the pre-login session ID gives no access", old.get("index.php")[0] == 401)
    check("last_login_at stored", scalar("SELECT last_login_at IS NOT NULL FROM admins WHERE email='admin.demo@example.com'") == "1")
    check("protected pages send Cache-Control: no-store and a CSP", "no-store" in b.request("index.php")[1].get("Cache-Control", "")
          and "default-src 'self'" in b.request("index.php")[1].get("Content-Security-Policy", ""))
    return b


def current_session_ok(b):
    return b.get("index.php")[0] == 200


def logout_checks():
    print("\n== Logout")
    b = Browser()
    b.login()
    sid = b.sid()
    status, _, _ = b.get("logout.php")
    check("GET logout.php does not log out", current_session_ok(b))
    b.post("logout.php", {"csrf_token": "0" * 64})
    check("POST logout.php with a wrong token does not log out", current_session_ok(b))
    status, headers, _ = b.post("logout.php", {"csrf_token": b.csrf()})
    _, _, page = b.follow(status, headers, "")
    check("POST logout.php with token -> 'You have been logged out successfully.'", status == 303 and "logged out successfully" in page)
    check("after logout index.php -> 401", b.get("index.php")[0] == 401)
    replay = Browser()
    replay.set_sid(sid)
    check("the old session cookie replayed -> 401 (session destroyed on the server)", replay.get("index.php")[0] == 401)


def listing_checks(b):
    print("\n== Event list and poster delivery")
    status, _, page = b.get("index.php")
    check("index.php lists all 12 events", status == 200 and len(table_ids(page)) == 12 and "Showing <strong>12</strong> of 12 events" in page)
    check("table shows poster, event, category, date & time, venue, status",
          all(f">{h}</th>" in page for h in ["Poster", "Event", "Category", "Date &amp; time", "Venue", "Status"]))
    thumbs = re.findall(r'<img class="poster-thumb" src="poster\.php\?file=([a-f0-9]{32}\.(?:jpg|png|webp))"', page)
    check("12 poster thumbnails delivered through poster.php", len(thumbs) == 12)
    check("Open and Closed status badges shown", page.count(">Open</span>") == 8 and page.count(">Closed</span>") == 4)
    name = scalar("SELECT poster_filename FROM events WHERE event_id=1")
    status, headers, body = b.request("poster.php?file=" + name)
    check("poster.php returns the exact image bytes with an image Content-Type and nosniff",
          status == 200 and headers.get("Content-Type") == "image/jpeg" and body == (ROOT / "uploads" / name).read_bytes()
          and headers.get("X-Content-Type-Options") == "nosniff")
    status, _, page = b.get("view.php?id=3")
    check("view.php shows the event details and the full-size poster", status == 200 and "AI in Healthcare Seminar" in page and 'class="img-fluid rounded border poster-full"' in page)


def traversal_checks(b, upload_dir):
    print("\n== Path traversal and upload-folder protection")
    for bad in ["../db.php", "..%2Fdb.php", "..\\db.php", "%2e%2e%2fdb.php", str(ROOT / "db.php"), "C:/Windows/win.ini",
                "x.php", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA.jpg", "1a023e38c1e411c26656d6a75e9ede04.jpg/../../db.php", ""]:
        status, _, body = b.request("poster.php?file=" + urllib.parse.quote(bad, safe="%"))
        check(f"poster.php?file={bad[:40]!r} -> 404, nothing revealed", status == 404 and b"<?php" not in body, str(status))
    seed = scalar("SELECT poster_filename FROM events WHERE event_id=1")
    for path in [f"uploads/{seed}", "uploads/.htaccess", "uploads/", "uploads/shell.php", "Uploads/x.php", "uploads%2Fx.php"]:
        check(f"direct request /{path} -> 403", b.get(path)[0] == 403)
    planted = "0" * 31 + "a.jpg"
    (pathlib.Path(upload_dir) / planted).write_bytes(b"<?php echo 'EXECUTED-' . (6*7); ?>")
    status, headers, body = b.request("poster.php?file=" + planted)
    check("PHP code inside the upload folder is never executed (sent as raw bytes with an image type)",
          b"EXECUTED-42" not in body and body.startswith(b"<?php") and headers.get("Content-Type") == "image/jpeg")
    (pathlib.Path(upload_dir) / planted).unlink()


def create_checks(b, upload_dir):
    print("\n== Create event with poster upload")
    names = []
    for ext, content, ctype in (("jpg", JPG, "image/jpeg"), ("png", PNG, "image/png"), ("webp", WEBP, "image/webp")):
        before_files, before = upload_files(upload_dir), count()
        status, headers, _ = add_event(b, f"my poster.{ext}", content, ctype, event_title=f"Upload Test {ext.upper()}")
        _, _, page = b.follow(status, headers, "")
        stored = scalar(f"SELECT poster_filename FROM events WHERE event_title='Upload Test {ext.upper()}'")
        new = upload_files(upload_dir) - before_files
        check(f"valid {ext.upper()} poster -> 303, success message, 1 new event",
              status == 303 and count() == before + 1 and "was added successfully" in flash(page)[1])
        check(f"{ext.upper()}: stored under a random name '<32 hex>.{ext}', identical bytes, original name not used",
              stored is not None and NAME_RE.match(stored) and stored.endswith("." + ext) and new == {stored}
              and (pathlib.Path(upload_dir) / stored).read_bytes() == content and "my poster" not in stored)
        names.append(stored)
    check("three uploads got three different random names", len(set(names)) == 3)
    status, headers, _ = add_event(b, "../../db.php.jpg", JPG, "image/jpeg", event_title="Traversal Name Test")
    stored = scalar("SELECT poster_filename FROM events WHERE event_title='Traversal Name Test'")
    check("upload named '../../db.php.jpg' is stored under a random name inside the upload folder",
          status == 303 and NAME_RE.match(stored or "") and (pathlib.Path(upload_dir) / stored).is_file() and (ROOT / "db.php").read_bytes().startswith(b"<?php"))
    eid = scalar("SELECT event_id FROM events WHERE event_title='Traversal Name Test'")
    _, _, page = b.follow(status, headers, "")
    check("after adding, the list highlights the new event", f'<tr class="table-warning" data-event-id="{eid}">' in page)

    print("\n== Event validation")
    before_files, before = upload_files(upload_dir), count()
    status, _, page = b.post("add.php", {"csrf_token": b.csrf()}, {"poster": ("", b"", "application/octet-stream")})
    check("empty form -> 422 with an error for title, description, category, date, time, venue and poster",
          status == 422 and all(t in page for t in ["Event title is required.", "Description is required.", "Please select a category.",
                                                   "Event date is required.", "Event time is required.", "Venue is required.", "Please choose a poster image."]))
    status, _, page = add_event(b, category="Music", event_date="2026-02-30", event_time="25:00", status="pending", event_title="AB")
    check("tampered values: unknown category, 30 Feb, 25:00, status 'pending', 2-letter title -> all refused",
          status == 422 and all(t in page for t in ["category from the list", "valid date", "valid time", "Open or Closed", "3–150 characters"]))
    status, _, page = add_event(b, event_title="")
    check("valid poster + invalid fields -> 422 and 'poster must be chosen again'", status == 422 and "must be chosen again" in page)
    check("no event and no file were stored by the rejected forms", count() == before and upload_files(upload_dir) == before_files)

    print("\n== Poster validation (rejected files)")
    big_ok = JPG + b"\x00" * (2 * 1024 * 1024 - len(JPG))
    cases = [
        ("valid PNG renamed to .gif", "poster.gif", PNG, "image/gif", "Invalid file type"),
        ("PHP script poster.php", "poster.php", b"<?php system($_GET['c']); ?>", "application/x-php", "Invalid file type"),
        ("PHP script disguised as poster.jpg", "poster.jpg", b"<?php system($_GET['c']); ?>", "image/jpeg", "Invalid file type"),
        ("SVG image poster.svg", "poster.svg", b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>', "image/svg+xml", "Invalid file type"),
        ("SVG disguised as poster.png", "poster.png", b'<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>', "image/png", "not a JPEG, PNG or WebP"),
        ("Windows executable as poster.jpg", "poster.jpg", b"MZ\x90\x00\x03" + b"\x00" * 200 + b"This program cannot be run in DOS mode", "image/jpeg", "not a JPEG, PNG or WebP"),
        ("MIME mismatch: PNG content named .jpg", "poster.jpg", PNG, "image/jpeg", "does not match its content"),
        ("MIME mismatch: JPEG content named .webp", "poster.webp", JPG, "image/webp", "does not match its content"),
        ("corrupted JPEG (valid header, garbage body)", "poster.jpg", b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + os.urandom(3000), "image/jpeg", "not a valid image or is damaged"),
        ("truncated PNG (header only, no image data)", "poster.png", PNG[:40], "image/png", "not a valid image or is damaged"),
        ("truncated PNG (cut in half)", "poster.png", PNG[:len(PNG) // 2], "image/png", "not a valid image or is damaged"),
        ("PNG with a damaged chunk (wrong CRC)", "poster.png", PNG[:60] + bytes([PNG[60] ^ 0xFF]) + PNG[61:], "image/png", "not a valid image or is damaged"),
        ("truncated JPEG (cut in half, no end marker)", "poster.jpg", JPG[:len(JPG) // 2], "image/jpeg", "not a valid image or is damaged"),
        ("truncated WebP (cut in half)", "poster.webp", WEBP[:len(WEBP) // 2], "image/webp", "not a valid image or is damaged"),
        ("JPEG with embedded PHP code (polyglot)", "poster.jpg", JPG + b"<?php echo 'x'; ?>", "image/jpeg", "contains embedded code"),
        ("oversized poster (2 MB + 1 byte)", "poster.jpg", big_ok + b"\x00", "image/jpeg", "maximum size is 2 MB"),
        ("image wider than 6000 px", "poster.png", png_bytes(7000, 1), "image/png", "between 1 and 6000 pixels"),
        ("empty file", "poster.jpg", b"", "image/jpeg", None),
    ]
    for label, filename, content, ctype, expected in cases:
        before_files, before = upload_files(upload_dir), count()
        status, _, page = add_event(b, filename, content, ctype, event_title=f"Rejected {label[:40]}")
        ok = status == 422 and count() == before and upload_files(upload_dir) == before_files and "The event was not added." in page
        check(f"{label} -> rejected" + (f" ('{expected}')" if expected else ""), ok and (expected is None or expected in page), f"{status}")
    status, headers, _ = add_event(b, "exact.jpg", big_ok, "image/jpeg", event_title="Exactly Two Megabytes")
    check("poster of exactly 2 MB (2 097 152 bytes) is accepted", status == 303 and count("event_title='Exactly Two Megabytes'") == 1)

    print("\n== Failed INSERT leaves no abandoned file")
    before_files, before = upload_files(upload_dir), count()
    status, _, page = add_event(b, "p.jpg", JPG, "image/jpeg", venue="Trigger Failure Hall", event_title="Insert Failure Test")
    check("INSERT forced to fail after the poster was stored -> 503 general message, no SQL details",
          status == 503 and "not available right now" in page and "forced test failure" not in page and "SQLSTATE" not in page)
    check("the stored poster was removed again (no abandoned file, no event)", upload_files(upload_dir) == before_files and count() == before)


def update_checks(b, upload_dir):
    print("\n== Update event and poster replacement")
    eid = 2
    old = scalar(f"SELECT poster_filename FROM events WHERE event_id={eid}")
    _, _, form = b.get(f"edit.php?id={eid}")
    check("edit form filled from MySQL with the current poster shown",
          'value="Web Frameworks Workshop"' in form and f"poster.php?file={old}" in form and "Leave empty to keep the current poster" in form)
    status, headers, _ = edit_event(b, eid, venue="Computer Lab 4", event_title="Web Frameworks Workshop II")
    _, _, page = b.follow(status, headers, "")
    row = mysql(f"SELECT event_title, venue, poster_filename FROM events WHERE event_id={eid}")[0]
    check("update without a new file -> success, 'existing poster was kept'", status == 303 and "existing poster was kept" in flash(page)[1])
    check("fields changed in MySQL, poster name and file unchanged",
          row == ["Web Frameworks Workshop II", "Computer Lab 4", old] and (pathlib.Path(upload_dir) / old).is_file())

    before_files = upload_files(upload_dir)
    status, headers, _ = edit_event(b, eid, "replacement.webp", WEBP, "image/webp")
    _, _, page = b.follow(status, headers, "")
    new = scalar(f"SELECT poster_filename FROM events WHERE event_id={eid}")
    check("valid replacement poster -> success, 'poster was replaced'", status == 303 and "poster was replaced" in flash(page)[1])
    check("new random .webp name stored, new file present, old file deleted after the update",
          new != old and NAME_RE.match(new) and new.endswith(".webp") and upload_files(upload_dir) == (before_files - {old}) | {new})

    before_files = upload_files(upload_dir)
    status, _, page = edit_event(b, eid, "evil.php", b"<?php phpinfo(); ?>", "application/x-php", event_title="Should Not Be Saved")
    check("invalid replacement -> 422, 'current poster was kept', nothing changed",
          status == 422 and "current poster was kept" in page and scalar(f"SELECT event_title FROM events WHERE event_id={eid}") == "Web Frameworks Workshop II"
          and scalar(f"SELECT poster_filename FROM events WHERE event_id={eid}") == new and upload_files(upload_dir) == before_files)
    status, _, page = edit_event(b, eid, "big.jpg", JPG + b"\x00" * (2 * 1024 * 1024), "image/jpeg")
    check("oversized replacement -> 422, old poster kept", status == 422 and "maximum size is 2 MB" in page and upload_files(upload_dir) == before_files)
    status, _, page = edit_event(b, eid, "ok.png", PNG, "image/png", event_title="")
    check("valid replacement + invalid title -> 422, no file stored, old poster kept",
          status == 422 and upload_files(upload_dir) == before_files and scalar(f"SELECT poster_filename FROM events WHERE event_id={eid}") == new)
    status, _, page = edit_event(b, eid, "ok.png", PNG, "image/png", venue="Trigger Failure Hall")
    check("UPDATE forced to fail after the new poster was stored -> 503, new file removed, old poster kept",
          status == 503 and upload_files(upload_dir) == before_files and scalar(f"SELECT poster_filename FROM events WHERE event_id={eid}") == new
          and (pathlib.Path(upload_dir) / new).is_file())
    status, _, _ = b.get("edit.php?id=9999")
    check("edit of an unknown ID -> redirect with 'not found'", status == 303 and "That event was not found." in flash(b.get("index.php")[2])[1])


def delete_checks(b, upload_dir):
    print("\n== Delete event")
    eid = int(scalar("SELECT event_id FROM events WHERE event_title='Upload Test PNG'"))
    poster = scalar(f"SELECT poster_filename FROM events WHERE event_id={eid}")
    status, _, page = b.get(f"delete.php?id={eid}")
    check("GET delete.php shows a confirmation ('Are you sure…'), nothing deleted",
          status == 200 and "Are you sure you want to delete" in page and "Yes, delete event" in page and count(f"event_id={eid}") == 1)
    b.post("delete.php", {"event_id": str(eid)})
    b.post("delete.php", {"event_id": str(eid), "csrf_token": "f" * 64})
    check("POST without / with a wrong CSRF token -> not deleted", count(f"event_id={eid}") == 1 and (pathlib.Path(upload_dir) / poster).is_file())
    before_files = upload_files(upload_dir)
    status, headers, _ = b.post("delete.php", {"event_id": str(eid), "csrf_token": b.csrf()})
    _, _, page = b.follow(status, headers, "")
    check("confirmed delete -> 'was deleted together with its poster file'", status == 303 and "deleted together with its poster file" in flash(page)[1])
    check("event row removed and only its poster file deleted", count(f"event_id={eid}") == 0 and upload_files(upload_dir) == before_files - {poster})
    status, headers, _ = b.post("delete.php", {"event_id": str(eid), "csrf_token": b.csrf()})
    check("deleting it again -> 'not found, nothing deleted'", "nothing was deleted" in flash(b.follow(status, headers, "")[2])[1])
    before_files, total = upload_files(upload_dir), count()
    b.post("delete.php", {"event_id": "1 OR 1=1", "csrf_token": b.csrf()})
    b.post("delete.php", {"event_id": "../db.php", "csrf_token": b.csrf()})
    check("event_id '1 OR 1=1' / '../db.php' -> nothing deleted", count() == total and upload_files(upload_dir) == before_files)


def filter_checks(b):
    print("\n== Category and Open/Closed filters")
    _, _, page = b.get("index.php?category=Workshop")
    cats = re.findall(r'<td><span class="badge text-bg-light border">(.*?)</span></td>', page)
    n_workshop, n_open, n_closed = count("category='Workshop'"), count("status='open'"), count("status='closed'")
    check(f"category=Workshop -> only Workshop events ({n_workshop})", cats and set(cats) == {"Workshop"} and len(cats) == n_workshop)
    _, _, page = b.get("index.php?status=open")
    check(f"status=open -> {n_open} events, all Open", len(table_ids(page)) == n_open and ">Closed</span>" not in page.split("<tbody>")[1])
    _, _, page = b.get("index.php?status=closed")
    check(f"status=closed -> {n_closed} events, all Closed", len(table_ids(page)) == n_closed and ">Open</span>" not in page.split("<tbody>")[1])
    _, _, page = b.get("index.php?category=Sports&status=closed")
    check("category=Sports + status=closed combined", len(table_ids(page)) == count("category='Sports' AND status='closed'") and "with status <strong>Closed</strong>" in page)
    _, _, page = b.get("index.php?category=Hackathon&status=open")
    check("filters stay selected in the form", '<option value="Hackathon" selected>' in page and '<option value="open" selected>' in page)
    _, _, page = b.get("index.php?category=Music&status=pending")
    check("unknown category/status values are ignored (all events listed)", len(table_ids(page)) == count())
    _, _, page = b.get("index.php?" + urllib.parse.urlencode({"category": "Sports' OR '1'='1", "status": "open' -- "}))
    check("SQL injection in the filters is ignored (all events listed)", len(table_ids(page)) == count())
    _, _, page = b.get("index.php?category=Cultural&status=open&x=1")
    check("a filter with no matches can show 'No events match'", len(table_ids(page)) == count("category='Cultural' AND status='open'"))


def security_checks(b, upload_dir):
    print("\n== XSS, SQL injection and CSRF")
    xss_title = '<script>alert("xss")</script> Gala'
    status, _, _ = add_event(b, event_title=xss_title, description='<img src=x onerror=alert(1)> evening program', venue='"><b>Hall</b>')
    eid = scalar("SELECT event_id FROM events WHERE venue='\"><b>Hall</b>'")
    pages = [b.get(p)[2] for p in ("index.php", f"view.php?id={eid}", f"edit.php?id={eid}", f"delete.php?id={eid}")]
    check("title/description/venue with HTML are stored as text", status == 303 and eid is not None)
    check("HTML is escaped in the list, view, edit and delete pages",
          all("<script>alert" not in p and "<img src=x" not in p and "<b>Hall</b>" not in p for p in pages)
          and "&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt; Gala" in pages[0] and "&lt;img src=x onerror=alert(1)&gt;" in pages[1])
    status, _, _ = add_event(b, event_title="Robert'); DROP TABLE events;--", venue="O'Neill Hall")
    check("SQL metacharacters stored literally, table intact",
          status == 303 and scalar("SELECT venue FROM events WHERE event_title='Robert''); DROP TABLE events;--'") == "O'Neill Hall")
    status, _, _ = b.get("view.php?id=1%20OR%201=1")
    check("view.php?id=1 OR 1=1 -> not found", status == 303)

    before, before_files = count(), upload_files(upload_dir)
    status, headers, _ = add_event(b, token="")
    check("add without CSRF token -> refused with an error, no event, no file",
          status == 303 and "security token" in flash(b.get("index.php")[2])[1] and count() == before and upload_files(upload_dir) == before_files)
    other = Browser()
    other.login()
    status, _, _ = add_event(b, token=other.csrf())
    check("add with another session's token -> refused", status == 303 and count() == before)
    status, _, _ = edit_event(b, 1, token="", event_title="CSRF Changed")
    check("edit without CSRF token -> refused, unchanged", status == 303 and scalar("SELECT event_title FROM events WHERE event_id=1") == "Code Sprint 2026")

    print("\n== Protected files")
    for path in ["db.php", "includes/upload.php", "includes/functions.php", "tools/set_admin_password.php", "tests/test_app.py",
                 "studenthub_prac12.sql", "README.md", "config.example.php", ".gitignore", ".htaccess", "start-server.bat"]:
        check(f"/{path} -> 403", b.get(path)[0] == 403)


def short_server_checks(log_dir, upload_dir):
    print("\n== Session timeout and server upload limits (second server: 2-second timeout, post_max_size=1M, upload_max_filesize=512K)")
    server = Server(PORT_SHORT, log_dir, env_for(upload_dir, P12_SESSION_TIMEOUT="2"), ["post_max_size=1M", "upload_max_filesize=512K"])
    try:
        b = Browser(PORT_SHORT)
        b.login()
        before, before_files = count(), upload_files(upload_dir)
        status, _, page = add_event(b, "big.jpg", JPG + b"\x00" * 1_200_000, "image/jpeg")
        check("POST larger than post_max_size -> 'too large for the server', not a CSRF error",
              status == 422 and "too large for the server" in page and count() == before and upload_files(upload_dir) == before_files)
        status, _, page = add_event(b, "mid.jpg", JPG + b"\x00" * 900_000, "image/jpeg", event_title="Ini Size Test")
        check("file above upload_max_filesize (UPLOAD_ERR_INI_SIZE) -> 'The poster is too large' message", status == 422 and "The poster is too large" in page)
        check("within the timeout the session stays valid", current_session_ok(b))
        time.sleep(3.2)
        status, headers, _ = b.get("index.php")
        _, _, page = b.follow(status, headers, "")
        check("after 3 s idle -> session ended, login page 'session expired'", status == 303 and "login.php?status=timeout" in headers.get("Location", "") and "session expired" in page)
        check("and the session is gone", b.get("index.php")[0] == 401)
    finally:
        server.stop()


def cleanup_tool_checks(upload_dir):
    print("\n== Abandoned-file clean-up tool")
    folder = pathlib.Path(upload_dir)
    orphan, recent, other = folder / ("b" * 32 + ".png"), folder / ("c" * 32 + ".jpg"), folder / "notes.txt"
    for f, data in ((orphan, PNG), (recent, JPG), (other, b"keep")):
        f.write_bytes(data)
    old_time = time.time() - 7200
    os.utime(orphan, (old_time, old_time))
    os.utime(other, (old_time, old_time))
    used = {r[0] for r in mysql("SELECT poster_filename FROM events")}
    env = {k: v for k, v in os.environ.items() if not k.startswith("P12_")}
    env.update(env_for(upload_dir))
    listed = subprocess.run([PHP, "tools/cleanup_orphan_posters.php"], cwd=ROOT, env=env, capture_output=True, text=True).stdout
    check("list mode reports only the abandoned old poster, deletes nothing", orphan.name in listed and recent.name not in listed and orphan.exists())
    out = subprocess.run([PHP, "tools/cleanup_orphan_posters.php", "--delete"], cwd=ROOT, env=env, capture_output=True, text=True).stdout
    check("--delete removes it; recent files, other files and every used poster are kept",
          not orphan.exists() and recent.exists() and other.exists() and all((folder / n).exists() for n in used) and "1 deleted" in out)
    recent.unlink()
    other.unlink()
    check("the CLI tools refuse to run in a web request (PHP_SAPI check present)",
          all("PHP_SAPI !== 'cli'" in (ROOT / "tools" / n).read_text(encoding="utf-8") for n in ("set_admin_password.php", "cleanup_orphan_posters.php")))


def database_down_checks(log_dir, upload_dir):
    print("\n== MySQL unreachable")
    server = Server(PORT_DOWN, log_dir, env_for(upload_dir, P12_DB_PORT="1"))
    try:
        b = Browser(PORT_DOWN)
        status, _, page = b.get("login.php")
        status2, _, page2 = b.login()
        check("login -> 503 'The event database is not available right now', no technical details",
              status2 == 503 and "not available right now" in page2 and not re.search(r"mysqli|Access denied|SQLSTATE|127\.0\.0\.1:1|Stack trace", page2))
        time.sleep(0.3)
        check("the real error is written to the PHP log", "Practical 12 database connection failed" in server.logged())
    finally:
        server.stop()


def main():
    print(f"StudentHub Practical 12 tests  (PHP: {PHP}, MySQL: {MYSQL})")
    static_checks()
    drop_test_db()
    create_test_db()
    work = pathlib.Path(tempfile.mkdtemp(prefix="p12-tests-"))
    upload_dir, log_dir = work / "uploads", work / "logs"
    upload_dir.mkdir()
    log_dir.mkdir()
    for p in (ROOT / "uploads").iterdir():
        if NAME_RE.match(p.name):
            shutil.copy(p, upload_dir / p.name)
    real_uploads_before = upload_files(ROOT / "uploads")
    try:
        env = {k: v for k, v in os.environ.items() if not k.startswith("P12_")}
        env.update(env_for(upload_dir))
        r = subprocess.run([PHP, "tools/set_admin_password.php", ADMIN], input=PASSWORD + "\n", cwd=ROOT, env=env, capture_output=True, text=True)
        check("tools/set_admin_password.php sets a password_hash() hash (test database)", r.returncode == 0
              and scalar("SELECT password_hash LIKE '$2y$%' FROM admins") == "1" and PASSWORD not in scalar("SELECT password_hash FROM admins"))
        database_checks(upload_dir)
        server = Server(PORT, log_dir, env_for(upload_dir))
        try:
            b = auth_checks(server)
            listing_checks(b)
            traversal_checks(b, upload_dir)
            create_checks(b, upload_dir)
            update_checks(b, upload_dir)
            delete_checks(b, upload_dir)
            filter_checks(b)
            security_checks(b, upload_dir)
            logout_checks()
            print("\n== Server log")
            log = server.logged()
            unexpected = [l for l in log.splitlines() if re.search(r"PHP (Warning|Notice|Deprecated|Fatal|Parse)", l)]
            check("no PHP warnings, notices or fatal errors logged", not unexpected, "\n".join(unexpected[:3]))
            check("the two forced failures were logged with details (not shown to the user)", log.count("forced test failure") == 2, str(log.count("forced test failure")))
        finally:
            server.stop()
        short_server_checks(log_dir, upload_dir)
        cleanup_tool_checks(upload_dir)
        database_down_checks(log_dir, upload_dir)
        check("the real uploads folder was not changed by the tests", upload_files(ROOT / "uploads") == real_uploads_before)
    finally:
        drop_test_db()
        shutil.rmtree(work, ignore_errors=True)
        check("test database and temporary upload folder removed", not mysql(f"SHOW DATABASES LIKE '{TEST_DB}'", None) and not work.exists())
        live = mysql("SELECT COUNT(*) FROM events", "studenthub_prac12")[0][0]
        print(f"(studenthub_prac12 was not used by the tests; it holds {live} events)")
    print(f"\nResult: {passed} passed, {failed} failed, {passed + failed} checks")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
