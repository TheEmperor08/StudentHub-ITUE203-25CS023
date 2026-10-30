"""StudentHub - tests for migration 001 (Practical 8 database foundation). Python 3, standard library only.

    python database\\tests\\test_001_practical8_foundation.py                       # fixture (fictional v1 data)
    python database\\tests\\test_001_practical8_foundation.py --source-dump X.sql   # a mysqldump of studenthub_db
    python database\\tests\\test_001_practical8_foundation.py --verify-live --baseline-dump X.sql

Default / --source-dump: loads the pre-migration database into the disposable database studenthub_mig001_test and checks
the upgrade there - structure, data preservation, e-mail linking, repeated runs, rollback, the precondition stop, the
transactional capacity rule (also with parallel requests), foreign-key delete behaviour, the audit-log fallback and the
existing portal pages (PHP built-in server with DB_NAME pointing at the test copy). It also checks a fresh install from
database/studenthub_demo.sql. Every disposable database carries a marker table and is dropped at the end; the real
studenthub_db is never touched in these modes.

--verify-live: READ-ONLY check of the live studenthub_db after the migration. The baseline dump (taken just before the
migration) is restored into the disposable database to know what the live data must still contain.
"""
import argparse, hashlib, http.cookiejar, json, os, pathlib, re, secrets, subprocess, sys, tempfile, time
import urllib.error, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "database" / "migrations" / "001_practical8_foundation.sql"
ROLLBACK = ROOT / "database" / "migrations" / "001_practical8_foundation.down.sql"
FIXTURE = ROOT / "database" / "tests" / "fixtures" / "studenthub_v1_fixture.sql"
DEMO = ROOT / "database" / "studenthub_demo.sql"
# migrations after 001 (e.g. 002: UNIQUE students.enrollment_no) - studenthub_demo.sql already contains them
LATER_MIGRATIONS = sorted(p for p in (ROOT / "database" / "migrations").glob("0*.sql")
                          if not p.name.endswith(".down.sql") and p.name != "001_practical8_foundation.sql")
APP = ROOT / "studenthub"
HELPER = APP / "includes" / "event_registration.php"
LOGGER = APP / "audit_logger.php"
PHP = r"C:\xampp\php\php.exe" if os.path.exists(r"C:\xampp\php\php.exe") else "php"
MYSQL = r"C:\xampp\mysql\bin\mysql.exe" if os.path.exists(r"C:\xampp\mysql\bin\mysql.exe") else "mysql"
TEST_DB, FRESH_DB, PRE_DB, LIVE_DB = "studenthub_mig001_test", "studenthub_mig001_fresh", "studenthub_mig001_pre", "studenthub_db"
MARKER = "zz_mig001_test_marker"
ORIGINAL_TABLES = ("users", "students", "events", "menu_items", "audit_logs")
PORT = 8711
passed = failed = 0
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def check(name, ok, detail=""):
    global passed, failed
    passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))
    return ok


def info(text):
    print(f"INFO  {text}")


# ---------------------------------------------------------------- MySQL helpers
def mysql(sql, db=None, check_rc=True):
    r = subprocess.run([MYSQL, "-u", "root", "-N", "-B"] + ([db] if db else []), input=sql, capture_output=True,
                       text=True, encoding="utf-8")
    if check_rc and r.returncode:
        raise RuntimeError(r.stderr.strip())
    return [line.split("\t") for line in r.stdout.splitlines()]


def mysql_try(sql, db):
    r = subprocess.run([MYSQL, "-u", "root", "-N", "-B", db], input=sql, capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stderr.strip()


def run_file(path, db):
    text = pathlib.Path(path).read_text(encoding="utf-8")
    r = subprocess.run([MYSQL, "-u", "root", db], input=text, capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stderr.strip()


def scalar(sql, db):
    rows = mysql(sql, db)
    return rows[0][0] if rows else None


def db_exists(name):
    return bool(mysql(f"SHOW DATABASES LIKE '{name}'"))


def create_disposable(name):
    assert name != LIVE_DB
    drop_disposable(name)
    mysql(f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; "
          f"CREATE TABLE `{name}`.`{MARKER}` (id INT) ENGINE=InnoDB;")


def drop_disposable(name):
    assert name != LIVE_DB
    if db_exists(name):
        if not mysql(f"SHOW TABLES FROM `{name}` LIKE '{MARKER}'"):
            raise RuntimeError(f"{name} exists but was not created by these tests - not dropped")
        mysql(f"DROP DATABASE `{name}`")


def load_source(db, dump):
    if dump is None:
        rc, err = run_file(FIXTURE, db)
        assert rc == 0, err
        return
    text = pathlib.Path(dump).read_text(encoding="utf-8")
    text, n1 = re.subn(r"^(CREATE DATABASE .*?)`studenthub_db`", rf"\1`{db}`", text, flags=re.M)
    text, n2 = re.subn(r"^USE `studenthub_db`;", f"USE `{db}`;", text, flags=re.M)
    assert re.search(r"^USE ", text, re.M) is None or n2 == 1, "unexpected USE statements in the dump"
    r = subprocess.run([MYSQL, "-u", "root", db], input=text, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr


# ---------------------------------------------------------------- structure and data snapshots
def structure(db):
    q = lambda sql: mysql(sql.replace("@DB", db))
    s = {}
    s["tables"] = {r[0]: (r[1], r[2]) for r in q(
        "SELECT TABLE_NAME, ENGINE, TABLE_COLLATION FROM information_schema.TABLES WHERE TABLE_SCHEMA='@DB'") if r[0] != MARKER}
    s["columns"] = {(r[0], r[1]): tuple(r[2:]) for r in q(
        "SELECT TABLE_NAME, COLUMN_NAME, ORDINAL_POSITION, COLUMN_TYPE, IS_NULLABLE, IFNULL(COLUMN_DEFAULT,'<NULL>'), EXTRA,"
        " IFNULL(COLLATION_NAME,'-') FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='@DB'") if r[0] != MARKER}
    s["indexes"] = {(r[0], r[1]): (r[2], r[3]) for r in q(
        "SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) FROM information_schema.STATISTICS"
        " WHERE TABLE_SCHEMA='@DB' GROUP BY TABLE_NAME, INDEX_NAME, NON_UNIQUE") if r[0] != MARKER}
    s["fks"] = {(r[0], r[1]): tuple(r[2:]) for r in q(
        "SELECT k.TABLE_NAME, k.CONSTRAINT_NAME, GROUP_CONCAT(k.COLUMN_NAME ORDER BY k.ORDINAL_POSITION), k.REFERENCED_TABLE_NAME,"
        " GROUP_CONCAT(k.REFERENCED_COLUMN_NAME ORDER BY k.ORDINAL_POSITION), r.UPDATE_RULE, r.DELETE_RULE"
        " FROM information_schema.KEY_COLUMN_USAGE k JOIN information_schema.REFERENTIAL_CONSTRAINTS r"
        " ON r.CONSTRAINT_SCHEMA = k.TABLE_SCHEMA AND r.CONSTRAINT_NAME = k.CONSTRAINT_NAME AND r.TABLE_NAME = k.TABLE_NAME"
        " WHERE k.TABLE_SCHEMA='@DB' AND k.REFERENCED_TABLE_NAME IS NOT NULL GROUP BY k.TABLE_NAME, k.CONSTRAINT_NAME, k.REFERENCED_TABLE_NAME,"
        " r.UPDATE_RULE, r.DELETE_RULE")}
    s["checks"] = {(r[0], r[1]): r[2] for r in q(
        "SELECT TABLE_NAME, CONSTRAINT_NAME, CHECK_CLAUSE FROM information_schema.CHECK_CONSTRAINTS WHERE CONSTRAINT_SCHEMA='@DB'")}
    return s


def diff_structure(a, b):
    out = []
    for part in ("tables", "columns", "indexes", "fks", "checks"):
        for k in sorted(set(a[part]) | set(b[part]), key=str):
            if a[part].get(k) != b[part].get(k):
                out.append(f"{part} {k}: {a[part].get(k)} -> {b[part].get(k)}")
    return out


def fingerprints(db, snap):
    """sha256 + row count of the ORIGINAL columns of each original table (as they were before the migration)."""
    fp = {}
    for t in ORIGINAL_TABLES:
        cols = [c for (tbl, c), v in sorted(snap["columns"].items(), key=lambda kv: int(kv[1][0])) if tbl == t]
        rows = mysql(f"SELECT {', '.join('`' + c + '`' for c in cols)} FROM `{t}` ORDER BY id", db)
        fp[t] = (len(rows), hashlib.sha256("\n".join("\t".join(r) for r in rows).encode()).hexdigest())
    return fp


def expected_links(db):
    """Independent re-implementation of the linking rule from the pre-migration data."""
    users = mysql("SELECT id, email, role FROM users", db)
    students = mysql("SELECT id, email FROM students", db)
    norm = lambda e: e.strip(" ").lower()
    by_email_users, by_email_students = {}, {}
    for uid, email, role in users:
        by_email_users.setdefault(norm(email), []).append((int(uid), role))
    for sid, email in students:
        by_email_students.setdefault(norm(email), []).append(int(sid))
    links = {}
    for email, us in by_email_users.items():
        ss = by_email_students.get(email, [])
        if len(us) == 1 and us[0][1] == "student" and len(ss) == 1:
            links[ss[0]] = us[0][0]
    return links


def actual_links(db):
    return {int(r[0]): int(r[1]) for r in mysql("SELECT id, user_id FROM students WHERE user_id IS NOT NULL", db)}


# ---------------------------------------------------------------- expected structure of migration 001
def check_migrated_structure(db, label):
    s = structure(db)
    col = lambda t, c: s["columns"].get((t, c))
    check(f"{label}: students.user_id int(11) NULL, placed after id",
          col("students", "user_id") is not None and col("students", "user_id")[0:3] == ("2", "int(11)", "YES"), str(col("students", "user_id")))
    check(f"{label}: UNIQUE uq_students_user_id (one account per student record)", s["indexes"].get(("students", "uq_students_user_id")) == ("0", "user_id"))
    check(f"{label}: fk_students_user -> users.id ON DELETE SET NULL, ON UPDATE CASCADE",
          s["fks"].get(("students", "fk_students_user")) == ("user_id", "users", "id", "CASCADE", "SET NULL"), str(s["fks"].get(("students", "fk_students_user"))))
    check(f"{label}: CHECK chk_students_semester (NULL or 1-8)", "between 1 and 8" in s["checks"].get(("students", "chk_students_semester"), ""))
    # migration 001 adds no index on enrollment_no; migration 002 (if recorded in this database) adds exactly its UNIQUE one
    allowed = {"uq_students_enrollment_no"} if scalar("SELECT COUNT(*) FROM schema_migrations WHERE version='002'", db) == "1" else set()
    check(f"{label}: students.enrollment_no unchanged (varchar(20) NULL, no index added by 001)",
          col("students", "enrollment_no")[1:3] == ("varchar(20)", "YES")
          and {i for (t, i), v in s["indexes"].items() if t == "students" and v[1] == "enrollment_no"} == allowed)
    check(f"{label}: students.semester keeps int(11) NULL DEFAULT 3", col("students", "semester")[1:4] == ("int(11)", "YES", "3"))
    check(f"{label}: events.event_time TIME NULL after event_date", col("events", "event_time") is not None and col("events", "event_time")[0:3] == ("4", "time", "YES"))
    check(f"{label}: events.capacity SMALLINT UNSIGNED NULL", col("events", "capacity") is not None and col("events", "capacity")[1:3] == ("smallint(5) unsigned", "YES"))
    check(f"{label}: CHECK chk_events_capacity (NULL or > 0)", "> 0" in s["checks"].get(("events", "chk_events_capacity"), ""))
    check(f"{label}: events.location unchanged (varchar(150) NOT NULL)", col("events", "location")[1:3] == ("varchar(150)", "NO"))
    check(f"{label}: index idx_events_date (event_date, event_time)", s["indexes"].get(("events", "idx_events_date")) == ("1", "event_date,event_time"))
    reg = {c: v for (t, c), v in s["columns"].items() if t == "registrations"}
    check(f"{label}: registrations columns and signed INT(11) keys",
          [(c, reg[c][1]) for c in sorted(reg, key=lambda c: int(reg[c][0]))] == [
              ("registration_id", "int(11)"), ("student_id", "int(11)"), ("event_id", "int(11)"), ("registered_at", "datetime"),
              ("status", "enum('registered','attended','cancelled')")], str(reg))
    check(f"{label}: registrations PK, UNIQUE (student_id, event_id), index on event_id",
          s["indexes"].get(("registrations", "PRIMARY")) == ("0", "registration_id")
          and s["indexes"].get(("registrations", "uq_registrations_student_event")) == ("0", "student_id,event_id")
          and s["indexes"].get(("registrations", "idx_registrations_event")) == ("1", "event_id"))
    check(f"{label}: registrations FKs to students.id and events.id, ON DELETE/UPDATE CASCADE",
          s["fks"].get(("registrations", "fk_registrations_student")) == ("student_id", "students", "id", "CASCADE", "CASCADE")
          and s["fks"].get(("registrations", "fk_registrations_event")) == ("event_id", "events", "id", "CASCADE", "CASCADE"))
    check(f"{label}: fk_audit_logs_user -> users.id ON DELETE SET NULL (audit_logs.user_id stays nullable)",
          s["fks"].get(("audit_logs", "fk_audit_logs_user")) == ("user_id", "users", "id", "CASCADE", "SET NULL") and col("audit_logs", "user_id")[2] == "YES")
    mismatched = [k for k, v in s["fks"].items()
                  if col(k[0], v[0])[1] != col(v[1], v[2])[1]]
    check(f"{label}: every foreign-key column has exactly the type of the key it references", not mismatched, str(mismatched))
    check(f"{label}: all original tables still exist (users, students, events, menu_items, audit_logs)", all(t in s["tables"] for t in ORIGINAL_TABLES))
    check(f"{label}: all tables InnoDB / utf8mb4_unicode_ci", all(v == ("InnoDB", "utf8mb4_unicode_ci") for v in s["tables"].values()), str(s["tables"]))
    check(f"{label}: schema_migrations records version 001 once", scalar("SELECT COUNT(*) FROM schema_migrations WHERE version='001'", db) == "1")
    return s


# ---------------------------------------------------------------- PHP helpers (registration and audit logger)
PHP_DRIVER = r"""<?php
mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);
require $argv[1];
require $argv[2];
$db = new mysqli('127.0.0.1', 'root', '', $argv[3]);
$db->set_charset('utf8mb4');
$cmd = $argv[4];
if ($cmd === 'register') {
    if (isset($argv[7])) { while (microtime(true) < (float) $argv[7]) { usleep(500); } }   // start barrier
    try {
        echo json_encode(['ok' => true, 'id' => register_student_for_event($db, (int) $argv[5], (int) $argv[6])]);
    } catch (EventRegistrationException $e) {
        echo json_encode(['ok' => false, 'reason' => $e->reason]);
    }
} elseif ($cmd === 'audit') {
    log_audit($db, $argv[5] === 'null' ? null : (int) $argv[5], $argv[6], $argv[7], 'test entry', 'SUCCESS');
    echo json_encode(['ok' => true, 'id' => $db->insert_id]);
}
"""


class PhpDriver:
    def __init__(self, workdir, db):
        self.path = pathlib.Path(workdir) / "driver.php"
        self.path.write_text(PHP_DRIVER, encoding="utf-8")
        self.db = db

    def args(self, *extra):
        return [PHP, str(self.path), str(HELPER), str(LOGGER), self.db, *map(str, extra)]

    def run(self, *extra):
        r = subprocess.run(self.args(*extra), capture_output=True, text=True)
        try:
            return json.loads(r.stdout)
        except ValueError:
            return {"ok": False, "reason": "php-error", "stderr": (r.stdout + r.stderr)[-300:]}

    def register(self, student, event):
        return self.run("register", student, event)


# ---------------------------------------------------------------- portal (HTTP)
class Browser:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def token(self, path):
        _, _, page = self.get(path)
        m = re.search(r'name="csrf_token" value="([0-9a-f]{64})"', page)
        return m.group(1) if m else ""

    def get(self, path, data=None):
        body = urllib.parse.urlencode(data).encode() if data is not None else None
        try:
            with self.opener.open(f"http://127.0.0.1:{PORT}/{path}", data=body, timeout=30) as r:
                return r.status, r.geturl(), r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.geturl(), e.read().decode("utf-8", "replace")


PHP_PROBLEMS = re.compile(r"(Fatal error|Warning|Notice|Deprecated|Parse error)(</b>)?: .{0,400}? on line|Uncaught |Stack trace:", re.S)


def start_portal(db, log_dir):
    env = dict(os.environ, DB_NAME=db)
    log = pathlib.Path(log_dir) / "portal-php.log"
    out = open(pathlib.Path(log_dir) / "portal-server.txt", "w")
    proc = subprocess.Popen([PHP, "-d", f"error_log={log}", "-d", "log_errors=1", "-S", f"127.0.0.1:{PORT}"], cwd=APP,
                            env=env, stdout=out, stderr=subprocess.STDOUT)
    for _ in range(50):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/login.php", timeout=2)
            break
        except Exception:
            time.sleep(0.2)
    return proc, out, log


def create_account(db, username, email, role, password):
    r = subprocess.run([PHP, "tools/create_demo_user.php", f"--db={db}", f"--username={username}", f"--email={email}", f"--role={role}"],
                       input=password + "\n", cwd=ROOT, capture_output=True, text=True)
    return r.returncode == 0


# ================================================================ test sections
def upgrade_tests(dump, workdir):
    print("\n== Load the pre-migration database into " + TEST_DB)
    create_disposable(TEST_DB)
    load_source(TEST_DB, dump)
    before = structure(TEST_DB)
    check("source has the pre-migration structure (no students.user_id, no registrations table)",
          ("students", "user_id") not in before["columns"] and "registrations" not in before["tables"])
    fp_before = fingerprints(TEST_DB, before)
    expected = expected_links(TEST_DB)
    counts = {t: fp_before[t][0] for t in ORIGINAL_TABLES}
    info(f"rows before: {counts}")

    print("\n== Apply migration 001")
    rc, err = run_file(MIGRATION, TEST_DB)
    check("migration runs without error", rc == 0, err)
    after = check_migrated_structure(TEST_DB, "after migration")
    check("all original rows and values unchanged (sha256 of every original column, incl. password hashes)",
          fingerprints(TEST_DB, before) == fp_before, str(fingerprints(TEST_DB, before)))
    check("registrations starts empty (no data invented)", scalar("SELECT COUNT(*) FROM registrations", TEST_DB) == "0")
    check("existing events get capacity NULL and event_time NULL (nothing invented)",
          scalar("SELECT COUNT(*) FROM events WHERE capacity IS NOT NULL OR event_time IS NOT NULL", TEST_DB) == "0")

    print("\n== Linking students to accounts")
    links = actual_links(TEST_DB)
    check(f"students linked only through unique, verified e-mail matches with a student account ({len(expected)} expected)",
          links == expected, f"actual {links} expected {expected}")
    check("no student record linked to an admin or editor account",
          scalar("SELECT COUNT(*) FROM students s JOIN users u ON u.id = s.user_id WHERE u.role <> 'student'", TEST_DB) == "0")
    unmatched = int(scalar("SELECT COUNT(*) FROM students WHERE user_id IS NULL", TEST_DB))
    orphan_accounts = int(scalar("SELECT COUNT(*) FROM users u LEFT JOIN students s ON s.user_id = u.id WHERE u.role='student' AND s.id IS NULL", TEST_DB))
    check("unmatched student records are kept (user_id NULL) and no account was created",
          int(scalar("SELECT COUNT(*) FROM students", TEST_DB)) == counts["students"] and int(scalar("SELECT COUNT(*) FROM users", TEST_DB)) == counts["users"])
    info(f"linked {len(links)}, student records without account {unmatched}, student accounts without linked record {orphan_accounts}")
    roles = mysql("SELECT role, COUNT(*) FROM users GROUP BY role ORDER BY role", TEST_DB)
    info(f"roles unchanged and distinct: {roles}")

    print("\n== Running the migration again")
    rc, err = run_file(MIGRATION, TEST_DB)
    check("second run exits without error", rc == 0, err)
    check("second run leaves the structure identical", not diff_structure(after, structure(TEST_DB)), "; ".join(diff_structure(after, structure(TEST_DB))[:3]))
    check("second run leaves all data and links identical", fingerprints(TEST_DB, before) == fp_before and actual_links(TEST_DB) == links)

    print("\n== Rollback (down script) and re-apply")
    rc, err = run_file(ROLLBACK, TEST_DB)
    check("rollback runs without error", rc == 0, err)
    d = diff_structure(before, structure(TEST_DB))
    check("after rollback the structure is exactly the pre-migration structure", not d, "; ".join(d[:4]))
    check("after rollback all original data is unchanged", fingerprints(TEST_DB, before) == fp_before)
    rc, err = run_file(ROLLBACK, TEST_DB)
    check("rollback can run twice", rc == 0 and not diff_structure(before, structure(TEST_DB)), err)
    rc, err = run_file(MIGRATION, TEST_DB)
    check("migration re-applies cleanly after rollback (same structure, same links)",
          rc == 0 and not diff_structure(after, structure(TEST_DB)) and actual_links(TEST_DB) == expected, err)
    return before, after, fp_before


def precondition_tests():
    print("\n== Precondition stop (nothing changes when the data is not ready)")
    create_disposable(PRE_DB)
    rc, err = run_file(FIXTURE, PRE_DB)
    assert rc == 0, err
    mysql("INSERT INTO audit_logs (user_id, username, action, ip_address) VALUES (999, 'deleted_user', 'USER_LOGIN', '127.0.0.1')", PRE_DB)
    s0 = structure(PRE_DB)
    rc, err = run_file(MIGRATION, PRE_DB)
    check("audit_logs with user_id of a deleted account -> migration stops with a clear message", rc != 0 and "deleted accounts" in err, err)
    check("... and the database structure is unchanged", not diff_structure(s0, structure(PRE_DB)))
    mysql("DELETE FROM audit_logs WHERE user_id = 999; UPDATE students SET semester = 9 WHERE id = 4", PRE_DB)
    rc, err = run_file(MIGRATION, PRE_DB)
    check("a semester outside 1-8 -> migration stops, structure unchanged", rc != 0 and "outside 1-8" in err and not diff_structure(s0, structure(PRE_DB)), err)
    mysql("UPDATE students SET semester = 1 WHERE id = 4", PRE_DB)
    rc, err = run_file(DEMO, PRE_DB)
    check("importing studenthub_demo.sql into a pre-migration database is refused (points to the migration)",
          rc != 0 and "before migration 001" in err and not diff_structure(s0, structure(PRE_DB)), err)
    rc, err = subprocess.run([MYSQL, "-u", "root"], input=MIGRATION.read_text(encoding="utf-8"), capture_output=True, text=True).returncode, ""
    check("running the migration without selecting a database fails safely", rc != 0)
    drop_disposable(PRE_DB)


def behaviour_tests(workdir):
    print("\n== Registrations: transactional capacity rule (disposable test records)")
    db = TEST_DB
    mysql("""
        INSERT INTO users (username, email, password, role) VALUES ('mig001_linked', 'mig001.linked@example.com', 'placeholder-not-a-password-hash', 'student');
        INSERT INTO students (user_id, enrollment_no, name, email, course, gender, semester, status) VALUES
          (LAST_INSERT_ID(), 'MIGT001', 'Mig Test 1', 'mig001.t1@example.com', 'Computer Science', 'Female', 3, 'Active');
        INSERT INTO students (enrollment_no, name, email, course, gender, semester, status) VALUES
          ('MIGT002', 'Mig Test 2', 'mig001.t2@example.com', 'Computer Science', 'Male', 3, 'Active'),
          ('MIGT003', 'Mig Test 3', 'mig001.t3@example.com', 'Data Science', 'Female', 5, 'Active'),
          ('MIGT004', 'Mig Test 4', 'mig001.t4@example.com', 'Data Science', 'Male', 5, 'Inactive');
        INSERT INTO events (title, event_date, event_time, location, capacity, category) VALUES
          ('Mig Test Capacity 2', '2027-01-10', '10:00:00', 'Test Hall', 2, 'Workshop'),
          ('Mig Test Unlimited', '2027-01-11', NULL, 'Test Hall', NULL, 'Seminar'),
          ('Mig Test Parallel 3', '2027-01-12', '09:00:00', 'Test Hall', 3, 'Hackathon');
    """, db)
    sid = {n: int(scalar(f"SELECT id FROM students WHERE enrollment_no='MIGT00{n}'", db)) for n in (1, 2, 3, 4)}
    eid = {k: int(scalar(f"SELECT id FROM events WHERE title='{t}'", db)) for k, t in
           (("cap2", "Mig Test Capacity 2"), ("unl", "Mig Test Unlimited"), ("par", "Mig Test Parallel 3"))}
    php = PhpDriver(workdir, db)

    r1 = php.register(sid[1], eid["cap2"])
    check("register student 1 for the capacity-2 event -> registration id", r1.get("ok") and r1["id"] > 0, str(r1))
    check("... stored with status 'registered'", scalar(f"SELECT status FROM registrations WHERE registration_id={r1.get('id', 0)}", db) == "registered")
    r = php.register(sid[1], eid["cap2"])
    check("registering the same student again -> 'duplicate'", r == {"ok": False, "reason": "duplicate"}, str(r))
    rc, err = mysql_try(f"INSERT INTO registrations (student_id, event_id) VALUES ({sid[1]}, {eid['cap2']})", db)
    check("the database itself refuses a duplicate (UNIQUE student_id, event_id)", rc != 0 and "uq_registrations_student_event" in err, err)
    r2 = php.register(sid[2], eid["cap2"])
    r3 = php.register(sid[3], eid["cap2"])
    check("second student fits, third student -> 'event_full' (capacity 2)", r2.get("ok") and r3 == {"ok": False, "reason": "event_full"}, f"{r2} {r3}")
    check("seats taken = capacity (no overbooking)", scalar(f"SELECT COUNT(*) FROM registrations WHERE event_id={eid['cap2']} AND status<>'cancelled'", db) == "2")
    mysql(f"UPDATE registrations SET status='cancelled' WHERE registration_id={r2['id']}", db)
    r3b = php.register(sid[3], eid["cap2"])
    check("a cancelled registration frees its seat -> third student now fits", r3b.get("ok"), str(r3b))
    r2b = php.register(sid[2], eid["cap2"])
    check("the cancelled student cannot re-register while the event is full", r2b == {"ok": False, "reason": "event_full"}, str(r2b))
    mysql(f"UPDATE registrations SET status='cancelled' WHERE registration_id={r3b['id']}", db)
    r2c = php.register(sid[2], eid["cap2"])
    check("re-registering a cancelled registration reactivates the same row (no duplicate row)",
          r2c.get("ok") and r2c["id"] == r2["id"] and scalar(f"SELECT COUNT(*) FROM registrations WHERE student_id={sid[2]} AND event_id={eid['cap2']}", db) == "1", str(r2c))
    oks = [php.register(sid[n], eid["unl"]).get("ok") for n in (1, 2, 3)]
    check("capacity NULL (legacy / not set) = no limit", all(oks), str(oks))
    r = php.register(sid[4], eid["unl"])
    check("an Inactive student cannot register -> 'student_inactive'", r == {"ok": False, "reason": "student_inactive"}, str(r))
    r = php.register(999999, eid["unl"])
    r_e = php.register(sid[1], 999999)
    check("unknown student / unknown event -> 'student_not_found' / 'event_not_found'",
          r == {"ok": False, "reason": "student_not_found"} and r_e == {"ok": False, "reason": "event_not_found"}, f"{r} {r_e}")

    print("\n== Parallel registrations (8 processes, capacity 3)")
    mysql("INSERT INTO students (enrollment_no, name, email, course, gender, semester, status) VALUES " + ", ".join(
        f"('MIGP{i:03d}', 'Parallel {i}', 'mig001.p{i}@example.com', 'Computer Science', 'Male', 3, 'Active')" for i in range(1, 9)), db)
    pids = [int(r[0]) for r in mysql("SELECT id FROM students WHERE enrollment_no LIKE 'MIGP%' ORDER BY id", db)]
    barrier = f"{time.time() + 2.0:.3f}"
    procs = [subprocess.Popen(php.args("register", p, eid["par"], barrier), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for p in pids]
    results = []
    for p in procs:
        out, err = p.communicate(timeout=60)
        try:
            results.append(json.loads(out))
        except ValueError:
            results.append({"ok": False, "reason": "php-error", "stderr": (out + err)[-200:]})
    ok_count = sum(1 for r in results if r.get("ok"))
    full_count = sum(1 for r in results if r.get("reason") == "event_full")
    check("exactly 3 of 8 simultaneous registrations succeed, 5 get 'event_full'", ok_count == 3 and full_count == 5, str(results))
    check("the event has exactly 3 registrations afterwards", scalar(f"SELECT COUNT(*) FROM registrations WHERE event_id={eid['par']}", db) == "3")

    print("\n== CHECK constraints")
    rc, err = mysql_try("INSERT INTO events (title, event_date, location, capacity, category) VALUES ('Bad', '2027-01-01', 'X', 0, 'Workshop')", db)
    check("capacity 0 is refused (chk_events_capacity)", rc != 0 and "chk_events_capacity" in err, err)
    rc, err = mysql_try(f"UPDATE students SET semester = 9 WHERE id = {sid[2]}", db)
    check("semester 9 is refused (chk_students_semester)", rc != 0 and "chk_students_semester" in err, err)
    rc, err = mysql_try(f"UPDATE students SET semester = 0 WHERE id = {sid[2]}", db)
    check("semester 0 is refused", rc != 0 and "chk_students_semester" in err, err)
    rc, err = mysql_try(f"UPDATE students SET semester = NULL WHERE id = {sid[2]}; UPDATE students SET semester = 8 WHERE id = {sid[2]}", db)
    check("semester NULL (legacy) and 8 are accepted", rc == 0, err)

    print("\n== Foreign keys and delete behaviour")
    rc, err = mysql_try(f"INSERT INTO registrations (student_id, event_id) VALUES (999999, {eid['unl']})", db)
    rc2, err2 = mysql_try(f"INSERT INTO registrations (student_id, event_id) VALUES ({sid[1]}, 999999)", db)
    check("a registration for a missing student or event is refused (fk_registrations_*)",
          rc != 0 and "fk_registrations_student" in err and rc2 != 0 and "fk_registrations_event" in err2, err + " | " + err2)
    rc, err = mysql_try("INSERT INTO audit_logs (user_id, username, action, ip_address) VALUES (999999, 'ghost', 'X', '127.0.0.1')", db)
    check("an audit row for a missing account is refused by the database (fk_audit_logs_user)", rc != 0 and "fk_audit_logs_user" in err, err)
    rc, err = mysql_try(f"UPDATE students SET user_id = 999999 WHERE id = {sid[2]}", db)
    check("a student cannot be linked to a missing account (fk_students_user)", rc != 0 and "fk_students_user" in err, err)
    linked_uid = int(scalar(f"SELECT user_id FROM students WHERE id={sid[1]}", db))
    rc, err = mysql_try(f"UPDATE students SET user_id = {linked_uid} WHERE id = {sid[2]}", db)
    check("one account cannot be linked to two student records (uq_students_user_id)", rc != 0 and "uq_students_user_id" in err, err)
    regs_unl = int(scalar(f"SELECT COUNT(*) FROM registrations WHERE event_id={eid['unl']}", db))
    mysql(f"DELETE FROM events WHERE id={eid['unl']}", db)
    check(f"deleting an event deletes its {regs_unl} registrations (ON DELETE CASCADE)",
          regs_unl == 3 and scalar(f"SELECT COUNT(*) FROM registrations WHERE event_id={eid['unl']}", db) == "0")
    regs_s3 = int(scalar(f"SELECT COUNT(*) FROM registrations WHERE student_id={sid[3]}", db))
    mysql(f"DELETE FROM students WHERE id={sid[3]}", db)
    check("deleting a student deletes that student's registrations (ON DELETE CASCADE)",
          regs_s3 >= 1 and scalar(f"SELECT COUNT(*) FROM registrations WHERE student_id={sid[3]}", db) == "0")
    php.run("audit", linked_uid, "mig001_linked", "TEST_LINKED")
    check("audit entry for an existing account keeps its user_id", scalar(f"SELECT COUNT(*) FROM audit_logs WHERE action='TEST_LINKED' AND user_id={linked_uid}", db) == "1")
    mysql(f"DELETE FROM users WHERE id={linked_uid}", db)
    check("deleting a linked account keeps the student record and sets students.user_id to NULL (ON DELETE SET NULL)",
          scalar(f"SELECT IFNULL(user_id, 'NULL') FROM students WHERE id={sid[1]}", db) == "NULL")
    check("... and keeps its audit entries with the username, user_id set to NULL",
          scalar("SELECT CONCAT(IFNULL(user_id,'NULL'),'|',username) FROM audit_logs WHERE action='TEST_LINKED'", db) == "NULL|mig001_linked")
    check("... and the student's registrations are kept", scalar(f"SELECT COUNT(*) FROM registrations WHERE student_id={sid[1]}", db) != "0")
    r = php.run("audit", linked_uid, "mig001_linked", "TEST_STALE_SESSION")
    check("log_audit() with the id of a deleted account (stale session) stores the entry with user_id NULL instead of failing",
          r.get("ok") and scalar("SELECT CONCAT(IFNULL(user_id,'NULL'),'|',username) FROM audit_logs WHERE action='TEST_STALE_SESSION'", db) == "NULL|mig001_linked", str(r))
    r = php.run("audit", "null", "anonymous", "TEST_ANONYMOUS")
    check("log_audit() for an anonymous action (user_id NULL) still works", r.get("ok") and scalar("SELECT IFNULL(user_id,'NULL') FROM audit_logs WHERE action='TEST_ANONYMOUS'", db) == "NULL")


def portal_tests(workdir):
    print("\n== Existing portal pages against the migrated copy (PHP built-in server, DB_NAME=" + TEST_DB + ")")
    admin_pw, student_pw = secrets.token_urlsafe(12), secrets.token_urlsafe(12)
    ok = create_account(TEST_DB, "mig001_admin", "mig001.admin@example.com", "admin", admin_pw) and \
        create_account(TEST_DB, "mig001_student", "mig001.student@example.com", "student", student_pw)
    check("tools/create_demo_user.php still creates accounts after the migration", ok)
    proc, out, log = start_portal(TEST_DB, workdir)
    try:
        b = Browser()
        status, url, page = b.get("login.php", {"login_input": "mig001_admin", "password": admin_pw, "csrf_token": b.token("login.php")})
        check("admin login -> Admin Console", status == 200 and "admin_dashboard.php" in url, f"{status} {url}")
        problems = []
        for tab in ("overview", "students", "events", "users", "audits"):
            status, _, page = b.get(f"admin_dashboard.php?tab={tab}")
            if status != 200 or PHP_PROBLEMS.search(page):
                problems.append(f"{tab}:{status}")
        check("Admin Console tabs load (overview, students, events, users, audits)", not problems, str(problems))
        token = b.token("admin_dashboard.php")
        status, _, page = b.get("admin_dashboard.php", {"csrf_token": token, "action": "add_student", "enrollment_no": "26CS950", "name": "Web Added", "email": "mig001.web@example.com",
                                                        "course": "Computer Science", "semester": "4", "gender": "Female"})
        check("admin 'add student' still works (row stored with semester 4, user_id NULL)",
              scalar("SELECT CONCAT(semester,'|',IFNULL(user_id,'NULL')) FROM students WHERE email='mig001.web@example.com'", TEST_DB) == "4|NULL")
        status, _, page = b.get("admin_dashboard.php", {"csrf_token": token, "action": "add_event", "title": "Web Added Event", "category": "Workshop",
                                                        "event_date": "2027-02-01", "location": "Lab 1", "description": "added by the test"})
        new_event = scalar("SELECT id FROM events WHERE title='Web Added Event'", TEST_DB)
        check("admin 'add event' still works (capacity and time stay NULL)",
              new_event is not None and scalar(f"SELECT CONCAT(IFNULL(capacity,'NULL'),'|',IFNULL(event_time,'NULL')) FROM events WHERE id={new_event}", TEST_DB) == "NULL|NULL")
        web_student = scalar("SELECT id FROM students WHERE email='mig001.web@example.com'", TEST_DB)
        reg = PhpDriver(workdir, TEST_DB).register(web_student, new_event)
        had_registration = reg.get("ok") and scalar(f"SELECT COUNT(*) FROM registrations WHERE event_id={new_event}", TEST_DB) == "1"
        b.get("admin_dashboard.php", {"csrf_token": token, "action": "delete_event", "id": new_event})
        check("admin 'delete event' refuses an event with registrations (Practical 12: the registration history is kept)",
              had_registration and scalar(f"SELECT COUNT(*) FROM events WHERE id={new_event}", TEST_DB) == "1"
              and scalar(f"SELECT COUNT(*) FROM registrations WHERE event_id={new_event}", TEST_DB) == "1", str(reg))
        b.get("admin_dashboard.php", {"csrf_token": token, "action": "add_event", "title": "Web Added Event 2", "category": "Workshop",
                                      "event_date": "2027-02-02", "location": "Lab 2", "description": ""})
        other_event = scalar("SELECT id FROM events WHERE title='Web Added Event 2'", TEST_DB)
        b.get("admin_dashboard.php", {"csrf_token": token, "action": "delete_event", "id": other_event})
        check("admin 'delete event' still deletes an event without registrations",
              other_event is not None and scalar(f"SELECT COUNT(*) FROM events WHERE id={other_event}", TEST_DB) == "0")
        b.get("admin_dashboard.php", {"csrf_token": token, "action": "deactivate_student", "id": web_student})
        check("admin 'deactivate student' (Practical 11 soft delete) keeps the record and marks it Inactive",
              scalar(f"SELECT status FROM students WHERE id={web_student}", TEST_DB) == "Inactive")
        b.get("logout.php", {"csrf_token": token})

        s = Browser()
        status, url, page = s.get("login.php", {"login_input": "mig001.student@example.com", "password": student_pw, "csrf_token": s.token("login.php")})
        check("student login -> dashboard", status == 200 and "dashboard.php" in url, f"{status} {url}")
        problems = []
        for p in ("dashboard.php", "student_dashboard.php", "profile.php", "courses.php", "attendance.php", "assignments.php",
                  "results.php", "achievements.php", "notifications.php", "directory.php", "contact.php", "index.php"):
            status, _, page = s.get(p)
            if status != 200 or PHP_PROBLEMS.search(page):
                problems.append(f"{p}:{status}")
        check("all student pages load with status 200 and no PHP errors", not problems, str(problems))
        status, _, page = s.get("admin_dashboard.php")
        check("a student opening the Admin Console still gets the 403 page", status == 403 or "403" in page, str(status))
        s.get("logout.php", {"csrf_token": s.token("dashboard.php")})

        r = Browser()
        _, _, reg_page = r.get("register.php")
        year = re.search(r'<option value="(\d{4})" selected', reg_page).group(1)
        status, url, page = r.get("register.php", {"name": "Reg Test", "username": "mig001_reg", "email": "mig001.reg@example.com", "gender": "Female",
                                                   "course": "Data Science", "adm_year": year, "password": "RegTest#2026", "confirm_password": "RegTest#2026",
                                                   "agree": "1", "csrf_token": r.token("register.php")})
        row = mysql("SELECT u.role, s.semester, s.user_id = u.id FROM users u JOIN students s ON s.email = u.email WHERE u.email='mig001.reg@example.com'", TEST_DB)
        check("self-registration creates the account and its student record, linked through students.user_id (Practical 9)",
              bool(row) and row[0][0] == "student" and row[0][2] == "1" and 1 <= int(row[0][1]) <= 8, str(row))
        log_text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
        check("no PHP warnings or errors in the server log", not re.search(r"PHP (Warning|Notice|Deprecated|Fatal|Parse)", log_text), log_text[-300:])
    finally:
        proc.terminate()
        proc.wait(10)
        out.close()


def fresh_install_tests(migrated):
    print("\n== Fresh install from database/studenthub_demo.sql")
    # the demo file also contains the later migrations: bring the upgraded copy to the same version before comparing
    for later in LATER_MIGRATIONS:
        rc, err = run_file(later, TEST_DB)
        assert rc == 0, f"{later.name}: {err}"
    if LATER_MIGRATIONS:
        info("upgraded copy compared after the later migrations: " + ", ".join(p.name for p in LATER_MIGRATIONS))
        migrated = structure(TEST_DB)
    create_disposable(FRESH_DB)
    rc, err = run_file(DEMO, FRESH_DB)
    check("studenthub_demo.sql imports into an empty database", rc == 0, err)
    fresh = structure(FRESH_DB)
    d = diff_structure(migrated, fresh)
    check("fresh-install structure is identical to an upgraded database", not d, "; ".join(d[:4]))
    snap = {t: mysql(f"SELECT * FROM `{t}` ORDER BY 1", FRESH_DB) for t in fresh["tables"]}
    rc, err = run_file(MIGRATION, FRESH_DB)
    check("migration 001 on a fresh install changes nothing", rc == 0 and not diff_structure(fresh, structure(FRESH_DB))
          and {t: mysql(f"SELECT * FROM `{t}` ORDER BY 1", FRESH_DB) for t in fresh["tables"]} == snap, err)
    rc, err = run_file(DEMO, FRESH_DB)
    check("studenthub_demo.sql can be imported again without changes", rc == 0 and not diff_structure(fresh, structure(FRESH_DB)), err)
    drop_disposable(FRESH_DB)


def verify_live(baseline):
    print(f"\n== READ-ONLY verification of the live database {LIVE_DB} against the baseline dump")
    create_disposable(TEST_DB)
    load_source(TEST_DB, baseline)
    before = structure(TEST_DB)
    fp_before = fingerprints(TEST_DB, before)
    expected = expected_links(TEST_DB)
    rc, err = run_file(MIGRATION, TEST_DB)
    assert rc == 0, err
    applied = {r[0] for r in mysql("SELECT version FROM schema_migrations", LIVE_DB)}
    for later in LATER_MIGRATIONS:                       # later migrations that the live database has as well
        if later.name[:3] in applied:
            rc, err = run_file(later, TEST_DB)
            assert rc == 0, f"{later.name}: {err}"
    reference = structure(TEST_DB)
    live = check_migrated_structure(LIVE_DB, "live")
    d = diff_structure(reference, live)
    check("live structure is identical to the baseline migrated in the test copy", not d, "; ".join(d[:4]))
    fp_live = fingerprints(LIVE_DB, before)
    fp_expected = fingerprints(TEST_DB, before)        # the baseline after the same migrations (e.g. 004 corrects the menu)
    check("every original row and value of the live database equals the migrated baseline (incl. password hashes)", fp_live == fp_expected,
          str({t: (fp_expected[t][0], fp_live[t][0]) for t in ORIGINAL_TABLES if fp_live[t] != fp_expected[t]}))
    check(f"live links equal the verified e-mail matches ({len(expected)})", actual_links(LIVE_DB) == expected, f"{actual_links(LIVE_DB)} vs {expected}")
    check("live registrations table is empty, event capacity/time NULL", scalar("SELECT COUNT(*) FROM registrations", LIVE_DB) == "0"
          and scalar("SELECT COUNT(*) FROM events WHERE capacity IS NOT NULL OR event_time IS NOT NULL", LIVE_DB) == "0")
    info("live rows: " + ", ".join(f"{t} {fp_live[t][0]}" for t in ORIGINAL_TABLES))
    drop_disposable(TEST_DB)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dump")
    ap.add_argument("--verify-live", action="store_true")
    ap.add_argument("--baseline-dump")
    a = ap.parse_args()
    print(f"StudentHub migration 001 tests (PHP {PHP}, MySQL {MYSQL})")
    workdir = tempfile.mkdtemp(prefix="mig001-")
    try:
        if a.verify_live:
            if not a.baseline_dump:
                sys.exit("--verify-live needs --baseline-dump")
            verify_live(a.baseline_dump)
        else:
            info("source: " + (a.source_dump and "dump " + pathlib.Path(a.source_dump).name or "fixture " + FIXTURE.name))
            before, migrated, _ = upgrade_tests(a.source_dump, workdir)
            precondition_tests()
            # the registration helper and the portal use the current schema (e.g. events.status from migration 003)
            for later in LATER_MIGRATIONS:
                rc, err = run_file(later, TEST_DB)
                assert rc == 0, f"{later.name}: {err}"
            info("behaviour and portal tests run after the later migrations: " + ", ".join(p.name for p in LATER_MIGRATIONS))
            behaviour_tests(workdir)
            portal_tests(workdir)
            fresh_install_tests(migrated)
    finally:
        for name in (TEST_DB, FRESH_DB, PRE_DB):
            drop_disposable(name)
        check("all disposable databases removed", not any(db_exists(n) for n in (TEST_DB, FRESH_DB, PRE_DB)))
    print(f"\nResult: {passed} passed, {failed} failed, {passed + failed} checks")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
