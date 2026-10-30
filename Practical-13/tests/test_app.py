"""StudentHub – Practical 13: automated tests of the JSON API and the source files (Python 3, standard library only).

Run from the Practical-13 folder:  python tests\\test_app.py
Creates the disposable database studenthub_prac13_test from schema.sql (only the name changed), starts XAMPP's PHP
built-in server twice (normal, and with MySQL unreachable) and removes the test database at the end.
studenthub_prac13 is never changed. The browser part (Fetch, no reload, debounce, loading state) is tested in Edge by
tests/browser_screenshots.py.
"""
import json, os, pathlib, re, subprocess, sys, tempfile, time, urllib.error, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
PHP = r"C:\xampp\php\php.exe" if os.path.exists(r"C:\xampp\php\php.exe") else "php"
MYSQL = r"C:\xampp\mysql\bin\mysql.exe" if os.path.exists(r"C:\xampp\mysql\bin\mysql.exe") else "mysql"
TEST_DB = "studenthub_prac13_test"
PORT, PORT_DOWN = 8693, 8694
passed = failed = 0
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def check(name, ok, detail=""):
    global passed, failed
    passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))


def mysql(sql_text, database=TEST_DB):
    r = subprocess.run([MYSQL, "-u", "root", "-N", "-B"] + ([database] if database else []), input=sql_text,
                       capture_output=True, text=True, encoding="utf-8")
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
        if not mysql(f"SHOW TABLES FROM {TEST_DB} LIKE 'p13_test_marker'", None):
            raise RuntimeError(f"{TEST_DB} exists but was not created by these tests - not dropped")
        mysql(f"DROP DATABASE {TEST_DB}", None)


def create_test_db():
    sql = (ROOT / "schema.sql").read_text(encoding="utf-8").replace("`studenthub_prac13`", f"`{TEST_DB}`")
    assert "`studenthub_prac13`" not in sql and f"USE `{TEST_DB}`;" in sql
    mysql(sql + f"\nCREATE TABLE {TEST_DB}.p13_test_marker (id INT);\n", None)


class Server:
    def __init__(self, port, log_dir, env):
        self.port, self.log = port, pathlib.Path(log_dir) / f"php-{port}.log"
        self.out = open(pathlib.Path(log_dir) / f"server-{port}.txt", "w")
        e = {k: v for k, v in os.environ.items() if not k.startswith("P13_")}
        e.update(env)
        self.proc = subprocess.Popen([PHP, "-d", f"error_log={self.log}", "-S", f"127.0.0.1:{port}", "router.php"], cwd=ROOT,
                                     env=e, stdout=self.out, stderr=subprocess.STDOUT)
        for _ in range(50):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/style.css", timeout=2)
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


def call(action, method="GET", params=None, body=None, port=PORT, headers=None, raw=None):
    """Sends a request like script.js does. Returns (status, headers, parsed JSON or None, raw bytes)."""
    q = urllib.parse.urlencode({"action": action, **(params or {})})
    h = {"Accept": "application/json"}
    data = None
    if body is not None or raw is not None:
        h.update({"Content-Type": "application/json", "X-Requested-With": "fetch"})
        data = raw if raw is not None else json.dumps(body).encode()
    h.update(headers or {})
    h = {k: v for k, v in h.items() if v is not None}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/api.php?{q}", data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            status, hdrs, content = r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        status, hdrs, content = e.code, e.headers, e.read()
    try:
        parsed = json.loads(content)
    except ValueError:
        parsed = None
    return status, hdrs, parsed, content


def valid_event(**over):
    e = {"title": "Spring Coding Marathon", "description": "A full-day coding marathon for all students.", "category": "Hackathon",
         "event_date": "2027-03-20", "start_time": "09:30", "venue": "Seminar Hall 2", "capacity": "150", "status": "open"}
    e.update(over)
    return e


def static_checks():
    print("\n== Required files and static checks")
    for name in ("db.php", "api.php", "index.html", "script.js", "schema.sql"):
        check(f"required file Practical-13/{name} exists", (ROOT / name).is_file())
    php_files = sorted(ROOT.glob("*.php"))
    bad = [p.name for p in php_files if subprocess.run([PHP, "-l", str(p)], capture_output=True).returncode]
    check(f"php -l: no syntax errors in all {len(php_files)} PHP files", not bad, ", ".join(bad))
    api, db = (ROOT / "api.php").read_text(encoding="utf-8"), (ROOT / "db.php").read_text(encoding="utf-8")
    check("db.php uses MySQLi (new mysqli), not PDO", "new mysqli(" in db and "PDO" not in db)
    check("api.php: prepared statements only (no query()/multi_query)", not re.search(r"->query\(|mysqli_query|multi_query", api)
          and api.count("->prepare(") >= 6 and api.count("bind_param(") >= 5)
    js_full = (ROOT / "script.js").read_text(encoding="utf-8")
    js = re.sub(r"//[^\n]*", "", js_full)                          # code only, without comments
    check("script.js uses fetch() with GET and POST and JSON", "fetch(url, options)" in js and "method: 'POST'" in js and "JSON.stringify" in js and "response.json()" in js)
    check("script.js never uses innerHTML / document.write / eval (data inserted with textContent)",
          not re.search(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|eval\(", js) and "textContent" in js)
    check("script.js debounces the search (setTimeout 350 ms, clearTimeout) and cancels stale requests (AbortController)",
          "clearTimeout(searchTimer)" in js and "setTimeout(() => loadEvents(), 350)" in js and "AbortController" in js)
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    check("index.html loads script.js, has the table, form, search, loading indicator and confirm dialog",
          all(x in html for x in ('src="script.js"', 'id="event-rows"', 'id="event-form"', 'id="search"', 'id="loading"', '<dialog id="confirm-dialog"')))
    check("the event form does not submit to the server by itself (no action attribute, handled by Fetch)", 'action=' not in html.split('id="event-form"')[1].split(">")[0])


def database_checks():
    print("\n== Database (schema.sql imported into studenthub_prac13_test)")
    check("12 seed events: 9 open, 3 closed", count() == 12 and count("status='open'") == 9 and count("status='closed'") == 3)
    check("table is InnoDB", scalar(f"SELECT ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA='{TEST_DB}' AND TABLE_NAME='events'") == "InnoDB")
    idx = {r[0] for r in mysql(f"SELECT INDEX_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA='{TEST_DB}' AND TABLE_NAME='events'")}
    check("indexes on date, category and title", {"idx_events_date", "idx_events_category", "idx_events_title"} <= idx, str(idx))
    for sql, name in (("INSERT INTO events (title,description,category,event_date,start_time,venue,capacity) VALUES ('Bad','xxxxxxxxxx','Music','2027-01-01','10:00','Hall',10)", "chk_events_category"),
                      ("INSERT INTO events (title,description,category,event_date,start_time,venue,capacity) VALUES ('Bad','xxxxxxxxxx','Sports','2027-01-01','10:00','Hall',0)", "chk_events_capacity")):
        try:
            mysql(sql)
            check(f"CHECK constraint {name} enforced", False)
        except RuntimeError as e:
            check(f"CHECK constraint {name} enforced", name in str(e))


def api_checks(server):
    print("\n== GET list")
    status, h, d, raw = call("list")
    check("GET list -> 200, Content-Type application/json, valid JSON {ok:true}", status == 200 and h["Content-Type"] == "application/json; charset=utf-8" and d and d["ok"] is True)
    check("list returns all 12 events with count/total", d["count"] == 12 and d["total"] == 12 and len(d["events"]) == 12)
    e = d["events"][0]
    check("event fields and types (ids/capacity are numbers, time HH:MM)",
          set(e) == {"event_id", "title", "description", "category", "event_date", "start_time", "venue", "capacity", "status", "created_at", "updated_at"}
          and isinstance(e["event_id"], int) and isinstance(e["capacity"], int) and re.fullmatch(r"\d\d:\d\d", e["start_time"]))
    dates = [(x["event_date"], x["start_time"]) for x in d["events"]]
    check("events sorted by date and time", dates == sorted(dates))

    print("\n== Search (used by the debounced search box) and category filter")
    for q, expect in (("workshop", count("title LIKE '%workshop%' OR venue LIKE '%workshop%' OR category LIKE '%workshop%' OR description LIKE '%workshop%'")),
                      ("LAB", count("title LIKE '%lab%' OR venue LIKE '%lab%' OR category LIKE '%lab%' OR description LIKE '%lab%'")),
                      ("Robotics", 1), ("zzzz", 0), ("%", 0), ("_", 0)):
        status, _, d, _ = call("list", params={"q": q})
        check(f"q={q!r} -> {expect} event(s)", status == 200 and d["count"] == expect and d["query"] == q, str(d and d.get("count")))
    status, _, d, _ = call("list", params={"category": "Sports"})
    check("category=Sports -> only Sports events", d["count"] == count("category='Sports'") and {x["category"] for x in d["events"]} == {"Sports"})
    status, _, d, _ = call("list", params={"q": "hall", "category": "Seminar"})
    check("search + category combined", d["count"] == count("category='Seminar' AND (title LIKE '%hall%' OR venue LIKE '%hall%' OR category LIKE '%hall%' OR description LIKE '%hall%')"))
    status, _, d, _ = call("list", params={"category": "Music"})
    check("unknown category is ignored (all events)", d["count"] == 12 and d["category"] == "")

    print("\n== GET one event")
    status, _, d, _ = call("get", params={"id": "3"})
    check("get id=3 -> 200 with the event", status == 200 and d["event"]["event_id"] == 3 and d["event"]["title"] == "AI in Healthcare Seminar")
    for params, code in (({"id": "9999"}, 404), ({}, 400), ({"id": "1 OR 1=1"}, 400), ({"id": "-1"}, 400), ({"id": "abc"}, 400)):
        status, h, d, _ = call("get", params=params)
        check(f"get {params or 'without id'} -> {code} JSON error", status == code and d and d["ok"] is False and d["error"] and "json" in h["Content-Type"])

    print("\n== POST create")
    before = count()
    status, _, d, _ = call("create", "POST", body=valid_event(title="  Spring   Coding Marathon  "))
    new_id = d["event"]["event_id"] if d and d.get("ok") else None
    check("valid create -> 200 {ok:true, message, event}", status == 200 and d["ok"] and "was added" in d["message"] and new_id)
    check("row inserted, spaces in the title cleaned, capacity stored as number",
          count() == before + 1 and scalar(f"SELECT CONCAT(title,'|',capacity,'|',start_time) FROM events WHERE event_id={new_id}") == "Spring Coding Marathon|150|09:30:00")
    status, _, d, _ = call("create", "POST", body={})
    check("empty create -> 422 with an error for all 8 fields", status == 422 and set(d["errors"]) == {"title", "description", "category", "event_date", "start_time", "venue", "capacity", "status"})
    cases = [({"title": "AB"}, "title"), ({"title": "x" * 121}, "title"), ({"description": "short"}, "description"), ({"category": "Music"}, "category"),
             ({"event_date": "2026-02-30"}, "event_date"), ({"event_date": "2150-01-01"}, "event_date"), ({"start_time": "25:00"}, "start_time"),
             ({"venue": "X"}, "venue"), ({"capacity": "0"}, "capacity"), ({"capacity": "5001"}, "capacity"), ({"capacity": "12abc"}, "capacity"),
             ({"status": "pending"}, "status"), ({"title": ["array"]}, "title")]
    for over, field in cases:
        status, _, d, _ = call("create", "POST", body=valid_event(**over))
        check(f"invalid {field} {str(list(over.values())[0])[:20]!r} -> 422 with an error for {field}", status == 422 and field in d.get("errors", {}), str(status))
    check("no invalid event was stored", count() == before + 1)

    print("\n== POST update")
    status, _, d, _ = call("update", "POST", body=valid_event(event_id=new_id, title="Spring Coding Marathon 2027", venue="Main Auditorium", capacity=200, status="closed"))
    row = mysql(f"SELECT title, venue, capacity, status FROM events WHERE event_id={new_id}")[0]
    check("valid update -> 200 {ok:true}, row changed", status == 200 and d["ok"] and "was updated" in d["message"] and row == ["Spring Coding Marathon 2027", "Main Auditorium", "200", "closed"])
    check("update returns the saved event", d["event"]["title"] == "Spring Coding Marathon 2027" and d["event"]["capacity"] == 200)
    status, _, d, _ = call("update", "POST", body=valid_event(event_id=new_id, title=""))
    check("invalid update -> 422, row unchanged", status == 422 and "title" in d["errors"] and scalar(f"SELECT title FROM events WHERE event_id={new_id}") == "Spring Coding Marathon 2027")
    status, _, d, _ = call("update", "POST", body=valid_event(event_id=9999))
    check("update of an unknown event -> 404", status == 404 and d["ok"] is False)
    status, _, d, _ = call("update", "POST", body=valid_event(event_id="1 OR 1=1"))
    check("update with event_id '1 OR 1=1' -> 400, nothing changed", status == 400 and count("title='Spring Coding Marathon'") == 0)

    print("\n== POST delete")
    before = count()
    status, _, d, _ = call("delete", "POST", body={"event_id": new_id})
    check("delete -> 200 {ok:true, deleted_id}, row removed", status == 200 and d["deleted_id"] == new_id and count() == before - 1 and count(f"event_id={new_id}") == 0)
    status, _, d, _ = call("delete", "POST", body={"event_id": new_id})
    check("deleting it again -> 404 'not found'", status == 404 and "not found" in d["error"])
    status, _, d, _ = call("delete", "POST", body={"event_id": "abc"})
    check("delete with an invalid id -> 400, nothing deleted", status == 400 and count() == before - 1)

    print("\n== Methods, headers and JSON errors")
    status, h, d, _ = call("create")
    check("GET on create -> 405 JSON with Allow: POST", status == 405 and h.get("Allow") == "POST" and d["ok"] is False)
    status, h, d, _ = call("list", "POST", body={})
    check("POST on list -> 405 with Allow: GET", status == 405 and h.get("Allow") == "GET")
    status, _, d, _ = call("create", "POST", raw=b"title=x", headers={"Content-Type": "application/x-www-form-urlencoded"})
    check("form-encoded POST (like a cross-site HTML form) -> 415, nothing stored", status == 415 and d["ok"] is False)
    status, _, d, _ = call("create", "POST", body=valid_event(), headers={"X-Requested-With": None})
    check("JSON POST without X-Requested-With -> 400", status == 400)
    status, _, d, _ = call("create", "POST", raw=b"{not json")
    check("invalid JSON body -> 400 'not valid JSON'", status == 400 and "not valid JSON" in d["error"])
    status, _, d, _ = call("create", "POST", raw=b"[1,2,3]")
    check("JSON array instead of object -> 400", status == 400)
    status, _, d, _ = call("create", "POST", raw=json.dumps(valid_event(description="x" * 30000)).encode())
    check("oversized body -> 400", status == 400)
    status, _, d, _ = call("nonsense")
    check("unknown action -> 400 JSON", status == 400 and "Unknown action" in d["error"])

    print("\n== SQL injection and XSS")
    status, _, d, _ = call("list", params={"q": "' OR '1'='1"})
    check("search \"' OR '1'='1\" -> 0 results, 200", status == 200 and d["count"] == 0)
    status, _, d, _ = call("list", params={"q": "x%' UNION SELECT 1,2,3,4,5,6,7,8,9,10,11 -- "})
    check("UNION injection in search -> 0 results, no error", status == 200 and d["count"] == 0)
    status, _, d, _ = call("create", "POST", body=valid_event(title="Robert'); DROP TABLE events;--", venue="O'Neill Hall"))
    check("SQL metacharacters stored literally, table intact", status == 200 and scalar("SELECT venue FROM events WHERE title='Robert''); DROP TABLE events;--'") == "O'Neill Hall")
    status, _, d, raw = call("create", "POST", body=valid_event(title='<script>alert("x")</script> Gala', venue="<img src=x onerror=alert(1)>"))
    check("HTML is stored as text and returned unchanged in JSON", status == 200 and d["event"]["title"] == '<script>alert("x")</script> Gala')
    check("JSON escapes < > & ' \" (\\u003C…) so it can never be read as HTML", b"<script>" not in raw and b"\\u003Cscript\\u003E" in raw)
    check("API responses have X-Content-Type-Options: nosniff and Cache-Control: no-store",
          call("list")[1].get("X-Content-Type-Options") == "nosniff" and "no-store" in call("list")[1].get("Cache-Control", ""))

    print("\n== Protected files")
    for path in ["schema.sql", "README.md", "config.example.php", "router.php", "tests/test_app.py", ".gitignore", "db.php", "start-server.bat"]:
        try:
            status = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/{path}", timeout=10).status
        except urllib.error.HTTPError as e:
            status = e.code
        check(f"/{path} -> 403", status == 403, str(status))

    print("\n== Server log")
    log = server.logged()
    check("no PHP warnings, notices or errors logged", not re.search(r"PHP (Warning|Notice|Deprecated|Fatal|Parse)", log), log[-300:])


def database_down_checks(log_dir):
    print("\n== MySQL unreachable (centralized JSON error handling)")
    server = Server(PORT_DOWN, log_dir, {"P13_DB_NAME": TEST_DB, "P13_DB_PORT": "1"})
    try:
        status, h, d, raw = call("list", port=PORT_DOWN)
        check("list -> 500 JSON {ok:false, error} with a general message", status == 500 and "json" in h["Content-Type"] and d["ok"] is False and "could not complete" in d["error"])
        check("no SQL / connection details in the response", not re.search(rb"mysqli|SQLSTATE|127\.0\.0\.1|Access denied|Stack trace|\.php", raw))
        time.sleep(0.3)
        check("the real error is in the PHP log", "Practical 13 database connection failed" in server.logged())
    finally:
        server.stop()


def main():
    print(f"StudentHub Practical 13 tests  (PHP: {PHP}, MySQL: {MYSQL})")
    static_checks()
    drop_test_db()
    create_test_db()
    log_dir = tempfile.mkdtemp(prefix="p13-tests-")
    try:
        database_checks()
        server = Server(PORT, log_dir, {"P13_DB_NAME": TEST_DB})
        try:
            api_checks(server)
        finally:
            server.stop()
        database_down_checks(log_dir)
    finally:
        drop_test_db()
        check("test database removed", not mysql(f"SHOW DATABASES LIKE '{TEST_DB}'", None))
        print(f"(studenthub_prac13 was not used by the tests; it holds {mysql('SELECT COUNT(*) FROM events', 'studenthub_prac13')[0][0]} events)")
    print(f"\nResult: {passed} passed, {failed} failed, {passed + failed} checks")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
