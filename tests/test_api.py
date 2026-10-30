"""StudentHub - tests of the events JSON API and the Event Finder page (Practical 13).
Python 3, standard library only.

    python tests\\test_api.py                        # disposable DB built from database/studenthub_demo.sql
    python tests\\test_api.py --source-dump X.sql    # disposable DB restored from a mysqldump (missing migrations applied)

Disposable database studenthub_p11_test (see test_students.py) and XAMPP's PHP built-in server on the canonical application
(a second server points at a database that does not exist). The live database is only read to prove it is unchanged.
"""
import argparse, concurrent.futures, json, pathlib, re, secrets, subprocess, sys, tempfile, threading, urllib.error, urllib.parse, urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import test_students as P  # noqa: E402

PORT, PORT_NODB = 8733, 8734
MIGRATIONS = P.ROOT / "database" / "migrations"
check, info, mysql, scalar, q = P.check, P.info, P.mysql, P.scalar, P.q
ACCOUNTS = {}
EVENT_KEYS = {"id", "title", "category", "event_date", "event_time", "when", "location", "description", "capacity", "seats_taken", "seats_left",
              "status", "is_past", "poster_url", "registrations_total", "my_registration"}


def call(b, action, method="GET", params=None, body=None, token=None, content_type="application/json", raw=None, port=PORT):
    """returns (status, headers, json-or-None, raw text)"""
    query = urllib.parse.urlencode({"action": action, **(params or {})})
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    if method == "POST" and data is None:
        data = b""
    req = urllib.request.Request(f"http://127.0.0.1:{port}/api/events.php?{query}", data=data, method=method)
    req.add_header("Accept", "application/json")
    if data is not None and content_type:
        req.add_header("Content-Type", content_type)
    if token:
        req.add_header("X-CSRF-Token", token)
    try:
        with b.opener.open(req, timeout=30) as r:
            status, headers, text = r.status, r.headers, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        status, headers, text = e.code, e.headers, e.read().decode("utf-8", "replace")
    try:
        return status, headers, json.loads(text), text
    except ValueError:
        return status, headers, None, text


def login(name):
    b = P.Browser(PORT)
    b.login(name, ACCOUNTS[name])
    return b, b.token("dashboard.php")


def audit(action):
    return int(scalar(f"SELECT COUNT(*) FROM audit_logs WHERE action={q(action)}"))


def count_events():
    return int(scalar("SELECT COUNT(*) FROM events"))


VALID = {"title": "API Test Bootcamp", "category": "Workshop", "event_date": "2027-06-10", "event_time": "10:00", "location": "Lab 7",
         "capacity": 30, "status": "open", "description": "Created through the JSON API."}


# ================================================================ tests
def static_checks():
    print("\n== Static checks")
    api_src = (P.APP / "api" / "events.php").read_text(encoding="utf-8")
    bad = [p.name for p in (P.APP / "api").glob("*.php") if subprocess.run([P.PHP, "-l", str(p)], capture_output=True).returncode]
    check("php -l: api/*.php, events_live.php have no syntax errors", not bad and subprocess.run([P.PHP, "-l", str(P.APP / "events_live.php")], capture_output=True).returncode == 0)
    check("the API uses the portal's connection and helpers (no own mysqli/PDO connection, no ->query())",
          "new mysqli" not in api_src and "new PDO" not in api_src and "->query(" not in api_src and "require_once dirname(__DIR__) . '/db.php'" in api_src)
    js = (P.APP / "assets" / "js" / "events-live.js").read_text(encoding="utf-8")
    check("events-live.js inserts server data with textContent only (no innerHTML) and sends X-CSRF-Token", "innerHTML" not in js and "X-CSRF-Token" in js and "fetch(" in js)
    check("debounced search (setTimeout 300 ms after the last key press)", "setTimeout(load, 300)" in js and "clearTimeout(timer)" in js)


def auth_tests():
    print("\n== Authentication (JSON 401, never a redirect)")
    g = P.Browser(PORT)
    st, hd, js, _ = call(g, "list")
    check("not signed in: list -> 401 JSON {ok: false} (application/json, no redirect)",
          st == 401 and js == {"ok": False, "error": "Please sign in to use StudentHub."} and hd.get("Content-Type", "").startswith("application/json"))
    st, _, js, _ = call(g, "create", "POST", body=VALID)
    check("not signed in: create -> 401, nothing stored", st == 401 and js["ok"] is False and scalar("SELECT COUNT(*) FROM events WHERE title='API Test Bootcamp'") == "0")


def list_tests(s, a):
    print("\n== GET list / get")
    st, hd, js, text = call(s, "list", params={"when": ""})
    check("list -> 200 {ok, count, events, filters, can_manage, can_register} with nosniff and no-store",
          st == 200 and js["ok"] is True and js["count"] == len(js["events"]) == count_events() and set(js) == {"ok", "count", "events", "filters", "can_manage", "can_register"}
          and hd.get("X-Content-Type-Options") == "nosniff" and "no-store" in hd.get("Cache-Control", ""))
    check("each event has exactly the documented fields (no file names, no internal columns)", all(set(e) == EVENT_KEYS for e in js["events"]))
    check("a student sees can_register=true, can_manage=false", js["can_register"] is True and js["can_manage"] is False)
    check("posters are only exposed as poster.php URLs (or null)", all(e["poster_url"] is None or re.fullmatch(r"poster\.php\?event=\d+", e["poster_url"]) for e in js["events"]))
    st, _, js_a, _ = call(a, "list")
    check("an administrator sees can_manage=true, can_register=false; default list = all dates", js_a["can_manage"] is True and js_a["can_register"] is False)
    rows = mysql("SELECT title, location, IFNULL(description,''), category, status, event_date < CURDATE() FROM events")

    def expect(qt="", cat="", status="", when=""):
        return sorted(r[0] for r in rows if (not qt or any(qt.lower() in v.lower() for v in r[:3])) and (not cat or r[3] == cat)
                      and (not status or r[4] == status) and (not when or (r[5] == "1") == (when == "past")))
    for label, params in (("search 'work'", {"q": "work"}), ("category Workshop", {"category": "Workshop"}), ("status closed", {"status": "closed"}),
                          ("upcoming", {"when": "upcoming"}), ("past", {"when": "past"}), ("search + category + upcoming", {"q": "a", "category": "Workshop", "when": "upcoming"})):
        st, _, js, _ = call(s, "list", params=params)
        got = sorted(e["title"] for e in js["events"])
        want = expect(params.get("q", ""), params.get("category", ""), params.get("status", ""), params.get("when", ""))
        check(f"{label} -> exactly the {len(want)} matching event(s)", st == 200 and got == want, f"{got} vs {want}")
    for value in ("' OR '1'='1", "%", "_", "\" OR 1=1 --"):
        st, _, js, _ = call(s, "list", params={"q": value})
        check(f"search {value!r} is treated as text", st == 200 and sorted(e["title"] for e in js["events"]) == expect(value))
    st, _, js, _ = call(s, "list", params={"category": "Workshop' OR '1'='1", "q": "zzzz"})
    check("an injected category is ignored (unknown value), no SQL error", st == 200 and js["count"] == 0)
    mysql("INSERT INTO events (title, category, event_date, location) VALUES ('<script>alert(1)</script> Night', 'Cultural', '2027-01-01', 'Hall')")
    st, _, js, text = call(s, "list", params={"q": "Night"})
    check("HTML in a title is returned as data and escaped in the JSON text (\\u003C), never as markup",
          any(e["title"] == "<script>alert(1)</script> Night" for e in js["events"]) and "<script>" not in text and "\\u003Cscript\\u003E" in text)
    eid = int(scalar("SELECT id FROM events ORDER BY id LIMIT 1"))
    st, _, js, _ = call(s, "get", params={"id": eid})
    check("get -> 200 with one event", st == 200 and js["event"]["id"] == eid and set(js["event"]) == EVENT_KEYS)
    for bad in ("999999", "0", "abc", "1 OR 1=1"):
        st, _, js, _ = call(s, "get", params={"id": bad})
        if st != 404 or js["ok"] is not False:
            check(f"get id={bad!r} -> 404", False)
            break
    else:
        check("get with an unknown or malformed id (999999, 0, abc, '1 OR 1=1') -> 404 JSON", True)


def protocol_tests(a, token):
    print("\n== Methods, content type, CSRF and request format")
    n = count_events()
    st, hd, js, _ = call(a, "list", "POST", body={}, token=token)
    check("POST to a GET action -> 405 with Allow: GET", st == 405 and hd.get("Allow") == "GET" and js["ok"] is False)
    st, hd, js, _ = call(a, "create")
    check("GET to a POST action -> 405 with Allow: POST", st == 405 and hd.get("Allow") == "POST")
    st, _, js, _ = call(a, "drop_table")
    check("unknown action -> 400 JSON", st == 400 and "Unknown action" in js["error"])
    rejected = audit("CSRF_REJECTED")
    st, _, js, _ = call(a, "create", "POST", body=VALID)
    st2, _, _, _ = call(a, "create", "POST", body=VALID, token="0" * 64)
    st3, _, _, _ = call(a, "create", "POST", body=VALID, token=token + "x")
    check("create without, with a wrong or a modified X-CSRF-Token -> 403, nothing stored, audit-logged",
          (st, st2, st3) == (403, 403, 403) and count_events() == n and audit("CSRF_REJECTED") == rejected + 3)
    st, _, js, _ = call(a, "create", "POST", raw=urllib.parse.urlencode(VALID).encode(), token=token, content_type="application/x-www-form-urlencoded")
    check("a form-encoded POST (as a cross-site form would send) -> 415", st == 415 and count_events() == n)
    st, _, js, _ = call(a, "create", "POST", raw=b"{not json", token=token)
    st2, _, _, _ = call(a, "create", "POST", raw=b"[1, 2]", token=token)
    st3, _, _, _ = call(a, "create", "POST", raw=json.dumps({**VALID, "description": "x" * 30000}).encode(), token=token)
    check("malformed JSON, a JSON array and a body over 20 kB -> 400", (st, st2, st3) == (400, 400, 400) and count_events() == n)


def crud_tests(a, token):
    print("\n== Create / update / delete (administrators)")
    created = audit("CREATE_EVENT")
    st, _, js, _ = call(a, "create", "POST", body=VALID, token=token)
    row = mysql("SELECT id, title, category, event_date, event_time, location, capacity, status FROM events WHERE title='API Test Bootcamp'")
    check("create -> 201 {ok, event, message}; stored; CREATE_EVENT audit entry",
          st == 201 and js["ok"] and js["event"]["title"] == "API Test Bootcamp" and js["message"] == "Event “API Test Bootcamp” was published."
          and row and row[0][4] == "10:00:00" and row[0][6] == "30" and audit("CREATE_EVENT") == created + 1, str(js))
    new_id = js["event"]["id"]
    n = count_events()
    for label, over, field in (("empty title", {"title": ""}, "title"), ("unknown category", {"category": "Nope"}, "category"),
                               ("impossible date", {"event_date": "2027-02-30"}, "event_date"), ("capacity 0", {"capacity": 0}, "capacity"),
                               ("capacity as text", {"capacity": "many"}, "capacity"), ("status 'maybe'", {"status": "maybe"}, "status"),
                               ("title as a JSON array", {"title": ["x"]}, "title"), ("time 25:61", {"event_time": "25:61"}, "event_time")):
        st, _, js, _ = call(a, "create", "POST", body={**VALID, **over}, token=token)
        check(f"{label} -> 422 with errors.{field}", st == 422 and js["ok"] is False and field in js.get("errors", {}), f"{st} {js}")
    check("nothing was stored by the invalid requests", count_events() == n)
    st, _, js, _ = call(a, "update", "POST", body={**VALID, "id": new_id, "title": "API Test Bootcamp (moved)", "location": "Lab 8", "capacity": None}, token=token)
    check("update -> 200; new values stored; capacity null = no limit",
          st == 200 and js["event"]["location"] == "Lab 8" and js["event"]["capacity"] is None
          and scalar(f"SELECT CONCAT(title,'|',IFNULL(capacity,'NULL')) FROM events WHERE id={new_id}") == "API Test Bootcamp (moved)|NULL")
    st, _, js, _ = call(a, "update", "POST", body={**VALID, "id": 999999}, token=token)
    check("update of an unknown id -> 404", st == 404)
    st, _, js, _ = call(a, "update", "POST", body={**VALID, "id": new_id, "event_date": "next week"}, token=token)
    check("update with an invalid date -> 422", st == 422 and "event_date" in js["errors"])
    return new_id


def registration_tests(a, token, students, new_id):
    print("\n== Register / cancel (students) and conflicts")
    mysql("INSERT INTO events (title, category, event_date, location, capacity, status) VALUES "
          "('API Small Seminar', 'Seminar', DATE_ADD(CURDATE(), INTERVAL 10 DAY), 'Room 1', 1, 'open'), "
          "('API Closed Talk', 'Seminar', DATE_ADD(CURDATE(), INTERVAL 10 DAY), 'Room 2', NULL, 'closed'), "
          "('API Old Meetup', 'Technical', DATE_SUB(CURDATE(), INTERVAL 3 DAY), 'Room 3', NULL, 'open'), "
          "('API Parallel Lab', 'Workshop', DATE_ADD(CURDATE(), INTERVAL 15 DAY), 'Lab 9', 3, 'open')")
    eid = {t: int(scalar(f"SELECT id FROM events WHERE title={q(t)}")) for t in ("API Small Seminar", "API Closed Talk", "API Old Meetup", "API Parallel Lab")}
    s1, t1 = login(students[0])
    s2, t2 = login(students[1])
    st, _, js, _ = call(s1, "register", "POST", body={"event_id": eid["API Small Seminar"]}, token=t1)
    check("register -> 201 {ok, message, event} with my_registration='registered'",
          st == 201 and js["message"] == "You are registered for “API Small Seminar”." and js["event"]["my_registration"] == "registered" and js["event"]["seats_left"] == 0)
    for label, b, t, body, code, text in (
            ("registering again", s1, t1, {"event_id": eid["API Small Seminar"]}, 409, "already registered"),
            ("a full event (capacity 1)", s2, t2, {"event_id": eid["API Small Seminar"]}, 409, "The event is full."),
            ("a closed event", s2, t2, {"event_id": eid["API Closed Talk"]}, 409, "closed"),
            ("a past event", s2, t2, {"event_id": eid["API Old Meetup"]}, 409, "already taken place"),
            ("an unknown event", s2, t2, {"event_id": 999999}, 404, "not found"),
            ("an event id as text", s2, t2, {"event_id": "1 OR 1=1"}, 404, "not found")):
        st, _, js, _ = call(b, "register", "POST", body=body, token=t)
        check(f"{label} -> {code} '{text}'", st == code and js["ok"] is False and text in js["error"], f"{st} {js}")
    st, _, js, _ = call(s1, "cancel", "POST", body={"event_id": eid["API Small Seminar"]}, token=t1)
    check("cancel -> 200, row kept as 'cancelled', seat freed", st == 200 and js["event"]["my_registration"] == "cancelled" and js["event"]["seats_left"] == 1)
    st, _, js, _ = call(s1, "cancel", "POST", body={"event_id": eid["API Small Seminar"]}, token=t1)
    check("cancelling again -> 409", st == 409 and "no active registration" in js["error"])
    st, _, js, _ = call(s1, "register", "POST", body={"event_id": eid["API Small Seminar"]})
    check("register without X-CSRF-Token -> 403", st == 403)
    u, tu = login("p13_unlinked")
    st, _, js, _ = call(u, "register", "POST", body={"event_id": eid["API Parallel Lab"]}, token=tu)
    st2, _, _, _ = call(a, "register", "POST", body={"event_id": eid["API Parallel Lab"]}, token=token)
    check("an unlinked student account and an administrator cannot register (403)", st == 403 and st2 == 403 and "linked student record" in js["error"])
    st, _, js, _ = call(s2, "list", params={"q": "API Small"})
    check("the list shows each student's own registration state", js["events"][0]["my_registration"] is None)

    sessions = [login(n) for n in students]
    barrier = threading.Barrier(len(sessions))

    def go(pair):
        b, t = pair
        barrier.wait()
        return call(b, "register", "POST", body={"event_id": eid["API Parallel Lab"]}, token=t)[0]
    with concurrent.futures.ThreadPoolExecutor(len(sessions)) as ex:
        codes = sorted(ex.map(go, sessions))
    check("6 simultaneous API registrations for 3 seats -> exactly three 201 and three 409 (no overbooking)",
          codes == [201, 201, 201, 409, 409, 409] and scalar(f"SELECT COUNT(*) FROM registrations WHERE event_id={eid['API Parallel Lab']} AND status<>'cancelled'") == "3", str(codes))

    st, _, js, _ = call(a, "update", "POST", body={**VALID, "id": eid["API Parallel Lab"], "title": "API Parallel Lab", "capacity": 2}, token=token)
    check("capacity below the seats taken -> 422", st == 422 and "cannot be lower than the 3 seats" in js["errors"]["capacity"])
    st, _, js, _ = call(a, "delete", "POST", body={"id": eid["API Parallel Lab"]}, token=token)
    check("deleting an event with registrations -> 409, event and registrations kept",
          st == 409 and "cannot be deleted" in js["error"] and scalar(f"SELECT COUNT(*) FROM events WHERE id={eid['API Parallel Lab']}") == "1")
    deleted = audit("DELETE_EVENT")
    st, _, js, _ = call(a, "delete", "POST", body={"id": new_id}, token=token)
    check("deleting an event without registrations -> 200, removed, DELETE_EVENT audit entry",
          st == 200 and js["id"] == new_id and scalar(f"SELECT COUNT(*) FROM events WHERE id={new_id}") == "0" and audit("DELETE_EVENT") == deleted + 1)
    st, _, js, _ = call(a, "delete", "POST", body={"id": new_id}, token=token)
    check("deleting it again -> 404", st == 404)
    return eid


def role_tests(eid):
    print("\n== Roles")
    n = count_events()
    for role in ("p13_s1", "p13_editor"):
        b, t = login(role)
        denied = audit("ACCESS_DENIED")
        codes = [call(b, "create", "POST", body=VALID, token=t)[0], call(b, "update", "POST", body={**VALID, "id": eid["API Closed Talk"]}, token=t)[0],
                 call(b, "delete", "POST", body={"id": eid["API Old Meetup"]}, token=t)[0]]
        check(f"{'student' if role == 'p13_s1' else 'editor'}: create / update / delete -> 403, nothing changed, ACCESS_DENIED logged",
              codes == [403, 403, 403] and count_events() == n and audit("ACCESS_DENIED") == denied + 3, str(codes))
    b, t = login("p13_s6")
    sid = scalar("SELECT s.id FROM students s JOIN users u ON u.id=s.user_id WHERE u.username='p13_s6'")
    mysql(f"UPDATE students SET status='Inactive' WHERE id={sid}")
    st, _, js, _ = call(b, "list")
    check("a student whose record was deactivated loses API access at the next request (401, generic message)",
          st == 401 and js["error"].startswith("Your access to StudentHub is currently disabled"))
    mysql(f"UPDATE students SET status='Active' WHERE id={sid}")


def page_tests():
    print("\n== Event Finder page")
    s, _ = login("p13_s1")
    st, _, page = s.request("events_live.php")
    check("student: events_live.php (200) has the CSRF meta tag, the script, the filters and no New-event button",
          st == 200 and re.search(r'<meta name="csrf-token" content="[0-9a-f]{64}">', page) and "assets/js/events-live.js" in page
          and 'id="live-q"' in page and 'data-can-register="1"' in page and 'id="new-event"' not in page)
    a, _ = login("p13_admin")
    st, _, page = a.request("events_live.php")
    check("admin: the page offers New event and the edit dialog", st == 200 and 'id="new-event"' in page and 'id="event-dialog"' in page and 'data-can-manage="1"' in page)
    e, _ = login("p13_editor")
    st, _, page = e.request("events_live.php")
    check("editor: can view and search, but neither manage nor register", st == 200 and 'data-can-manage="0"' in page and 'data-can-register="0"' in page)
    st, hd, _ = P.Browser(PORT).request("events_live.php")
    check("not signed in: the page redirects to the login page", st == 303 and "login.php" in hd.get("Location", ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dump")
    args = ap.parse_args()
    print(f"StudentHub events API tests - Practical 13 (PHP {P.PHP}, MySQL {P.MYSQL})")
    info("source: " + (pathlib.Path(args.source_dump).name if args.source_dump else "database/studenthub_demo.sql"))
    live_before = P.live_fingerprint()
    live_events = mysql("SELECT * FROM events ORDER BY id", P.LIVE_DB)
    static_checks()
    workdir = tempfile.mkdtemp(prefix="p13-")
    server = nodb = None
    try:
        P.create_test_db(args.source_dump)
        for m in sorted(MIGRATIONS.glob("0*.sql")):
            if not m.name.endswith(".down.sql") and scalar(f"SELECT COUNT(*) FROM schema_migrations WHERE version='{m.name[:3]}'") == "0":
                r = subprocess.run([P.MYSQL, "-u", "root", P.TEST_DB], input=m.read_text(encoding="utf-8"), capture_output=True, text=True, encoding="utf-8")
                assert r.returncode == 0, r.stderr
        students = [f"p13_s{i}" for i in range(1, 7)]
        for name, role in [("p13_admin", "admin"), ("p13_editor", "editor"), ("p13_unlinked", "student")] + [(s, "student") for s in students]:
            ACCOUNTS[name] = secrets.token_urlsafe(12) + "A1!"
            P.create_account(name, f"{name}@example.com", role, ACCOUNTS[name])
        for i, name in enumerate(students, 1):
            uid = scalar(f"SELECT id FROM users WHERE username={q(name)}")
            mysql(f"INSERT INTO students (user_id, enrollment_no, name, email, course, gender, semester, status) VALUES "
                  f"({uid}, '26WD8{i:02d}', 'API Student {i}', '{name}@example.com', 'Web Development', 'Male', 1, 'Active')")
        server = P.Server(PORT, workdir, {"DB_NAME": P.TEST_DB})
        auth_tests()
        s, _ = login("p13_s1")
        a, token = login("p13_admin")
        list_tests(s, a)
        protocol_tests(a, token)
        new_id = crud_tests(a, token)
        eid = registration_tests(a, token, students, new_id)
        role_tests(eid)
        page_tests()
        problems = [l for l in server.logged().splitlines() if re.search(r"PHP (Warning|Notice|Fatal|Deprecated|Parse)|StudentHub API error", l)]
        check("no PHP warnings and no unexpected API errors in the server log", not problems, "; ".join(problems[:3]))
        print("\n== Database unavailable")
        nodb = P.Server(PORT_NODB, workdir, {"DB_NAME": "studenthub_no_such_db"})
        st, hd, js, text = call(P.Browser(PORT_NODB), "list", port=PORT_NODB)
        check("the API answers HTTP 503 in JSON with a general message only (no database name, SQL or stack trace)",
              st == 503 and hd.get("Content-Type", "").startswith("application/json") and js["ok"] is False
              and "studenthub_no_such_db" not in text and "mysqli" not in text.lower() and "Stack" not in text, text[:200])
    finally:
        for srv in (server, nodb):
            if srv:
                srv.stop()
        P.drop_test_db()
    print("\n== Clean-up")
    check("disposable database removed", not mysql(f"SHOW DATABASES LIKE '{P.TEST_DB}'", None))
    check("the live studenthub_db was not touched", P.live_fingerprint() == live_before and mysql("SELECT * FROM events ORDER BY id", P.LIVE_DB) == live_events)
    print(f"\nResult: {P.passed} passed, {P.failed} failed, {P.passed + P.failed} checks")
    return 1 if P.failed else 0


if __name__ == "__main__":
    sys.exit(main())
