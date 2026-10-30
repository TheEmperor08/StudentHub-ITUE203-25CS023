"""StudentHub – Practical 11: automated tests (Python 3, standard library only).

Run from the Practical-11 folder:  python tests\\test_app.py
Creates the disposable database studenthub_prac11_test from studenthub_prac11.sql (only the name changed), starts
XAMPP's PHP built-in server twice (normal, and with an unreachable MySQL port) and removes the test database at
the end. studenthub_prac11 and every other database are never changed.
"""
import csv, http.cookiejar, io, os, pathlib, re, subprocess, sys, tempfile, time, urllib.error, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
PHP = r"C:\xampp\php\php.exe" if os.path.exists(r"C:\xampp\php\php.exe") else "php"
MYSQL = r"C:\xampp\mysql\bin\mysql.exe" if os.path.exists(r"C:\xampp\mysql\bin\mysql.exe") else "mysql"
TEST_DB = "studenthub_prac11_test"
PORT, PORT_DOWN = 8691, 8692
passed = failed = 0
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def check(name, ok, detail=""):
    global passed, failed
    passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))


def mysql(sql_text, database=TEST_DB):
    args = [MYSQL, "-u", "root", "-N", "-B"] + ([database] if database else [])
    r = subprocess.run(args, input=sql_text, capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        raise RuntimeError(r.stderr)
    return [line.split("\t") for line in r.stdout.splitlines()]


def scalar(sql_text):
    rows = mysql(sql_text)
    return rows[0][0] if rows else None


def drop_test_db():
    if mysql(f"SHOW DATABASES LIKE '{TEST_DB}'", None):
        if not mysql(f"SHOW TABLES FROM {TEST_DB} LIKE 'p11_test_marker'", None):
            raise RuntimeError(f"{TEST_DB} exists but was not created by these tests - not dropped")
        mysql(f"DROP DATABASE {TEST_DB}", None)


def create_test_db():
    dump = (ROOT / "studenthub_prac11.sql").read_text(encoding="utf-8")
    sql = dump.replace("`studenthub_prac11`", f"`{TEST_DB}`")
    assert "`studenthub_prac11`" not in sql and f"USE `{TEST_DB}`;" in sql
    mysql(sql + f"\nCREATE TABLE {TEST_DB}.p11_test_marker (id INT);\n", None)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Browser:
    def __init__(self, port=PORT):
        self.port, self.jar = port, http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar), NoRedirect)

    def request(self, path, data=None):
        body = urllib.parse.urlencode(data).encode() if data is not None else None
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/{path.lstrip('/')}", data=body)
        try:
            with self.opener.open(req, timeout=30) as r:
                return r.status, r.headers, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read()

    def get(self, path):
        status, headers, body = self.request(path)
        return status, headers, body.decode("utf-8")

    def post(self, path, data):
        status, headers, body = self.request(path, data)
        return status, headers, body.decode("utf-8")

    def follow(self, status, headers, page):
        if status in (302, 303):
            return self.get(headers["Location"])
        return status, headers, page

    @staticmethod
    def token(page):
        m = re.search(r'name="form_token" value="([0-9a-f]{64})"', page)
        return m.group(1) if m else ""


class Server:
    def __init__(self, port, log_dir, env):
        self.port, self.log = port, pathlib.Path(log_dir) / f"php-{port}.log"
        self.out = open(pathlib.Path(log_dir) / f"server-{port}.txt", "w")
        environment = {k: v for k, v in os.environ.items() if not k.startswith("P11_")}
        environment.update(env)
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
        self.proc.terminate()
        self.proc.wait(10)
        self.out.close()


def count(where="1=1"):
    return int(scalar(f"SELECT COUNT(*) FROM students WHERE {where}"))


def table_rows(page):
    return re.findall(r'<tr class="[^"]*">\s*<td data-label="ID">(\d+)</td>', page)


def flash(page):
    m = re.search(r'<div class="alert (alert-\w+)" role="\w+">(.*?)</div>', page, re.S)
    return (m.group(1), m.group(2)) if m else (None, "")


def add_student(b, **fields):
    _, _, form = b.get("add.php")
    data = {"form_token": b.token(form), "full_name": "", "email": "", "course": "", "semester": ""}
    data.update(fields)
    return b.post("add.php", data)


def edit_student(b, student_id, **fields):
    _, _, form = b.get(f"edit.php?id={student_id}")
    data = {"form_token": b.token(form), "student_id": str(student_id)}
    data.update(fields)
    return b.post("edit.php", data)


def export_rows(b, query=""):
    status, headers, body = b.request("export.php" + query)
    text = body.decode("utf-8-sig")
    return status, headers, body, list(csv.reader(io.StringIO(text, newline="")))


def static_checks():
    print("\n== Static checks")
    php_files = sorted(p for p in ROOT.rglob("*.php"))
    bad = [p.name for p in php_files
           if subprocess.run([PHP, "-l", str(p)], capture_output=True, text=True).returncode != 0]
    check(f"php -l: no syntax errors in all {len(php_files)} PHP files", not bad, ", ".join(bad))
    app = {p.name: p.read_text(encoding="utf-8") for p in php_files if p.name not in ("router.php", "config.example.php")}
    source = "\n".join(app.values())
    check("no ->query() / mysqli_query() / multi_query in the application (prepared statements only)",
          not re.search(r"->query\(|mysqli_query|multi_query|real_query", source))
    check("every SQL statement goes through prepare()", source.count("->prepare(") >= 7 and "->execute()" in source)
    check("no permanent DELETE statement anywhere (soft delete only)", not re.search(r"DELETE\s+FROM", source, re.I))


def database_checks():
    print("\n== Database (imported studenthub_prac11.sql into studenthub_prac11_test)")
    check("24 seed records imported", count() == 24, str(count()))
    check("22 active and 2 inactive", count("status='active'") == 22 and count("status='inactive'") == 2)
    check("inactive seed records have deleted_at, active ones do not",
          count("status='inactive' AND deleted_at IS NOT NULL") == 2 and count("status='active' AND deleted_at IS NULL") == 22)
    check("engine is InnoDB", scalar(f"SELECT ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA='{TEST_DB}' AND TABLE_NAME='students'") == "InnoDB")
    idx = {r[0] for r in mysql(f"SELECT INDEX_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA='{TEST_DB}' AND TABLE_NAME='students'")}
    check("indexes: PRIMARY, uq_students_email, course, status, full_name",
          {"PRIMARY", "uq_students_email", "idx_students_course", "idx_students_status", "idx_students_full_name"} <= idx, str(idx))
    try:
        mysql("INSERT INTO students (full_name,email,course,semester) VALUES ('Dup Test','AARAV.PATEL@example.com','Data Science',1)")
        check("UNIQUE email refuses a duplicate (case-insensitive)", False)
    except RuntimeError as e:
        check("UNIQUE email refuses a duplicate (case-insensitive)", "Duplicate entry" in str(e))
    try:
        mysql("INSERT INTO students (full_name,email,course,semester) VALUES ('Sem Test','sem.test@example.com','Data Science',9)")
        check("CHECK constraint refuses semester 9", False)
    except RuntimeError as e:
        check("CHECK constraint refuses semester 9", "chk_students_semester" in str(e))
    try:
        mysql("UPDATE students SET status='inactive' WHERE student_id=1")
        check("CHECK constraint refuses inactive without deleted_at", False)
    except RuntimeError as e:
        check("CHECK constraint refuses inactive without deleted_at", "chk_students_soft_delete" in str(e))


def app_checks(server):
    b = Browser()
    print("\n== Connection and student list")
    status, headers, page = b.get("index.php")
    check("index.php connects to MySQL and returns 200", status == 200, str(status))
    check("student table with all column headings",
          all(f">{h}</th>" in page for h in ["ID", "Full name", "Email", "Course", "Sem.", "Status", "Last updated", "Actions"]))
    check("page 1 shows 10 records and 'Showing 1–10 of 24 students'",
          len(table_rows(page)) == 10 and "Showing 1–10 of 24 students" in page)
    check("Active and Inactive status badges displayed",
          '<span class="badge badge-active">Active</span>' in page and '<span class="badge badge-inactive">Inactive</span>' in page)
    check("security headers (CSP, X-Frame-Options, nosniff) sent",
          "default-src 'self'" in headers.get("Content-Security-Policy", "") and headers.get("X-Frame-Options") == "DENY"
          and headers.get("X-Content-Type-Options") == "nosniff")
    check("session cookie is HttpOnly and SameSite=Strict",
          re.search(r"P11SESSID=.*HttpOnly.*SameSite=Strict", headers.get("Set-Cookie", ""), re.I) is not None)

    print("\n== Pagination")
    _, _, p2 = b.get("index.php?page=2")
    _, _, p3 = b.get("index.php?page=3")
    ids = table_rows(page) + table_rows(p2) + table_rows(p3)
    check("page 2 shows records 11–20", len(table_rows(p2)) == 10 and "Showing 11–20 of 24" in p2)
    check("page 3 shows records 21–24", len(table_rows(p3)) == 4 and "Showing 21–24 of 24" in p3)
    check("the three pages together list all 24 students exactly once", len(ids) == 24 and len(set(ids)) == 24)
    _, _, p99 = b.get("index.php?page=99")
    _, _, pbad = b.get("index.php?page=abc")
    check("page=99 is clamped to the last page, page=abc to page 1",
          "Showing 21–24 of 24" in p99 and "Showing 1–10 of 24" in pbad)
    _, _, pf = b.get("index.php?course=Computer+Engineering")
    _, _, pa = b.get("index.php?status=active&page=3")
    check("page links keep the filter (status=active: 22 records, 3 pages)",
          'href="index.php?status=active&amp;page=2"' in pa and "Showing 21–22 of 22" in pa)
    check("no page links when one page is enough", 'class="pagination"' not in pf and 'href="index.php?page=2"' in page)

    print("\n== Add student")
    before = count()
    status, headers, _ = add_student(b, full_name="Neha Raval", email="Neha.Raval@Example.com",
                                     course="Information Technology", semester="3")
    check("valid POST add.php -> 303 redirect to index.php", status == 303 and headers["Location"] == "index.php", str(status))
    _, _, page = b.get("index.php")
    kind, text = flash(page)
    check("success message 'Student “Neha Raval” was added successfully'",
          kind == "alert-success" and "Student “Neha Raval” was added successfully" in text, text)
    new_id = scalar("SELECT student_id FROM students WHERE email='neha.raval@example.com'")
    check("record inserted once, email stored in lower case, status active",
          count() == before + 1 and new_id is not None and scalar(f"SELECT status FROM students WHERE student_id={new_id}") == "active")
    check("new student is shown first and highlighted in the list",
          table_rows(page)[0] == new_id and 'row-highlight' in page)
    _, _, again = b.get("index.php")
    check("the message is shown only once (gone after refresh)", flash(again)[0] is None)

    print("\n== Validation")
    before = count()
    status, _, page = add_student(b)
    check("all fields empty -> 422 and an error under each of the 4 fields",
          status == 422 and page.count('class="field-error"') == 4 and "Full name is required." in page
          and "Email is required." in page and "Please select a course." in page and "Please select a semester." in page)
    check("error summary 'The student was not added'", "The student was not added. Please correct the highlighted fields." in page)
    status, _, page = add_student(b, full_name="Test Student", email="not-an-email", course="Data Science", semester="2")
    check("invalid email -> 'Enter a valid email address'", status == 422 and "Enter a valid email address" in page)
    check("entered values are kept after an error", 'value="Test Student"' in page and 'value="not-an-email"' in page)
    status, _, page = add_student(b, full_name="Copy Of Diya", email="DIYA.SHAH@example.com", course="Data Science", semester="2")
    check("duplicate email (other case) -> 'already registered to another student'",
          status == 422 and "This email is already registered to another student." in page)
    status, _, page = add_student(b, full_name="Om Again", email="om.thakkar@example.com", course="Data Science", semester="2")
    check("email of an inactive student is still reserved", status == 422 and "already registered" in page)
    status, _, page = add_student(b, full_name="X", email="x.y@example.com", course="Medicine", semester="9")
    check("tampered values: 1-letter name, unknown course, semester 9 are refused",
          status == 422 and "Use 2–100 letters" in page and "select a course from the list" in page and "number from 1 to 8" in page)
    status, _, page = add_student(b, full_name="   ", email="   ", course="Data Science", semester="1")
    check("spaces only count as empty", status == 422 and "Full name is required." in page and "Email is required." in page)
    check("no invalid record was inserted", count() == before)

    print("\n== Update student")
    _, _, form = b.get("edit.php?id=2")
    check("edit.php?id=2 shows the form filled from MySQL",
          'value="Diya Shah"' in form and 'value="diya.shah@example.com"' in form
          and '<option value="Information Technology" selected>' in form and '<option value="3" selected>' in form)
    time.sleep(1.1)   # updated_at has 1-second resolution; the list puts the most recently changed record first
    status, headers, _ = edit_student(b, 2, full_name="Diya Shah", email="diya.shah@example.com",
                                      course="Computer Science", semester="4")
    _, _, page = b.get("index.php")
    row = mysql("SELECT course, semester FROM students WHERE student_id=2")[0]
    check("valid update -> 303, message 'was updated successfully'",
          status == 303 and "Student “Diya Shah” was updated successfully." in flash(page)[1])
    check("course and semester changed in MySQL", row == ["Computer Science", "4"], str(row))
    check("updated student is shown first and highlighted", table_rows(page)[0] == "2")
    status, _, page = edit_student(b, 2, full_name="Diya Shah", email="aarav.patel@example.com", course="Computer Science", semester="4")
    check("update to another student's email -> error, not saved",
          status == 422 and "already registered" in page and scalar("SELECT email FROM students WHERE student_id=2") == "diya.shah@example.com")
    status, _, page = edit_student(b, 2, full_name="", email="diya.shah@example.com", course="Computer Science", semester="4")
    check("update with an empty name -> 'Full name is required.'", status == 422 and "Full name is required." in page)
    status, headers, _ = b.get("edit.php?id=9999")
    _, _, page = b.get("index.php")
    check("edit of an unknown ID -> list with 'record was not found'", status == 303 and "That student record was not found." in page)

    print("\n== Soft delete")
    status, _, page = b.get("delete.php?id=15")
    check("GET delete.php?id=15 shows a confirmation page, not a change",
          status == 200 and "Deactivate this student?" in page and "Are you sure you want to deactivate <strong>Rohan Verma</strong>?" in page
          and scalar("SELECT status FROM students WHERE student_id=15") == "active")
    check("confirmation page has a POST form with token, a confirm button and Cancel",
          'method="post" action="delete.php"' in page and b.token(page) and "Yes, deactivate student" in page and ">Cancel</a>" in page)
    before = count()
    status, headers, _ = b.post("delete.php", {"form_token": b.token(page), "student_id": "15"})
    _, _, listing = b.get("index.php")
    check("confirmed POST -> 303 and message 'was deactivated'",
          status == 303 and "Student “Rohan Verma” was deactivated" in flash(listing)[1])
    row = mysql("SELECT status, deleted_at IS NOT NULL FROM students WHERE student_id=15")[0]
    check("status changed to 'inactive' and deleted_at set", row == ["inactive", "1"], str(row))
    check("record still exists in MySQL (row count unchanged)", count() == before)
    m = re.search(r'<tr class="row-inactive row-highlight">\s*<td data-label="ID">15</td>.*?</tr>', listing, re.S)
    check("list shows the row as Inactive, highlighted, without a Deactivate button",
          m is not None and "badge-inactive" in m.group(0) and "delete.php?id=15" not in m.group(0))
    status, headers, page = b.get("delete.php?id=15")
    _, _, page = b.follow(status, headers, page)
    check("deactivating an inactive student again -> redirect, 'is already inactive'",
          status == 303 and "Student “Rohan Verma” is already inactive." in flash(page)[1])
    _, _, form = b.get("delete.php?id=16")
    b.get("index.php")
    _, _, form2 = b.get("delete.php?id=16")
    status, _, _ = b.post("delete.php", {"form_token": b.token(form), "student_id": "999999"})
    _, _, page = b.get("index.php")
    check("POST for an unknown ID -> 'record was not found', nothing changed",
          "That student record was not found." in flash(page)[1] and count("status='inactive'") == 3)
    _, _, inactive = b.get("index.php?status=inactive")
    check("status filter 'Inactive' lists the 3 inactive records", len(table_rows(inactive)) == 3)

    print("\n== Search and course filter")
    _, _, page = b.get("index.php?q=Patel")
    check("search by name 'Patel' -> Aarav Patel", table_rows(page) == ["1"])
    _, _, page = b.get("index.php?q=kiara.iyer%40example")
    check("search by email 'kiara.iyer@example' -> Kiara Iyer", table_rows(page) == ["12"])
    _, _, page = b.get("index.php?q=data+science")
    expected = count("course='Data Science'")
    check(f"search by course text 'data science' (case-insensitive) -> {expected} records",
          len(table_rows(page)) == expected and "matching “<strong>data science</strong>”" in page)
    _, _, page = b.get("index.php?q=zzzz")
    check("search without matches -> 'No students found'", not table_rows(page) and "No students found" in page)
    _, _, page = b.get("index.php?q=%25")
    check("'%' is searched literally (LIKE wildcards escaped)", not table_rows(page))
    _, _, page = b.get("index.php?course=Information+Technology")
    expected = count("course='Information Technology'")
    courses = re.findall(r'<td data-label="Course">(.*?)</td>', page)
    check(f"course filter 'Information Technology' -> {expected} records, all of that course",
          len(courses) == expected and set(courses) == {"Information Technology"} and "in <strong>Information Technology</strong>" in page)
    check("selected course stays selected in the filter", '<option value="Information Technology" selected>' in page)
    _, _, page = b.get("index.php?course=Electronics+%26+Communication")
    check("course with '&' filters correctly and is escaped as &amp;",
          len(table_rows(page)) == count("course='Electronics & Communication'") and "Electronics &amp; Communication" in page)
    _, _, page = b.get("index.php?q=a&course=Data+Science&status=active")
    check("search + course + status combined",
          len(table_rows(page)) == count("course='Data Science' AND status='active' AND (full_name LIKE '%a%' OR email LIKE '%a%' OR course LIKE '%a%')"))
    _, _, page = b.get("index.php?course=Medicine&status=deleted")
    check("unknown course/status values are ignored (all records listed)", f"of {count()} students" in page)

    print("\n== CSV export")
    status, headers, body, rows = export_rows(b)
    check("export.php -> 200 text/csv attachment students_YYYYMMDD_HHMMSS.csv",
          status == 200 and headers.get("Content-Type", "").startswith("text/csv")
          and re.search(r'attachment; filename="students_\d{8}_\d{6}\.csv"', headers.get("Content-Disposition", "")) is not None)
    check("UTF-8 byte-order mark and CRLF line endings (Excel)", body.startswith(b"\xef\xbb\xbf") and body.count(b"\r\n") == len(rows))
    check("header row", rows[0] == ["Student ID", "Full Name", "Email", "Course", "Semester", "Status", "Created At", "Updated At", "Deactivated At"])
    check("one row per student, 9 columns each (active and inactive)",
          len(rows) - 1 == count() and all(len(r) == 9 for r in rows))
    rohan = next((r for r in rows if r[0] == "15"), None)
    check("soft-deleted student exported with Status 'Inactive' and a Deactivated At time",
          rohan is not None and rohan[5] == "Inactive" and re.match(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d", rohan[8]))
    check("'Electronics & Communication' exported as plain text", any(r[3] == "Electronics & Communication" for r in rows))
    _, _, _, rows = export_rows(b, "?course=Data+Science&status=active")
    check("export respects course + status filter",
          len(rows) - 1 == count("course='Data Science' AND status='active'") and {r[3] for r in rows[1:]} == {"Data Science"})
    _, _, _, rows = export_rows(b, "?q=Patel")
    check("export respects the search text", [r[0] for r in rows[1:]] == ["1"])
    mysql("INSERT INTO students (full_name,email,course,semester) VALUES "
          "('=HYPERLINK(\"http://evil.example\",\"Click\")','@sum.test@example.com','Data Science',1),"
          "('+1+1','plus.test@example.com','Data Science',1),('-2+3','minus.test@example.com','Data Science',1)")
    _, _, _, rows = export_rows(b, "?q=test%40example.com")
    names = sorted(r[1] for r in rows[1:])
    emails = sorted(r[2] for r in rows[1:])
    check("formula injection: cells starting with = + - @ are prefixed with an apostrophe",
          names == ["'+1+1", "'-2+3", "'=HYPERLINK(\"http://evil.example\",\"Click\")"] and "'@sum.test@example.com" in emails, str(names + emails))

    print("\n== CSRF and duplicate submissions")
    before = count()
    status, headers, _ = b.post("add.php", {"full_name": "No Token", "email": "no.token@example.com", "course": "Data Science", "semester": "1"})
    _, _, page = b.get("index.php")
    check("add without token -> refused with an error message, nothing inserted",
          status == 303 and "has expired or was already submitted" in flash(page)[1] and count() == before)
    status, _, _ = add_student(b, form_token="a" * 64, full_name="Fake Token", email="fake.token@example.com", course="Data Science", semester="1")
    check("add with a made-up token -> refused", status == 303 and count() == before)
    other = Browser()
    _, _, other_form = other.get("add.php")
    status, _, _ = b.post("add.php", {"form_token": other.token(other_form), "full_name": "Other Session",
                                      "email": "other.session@example.com", "course": "Data Science", "semester": "1"})
    check("token from another session -> refused", status == 303 and count() == before)
    _, _, form = b.get("add.php")
    data = {"form_token": b.token(form), "full_name": "Twice Sent", "email": "twice.sent@example.com", "course": "Data Science", "semester": "1"}
    first, _, _ = b.post("add.php", data)
    second, _, _ = b.post("add.php", data)
    check("the same form sent twice -> first saved, second refused (1 record)",
          first == 303 and second == 303 and count("email='twice.sent@example.com'") == 1)
    status, _, _ = b.post("delete.php", {"student_id": "16"})
    status2, _, _ = b.post("edit.php", {"student_id": "16", "full_name": "Hacked", "email": "hacked@example.com", "course": "Data Science", "semester": "1"})
    check("soft delete and update without token -> refused, record unchanged",
          scalar("SELECT CONCAT(status,'|',full_name) FROM students WHERE student_id=16") == "active|Tara Menon")
    status, _, _ = b.post("delete.php", {"form_token": b.token(form2), "student_id": "16"})
    status, _, page = b.get("index.php")
    check("a valid unused confirmation token still works", "Tara Menon" in flash(page)[1] and count("student_id=16 AND status='inactive'") == 1)
    status, _, _ = b.post("delete.php", {"form_token": b.token(form2), "student_id": "17"})
    check("a used confirmation token cannot be replayed for another student", count("student_id=17 AND status='active'") == 1)

    print("\n== SQL injection")
    total = count()
    status, _, page = b.get("index.php?" + urllib.parse.urlencode({"q": "' OR '1'='1"}))
    check("search \"' OR '1'='1\" is treated as text -> no results", status == 200 and not table_rows(page))
    _, _, page = b.get("index.php?" + urllib.parse.urlencode({"q": "x%' UNION SELECT 1,2,3,4,5,6,7,8,9 -- "}))
    check("UNION injection in search -> no results, no error", not table_rows(page) and "Student records" in page)
    _, _, page = b.get("index.php?" + urllib.parse.urlencode({"course": "Data Science' OR '1'='1"}))
    check("injection in course filter is ignored (not in the allowed list)", f"of {total} students" in page)
    status, headers, _ = b.get("edit.php?id=1%20OR%201=1")
    check("edit.php?id=1 OR 1=1 -> refused as unknown record", status == 303)
    _, _, form = b.get("delete.php?id=17")
    b.post("delete.php", {"form_token": b.token(form), "student_id": "17 OR 1=1"})
    check("soft delete with student_id '17 OR 1=1' changes nothing", count("status='inactive'") == 4)
    status, _, _ = add_student(b, full_name="O'Brien-Smith", email="o'brien@example.com", course="Data Science", semester="2")
    check("quotes are stored literally (O'Brien-Smith / o'brien@example.com)",
          status == 303 and scalar("SELECT full_name FROM students WHERE email='o''brien@example.com'") == "O'Brien-Smith")
    status, _, page = add_student(b, full_name="Robert'); DROP TABLE students;--", email="bobby@example.com", course="Data Science", semester="2")
    check("'Robert'); DROP TABLE students;--' refused by validation; table intact",
          status == 422 and int(scalar(f"SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='{TEST_DB}' AND TABLE_NAME='students'")) == 1)

    print("\n== XSS output escaping")
    payload = "<script>alert(1)</script>"
    _, _, page = b.get("index.php?" + urllib.parse.urlencode({"q": payload}))
    check("search text is escaped in the input and the summary", payload not in page and "&lt;script&gt;alert(1)&lt;/script&gt;" in page)
    mysql("INSERT INTO students (full_name,email,course,semester) VALUES "
          "('<img src=x onerror=alert(1)>','xss.test@example.com','Data Science',1)")
    xss_id = scalar("SELECT student_id FROM students WHERE email='xss.test@example.com'")
    _, _, page = b.get("index.php?q=xss.test")
    check("stored HTML in a name is escaped in the list", "<img src=x" not in page and "&lt;img src=x onerror=alert(1)&gt;" in page)
    _, _, page = b.get(f"edit.php?id={xss_id}")
    check("stored HTML is escaped in the edit form value", "<img src=x" not in page and 'value="&lt;img src=x onerror=alert(1)&gt;"' in page)
    _, _, page = b.get(f"delete.php?id={xss_id}")
    check("stored HTML is escaped on the confirmation page", "<img src=x" not in page)
    status, _, page = add_student(b, full_name="\"><b>bold</b>", email="\"><script>@x.com", course="Data Science", semester="1")
    check("rejected input is escaped when the form is shown again", status == 422 and "<b>bold</b>" not in page and "&quot;&gt;&lt;b&gt;" in page)

    print("\n== Protected files")
    for path in ["db.php", "includes/functions.php", "config.example.php", "router.php", "studenthub_prac11.sql",
                 "README.md", "tests/test_app.py", ".gitignore", "start-server.bat"]:
        status, _, _ = b.get(path)
        check(f"{path} -> 403", status == 403, str(status))

    print("\n== Server log")
    log = server.logged()
    check("no PHP warnings, notices or errors logged", not re.search(r"PHP (Warning|Notice|Deprecated|Fatal|Parse)", log), log[-400:])


def database_down_checks(log_dir):
    print("\n== MySQL unreachable")
    server = Server(PORT_DOWN, log_dir, {"P11_DB_NAME": TEST_DB, "P11_DB_PORT": "1"})
    try:
        b = Browser(PORT_DOWN)
        status, _, page = b.get("index.php")
        check("index.php -> 503 'The student database is not available right now'",
              status == 503 and "The student database is not available right now" in page)
        check("no technical details in the page", not re.search(r"mysqli|Access denied|127\.0\.0\.1|SQLSTATE|Stack trace|\.php on line", page))
        time.sleep(0.3)
        check("the real error is written to the PHP log", "Practical 11 database connection failed" in server.logged())
    finally:
        server.stop()


def main():
    print(f"StudentHub Practical 11 tests  (PHP: {PHP}, MySQL: {MYSQL})")
    static_checks()
    drop_test_db()
    create_test_db()
    log_dir = tempfile.mkdtemp(prefix="p11-tests-")
    try:
        database_checks()
        server = Server(PORT, log_dir, {"P11_DB_NAME": TEST_DB})
        try:
            app_checks(server)
        finally:
            server.stop()
        database_down_checks(log_dir)
    finally:
        drop_test_db()
        check("test database removed again", not mysql(f"SHOW DATABASES LIKE '{TEST_DB}'", None))
        live = mysql("SELECT COUNT(*) FROM students", "studenthub_prac11")[0][0]
        print(f"(studenthub_prac11 was not used by the tests; it holds {live} records)")
    print(f"\nResult: {passed} passed, {failed} failed, {passed + failed} checks")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
