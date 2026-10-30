"""StudentHub - tests of the student management integrated into the Admin Console (Practical 11).
Python 3, standard library only.

    python tests\\test_students.py                        # disposable DB built from database/studenthub_demo.sql
    python tests\\test_students.py --source-dump X.sql    # disposable DB restored from a mysqldump of studenthub_db
                                                          # (migration 002 is applied to the copy if it is missing)

Creates the disposable database studenthub_p11_test (with a marker table), test accounts with random passwords
(tools/create_demo_user.php) and runs XAMPP's PHP built-in server on the canonical application (studenthub/) with DB_NAME
pointing at the disposable database. The live studenthub_db is only read (to prove it is unchanged). Everything is
removed at the end.
"""
import argparse, csv, datetime, hashlib, html, io, json, os, pathlib, re, secrets, subprocess, sys, tempfile, urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_auth import APP, DEMO, MYSQL, PHP, ROOT, Browser, Server, post_forms_without_token  # noqa: E402

TEST_DB, MARKER, LIVE_DB = "studenthub_p11_test", "zz_p11_test_marker", "studenthub_db"
MIGRATION_002 = ROOT / "database" / "migrations" / "002_unique_enrollment_no.sql"
PORT = 8731
CONSOLE = "admin_dashboard.php?tab=students"
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


def mysql_try(sql, db=TEST_DB):
    r = subprocess.run([MYSQL, "-u", "root", "-N", "-B", db], input=sql, capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stderr.strip()


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
    if scalar("SELECT COUNT(*) FROM schema_migrations WHERE version='002'") != "1":
        r = subprocess.run([MYSQL, "-u", "root", TEST_DB], input=MIGRATION_002.read_text(encoding="utf-8"), capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        info("migration 002 applied to the disposable copy")


def create_account(username, email, role, password):
    r = subprocess.run([PHP, "tools/create_demo_user.php", f"--db={TEST_DB}", f"--username={username}", f"--email={email}", f"--role={role}"],
                       input=password + "\n", cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return int(scalar(f"SELECT id FROM users WHERE username={q(username)}"))


def student(where):
    rows = mysql(f"SELECT id, IFNULL(user_id,'NULL'), IFNULL(enrollment_no,'NULL'), name, email, course, IFNULL(semester,'NULL'), gender, IFNULL(status,'NULL'), created_at FROM students WHERE {where}")
    keys = ("id", "user_id", "enrollment_no", "name", "email", "course", "semester", "gender", "status", "created_at")
    return dict(zip(keys, rows[0])) if rows else None


def count(where="1"):
    return int(scalar(f"SELECT COUNT(*) FROM students WHERE {where}"))


def audit_count(action):
    return int(scalar(f"SELECT COUNT(*) FROM audit_logs WHERE action={q(action)}"))


def live_fingerprint():
    rows = mysql("SELECT id, IFNULL(user_id,''), IFNULL(enrollment_no,''), name, email, course, IFNULL(semester,''), gender, IFNULL(status,'') FROM students ORDER BY id", LIVE_DB)
    users = mysql("SELECT id, username, email, password, role FROM users ORDER BY id", LIVE_DB)
    regs = mysql("SELECT * FROM registrations ORDER BY registration_id", LIVE_DB)
    return hashlib.sha256(repr((rows, users, regs)).encode()).hexdigest(), len(rows)


def academic_year():
    today = datetime.date.today()
    return today.year if today.month >= 7 else today.year - 1


def next_number(prefix):
    nums = [int(r[0][len(prefix):]) for r in mysql(f"SELECT enrollment_no FROM students WHERE enrollment_no LIKE {q(prefix + '%')}") if re.fullmatch(re.escape(prefix) + r"\d{3}", r[0])]
    return f"{prefix}{max(nums, default=0) + 1:03d}"


# ---------------------------------------------------------------- page helpers
def shown(page):
    """enrollment numbers in the student table of one page"""
    m = re.search(r'<table[^>]*id="student-table".*?<tbody>(.*?)</tbody>', page, re.S)
    if not m:
        return None
    return [html.unescape(x) for x in re.findall(r'<td><span class="badge bg-light text-dark border">(.*?)</span></td>', m.group(1))]


def shown_all(b, query):
    """enrollment numbers of every page of a filtered list"""
    found, page_no = [], 1
    while True:
        st, _, page = b.request(f"{CONSOLE}&{query}&page={page_no}" if query else f"{CONSOLE}&page={page_no}")
        rows = shown(page)
        if st != 200 or rows is None:
            return None
        found += rows
        total = re.search(r"of (\d+) (?:matching )?records?", page)
        if not total or len(found) >= int(total.group(1)) or not rows:
            return found
        page_no += 1


def errors_of(page):
    return {m[0]: html.unescape(m[1]) for m in re.findall(r'<div class="invalid-feedback d-block" id="(\w+)-error">(.*?)</div>', page)}


def form_values(page):
    return {m[0]: html.unescape(m[1]) for m in re.findall(r'<input type="(?:text|email)" id="(\w+)" name="\w+"[^>]*value="([^"]*)"', page, re.S)}


def flash_of(page):
    m = re.search(r'<div class="alert alert-(success|danger)[^"]*"[^>]*>\s*<i[^>]*></i>\s*<div>(.*?)</div>', page, re.S)
    return ({"success": "success", "danger": "error"}[m.group(1)], html.unescape(m.group(2))) if m else None


class PhpDriver:
    """calls register_student_for_event() (includes/event_registration.php) on the disposable database"""

    def __init__(self, workdir):
        self.script = pathlib.Path(workdir) / "register_driver.php"
        self.script.write_text(
            "<?php\nmysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);\nrequire $argv[1];\n"
            "$db = new mysqli('localhost', 'root', '', $argv[2]);\n"
            "try { echo json_encode(['ok' => true, 'id' => register_student_for_event($db, (int) $argv[3], (int) $argv[4])]); }\n"
            "catch (EventRegistrationException $e) { echo json_encode(['ok' => false, 'reason' => $e->reason]); }\n", encoding="utf-8")

    def register(self, student_id, event_id):
        r = subprocess.run([PHP, str(self.script), str(APP / "includes" / "event_registration.php"), TEST_DB, str(student_id), str(event_id)],
                           capture_output=True, text=True)
        try:
            return json.loads(r.stdout)
        except ValueError:
            return {"ok": False, "reason": "php-error", "out": (r.stdout + r.stderr)[-200:]}


# ================================================================ tests
def static_checks():
    print("\n== Static checks")
    php_files = sorted(APP.rglob("*.php")) + sorted((ROOT / "tools").glob("*.php"))
    bad = [p.name for p in php_files if subprocess.run([PHP, "-l", str(p)], capture_output=True).returncode]
    check(f"php -l: no syntax errors in all {len(php_files)} PHP files of studenthub/ and tools/", not bad, ", ".join(bad))
    sources = {p.relative_to(APP).as_posix(): p.read_text(encoding="utf-8") for p in APP.rglob("*.php")}
    check("no page or include deletes student records (no DELETE FROM students anywhere)",
          not [n for n, s in sources.items() if re.search(r"DELETE\s+FROM\s+`?students", s, re.I)])
    module = sources["includes/student_management.php"]
    dynamic = [line.strip() for line in module.splitlines() if re.search(r"""->query\(\s*(\$|"[^"]*\$|'[^']*'\s*\.)""", line)]
    check("student_management.php: queries with values are prepared statements (->query() only with fixed SQL)", not dynamic, str(dynamic))
    admin = sources["admin_dashboard.php"]
    check("admin_dashboard.php: no hard-delete action for students any more", "delete_student" not in admin and "DELETE FROM students" not in admin)
    check("student actions require the students.manage permission on the server", admin.count('require_permission("students.manage")') == 2)


def schema_checks():
    print("\n== Database (migration 002)")
    idx = mysql(f"SELECT NON_UNIQUE, GROUP_CONCAT(COLUMN_NAME) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA='{TEST_DB}' "
                "AND TABLE_NAME='students' AND INDEX_NAME='uq_students_enrollment_no' GROUP BY NON_UNIQUE")
    check("students.enrollment_no has the UNIQUE index uq_students_enrollment_no", idx == [["0", "enrollment_no"]], str(idx))
    check("schema_migrations records 002", scalar("SELECT COUNT(*) FROM schema_migrations WHERE version='002'") == "1")
    existing = mysql("SELECT enrollment_no FROM students WHERE enrollment_no IS NOT NULL LIMIT 1")
    if existing:
        rc, err = mysql_try(f"INSERT INTO students (enrollment_no, name, email, course, gender) VALUES ({q(existing[0][0].lower())}, 'Dup', 'p11.dup@example.com', 'Data Science', 'Male')")
        check("the database itself refuses a duplicate enrollment number (also in other letter case)", rc != 0 and "uq_students_enrollment_no" in err, err)
    rc, err = mysql_try("INSERT INTO students (enrollment_no, name, email, course, gender) VALUES (NULL, 'Legacy A', 'p11.null1@example.com', 'Data Science', 'Male'), "
                        "(NULL, 'Legacy B', 'p11.null2@example.com', 'Data Science', 'Male'); DELETE FROM students WHERE email LIKE 'p11.null_@example.com'")
    check("several legacy records without an enrollment number (NULL) are still allowed", rc == 0, err)


def listing_tests(a):
    print("\n== Student listing (admin)")
    st, _, page = a.request(CONSOLE)
    all_numbers = [r[0] for r in mysql("SELECT IFNULL(NULLIF(enrollment_no,''),'—') FROM students ORDER BY id DESC")]
    check("admin -> Student Records tab (200) lists the records, newest first", st == 200 and shown(page) == all_numbers[:10], f"{shown(page)} vs {all_numbers[:10]}")
    for col in ("Enrollment", "Name", "Email", "Course", "Sem", "Status", "Account", "Actions"):
        if not f'<th scope="col"' in page or f">{col}</th>" not in page:
            check(f"column {col} present", False)
            break
    else:
        check("table shows enrollment, name, email, course, semester, status, account link and actions", True)
    active, inactive = count("COALESCE(TRIM(status),'') <> 'Inactive'"), count("TRIM(status) = 'Inactive'")
    check(f"summary: total, {active} active and {inactive} inactive", f"· {active} active, {inactive} inactive in total" in page)
    check("inactive records are marked (Inactive badge, greyed row, Reactivate button)",
          inactive == 0 or ('class="student-inactive"' in page and "bg-danger-subtle text-danger\">Inactive" in page and 'value="reactivate_student"' in page))
    check("every POST form in the tab carries a CSRF token", not post_forms_without_token(page), str(post_forms_without_token(page)[:2]))
    check("no hard-delete button for students; deactivation goes through a confirmation page",
          'value="delete_student"' not in page and "view=deactivate&amp;id=" in page)
    st, _, page = a.request(f"{CONSOLE}&q=zzz-no-such-student")
    check("empty result -> helpful empty state with a link back to all records",
          st == 200 and "No student records match these filters." in page and shown(page) == [])


def add_tests(a, users_before):
    print("\n== Add student")
    st, _, page = a.request(f"{CONSOLE}&view=add")
    check("GET view=add shows the add form (CSRF token, all fields, no login-account fields)",
          st == 200 and 'value="add_student"' in page and all(f'name="{f}"' in page for f in ("enrollment_no", "name", "email", "course", "semester", "gender"))
          and 'name="password"' not in page and 'name="role"' not in page and not post_forms_without_token(page))
    token = a.token(CONSOLE)
    base = {"csrf_token": token, "action": "add_student", "enrollment_no": "26IT101", "name": "  Nisha   Verma ", "email": " Nisha.Verma@Example.com ",
            "course": "Information Technology", "semester": "1", "gender": "Female"}
    created_before = audit_count("CREATE_STUDENT")
    st, hd, _ = a.request("admin_dashboard.php", base)
    row = student("enrollment_no='26IT101'")
    check("valid student with an entered enrollment number -> 303 back to the list", st == 303 and hd.get("Location") == CONSOLE, f"{st} {hd.get('Location')}")
    check("... stored as Active with name/e-mail normalised (spaces collapsed, e-mail lower case)",
          row is not None and row["status"] == "Active" and row["name"] == "Nisha Verma" and row["email"] == "nisha.verma@example.com"
          and row["semester"] == "1" and row["gender"] == "Female", str(row))
    check("... no login account was created (users unchanged, students.user_id NULL)",
          row is not None and row["user_id"] == "NULL" and int(scalar("SELECT COUNT(*) FROM users")) == users_before)
    _, _, page = a.request(CONSOLE)
    msg = flash_of(page)
    check("success message names the student and the number, once (from the session)",
          msg == ("success", "Student “Nisha Verma” was added with enrollment number 26IT101.") and flash_of(a.request(CONSOLE)[2]) is None, str(msg))
    check("CREATE_STUDENT written to the audit log (record ID and number, no e-mail)", audit_count("CREATE_STUDENT") == created_before + 1
          and scalar("SELECT details FROM audit_logs WHERE action='CREATE_STUDENT' ORDER BY id DESC LIMIT 1") == f"Added student record ID {row['id']} (26IT101)")

    ay = academic_year()
    expected = next_number(f"{ay % 100:02d}IT")
    st, _, _ = a.request("admin_dashboard.php", {**base, "enrollment_no": "", "name": "Arjun Iyer", "email": "arjun.iyer@example.com", "semester": "2", "gender": "Male"})
    row = student("email='arjun.iyer@example.com'")
    check(f"empty enrollment number -> next number of the existing scheme ({expected}: admission year {ay} + IT)", st == 303 and row is not None and row["enrollment_no"] == expected, str(row))
    expected = next_number(f"{(ay - 1) % 100:02d}DS")
    st, _, _ = a.request("admin_dashboard.php", {**base, "enrollment_no": "", "name": "Sara D'Souza", "email": "sara.dsouza@example.com", "course": "Data Science", "semester": "3"})
    row = student("email='sara.dsouza@example.com'")
    check(f"semester 3 -> admitted last year: {expected}; apostrophe in the name accepted", st == 303 and row is not None and row["enrollment_no"] == expected and row["name"] == "Sara D'Souza", str(row))
    _, _, page = a.request(CONSOLE)
    check("the name with an apostrophe is HTML-escaped in the list", "Sara D&#039;Souza" in page and "Sara D'Souza" not in page)
    legacy_course = scalar("SELECT course FROM students WHERE course NOT IN ('Information Technology','Computer Science Engineering','Data Science','Web Development') LIMIT 1")
    if legacy_course:
        n = count()
        st, _, page = a.request("admin_dashboard.php", {**base, "enrollment_no": "", "name": "Code Less", "email": "code.less@example.com", "course": legacy_course})
        check(f"course without a code ('{legacy_course}') and no number -> asked to enter the number, nothing stored",
              st == 422 and "Please enter the enrollment number for this course" in errors_of(page).get("enrollment_no", "") and count() == n)
        st, _, _ = a.request("admin_dashboard.php", {**base, "enrollment_no": "25CE901", "name": "Code Less", "email": "code.less@example.com", "course": legacy_course})
        check("... with an entered number the existing course name is accepted unchanged", st == 303 and student("enrollment_no='25CE901'")["course"] == legacy_course)
    return token, base


def invalid_tests(a, token, base):
    print("\n== Invalid student details (server-side validation; nothing stored)")
    n = count()
    cases = [
        ("empty name", {"name": ""}, "name", "Please enter the full name."),
        ("name with digits", {"name": "Agent 007"}, "name", "letters, spaces"),
        ("name with HTML", {"name": "<script>alert(1)</script>"}, "name", "letters, spaces"),
        ("one-letter name", {"name": "A"}, "name", "2–100 characters"),
        ("invalid e-mail", {"email": "not-an-email"}, "email", "valid email address"),
        ("e-mail longer than 100 characters", {"email": "a" * 95 + "@example.com"}, "email", "valid email address"),
        ("course not in the list", {"course": "Hacking 101"}, "course", "course from the list"),
        ("gender not in the list", {"gender": "X"}, "gender", "Male, Female or Other"),
        ("enrollment number in the wrong format", {"enrollment_no": "ABC12"}, "enrollment_no", "2 digits, 2 letters and 3 digits"),
        ("enrollment number with SQL", {"enrollment_no": "26IT1' OR '1'='1"}, "enrollment_no", "2 digits, 2 letters and 3 digits"),
        ("field sent as an array", {"name[]": "x", "name": None}, "name", "characters that are not allowed"),
    ]
    for label, over, field, text in cases:
        data = {**base, "email": f"p11.invalid.{secrets.token_hex(3)}@example.com", "enrollment_no": next_number("26WD"), **over}
        data = {k: v for k, v in data.items() if v is not None}
        st, _, page = a.request("admin_dashboard.php", data)
        err = errors_of(page)
        check(f"{label} -> 422 '{text}'", st == 422 and text in err.get(field, ""), f"{st} {err}")
    st, _, page = a.request("admin_dashboard.php", {"csrf_token": token, "action": "add_student"})
    err = errors_of(page)
    check("all fields empty -> a message under every required field", st == 422 and {"name", "email", "course", "semester", "gender"} <= set(err), str(err))
    check("no record was stored by the rejected forms", count() == n)
    st, _, page = a.request("admin_dashboard.php", {**base, "enrollment_no": "", "name": "<b>Bold</b>", "email": "kept@example.com"})
    vals = form_values(page)
    check("rejected input is shown again, HTML-escaped, with the general error alert",
          vals.get("name") == "<b>Bold</b>" and "&lt;b&gt;Bold&lt;/b&gt;" in page and "<b>Bold</b>" not in page
          and vals.get("email") == "kept@example.com" and "Please correct the highlighted fields. Nothing was saved." in page)

    print("\n== Duplicate enrollment numbers and e-mails")
    dup = scalar("SELECT enrollment_no FROM students WHERE enrollment_no='26IT101'")
    for label, number in (("same", dup), ("lower case", dup.lower()), ("with spaces", f"  {dup} ")):
        st, _, page = a.request("admin_dashboard.php", {**base, "enrollment_no": number, "email": f"dup.{secrets.token_hex(3)}@example.com"})
        check(f"duplicate enrollment number ({label}) -> 'already used', nothing stored",
              st == 422 and "already used by another student" in errors_of(page).get("enrollment_no", "") and count(f"enrollment_no={q(dup)}") == 1)
    st, _, page = a.request("admin_dashboard.php", {**base, "enrollment_no": next_number("26WD"), "email": "  NISHA.verma@EXAMPLE.com "})
    check("duplicate e-mail (other case, spaces) -> refused", st == 422 and "already uses this email" in errors_of(page).get("email", "") and count() == n)
    st, _, page = a.request("admin_dashboard.php", {**base, "enrollment_no": dup, "email": "broken@", "semester": ""})
    err = errors_of(page)
    check("a duplicate number is reported together with the other errors (all problems at once)",
          st == 422 and "already used" in err.get("enrollment_no", "") and "valid email" in err.get("email", "") and "semester" in err.get("semester", ""), str(err))

    print("\n== Invalid semester values")
    for value in ("0", "9", "12", "-1", "3.5", "abc", "1 OR 1=1", ""):
        st, _, page = a.request("admin_dashboard.php", {**base, "enrollment_no": next_number("26WD"), "email": f"sem.{secrets.token_hex(3)}@example.com", "semester": value})
        text = "Please select a semester." if value == "" else "number from 1 to 8"
        check(f"semester {value!r} -> rejected ('{text}')", st == 422 and text in errors_of(page).get("semester", ""), f"{st} {errors_of(page)}")
    check("no record was stored with an invalid semester", count() == n)


def edit_tests(a, token, linked_id, linked_uid):
    print("\n== Edit student")
    before = student(f"id={linked_id}")
    regs_before = mysql(f"SELECT registration_id, event_id, status FROM registrations WHERE student_id={linked_id} ORDER BY 1")
    st, _, page = a.request(f"{CONSOLE}&view=edit&id={linked_id}")
    vals = form_values(page)
    check("GET view=edit shows the form filled from the database", st == 200 and 'value="update_student"' in page
          and vals.get("name") == before["name"] and vals.get("enrollment_no") == before["enrollment_no"] and f'name="id" value="{linked_id}"' in page)
    check("... it states the account link and the number of registrations", "linked to a login account" in page and f"· {len(regs_before)} event registration(s)." in page)
    upd = {"csrf_token": token, "action": "update_student", "id": str(linked_id), "enrollment_no": before["enrollment_no"], "name": "Diya R. Shah",
           "email": "diya.shah@example.com", "course": "Data Science", "semester": "6", "gender": before["gender"]}
    updated_before = audit_count("UPDATE_STUDENT")
    st, hd, _ = a.request("admin_dashboard.php", upd)
    after = student(f"id={linked_id}")
    check("valid update -> 303, new values stored", st == 303 and after["name"] == "Diya R. Shah" and after["email"] == "diya.shah@example.com"
          and after["course"] == "Data Science" and after["semester"] == "6", str(after))
    check("... account link, status, enrollment number and creation time unchanged",
          after["user_id"] == str(linked_uid) and after["status"] == before["status"] and after["enrollment_no"] == before["enrollment_no"]
          and after["created_at"] == before["created_at"])
    check("... event registrations unchanged", mysql(f"SELECT registration_id, event_id, status FROM registrations WHERE student_id={linked_id} ORDER BY 1") == regs_before)
    check("... UPDATE_STUDENT audit entry and a success message", audit_count("UPDATE_STUDENT") == updated_before + 1
          and flash_of(a.request(CONSOLE)[2]) == ("success", f"Student “Diya R. Shah” ({before['enrollment_no']}) was updated."))

    other = student("enrollment_no='26IT101'")
    st, _, page = a.request("admin_dashboard.php", {**upd, "enrollment_no": other["enrollment_no"]})
    check("changing to another student's enrollment number -> refused, record unchanged",
          st == 422 and "already used by another student" in errors_of(page).get("enrollment_no", "") and student(f"id={linked_id}") == after)
    st, _, page = a.request("admin_dashboard.php", {**upd, "email": other["email"].upper()})
    check("changing to another student's e-mail -> refused", st == 422 and "already uses this email" in errors_of(page).get("email", "") and student(f"id={linked_id}") == after)
    st, _, page = a.request("admin_dashboard.php", {**upd, "semester": "9"})
    check("invalid semester on edit -> refused, form shown again in edit mode", st == 422 and "number from 1 to 8" in errors_of(page).get("semester", "")
          and 'value="update_student"' in page and student(f"id={linked_id}") == after)
    st, _, page = a.request("admin_dashboard.php", {**upd, "enrollment_no": ""})
    check("removing the enrollment number on edit -> refused", st == 422 and "Please enter the enrollment number." in errors_of(page).get("enrollment_no", ""))
    st, _, page = a.request("admin_dashboard.php", {**upd, "enrollment_no": "27CS555"})
    check("a new, free enrollment number in the right format can be set", st == 303 and student(f"id={linked_id}")["enrollment_no"] == "27CS555")
    a.request("admin_dashboard.php", {**upd})                                         # back to the original number

    mysql("INSERT INTO students (enrollment_no, name, email, course, gender, semester, status) VALUES ('LEG-001', 'Legacy Learner', 'legacy.learner@example.com', 'Robotics (old)', 'M', NULL, 'Active')")
    leg = student("enrollment_no='LEG-001'")
    st, _, _ = a.request("admin_dashboard.php", {"csrf_token": token, "action": "update_student", "id": leg["id"], "enrollment_no": "LEG-001", "name": "Legacy Learner Two",
                                                 "email": "legacy.learner@example.com", "course": "Robotics (old)", "semester": "", "gender": "M"})
    leg2 = student(f"id={leg['id']}")
    check("a legacy record (old number format, old course, no semester, old gender value) can be edited; unchanged values are kept",
          st == 303 and leg2["name"] == "Legacy Learner Two" and leg2["enrollment_no"] == "LEG-001" and leg2["course"] == "Robotics (old)"
          and leg2["semester"] == "NULL" and leg2["gender"] == "M", str(leg2))
    for bad_id in ("999999", "0", "1 OR 1=1", "abc"):
        st, hd, _ = a.request("admin_dashboard.php", {**upd, "id": bad_id, "name": "Should Not Save"})
        if not (st == 303 and count("name='Should Not Save'") == 0):
            check(f"update with id {bad_id!r} -> 'not found', nothing changed", False)
            break
    else:
        check("update with an unknown or malformed id (999999, 0, '1 OR 1=1', 'abc') -> 'not found', nothing changed", True)
    st, hd, _ = a.request(f"{CONSOLE}&view=edit&id=999999")
    check("GET edit of an unknown record -> back to the list with an error", st == 303 and flash_of(a.request(CONSOLE)[2]) == ("error", "That student record was not found."))


def search_filter_tests(a):
    print("\n== Search and filters (parameterised; combined)")
    rows = mysql("SELECT IFNULL(NULLIF(enrollment_no,''),'—'), name, email, course, IFNULL(semester,''), IFNULL(status,'') FROM students ORDER BY id DESC")

    def expect(qtext="", course="", semester="", status=""):
        out = []
        for enr, name, email, crs, sem, stat in rows:
            if qtext and not any(qtext.lower() in v.lower() for v in (name, email, enr if enr != "—" else "")):
                continue
            if course and crs.lower() != course.lower():
                continue
            if semester and sem != semester:
                continue
            inactive = stat.strip().lower() == "inactive"
            if (status == "Active" and inactive) or (status == "Inactive" and not inactive):
                continue
            out.append(enr)
        return out

    sample = next(r for r in rows if r[0].startswith("25"))
    cases = [
        ("search by name", {"q": sample[1].split()[0]}),
        ("search by e-mail part", {"q": sample[2].split("@")[0]}),
        ("search by enrollment number prefix", {"q": "25CS"}),
        ("course filter", {"course": "Web Development"}),
        ("semester filter", {"semester": "5"}),
        ("status filter Active", {"status": "Active"}),
        ("status filter Inactive", {"status": "Inactive"}),
        ("search + course", {"q": "25CS", "course": "Web Development"}),
        ("search + semester + status", {"q": "a", "semester": "3", "status": "Active"}),
        ("course + status", {"course": "Computer Science", "status": "Inactive"}),
        ("all four together", {"q": "e", "course": "Data Science", "semester": "3", "status": "Active"}),
    ]
    for label, params in cases:
        want = expect(params.get("q", ""), params.get("course", ""), params.get("semester", ""), params.get("status", ""))
        got = shown_all(a, urllib.parse.urlencode(params))
        check(f"{label} {params} -> exactly the {len(want)} matching record(s)", got == want, f"{got} vs {want}")
    _, _, page = a.request(f"{CONSOLE}&" + urllib.parse.urlencode({"q": "25CS", "course": "Web Development", "semester": "7", "status": "Active"}))
    check("the chosen filters stay selected and the search text stays in the box",
          'value="25CS"' in page and '<option value="Web Development" selected' in page and '<option value="7" selected' in page and '<option value="Active" selected' in page)
    for label, value in (("%", "%"), ("_", "_")):
        got = shown_all(a, urllib.parse.urlencode({"q": value}))
        check(f"'{label}' in the search is matched literally (not as a wildcard)", got == expect(value), f"{got}")

    print("\n== SQL injection attempts")
    for value in ("' OR '1'='1", "x%' OR 1=1 -- ", "\" OR \"\"=\"", "'; DROP TABLE students; --"):
        st, _, page = a.request(f"{CONSOLE}&" + urllib.parse.urlencode({"q": value}))
        check(f"search {value!r} -> 200, treated as text, no extra records", st == 200 and shown(page) == expect(value), str(shown(page)))
    n_name = sample[1].split()[0]
    for label, params in (("course", {"course": "Web Development' OR '1'='1"}), ("semester", {"semester": "1 OR 1=1"}), ("status", {"status": "Active' OR 'x'='x"}),
                          ("page", {"page": "1; DROP TABLE students"})):
        st, _, page = a.request(f"{CONSOLE}&" + urllib.parse.urlencode({"q": n_name, **params}))
        check(f"injected {label} value is ignored (unknown value, not SQL); the search still filters", st == 200 and shown(page) == expect(n_name), str(shown(page)))
    check("the students table still exists and no record changed", count() == len(rows))


def pagination_tests(a):
    print("\n== Pagination")
    mysql("INSERT INTO students (enrollment_no, name, email, course, gender, semester, status) VALUES " + ", ".join(
        f"('24WD{900 + i}', 'Paging Student {chr(65 + i)}', 'paging.{i}@example.com', 'Web Development', 'Female', 5, 'Active')" for i in range(12)))
    total = count()
    pages = -(-total // 10)
    st, _, page = a.request(CONSOLE)
    check(f"{total} records -> 10 per page, {pages} pages with page links", st == 200 and len(shown(page)) == 10 and f"Showing 1–10 of {total} records" in page
          and 'aria-label="Student record pages"' in page)
    st, _, page = a.request(f"{CONSOLE}&page={pages}")
    check("the last page shows the rest", len(shown(page)) == total - (pages - 1) * 10)
    st, _, page = a.request(f"{CONSOLE}&page=999")
    check("a page number past the end shows the last page", st == 200 and len(shown(page)) == total - (pages - 1) * 10)
    _, _, page = a.request(f"{CONSOLE}&q=Paging&course=Web+Development")
    check("page links keep the search and filters", "q=Paging&amp;course=Web+Development&amp;page=2" in page and len(shown(page)) == 10)
    got = shown_all(a, "q=Paging&course=Web+Development")
    check("the second filtered page has the remaining matches", got is not None and len(got) == 12 and len(set(got)) == 12)


def soft_delete_tests(a, token, linked_id, linked_uid, driver):
    print("\n== Soft delete (deactivation) and reactivation")
    before = student(f"id={linked_id}")
    regs_before = mysql(f"SELECT registration_id, event_id, status, registered_at FROM registrations WHERE student_id={linked_id} ORDER BY 1")
    n = count()
    st, _, page = a.request(f"{CONSOLE}&view=deactivate&id={linked_id}")
    check("GET view=deactivate shows a confirmation page and changes nothing",
          st == 200 and "Deactivate this student?" in page and "Yes, deactivate student" in page and student(f"id={linked_id}")["status"] == "Active")
    check("... it explains the soft delete and the kept registrations", f"its {len(regs_before)} event registration(s)" in page and "soft delete" in page)
    for path in (f"admin_dashboard.php?tab=students&action=deactivate_student&id={linked_id}", f"admin_dashboard.php?action=deactivate_student&id={linked_id}&csrf_token={token}"):
        a.request(path)
    check("GET requests with action=deactivate_student (even with the token) change nothing", student(f"id={linked_id}")["status"] == "Active")
    st, _, page = a.request("admin_dashboard.php", {"action": "deactivate_student", "id": str(linked_id)})
    check("POST deactivation without the CSRF token -> 403, unchanged", st == 403 and "Security check failed" in page and student(f"id={linked_id}")["status"] == "Active")
    st, _, _ = a.request("admin_dashboard.php", {"csrf_token": "0" * 64, "action": "deactivate_student", "id": str(linked_id)})
    check("POST deactivation with a wrong token -> 403, unchanged", st == 403 and student(f"id={linked_id}")["status"] == "Active")
    deact_before = audit_count("DEACTIVATE_STUDENT")
    st, hd, _ = a.request("admin_dashboard.php", {"csrf_token": token, "action": "deactivate_student", "id": str(linked_id)})
    after = student(f"id={linked_id}")
    check("confirmed POST -> 303, status Inactive", st == 303 and after["status"] == "Inactive", str(after))
    check("... the record is not removed (same number of records, all other fields unchanged)",
          count() == n and {k: v for k, v in after.items() if k != "status"} == {k: v for k, v in before.items() if k != "status"})
    check("... the login-account link is kept", after["user_id"] == str(linked_uid))
    check("... historical event registrations are intact (same rows, statuses and times)",
          mysql(f"SELECT registration_id, event_id, status, registered_at FROM registrations WHERE student_id={linked_id} ORDER BY 1") == regs_before and len(regs_before) == 2)
    msg = flash_of(a.request(CONSOLE)[2])
    check("... DEACTIVATE_STUDENT audit entry and a message that the record is kept", audit_count("DEACTIVATE_STUDENT") == deact_before + 1
          and msg is not None and msg[0] == "success" and "was deactivated. The record, its account link and its event registrations are kept; a linked student account can no longer sign in." in msg[1], str(msg))
    _, _, page = a.request(f"{CONSOLE}&status=Inactive")
    check("the inactive record is listed with the Inactive filter and offers Reactivate", before["enrollment_no"] in shown(page) and 'value="reactivate_student"' in page)
    st, _, _ = a.request("admin_dashboard.php", {"csrf_token": token, "action": "deactivate_student", "id": str(linked_id)})
    check("deactivating it again -> 'already inactive'", st == 303 and "is already inactive." in (flash_of(a.request(CONSOLE)[2]) or ("", ""))[1])
    st, hd, _ = a.request(f"{CONSOLE}&view=deactivate&id={linked_id}")
    check("the confirmation page is not offered for an inactive record", st == 303)

    event = int(scalar("SELECT id FROM events ORDER BY id LIMIT 1 OFFSET 3"))
    r = driver.register(linked_id, event)
    check("an inactive student cannot register for a new event ('student_inactive')", r == {"ok": False, "reason": "student_inactive"}, str(r))
    check("... and no registration row was added", int(scalar(f"SELECT COUNT(*) FROM registrations WHERE student_id={linked_id}")) == 2)

    for path in (f"admin_dashboard.php?tab=students&action=reactivate_student&id={linked_id}",):
        a.request(path)
    check("GET with action=reactivate_student changes nothing", student(f"id={linked_id}")["status"] == "Inactive")
    st, _, _ = a.request("admin_dashboard.php", {"action": "reactivate_student", "id": str(linked_id)})
    check("POST reactivation without the token -> 403, still inactive", st == 403 and student(f"id={linked_id}")["status"] == "Inactive")
    react_before = audit_count("REACTIVATE_STUDENT")
    st, _, _ = a.request("admin_dashboard.php", {"csrf_token": token, "action": "reactivate_student", "id": str(linked_id)})
    check("reactivation with the token -> Active again, REACTIVATE_STUDENT audit entry",
          st == 303 and student(f"id={linked_id}")["status"] == "Active" and audit_count("REACTIVATE_STUDENT") == react_before + 1)
    r = driver.register(linked_id, event)
    check("after reactivation the student can register for the event again", r.get("ok") is True, str(r))
    st, _, _ = a.request("admin_dashboard.php", {"csrf_token": token, "action": "reactivate_student", "id": str(linked_id)})
    check("reactivating an active record -> 'already active'", "is already active." in (flash_of(a.request(CONSOLE)[2]) or ("", ""))[1])
    st, _, _ = a.request("admin_dashboard.php", {"csrf_token": token, "action": "deactivate_student", "id": "999999"})
    check("deactivating an unknown record -> 'not found'", st == 303 and flash_of(a.request(CONSOLE)[2]) == ("error", "That student record was not found."))


def directory_tests(s_browser, token, a):
    print("\n== Inactive records elsewhere in the portal")
    target = student("TRIM(status)='Active' AND name LIKE 'Paging Student A'")
    a.request("admin_dashboard.php", {"csrf_token": token, "action": "deactivate_student", "id": target["id"]})
    _, _, page = s_browser.request("directory.php")
    check("a deactivated student is no longer listed in the student directory; active ones are",
          "Paging Student A" not in page and "Paging Student B" in page)
    a.request("admin_dashboard.php", {"csrf_token": token, "action": "reactivate_student", "id": target["id"]})
    check("... and is listed again after reactivation", "Paging Student A" in s_browser.request("directory.php")[2])


def csv_tests(a):
    print("\n== CSV export")
    mysql("INSERT INTO students (enrollment_no, name, email, course, gender, semester, status) VALUES "
          "('24XX001', '=HYPERLINK(\"http://evil.example\",\"Click\")', 'formula1@example.com', '+cmd|'' /C calc''!A0', 'Male', 4, 'Active'), "
          "('24XX002', '@SUM(1+1)', '-2+3@example.com', 'Data Science', 'Female', 4, 'Inactive'), "
          "('24XX003', CONCAT(CHAR(9 USING utf8mb4), 'Tab Lead'), 'formula3@example.com', CONCAT(CHAR(13 USING utf8mb4), 'CR Lead'), 'Male', 4, 'Active')")
    exports_before = audit_count("EXPORT_CSV")
    st, hd, body = a.request(f"{CONSOLE}&export=csv")
    check("export -> 200 text/csv download with a .csv file name",
          st == 200 and hd.get("Content-Type", "").startswith("text/csv") and re.fullmatch(r'attachment; filename="studenthub_students_\d{8}_\d{6}\.csv"', hd.get("Content-Disposition", "")),
          f"{st} {hd.get('Content-Type')} {hd.get('Content-Disposition')}")
    stamp = re.search(r"_(\d{8}_\d{6})\.csv", hd.get("Content-Disposition", ""))
    db_now = datetime.datetime.strptime(scalar("SELECT DATE_FORMAT(NOW(), '%Y%m%d_%H%i%s')"), "%Y%m%d_%H%M%S")
    check("the file name's date and time match the database clock (portal time zone, not php.ini's Europe/Berlin)",
          stamp is not None and abs((datetime.datetime.strptime(stamp.group(1), "%Y%m%d_%H%M%S") - db_now).total_seconds()) < 120, str(stamp and stamp.group(1)))
    check("UTF-8 byte-order mark and CRLF line endings (Excel)", body.startswith("﻿") and "\r\n" in body and body.count("\n") == body.count("\r\n"))
    rows = list(csv.reader(io.StringIO(body.lstrip("﻿"), newline="")))
    header = ["Record ID", "Enrollment No", "Name", "Email", "Course", "Semester", "Status", "Login Account", "Created At"]
    check("header row: record fields only (no gender, password, role, token or session columns)", rows[0] == header, str(rows[0]))
    check(f"all {count()} records exported, inactive ones included with status Inactive",
          len(rows) - 1 == count() and any(r[6] == "Inactive" for r in rows[1:]))
    lower = body.lower()
    check("no password hashes, session or CSRF data in the file", "$2y$" not in body and "password" not in lower and "csrf" not in lower and "studenthubsessid" not in lower)
    by_number = {r[1]: r for r in rows[1:]}
    f1, f2, f3 = by_number.get("24XX001"), by_number.get("24XX002"), by_number.get("24XX003")
    check("formula injection: cells starting with = + - @ get a leading apostrophe",
          f1 is not None and f1[2] == "'=HYPERLINK(\"http://evil.example\",\"Click\")" and f1[4] == "'+cmd|' /C calc'!A0"
          and f2[2] == "'@SUM(1+1)" and f2[3] == "'-2+3@example.com", f"{f1} {f2}")
    check("... and so do cells starting with a tab or carriage return", f3 is not None and f3[2] == "'\tTab Lead" and f3[4] == "'\rCR Lead", str(f3))
    check("quotes and commas are escaped by RFC 4180 quoting (the file parses into 9 columns per row)", all(len(r) == 9 for r in rows))
    linked = [r for r in rows[1:] if r[7] == "Linked"]
    check("the account column shows only Linked/None", linked and all(r[7] in ("Linked", "None") for r in rows[1:]))
    check("EXPORT_CSV written to the audit log with the number of records", audit_count("EXPORT_CSV") == exports_before + 1
          and scalar("SELECT details FROM audit_logs WHERE action='EXPORT_CSV' ORDER BY id DESC LIMIT 1").startswith(f"Exported {count()} student records"))

    params = {"course": "Web Development", "status": "Active", "q": "Paging"}
    _, _, page = a.request(f"{CONSOLE}&" + urllib.parse.urlencode(params))
    link = re.search(r'href="([^"]*export=csv[^"]*)" id="export-students"', page)
    check("the Export button carries the current search and filters", link is not None and "q=Paging" in link.group(1) and "course=Web+Development" in link.group(1)
          and "status=Active" in link.group(1) and "(filtered)" in page)
    st, _, body = a.request(html.unescape(link.group(1)) if link else CONSOLE)
    got = sorted(r[1] for r in list(csv.reader(io.StringIO(body.lstrip("﻿"), newline="")))[1:])
    want = sorted(r[0] for r in mysql("SELECT enrollment_no FROM students WHERE course='Web Development' AND COALESCE(TRIM(status),'') <> 'Inactive' "
                                      "AND (name LIKE '%Paging%' OR email LIKE '%Paging%' OR enrollment_no LIKE '%Paging%')"))
    check(f"filtered export contains exactly the {len(want)} filtered records (all pages, not only the first 10)", st == 200 and got == want and len(want) > 10, f"{got} vs {want}")
    st, _, body = a.request(f"{CONSOLE}&export=csv&status=Inactive&semester=4")
    got = [r[1] for r in list(csv.reader(io.StringIO(body.lstrip("﻿"), newline="")))[1:]]
    check("status + semester filters apply to the export", got == ["24XX002"], str(got))
    return {"course": "Web Development"}


def access_tests(accounts):
    print("\n== Access control (students, editors, visitors)")
    victim = student("enrollment_no='26IT101'")
    n = count()
    for role in ("student", "editor"):
        b = Browser(PORT)
        b.login(f"p11_{role}", accounts[f"p11_{role}"])
        token = b.token("dashboard.php")
        results = [b.request(path)[0] for path in (CONSOLE, f"{CONSOLE}&view=add", f"{CONSOLE}&view=edit&id={victim['id']}", f"{CONSOLE}&export=csv")]
        check(f"{role}: Student Records tab, add/edit views and CSV export -> HTTP 403", results == [403, 403, 403, 403], str(results))
        st, hd, body = b.request(f"{CONSOLE}&export=csv")
        check(f"{role}: the 403 for the export contains no CSV data", "text/csv" not in hd.get("Content-Type", "") and victim["email"] not in body)
        posts = [
            {"action": "add_student", "enrollment_no": "26IT777", "name": "Role Test", "email": f"{role}.add@example.com", "course": "Data Science", "semester": "1", "gender": "Male"},
            {"action": "update_student", "id": victim["id"], "enrollment_no": victim["enrollment_no"], "name": "Hacked Name", "email": victim["email"],
             "course": victim["course"], "semester": victim["semester"], "gender": victim["gender"]},
            {"action": "deactivate_student", "id": victim["id"]},
        ]
        codes = [b.request("admin_dashboard.php", {"csrf_token": token, **p})[0] for p in posts]
        check(f"{role}: add / update / deactivate via POST with a valid token -> 403, nothing changed",
              codes == [403, 403, 403] and count() == n and student(f"id={victim['id']}") == victim, str(codes))
    g = Browser(PORT)
    st, hd, _ = g.request(f"{CONSOLE}&export=csv")
    st2, hd2, _ = g.request("admin_dashboard.php", {"action": "deactivate_student", "id": victim["id"]})
    check("not signed in: list/export and POST -> login page, nothing changed",
          st == 303 and hd["Location"] == "login.php?status=login_required" and st2 == 303 and student(f"id={victim['id']}") == victim)


def csrf_get_tests(a, token):
    print("\n== CSRF and GET requests")
    victim = student("enrollment_no='26IT101'")
    n = count()
    rejected_before = audit_count("CSRF_REJECTED")
    data = {"action": "add_student", "enrollment_no": "26IT888", "name": "No Token", "email": "no.token@example.com", "course": "Data Science", "semester": "1", "gender": "Male"}
    codes = [a.request("admin_dashboard.php", data)[0],
             a.request("admin_dashboard.php", {**data, "csrf_token": "f" * 64})[0],
             a.request("admin_dashboard.php", {**data, "csrf_token": token + "x"})[0],
             a.request("admin_dashboard.php", {"action": "update_student", "id": victim["id"], "enrollment_no": victim["enrollment_no"], "name": "No Token Edit",
                                                "email": victim["email"], "course": victim["course"], "semester": victim["semester"], "gender": victim["gender"]})[0]]
    check("add/update without, with a wrong or with a modified token -> 403 'Security check failed', nothing changed",
          codes == [403, 403, 403, 403] and count() == n and student(f"id={victim['id']}") == victim, str(codes))
    check("CSRF rejections are audit-logged", audit_count("CSRF_REJECTED") >= rejected_before + 4)
    other = Browser(PORT)
    other.login("p11_admin2", ACCOUNTS["p11_admin2"])
    st, _, _ = a.request("admin_dashboard.php", {**data, "csrf_token": other.token(CONSOLE)})
    check("a token from another admin's session is refused", st == 403 and count() == n)
    query = urllib.parse.urlencode({**data, "csrf_token": token})
    a.request(f"admin_dashboard.php?{query}")
    a.request(f"admin_dashboard.php?tab=students&" + urllib.parse.urlencode({"action": "update_student", "id": victim["id"], "name": "Get Edit", "csrf_token": token}))
    check("GET requests carrying add/update parameters (even the token) change nothing", count() == n and student(f"id={victim['id']}") == victim)


def inactive_login_tests(a, token):
    print("\n== Deactivated students cannot sign in or keep a session")
    mysql("INSERT INTO students (enrollment_no, name, email, course, gender, semester, status) VALUES "
          "('23DS801', 'Lina Learner', 'p11_learner@example.com', 'Data Science', 'Female', 7, 'Active'), "
          "('23DS802', 'Eddie Editor', 'p11_editor.record@example.com', 'Data Science', 'Male', 7, 'Active'), "
          "('23DS803', 'Ada Admin', 'p11_admin2.record@example.com', 'Data Science', 'Female', 7, 'Active')")
    uid = {u: int(scalar(f"SELECT id FROM users WHERE username='{u}'")) for u in ("p11_learner", "p11_unlinked", "p11_editor", "p11_admin2")}
    rec = {n: int(scalar(f"SELECT id FROM students WHERE enrollment_no='{n}'")) for n in ("23DS801", "23DS802", "23DS803")}
    # links as self-registration would create them; the editor and admin links prove that only student accounts are affected
    mysql(f"UPDATE students SET user_id={uid['p11_learner']} WHERE id={rec['23DS801']}; UPDATE students SET user_id={uid['p11_editor']} WHERE id={rec['23DS802']}; "
          f"UPDATE students SET user_id={uid['p11_admin2']} WHERE id={rec['23DS803']}")
    users_snap = lambda: mysql("SELECT id, username, email, password, role FROM users ORDER BY id")
    students_snap = lambda: mysql("SELECT id, IFNULL(user_id,''), IFNULL(enrollment_no,''), name, email, course, IFNULL(semester,''), gender, created_at FROM students ORDER BY id")
    regs_snap = lambda: mysql("SELECT * FROM registrations ORDER BY registration_id")
    before = (users_snap(), students_snap(), regs_snap())
    last_login = lambda u: scalar(f"SELECT IFNULL(last_login,'never') FROM users WHERE id={uid[u]}")
    logins = lambda u: int(scalar(f"SELECT COUNT(*) FROM audit_logs WHERE action='USER_LOGIN' AND username={q(u)}"))
    message = "Your access to StudentHub is currently disabled. Please contact the administrator."

    def set_status(record, active):
        st, _, _ = a.request("admin_dashboard.php", {"csrf_token": token, "action": "reactivate_student" if active else "deactivate_student", "id": str(record)})
        return st == 303 and student(f"id={record}")["status"] == ("Active" if active else "Inactive")

    # active linked student
    s = Browser(PORT)
    st, hd, _ = s.login("p11_learner", ACCOUNTS["p11_learner"])
    check("an active student with a linked record signs in normally (303 -> dashboard.php, page 200)",
          st == 303 and hd.get("Location") == "dashboard.php" and s.request("dashboard.php")[0] == 200, f"{st} {hd.get('Location')}")

    # an existing session loses access after the deactivation
    old_sid, old_token = s.sid(), s.token("profile.php")
    hash_before = scalar(f"SELECT password FROM users WHERE id={uid['p11_learner']}")
    revoked_before = int(scalar("SELECT COUNT(*) FROM audit_logs WHERE action='SESSION_REVOKED' AND username='p11_learner'"))
    check("the administrator deactivates the student's record in the console", set_status(rec["23DS801"], False))
    st, hd, _ = s.request("dashboard.php")
    check("the signed-in student's next request -> login page with status=access_disabled",
          st == 303 and hd.get("Location") == "login.php?status=access_disabled", f"{st} {hd.get('Location')}")
    check("... the session was ended on the server: new session ID, SESSION_REVOKED written once to the audit log",
          s.sid() != old_sid and int(scalar("SELECT COUNT(*) FROM audit_logs WHERE action='SESSION_REVOKED' AND username='p11_learner'")) == revoked_before + 1)
    r = Browser(PORT)
    r.set_sid(old_sid)
    st, hd, _ = r.request("dashboard.php")
    check("replaying the old session cookie gives no access (login_required)", st == 303 and hd.get("Location") == "login.php?status=login_required", f"{st} {hd.get('Location')}")
    st, hd, _ = s.request("profile.php", {"csrf_token": old_token, "form_action": "change_password", "oldpass": ACCOUNTS["p11_learner"],
                                          "newpass": "N3w!Password", "confirm_newpass": "N3w!Password"})
    check("a POST with the old form token is not processed (redirect to login, password unchanged)",
          st == 303 and "login.php" in hd.get("Location", "") and scalar(f"SELECT password FROM users WHERE id={uid['p11_learner']}") == hash_before)
    _, _, page = s.request("login.php?status=access_disabled")
    check("the login page shows the generic access message", message in page)
    _, _, page = s.request("index.php")
    check("public pages treat the ended session as signed out", "p11_learner" not in page)

    # sign-in refused while the record is inactive
    ll_before, logins_before = last_login("p11_learner"), logins("p11_learner")
    denied_before = int(scalar("SELECT COUNT(*) FROM audit_logs WHERE action='LOGIN_DENIED' AND username='p11_learner'"))
    d = Browser(PORT)
    st, _, page = d.login("p11_learner", ACCOUNTS["p11_learner"])
    check("correct password, inactive record -> sign-in refused (HTTP 403) with the generic message", st == 403 and message in page, str(st))
    st_d, hd_d, _ = d.request("dashboard.php")
    check("... no session is started (dashboard -> login_required), last_login and USER_LOGIN unchanged, LOGIN_DENIED logged",
          st_d == 303 and hd_d.get("Location") == "login.php?status=login_required"
          and last_login("p11_learner") == ll_before and logins("p11_learner") == logins_before
          and int(scalar("SELECT COUNT(*) FROM audit_logs WHERE action='LOGIN_DENIED' AND username='p11_learner'")) == denied_before + 1)
    lower = page.lower()
    check("... the message reveals nothing about the record (no 'inactive', 'deactivated', name or enrollment number)",
          "inactive" not in lower and "deactivat" not in lower and "Lina Learner" not in page and "23DS801" not in page)
    st, _, page = Browser(PORT).login("p11_learner@example.com", ACCOUNTS["p11_learner"])
    check("signing in with the e-mail address is refused the same way", st == 403 and message in page)
    st, _, page = Browser(PORT).login("p11_learner", "Wrong!Pass123")
    check("a wrong password for the inactive account gets the normal 'Invalid username/email or password.' (status not revealed)",
          st == 401 and "Invalid username/email or password." in page and message not in page)

    # admin and editor accounts are not affected, even when linked to an inactive record
    e = Browser(PORT)
    e.login("p11_editor", ACCOUNTS["p11_editor"])
    check("an editor signed in before its linked record is deactivated keeps access", set_status(rec["23DS802"], False) and e.request("dashboard.php")[0] == 200)
    e2 = Browser(PORT)
    st, hd, _ = e2.login("p11_editor", ACCOUNTS["p11_editor"])
    check("an editor linked to an inactive record signs in normally; the editor still gets 403 for the Admin Console (permissions unchanged)",
          st == 303 and hd.get("Location") == "dashboard.php" and e2.request("profile.php")[0] == 200 and e2.request(CONSOLE)[0] == 403)
    set_status(rec["23DS803"], False)
    a2 = Browser(PORT)
    st, hd, _ = a2.login("p11_admin2", ACCOUNTS["p11_admin2"])
    check("an admin linked to an inactive record signs in normally and opens the Admin Console",
          st == 303 and hd.get("Location") == "admin_dashboard.php" and a2.request(CONSOLE)[0] == 200)
    check("the administrator's own session is unaffected throughout", a.request(CONSOLE)[0] == 200)

    # a student account without a linked record
    u = Browser(PORT)
    st, hd, _ = u.login("p11_unlinked", ACCOUNTS["p11_unlinked"])
    check("a student account without a linked student record signs in normally; no link is created",
          st == 303 and hd.get("Location") == "dashboard.php" and u.request("dashboard.php")[0] == 200
          and scalar(f"SELECT COUNT(*) FROM students WHERE user_id={uid['p11_unlinked']}") == "0")

    # reactivation restores normal access
    check("the administrator reactivates the record", set_status(rec["23DS801"], True))
    s2 = Browser(PORT)
    st, hd, _ = s2.login("p11_learner", ACCOUNTS["p11_learner"])
    check("after reactivation the student signs in again (303 -> dashboard.php, pages 200, last_login and USER_LOGIN updated)",
          st == 303 and hd.get("Location") == "dashboard.php" and s2.request("dashboard.php")[0] == 200 and s2.request("profile.php")[0] == 200
          and last_login("p11_learner") != "never" and logins("p11_learner") == logins_before + 1)

    after = (users_snap(), students_snap(), regs_snap())
    check("users (incl. password hashes), student records (all fields but status), account links and registrations are unchanged",
          after == before)
    check("only the status of the records that were deactivated changed",
          [r[0] for r in mysql("SELECT enrollment_no FROM students WHERE TRIM(status)='Inactive' AND enrollment_no LIKE '23DS80%' ORDER BY 1")] == ["23DS802", "23DS803"])


def server_log_tests(server):
    print("\n== Server log")
    log = server.logged()
    problems = [l for l in log.splitlines() if re.search(r"PHP (Warning|Notice|Fatal|Deprecated|Parse)", l)]
    check("no PHP warnings, notices or fatal errors in the server log", not problems, "; ".join(problems[:3]))


ACCOUNTS = {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dump")
    args = ap.parse_args()
    print(f"StudentHub student management tests - Practical 11 (PHP {PHP}, MySQL {MYSQL})")
    info("source: " + (pathlib.Path(args.source_dump).name if args.source_dump else "database/studenthub_demo.sql"))
    live_before = live_fingerprint()
    static_checks()
    workdir = tempfile.mkdtemp(prefix="p11-")
    server = None
    try:
        create_test_db(args.source_dump)
        for name, role in (("p11_admin", "admin"), ("p11_admin2", "admin"), ("p11_editor", "editor"), ("p11_student", "student"),
                           ("p11_learner", "student"), ("p11_unlinked", "student")):
            ACCOUNTS[name] = secrets.token_urlsafe(12) + "A1!"
            create_account(name, f"{name}@example.com", role, ACCOUNTS[name])
        # a student record linked to the student account, with two historical event registrations
        linked_uid = int(scalar("SELECT id FROM users WHERE username='p11_student'"))
        linked_id = int(scalar("SELECT id FROM students WHERE user_id IS NULL AND COALESCE(TRIM(status),'') <> 'Inactive' AND enrollment_no IS NOT NULL ORDER BY id LIMIT 1 OFFSET 1"))
        mysql(f"UPDATE students SET user_id={linked_uid} WHERE id={linked_id}")
        events = [int(r[0]) for r in mysql("SELECT id FROM events ORDER BY id LIMIT 2")]
        mysql(f"INSERT INTO registrations (student_id, event_id, status, registered_at) VALUES ({linked_id}, {events[0]}, 'attended', '2026-08-22 09:00:00'), "
              f"({linked_id}, {events[1]}, 'registered', '2026-09-01 10:30:00')")
        users_before = int(scalar("SELECT COUNT(*) FROM users"))
        schema_checks()
        server = Server(PORT, workdir, {"DB_NAME": TEST_DB})
        a = Browser(PORT)
        a.login("p11_admin", ACCOUNTS["p11_admin"])
        listing_tests(a)
        token, base = add_tests(a, users_before)
        invalid_tests(a, token, base)
        edit_tests(a, token, linked_id, linked_uid)
        search_filter_tests(a)
        pagination_tests(a)
        soft_delete_tests(a, token, linked_id, linked_uid, PhpDriver(workdir))
        s = Browser(PORT)
        s.login("p11_student", ACCOUNTS["p11_student"])
        directory_tests(s, token, a)
        csv_tests(a)
        access_tests(ACCOUNTS)
        csrf_get_tests(a, token)
        inactive_login_tests(a, token)
        server_log_tests(server)
    finally:
        if server:
            server.stop()
        drop_test_db()
    print("\n== Clean-up")
    check("disposable database removed", not mysql(f"SHOW DATABASES LIKE '{TEST_DB}'", None))
    check("the live studenthub_db was not touched (students, users with password hashes, registrations unchanged)", live_fingerprint() == live_before)
    print(f"\nResult: {passed} passed, {failed} failed, {passed + failed} checks")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
