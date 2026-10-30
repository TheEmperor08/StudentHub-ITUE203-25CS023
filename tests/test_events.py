"""StudentHub - tests of the event management integrated into the Admin Console and the Campus Events page (Practical 12).
Python 3, standard library only.

    python tests\\test_events.py                        # disposable DB built from database/studenthub_demo.sql
    python tests\\test_events.py --source-dump X.sql    # disposable DB restored from a mysqldump (missing migrations applied)

Uses the disposable database studenthub_p11_test (see test_students.py), a temporary poster folder (STUDENTHUB_UPLOAD_DIR)
and XAMPP's PHP built-in server on the canonical application. The live database and studenthub/uploads are not touched.
Sample images are read (never changed) from Practical-12/uploads (fictional posters); the attack files are generated here.
"""
import argparse, concurrent.futures, hashlib, html, os, pathlib, random, re, secrets, struct, subprocess, sys, tempfile, threading, urllib.parse, urllib.request, zlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import test_students as P  # noqa: E402

PORT = 8732
CONSOLE = "admin_dashboard.php?tab=events"
SAMPLES = P.ROOT / "Practical-12" / "uploads"
MIGRATIONS = P.ROOT / "database" / "migrations"
check, info, mysql, scalar, q = P.check, P.info, P.mysql, P.scalar, P.q
ACCOUNTS = {}


# ---------------------------------------------------------------- images
def png_bytes(width=40, height=30, noise=False):
    raw = b"".join(b"\x00" + (os.urandom(width * 3) if noise else bytes([(x * 7) % 256 for x in range(width * 3)])) for _ in range(height))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 0 if noise else 6)) + chunk(b"IEND", b"")


def sample(ext):
    return next(p for p in sorted(SAMPLES.glob(f"*.{ext}"))).read_bytes()


# ---------------------------------------------------------------- multipart POST with the test browser
def post_multipart(b, path, fields, files=()):
    boundary = "----StudentHubTest" + secrets.token_hex(8)
    parts = []
    for k, v in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for name, filename, content, ctype in files:
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{filename}"\r\nContent-Type: {ctype}\r\n\r\n'.encode() + content + b"\r\n")
    body = b"".join(parts) + f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/{path}", data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with b.opener.open(req, timeout=60) as r:
            return r.status, r.headers, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read().decode("utf-8", "replace")


def get_raw(b, path):
    try:
        with b.opener.open(f"http://127.0.0.1:{PORT}/{path}", timeout=30) as r:
            return r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()


def errors_of(page):
    return {m[0]: html.unescape(m[1]) for m in re.findall(r'<div class="invalid-feedback d-block" id="([\w-]+)-error">(.*?)</div>', page)}


def flash_of(page):
    m = re.search(r'<div class="alert alert-(success|danger)[^"]*"[^>]*>\s*<i[^>]*></i>\s*<div>(.*?)</div>', page, re.S)
    return ({"success": "success", "danger": "error"}[m.group(1)], html.unescape(m.group(2))) if m else None


def page_flash(page):
    m = re.search(r'<div class="alert-(success|error) flash-message"[^>]*>.*?<p>(.*?)</p>', page, re.S)
    return (m.group(1), html.unescape(m.group(2))) if m else None


def event(where):
    rows = mysql(f"SELECT id, title, category, event_date, IFNULL(event_time,'NULL'), location, IFNULL(capacity,'NULL'), status, IFNULL(description,''), "
                 f"IFNULL(poster,'NULL'), IFNULL(updated_at,'NULL') FROM events WHERE {where}")
    keys = ("id", "title", "category", "event_date", "event_time", "location", "capacity", "status", "description", "poster", "updated_at")
    return dict(zip(keys, rows[0])) if rows else None


def uploads(folder):
    return sorted(p.name for p in pathlib.Path(folder).iterdir() if p.is_file())


def audit(action):
    return int(scalar(f"SELECT COUNT(*) FROM audit_logs WHERE action={q(action)}"))


def shown_titles(page):
    m = re.search(r'<table[^>]*id="event-table".*?<tbody>(.*?)</tbody>', page, re.S)
    return [html.unescape(t) for t in re.findall(r'<td class="fw-bold text-body">(.*?)(?:<div|</td>)', m.group(1))] if m else None


# ================================================================ tests
def static_checks():
    print("\n== Static checks")
    php_files = sorted(P.APP.rglob("*.php")) + sorted((P.ROOT / "tools").glob("*.php"))
    bad = [p.name for p in php_files if subprocess.run([P.PHP, "-l", str(p)], capture_output=True).returncode]
    check(f"php -l: no syntax errors in all {len(php_files)} PHP files of studenthub/ and tools/", not bad, ", ".join(bad))
    module = (P.APP / "includes" / "event_management.php").read_text(encoding="utf-8")
    check("event_management.php: no ->query() with values (prepared statements only)",
          not [l for l in module.splitlines() if re.search(r"""->query\(\s*(\$|"[^"]*\$|'[^']*'\s*\.)""", l)])
    check("the original upload file name is never used for storage (random 32-hex names)",
          "bin2hex(random_bytes(16))" in module and "move_uploaded_file($valid['tmp'], $dir . DIRECTORY_SEPARATOR . $name)" in module)
    ht = (P.APP / "uploads" / ".htaccess").read_text(encoding="utf-8")
    check("studenthub/uploads/.htaccess denies HTTP access and disables PHP (Apache)", "Require all denied" in ht and "php_flag engine off" in ht and "RemoveHandler .php" in ht)


def schema_checks():
    print("\n== Database (migration 003)")
    check("schema_migrations records 003", scalar("SELECT COUNT(*) FROM schema_migrations WHERE version='003'") == "1")
    check("events.status, events.updated_at, event_categories and fk_events_category exist",
          scalar(f"SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='{P.TEST_DB}' AND TABLE_NAME='events' AND COLUMN_NAME IN ('status','updated_at')") == "2"
          and scalar(f"SELECT COUNT(*) FROM information_schema.REFERENTIAL_CONSTRAINTS WHERE CONSTRAINT_SCHEMA='{P.TEST_DB}' AND CONSTRAINT_NAME='fk_events_category'") == "1")


def listing_tests(a, legacy_id):
    print("\n== Event listing (admin)")
    st, _, page = a.request(CONSOLE)
    n = int(scalar("SELECT COUNT(*) FROM events"))
    check(f"admin -> Campus Events tab (200) lists the {n} events", st == 200 and len(shown_titles(page) or []) == min(n, 10))
    check("columns: poster, event, category, date & time, location, seats, status, actions",
          all(f">{c}</th>" in page for c in ("Poster", "Event", "Category", "Date &amp; time", "Location", "Seats", "Status", "Actions")))
    legacy = event(f"id={legacy_id}")
    check("an older poster reference whose file does not exist shows a placeholder and 'poster file not available' (no broken image, value kept)",
          "poster file not available" in page and f'poster.php?event={legacy_id}"' not in page and legacy["poster"] == "uploads/odoo_hackathon.jpg")
    st, _, _ = get_raw(a, f"poster.php?event={legacy_id}")
    check("poster.php for that event -> 404 (the old path is never opened)", st == 404)
    check("every POST form in the tab carries a CSRF token", not P.post_forms_without_token(page))


def add_tests(a, token, folder):
    print("\n== Add event (server-side validation)")
    st, _, page = a.request(f"{CONSOLE}&view=add_event")
    check("GET view=add_event shows the form (multipart, CSRF token, poster field accepting JPEG/PNG/WebP only)",
          st == 200 and 'enctype="multipart/form-data"' in page and 'value="add_event"' in page and 'accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"' in page)
    base = {"csrf_token": token, "action": "add_event", "title": "Inter-College Coding Sprint", "category": "Hackathon", "event_date": "2027-03-14",
            "event_time": "09:30", "location": "CSPIT Lab 4", "capacity": "60", "status": "open", "description": "24-hour team coding challenge."}
    created = audit("CREATE_EVENT")
    st, hd, _ = post_multipart(a, "admin_dashboard.php", base)
    ev = event("title='Inter-College Coding Sprint'")
    check("valid event without a poster -> 303 to the list; all fields stored, status open",
          st == 303 and hd.get("Location") == CONSOLE and ev is not None and ev["event_time"] == "09:30:00" and ev["capacity"] == "60"
          and ev["status"] == "open" and ev["poster"] == "NULL", str(ev))
    check("success message (from the session) and CREATE_EVENT audit entry",
          flash_of(a.request(CONSOLE)[2]) == ("success", "Event “Inter-College Coding Sprint” was published.") and audit("CREATE_EVENT") == created + 1)
    for ext, ctype, content in (("png", "image/png", png_bytes()), ("jpg", "image/jpeg", sample("jpg")), ("webp", "image/webp", sample("webp"))):
        title = f"Poster Test {ext.upper()}"
        st, _, _ = post_multipart(a, "admin_dashboard.php", {**base, "title": title}, [("poster", f"My Poster.{ext}", content, ctype)])
        ev = event(f"title={q(title)}")
        stored = pathlib.Path(folder) / ev["poster"] if ev and ev["poster"] != "NULL" else None
        check(f"valid {ext.upper()} poster -> stored under a random name (32 hex + .{ext}), same bytes, original name not used",
              st == 303 and stored is not None and re.fullmatch(r"[a-f0-9]{32}\." + ext, ev["poster"]) and stored.read_bytes() == content
              and not (pathlib.Path(folder) / f"My Poster.{ext}").exists(), str(ev))
        if ext == "png":
            png_event = ev
    st, hd, body = get_raw(a, f"poster.php?event={png_event['id']}")
    check("poster.php delivers it as image/png with nosniff and a sandbox CSP", st == 200 and hd.get("Content-Type") == "image/png"
          and hd.get("X-Content-Type-Options") == "nosniff" and "sandbox" in hd.get("Content-Security-Policy", "") and body == png_bytes())
    st, hd, _ = get_raw(P.Browser(PORT), f"poster.php?event={png_event['id']}")
    check("posters are not served to visitors who are not signed in (redirect to the login page)", st == 303 and "login.php" in hd.get("Location", ""))
    st, _, _ = post_multipart(a, "admin_dashboard.php", {**base, "title": "Upper Case Extension"}, [("poster", "POSTER.PNG", png_bytes(), "image/png")])
    check("an upper-case extension (.PNG) is accepted and stored as .png", st == 303 and event("title='Upper Case Extension'")["poster"].endswith(".png"))
    return base, png_event


def invalid_tests(a, base, folder):
    print("\n== Invalid event details (nothing stored)")
    n, files = int(scalar("SELECT COUNT(*) FROM events")), uploads(folder)
    cases = [
        ("empty title", {"title": ""}, "title", "Please enter the event title."),
        ("two-character title", {"title": "AB"}, "title", "3–150 characters"),
        ("unknown category", {"category": "Hacking"}, "category", "category from the list"),
        ("impossible date 2027-02-30", {"event_date": "2027-02-30"}, "event_date", "valid date"),
        ("date in another format", {"event_date": "14/03/2027"}, "event_date", "valid date"),
        ("time 25:00", {"event_time": "25:00"}, "event_time", "valid time"),
        ("empty location", {"location": ""}, "location", "Please enter the location."),
        ("capacity 0", {"capacity": "0"}, "capacity", "1 to 65535"),
        ("capacity -5", {"capacity": "-5"}, "capacity", "1 to 65535"),
        ("capacity 70000", {"capacity": "70000"}, "capacity", "1 to 65535"),
        ("capacity 'ten'", {"capacity": "ten"}, "capacity", "1 to 65535"),
        ("unknown status", {"status": "maybe"}, "status", "Open or Closed"),
        ("description over 2000 characters", {"description": "x" * 2001}, "description", "at most 2000"),
        ("SQL in the category", {"category": "Hackathon' OR '1'='1"}, "category", "category from the list"),
    ]
    for label, over, field, text in cases:
        st, _, page = post_multipart(a, "admin_dashboard.php", {**base, "title": over.get("title", "Invalid Case"), **over})
        check(f"{label} -> 422 '{text}'", st == 422 and text in errors_of(page).get(field, ""), f"{st} {errors_of(page)}")
    st, _, page = post_multipart(a, "admin_dashboard.php", {**base, "title": "<script>alert(1)</script>", "location": ""})
    check("rejected input is shown again HTML-escaped", "&lt;script&gt;alert(1)&lt;/script&gt;" in page and "<script>alert(1)</script>" not in page)
    check("no event and no file were stored by the rejected forms", int(scalar("SELECT COUNT(*) FROM events")) == n and uploads(folder) == files)

    print("\n== Poster upload validation (every check on the server)")
    big = png_bytes(1000, 800, noise=True)
    truncated = png_bytes()[:-20]
    rejected_before = audit("UPLOAD_REJECTED")
    attacks = [
        ("a GIF image", "poster.gif", b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;", "image/gif", "Only JPEG, PNG and WebP"),
        ("an SVG with JavaScript", "poster.svg", b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>', "image/svg+xml", "Only JPEG, PNG and WebP"),
        ("a PHP script", "shell.php", b"<?php system($_GET['c']); ?>", "application/x-php", "Only JPEG, PNG and WebP"),
        # security software on Windows may block reading a known web-shell signature: rejected either way
        ("a PHP script renamed to .jpg", "shell.jpg", b"<?php system($_GET['c']); ?>", "image/jpeg", "not a JPEG, PNG or WebP image|could not be read as an image"),
        ("a double extension shell.php.jpg", "shell.php.jpg", b"<?php echo 1; ?>", "image/jpeg", "not a JPEG, PNG or WebP image"),
        ("PNG content named .jpg", "picture.jpg", png_bytes(), "image/jpeg", "does not match its content"),
        ("a truncated PNG", "broken.png", truncated, "image/png", "not a valid image or is damaged"),
        ("a JPEG with embedded PHP code", "evil.jpg", sample("jpg")[:-2] + b"<?php system('id'); ?>" + b"\xff\xd9", "image/jpeg", "contains embedded code"),
        ("a 2.3 MB PNG", "huge.png", big, "image/png", "maximum size is 2 MB"),
        ("an empty file", "empty.png", b"", "image/png", ""),
        ("a file with a forged image/png content type", "notes.txt", b"hello", "image/png", "Only JPEG, PNG and WebP"),
    ]
    for label, filename, content, ctype, text in attacks:
        st, _, page = post_multipart(a, "admin_dashboard.php", {**base, "title": f"Attack {secrets.token_hex(3)}"}, [("poster", filename, content, ctype)])
        err = errors_of(page).get("poster", "")
        check(f"{label} -> rejected ('{text or 'empty'}')", st == 422 and err != "" and any(t in err for t in text.split("|")), f"{st} {err}")
    check(f"big file really is over 2 MB ({len(big)} bytes)", len(big) > 2 * 1024 * 1024)
    check("no event and no file were stored for the rejected posters", int(scalar("SELECT COUNT(*) FROM events")) == n and uploads(folder) == files)
    check("rejected uploads are written to the audit log (UPLOAD_REJECTED)", audit("UPLOAD_REJECTED") >= rejected_before + len(attacks) - 1)


def edit_tests(a, token, png_event, folder):
    print("\n== Edit event")
    ev = event(f"id={png_event['id']}")
    st, _, page = a.request(f"{CONSOLE}&view=edit_event&id={ev['id']}")
    check("GET view=edit_event shows the form filled from the database with the current poster",
          st == 200 and f'value="{html.escape(ev["title"])}"' in page and f'poster.php?event={ev["id"]}' in page and 'value="update_event"' in page)
    upd = {"csrf_token": token, "action": "update_event", "id": ev["id"], "title": "Poster Test PNG (updated)", "category": "Technical", "event_date": "2027-04-01",
           "event_time": "", "location": "CSPIT Seminar Hall", "capacity": "", "status": "closed", "description": "Updated description."}
    st, _, _ = post_multipart(a, "admin_dashboard.php", upd)
    after = event(f"id={ev['id']}")
    check("update without a new file -> fields changed, poster kept, time and capacity cleared, updated_at set",
          st == 303 and after["title"] == "Poster Test PNG (updated)" and after["category"] == "Technical" and after["status"] == "closed"
          and after["event_time"] == "NULL" and after["capacity"] == "NULL" and after["poster"] == ev["poster"] and after["updated_at"] != "NULL", str(after))
    old_file = pathlib.Path(folder) / ev["poster"]
    st, _, _ = post_multipart(a, "admin_dashboard.php", upd, [("poster", "new.webp", sample("webp"), "image/webp")])
    after2 = event(f"id={ev['id']}")
    check("replacing the poster stores the new file and deletes the old one",
          st == 303 and after2["poster"].endswith(".webp") and after2["poster"] != ev["poster"] and not old_file.exists()
          and (pathlib.Path(folder) / after2["poster"]).exists())
    st, _, page = post_multipart(a, "admin_dashboard.php", upd, [("poster", "shell.jpg", b"<?php echo 1; ?>", "image/jpeg")])
    check("an invalid replacement poster is refused and the current poster stays", st == 422 and event(f"id={ev['id']}")["poster"] == after2["poster"]
          and (pathlib.Path(folder) / after2["poster"]).exists())
    check("UPDATE_EVENT written to the audit log", audit("UPDATE_EVENT") >= 2)
    return after2


def registration_tests(a, token, students):
    print("\n== Student event registration (transaction, duplicates, capacity, closed/past events)")
    mysql("INSERT INTO events (title, category, event_date, event_time, location, capacity, status) VALUES "
          "('Cloud Workshop', 'Workshop', DATE_ADD(CURDATE(), INTERVAL 20 DAY), '10:00:00', 'Lab 2', 2, 'open'), "
          "('Closed Seminar', 'Seminar', DATE_ADD(CURDATE(), INTERVAL 25 DAY), NULL, 'Hall 1', NULL, 'closed'), "
          "('Last Month Meetup', 'Technical', DATE_SUB(CURDATE(), INTERVAL 30 DAY), NULL, 'Hall 2', NULL, 'open'), "
          "('Parallel Bootcamp', 'Workshop', DATE_ADD(CURDATE(), INTERVAL 40 DAY), NULL, 'Lab 5', 3, 'open')")
    eid = {t: int(scalar(f"SELECT id FROM events WHERE title={q(t)}")) for t in ("Cloud Workshop", "Closed Seminar", "Last Month Meetup", "Parallel Bootcamp")}
    sess = {}
    for name in students[:3]:
        sess[name] = P.Browser(PORT)
        sess[name].login(name, ACCOUNTS[name])
    s1, s2, s3 = (sess[n] for n in students[:3])
    t1 = s1.token("notifications.php")
    _, _, page = s1.request("notifications.php")
    check("Campus Events page lists the upcoming event with seats and a Register button (CSRF token)",
          "Cloud Workshop" in page and "0 of 2 seats taken" in page and 'value="register"' in page and not P.post_forms_without_token(page))
    reg_before = audit("EVENT_REGISTER")
    st, hd, _ = s1.request("notifications.php", {"csrf_token": t1, "action": "register", "event_id": eid["Cloud Workshop"]})
    sid1 = scalar(f"SELECT s.id FROM students s JOIN users u ON u.id = s.user_id WHERE u.username={q(students[0])}")
    check("student registers -> 303, one 'registered' row, success message, EVENT_REGISTER audit entry",
          st == 303 and scalar(f"SELECT COUNT(*) FROM registrations WHERE student_id={sid1} AND event_id={eid['Cloud Workshop']} AND status='registered'") == "1"
          and page_flash(s1.request("notifications.php")[2]) == ("success", "You are registered for “Cloud Workshop”.") and audit("EVENT_REGISTER") == reg_before + 1)
    s1.request("notifications.php", {"csrf_token": t1, "action": "register", "event_id": eid["Cloud Workshop"]})
    check("registering again -> 'already registered', still one row",
          page_flash(s1.request("notifications.php")[2]) == ("error", "The student is already registered for this event.")
          and scalar(f"SELECT COUNT(*) FROM registrations WHERE student_id={sid1} AND event_id={eid['Cloud Workshop']}") == "1")
    s2.request("notifications.php", {"csrf_token": s2.token("notifications.php"), "action": "register", "event_id": eid["Cloud Workshop"]})
    s3.request("notifications.php", {"csrf_token": s3.token("notifications.php"), "action": "register", "event_id": eid["Cloud Workshop"]})
    check("capacity 2: the second student fits, the third gets 'The event is full.'",
          page_flash(s3.request("notifications.php")[2]) == ("error", "The event is full.")
          and scalar(f"SELECT COUNT(*) FROM registrations WHERE event_id={eid['Cloud Workshop']} AND status<>'cancelled'") == "2")
    _, _, page = s3.request("notifications.php")
    check("the full event shows 'Event full' instead of a Register button for the third student", "Event full" in page)
    s1.request("notifications.php", {"csrf_token": t1, "action": "register", "event_id": eid["Closed Seminar"]})
    check("a closed event -> 'Registration for this event is closed.'", page_flash(s1.request("notifications.php")[2]) == ("error", "Registration for this event is closed."))
    s1.request("notifications.php", {"csrf_token": t1, "action": "register", "event_id": eid["Last Month Meetup"]})
    check("a past event -> 'This event has already taken place.'", page_flash(s1.request("notifications.php")[2]) == ("error", "This event has already taken place."))
    cancel_before = audit("EVENT_REGISTRATION_CANCEL")
    s1.request("notifications.php", {"csrf_token": t1, "action": "cancel", "event_id": eid["Cloud Workshop"]})
    check("cancelling -> row kept as 'cancelled', the seat is freed, EVENT_REGISTRATION_CANCEL audit entry",
          scalar(f"SELECT status FROM registrations WHERE student_id={sid1} AND event_id={eid['Cloud Workshop']}") == "cancelled"
          and scalar(f"SELECT COUNT(*) FROM registrations WHERE event_id={eid['Cloud Workshop']} AND status<>'cancelled'") == "1"
          and audit("EVENT_REGISTRATION_CANCEL") == cancel_before + 1)
    s1.request("notifications.php", {"csrf_token": t1, "action": "cancel", "event_id": eid["Cloud Workshop"]})
    check("cancelling again -> 'There is no active registration to cancel.'", page_flash(s1.request("notifications.php")[2]) == ("error", "There is no active registration to cancel."))
    s3.request("notifications.php", {"csrf_token": s3.token("notifications.php"), "action": "register", "event_id": eid["Cloud Workshop"]})
    check("the freed seat can be taken by the third student", scalar(f"SELECT COUNT(*) FROM registrations WHERE event_id={eid['Cloud Workshop']} AND status<>'cancelled'") == "2")
    st, _, _ = s1.request("notifications.php", {"action": "register", "event_id": eid["Parallel Bootcamp"]})
    check("registration without the CSRF token -> 403, nothing stored", st == 403 and scalar(f"SELECT COUNT(*) FROM registrations WHERE event_id={eid['Parallel Bootcamp']}") == "0")
    a.request(f"admin_dashboard.php?tab=events&action=register&event_id={eid['Parallel Bootcamp']}")
    s1.request(f"notifications.php?action=register&event_id={eid['Parallel Bootcamp']}&csrf_token={t1}")
    check("GET requests with registration parameters change nothing", scalar(f"SELECT COUNT(*) FROM registrations WHERE event_id={eid['Parallel Bootcamp']}") == "0")
    u = P.Browser(PORT)
    u.login("p12_unlinked", ACCOUNTS["p12_unlinked"])
    u.request("notifications.php", {"csrf_token": u.token("notifications.php"), "action": "register", "event_id": eid["Parallel Bootcamp"]})
    check("a student account without a linked student record cannot register (clear message)",
          page_flash(u.request("notifications.php")[2]) == ("error", "Event registration is available to students with a linked student record."))
    a.request("notifications.php", {"csrf_token": a.token("notifications.php"), "action": "register", "event_id": eid["Parallel Bootcamp"]})
    check("an administrator cannot register as a student", scalar(f"SELECT COUNT(*) FROM registrations WHERE event_id={eid['Parallel Bootcamp']}") == "0")

    print("\n== Simultaneous registrations (6 students, 3 seats)")
    browsers = []
    for name in students:
        b = P.Browser(PORT)
        b.login(name, ACCOUNTS[name])
        browsers.append((b, b.token("notifications.php")))
    barrier = threading.Barrier(len(browsers))

    def go(pair):
        b, tok = pair
        barrier.wait()
        b.request("notifications.php", {"csrf_token": tok, "action": "register", "event_id": eid["Parallel Bootcamp"]})
        return page_flash(b.request("notifications.php")[2])

    with concurrent.futures.ThreadPoolExecutor(len(browsers)) as ex:
        results = list(ex.map(go, browsers))
    ok = sum(1 for r in results if r and r[0] == "success")
    full = sum(1 for r in results if r == ("error", "The event is full."))
    check("exactly 3 of 6 simultaneous registrations succeed, 3 get 'The event is full.' (no overbooking)",
          ok == 3 and full == 3 and scalar(f"SELECT COUNT(*) FROM registrations WHERE event_id={eid['Parallel Bootcamp']} AND status<>'cancelled'") == "3", str(results))
    return eid


def capacity_delete_tests(a, token, eid, folder):
    print("\n== Capacity edits, registrations view and deletion")
    cw = event(f"id={eid['Cloud Workshop']}")
    upd = {"csrf_token": token, "action": "update_event", "id": cw["id"], "title": cw["title"], "category": cw["category"], "event_date": cw["event_date"],
           "event_time": "10:00", "location": cw["location"], "capacity": "1", "status": "open", "description": ""}
    st, _, page = post_multipart(a, "admin_dashboard.php", upd)
    check("the capacity cannot be set below the seats already taken (2)", st == 422 and "cannot be lower than the 2 seats" in errors_of(page).get("capacity", "")
          and event(f"id={cw['id']}")["capacity"] == "2")
    st, _, page = a.request(f"{CONSOLE}&view=event_registrations&id={cw['id']}")
    check("the registrations view lists the students with their registration status", st == 200 and page.count("<tr>") >= 4 and "Cancelled" in page and "Registered" in page)
    st, _, page = a.request(f"{CONSOLE}&view=delete_event&id={cw['id']}")
    check("delete view for an event with registrations explains that it cannot be deleted (no delete button)",
          st == 200 and "cannot be deleted, so that the registration history is kept" in page and 'value="delete_event"' not in page)
    regs = scalar(f"SELECT COUNT(*) FROM registrations WHERE event_id={cw['id']}")
    st, _, _ = a.request("admin_dashboard.php", {"csrf_token": token, "action": "delete_event", "id": cw["id"]})
    check("a forged delete POST for that event is refused; the event and its registrations are kept",
          st == 303 and event(f"id={cw['id']}") is not None and scalar(f"SELECT COUNT(*) FROM registrations WHERE event_id={cw['id']}") == regs
          and "cannot be deleted" in (flash_of(a.request(CONSOLE)[2]) or ("", ""))[1])
    victim = event("title='Poster Test JPG'")
    poster_file = pathlib.Path(folder) / victim["poster"]
    st, _, page = a.request(f"{CONSOLE}&view=delete_event&id={victim['id']}")
    check("delete view for an event without registrations asks for confirmation; nothing deleted yet",
          st == 200 and "Yes, delete event" in page and event(f"id={victim['id']}") is not None)
    a.request(f"admin_dashboard.php?tab=events&action=delete_event&id={victim['id']}&csrf_token={token}")
    st, _, _ = a.request("admin_dashboard.php", {"action": "delete_event", "id": victim["id"]})
    check("GET with action=delete_event and a POST without the token change nothing (403 for the POST)", st == 403 and event(f"id={victim['id']}") is not None)
    deleted_before = audit("DELETE_EVENT")
    st, _, _ = a.request("admin_dashboard.php", {"csrf_token": token, "action": "delete_event", "id": victim["id"]})
    check("confirmed delete -> event removed, its poster file deleted, DELETE_EVENT audit entry",
          st == 303 and event(f"id={victim['id']}") is None and not poster_file.exists() and audit("DELETE_EVENT") == deleted_before + 1)


def filter_tests(a):
    print("\n== Search and filters")
    rows = mysql("SELECT title, location, IFNULL(description,''), category, status, event_date < CURDATE() FROM events ORDER BY event_date DESC, event_time DESC, id DESC")

    def expect(qt="", cat="", status="", when=""):
        return [r[0] for r in rows if (not qt or any(qt.lower() in v.lower() for v in r[:3])) and (not cat or r[3] == cat) and (not status or r[4] == status)
                and (not when or (r[5] == "1") == (when == "past"))]

    def got(params):
        _, _, page = a.request(CONSOLE + "&" + urllib.parse.urlencode(params))
        return shown_titles(page)
    for label, params in (("search 'workshop'", {"q": "workshop"}), ("category Workshop", {"category": "Workshop"}), ("status closed", {"status": "closed"}),
                          ("past events", {"when": "past"}), ("search + category + status", {"q": "a", "category": "Workshop", "status": "open"})):
        want = expect(params.get("q", ""), params.get("category", ""), params.get("status", ""), params.get("when", ""))[:10]
        check(f"{label} -> exactly the {len(want)} matching event(s)", got(params) == want, f"{got(params)} vs {want}")
    _, _, page = a.request(CONSOLE + "&" + urllib.parse.urlencode({"when": "upcoming"}))
    up = [r[0] for r in mysql("SELECT title FROM events WHERE event_date >= CURDATE() ORDER BY event_date, event_time, id")][:10]
    check("upcoming events, soonest first", shown_titles(page) == up)
    for value in ("' OR '1'='1", "%", "Workshop'; DROP TABLE events; --"):
        check(f"search {value!r} is treated as text", got({"q": value}) == expect(value)[:10])
    check("an injected category value is ignored (unknown value), events table intact", got({"category": "Workshop' OR '1'='1", "q": "zzzz"}) == []
          and int(scalar("SELECT COUNT(*) FROM events")) == len(rows))


def access_tests(eid, png_event):
    print("\n== Access control")
    n = int(scalar("SELECT COUNT(*) FROM events"))
    for role, user in (("student", "p12_s1"), ("editor", "p12_editor")):
        b = P.Browser(PORT)
        b.login(user, ACCOUNTS[user])
        token = b.token("dashboard.php")
        codes = [b.request(p)[0] for p in (CONSOLE, f"{CONSOLE}&view=add_event", f"{CONSOLE}&view=edit_event&id={png_event['id']}")]
        posts = [post_multipart(b, "admin_dashboard.php", {"csrf_token": token, "action": "add_event", "title": "Role Test", "category": "Workshop",
                                                          "event_date": "2027-05-05", "location": "X"})[0],
                 b.request("admin_dashboard.php", {"csrf_token": token, "action": "update_event", "id": png_event["id"], "title": "Hacked"})[0],
                 b.request("admin_dashboard.php", {"csrf_token": token, "action": "delete_event", "id": eid["Last Month Meetup"]})[0]]
        check(f"{role}: Events tab and forms -> 403; add / update / delete via POST -> 403, nothing changed",
              codes == [403, 403, 403] and posts == [403, 403, 403] and int(scalar("SELECT COUNT(*) FROM events")) == n
              and event(f"id={png_event['id']}")["title"] != "Hacked", f"{codes} {posts}")
    st, _, page = post_multipart(P.Browser(PORT), "admin_dashboard.php", {"action": "add_event", "title": "Anon"})
    check("not signed in: POST -> login page, nothing stored", st == 303 and int(scalar("SELECT COUNT(*) FROM events")) == n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dump")
    args = ap.parse_args()
    print(f"StudentHub event management tests - Practical 12 (PHP {P.PHP}, MySQL {P.MYSQL})")
    info("source: " + (pathlib.Path(args.source_dump).name if args.source_dump else "database/studenthub_demo.sql"))
    live_before = P.live_fingerprint()
    live_events = mysql("SELECT * FROM events ORDER BY id", P.LIVE_DB)
    real_uploads = uploads(P.APP / "uploads")
    static_checks()
    workdir, folder = tempfile.mkdtemp(prefix="p12-"), tempfile.mkdtemp(prefix="p12-posters-")
    server = None
    try:
        P.create_test_db(args.source_dump)
        for m in sorted(MIGRATIONS.glob("0*.sql")):
            if not m.name.endswith(".down.sql") and scalar(f"SELECT COUNT(*) FROM schema_migrations WHERE version='{m.name[:3]}'") == "0":
                r = subprocess.run([P.MYSQL, "-u", "root", P.TEST_DB], input=m.read_text(encoding="utf-8"), capture_output=True, text=True, encoding="utf-8")
                assert r.returncode == 0, r.stderr
                info(f"{m.name} applied to the disposable copy")
        students = [f"p12_s{i}" for i in range(1, 7)]
        for name, role in [("p12_admin", "admin"), ("p12_editor", "editor"), ("p12_unlinked", "student")] + [(s, "student") for s in students]:
            ACCOUNTS[name] = secrets.token_urlsafe(12) + "A1!"
            P.create_account(name, f"{name}@example.com", role, ACCOUNTS[name])
        for i, name in enumerate(students, 1):
            uid = scalar(f"SELECT id FROM users WHERE username={q(name)}")
            mysql(f"INSERT INTO students (user_id, enrollment_no, name, email, course, gender, semester, status) VALUES "
                  f"({uid}, '26DS9{i:02d}', 'Event Student {i}', '{name}@example.com', 'Data Science', 'Female', 1, 'Active')")
        legacy_id = int(scalar("SELECT id FROM events ORDER BY id LIMIT 1"))
        mysql(f"UPDATE events SET poster='uploads/odoo_hackathon.jpg' WHERE id={legacy_id}")      # like the live database
        schema_checks()
        server = P.Server(PORT, workdir, {"DB_NAME": P.TEST_DB, "STUDENTHUB_UPLOAD_DIR": folder})
        a = P.Browser(PORT)
        a.login("p12_admin", ACCOUNTS["p12_admin"])
        token = a.token(CONSOLE)
        listing_tests(a, legacy_id)
        base, png_event = add_tests(a, token, folder)
        invalid_tests(a, base, folder)
        png_event = edit_tests(a, token, png_event, folder)
        eid = registration_tests(a, token, students)
        capacity_delete_tests(a, token, eid, folder)
        filter_tests(a)
        access_tests(eid, png_event)
        print("\n== Storage and server log")
        names = uploads(folder)
        check("the poster folder contains only random names of stored posters still used by events",
              all(re.fullmatch(r"[a-f0-9]{32}\.(jpg|png|webp)", n) for n in names)
              and sorted(names) == sorted(r[0] for r in mysql("SELECT poster FROM events WHERE poster REGEXP '^[a-f0-9]{32}[.](jpg|png|webp)$'")))
        problems = [l for l in server.logged().splitlines() if re.search(r"PHP (Warning|Notice|Fatal|Deprecated|Parse)", l)]
        check("no PHP warnings, notices or fatal errors in the server log", not problems, "; ".join(problems[:3]))
    finally:
        if server:
            server.stop()
        P.drop_test_db()
    print("\n== Clean-up")
    check("disposable database removed", not mysql(f"SHOW DATABASES LIKE '{P.TEST_DB}'", None))
    check("the live studenthub_db was not touched (students, users, registrations, events) and studenthub/uploads is unchanged",
          P.live_fingerprint() == live_before and mysql("SELECT * FROM events ORDER BY id", P.LIVE_DB) == live_events and uploads(P.APP / "uploads") == real_uploads)
    print(f"\nResult: {P.passed} passed, {P.failed} failed, {P.passed + P.failed} checks")
    return 1 if P.failed else 0


if __name__ == "__main__":
    sys.exit(main())
