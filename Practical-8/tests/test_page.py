"""StudentHub – Practical 8: automated tests (Python 3, standard library only).

Run from the Practical-8 folder:  python tests\\test_page.py
  1. php -l on every PHP file
  2. tests/test_db.php (schema, keys, constraints, seed data, prepared statements, procedures)
  3. test_connection.php through XAMPP's PHP built-in server (records, prepared-statement filter, blocked files)
  4. error handling: servers started with a wrong database name, password, port and a database without the
     tables must answer with a general message only; the real error must go to the PHP error log.
MySQL must be running and schema.sql imported. Nothing in the database is changed.
"""
import os, pathlib, re, subprocess, sys, tempfile, time, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
PHP = r"C:\xampp\php\php.exe" if os.path.exists(r"C:\xampp\php\php.exe") else "php"
passed = failed = 0
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # the Windows console would fail on "→"


def check(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
    else:
        failed += 1
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def get(port, path):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=20) as r:
            return r.status, r.headers, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read().decode("utf-8")


class Server:
    """XAMPP's PHP built-in server with its own error log; extra environment variables change db.php's settings."""

    def __init__(self, port, log_dir, env=None):
        self.port, self.log = port, pathlib.Path(log_dir) / f"php-{port}.log"
        self.out = open(pathlib.Path(log_dir) / f"server-{port}.txt", "w")
        environment = {k: v for k, v in os.environ.items() if not k.startswith("P8_DB_")}
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
    if "_backup" in f.parts[-2] or f.parts[-2].startswith("_tmp"):
        continue
    r = subprocess.run([PHP, "-l", str(f)], capture_output=True, text=True)
    check(f"php -l {f.relative_to(ROOT)}", r.returncode == 0 and "No syntax errors" in r.stdout)

# 2. Database tests
print("-- tests/test_db.php")
r = subprocess.run([PHP, "tests/test_db.php"], cwd=ROOT, capture_output=True, text=True)
summary = re.search(r"Result: (\d+) passed, (\d+) failed", r.stdout)
check("tests/test_db.php: all database checks pass", r.returncode == 0 and summary and summary.group(2) == "0",
      summary.group(0) if summary else r.stdout[-300:])

with tempfile.TemporaryDirectory(prefix="p8-tests-") as tmp:
    # 3. The page through the web server
    print("-- test_connection.php (http://127.0.0.1:8608)")
    server = Server(8608, tmp)
    try:
        status, headers, body = get(8608, "/test_connection.php")
        check("page opens (200, UTF-8 HTML)", status == 200 and "charset=UTF-8" in headers.get("Content-Type", ""), str(status))
        check("connection status shown", "Connected successfully" in body and "<strong>studenthub_prac8</strong>" in body)
        for table, n in (("students", 8), ("events", 5), ("registrations", 12)):
            check(f"table {table} listed with {n} rows and its records shown",
                  re.search(rf"<strong>{table}</strong></td>\s*<td>InnoDB</td>\s*<td class=\"num\">{n}</td>", body) is not None
                  and f"<h2>{table} <span class=\"count\">({n} records" in body)
        check("primary and foreign keys shown", "PK registration_id" in body and "FK student_id → students.student_id" in body
              and "FK event_id → events.event_id" in body)
        check("all 8 fictional students shown", all(f"DEMO-S00{i}" in body for i in range(1, 9)) and body.count("@example.com") == 8)
        check("registrations joined with names and event titles",
              "<td>Aarohi Menon</td><td>Inter-college Hackathon</td><td>registered</td>" in body)
        check("default filter :branch = CSE → 3 students", ":branch = <strong>CSE</strong> → 3 students" in body)
        check("stored procedure roster for event 1 → 4 students", ":event_id = <strong>1</strong> → 4 students" in body)
        status, _, body = get(8608, "/test_connection.php?branch=IT")
        check("?branch=IT → 3 students", status == 200 and ":branch = <strong>IT</strong> → 3 students" in body)
        status, _, body = get(8608, "/test_connection.php?branch=CE")
        check("?branch=CE → 2 students", status == 200 and ":branch = <strong>CE</strong> → 2 students" in body)
        status, _, body = get(8608, "/test_connection.php?branch=CSE%27%20OR%20%271%27%3D%271")
        check("?branch=CSE' OR '1'='1 is not accepted (falls back to CSE)", status == 200 and ":branch = <strong>CSE</strong> → 3 students" in body)
        status, _, body = get(8608, "/test_connection.php?branch%5B%5D=IT")
        check("?branch[]=IT (array) is not accepted (falls back to CSE)", status == 200 and ":branch = <strong>CSE</strong>" in body)
        status, headers, _ = get(8608, "/assets/css/style.css")
        check("stylesheet loads", status == 200 and "text/css" in headers.get("Content-Type", ""))
        status, _, body = get(8608, "/db.php")
        check("db.php opened directly → 403 without settings", status == 403 and "root" not in body and "3306" not in body, str(status))
        for path in ("/config.example.php", "/config.local.php", "/tests/test_db.php", "/TESTS/test_page.py",
                     "/.gitignore", "/.htaccess", "/router.php", "/start-server.bat"):
            status, _, _ = get(8608, path)
            check(f"{path} → 403", status == 403, str(status))
        time.sleep(0.3)
        problems = re.findall(r"(?:Warning|Notice|Deprecated|Fatal error|Parse error)[^\n]*", server.logged())
        check("no PHP warnings, notices or errors in the server log", not problems, "; ".join(problems[:3]))
    finally:
        server.stop()

    # 4. Error handling with wrong settings (the database itself is not changed)
    print("-- error handling")
    leaks = ["root", "SQLSTATE", "Access denied", "Unknown database", "PDOException", "Stack trace", "3306", "3399",
             "127.0.0.1", "p8_missing_db", "wrong-test-password", "Base table", "information_schema.students"]
    scenarios = [
        (8611, {"P8_DB_NAME": "p8_missing_db"}, "database does not exist", "Unknown database", "Could not connect"),
        (8612, {"P8_DB_PASS": "wrong-test-password"}, "wrong password", "Access denied", "Could not connect"),
        (8613, {"P8_DB_PORT": "3399"}, "MySQL not reachable (port 3399)", "connect", "Could not connect"),
        (8614, {"P8_DB_NAME": "information_schema"}, "connected but tables missing", "Base table or view not found",
         "tables were not found"),
    ]
    for port, env, label, logged_text, shown_text in scenarios:
        server = Server(port, tmp, env)
        try:
            status, _, body = get(port, "/test_connection.php")
            text = re.sub(r"<[^>]+>", " ", body.split("<main", 1)[1].split("</main>", 1)[0])
            found = [word for word in leaks if word in body]
            check(f"{label}: HTTP 500 with a general message", status == 500 and shown_text in text, f"{status}: {' '.join(text.split())[:110]}")
            check(f"{label}: no details in the page", not found, ", ".join(found))
            time.sleep(0.3)
            check(f"{label}: real error written to the PHP error log", logged_text in server.logged())
        finally:
            server.stop()

    # get_db() called from the command line with a wrong password
    environment = {**{k: v for k, v in os.environ.items() if not k.startswith("P8_DB_")}, "P8_DB_PASS": "wrong-test-password"}
    r = subprocess.run([PHP, "-d", "display_errors=1", "-d", f"error_log={tmp}/cli.log", "-r",
                        "require 'db.php'; try { get_db(); echo 'connected'; } "
                        "catch (RuntimeException $e) { echo get_class($e), ': ', $e->getMessage(); }"],
                       cwd=ROOT, env=environment, capture_output=True, text=True)
    check("get_db() throws RuntimeException with a general message only",
          r.stdout == "RuntimeException: The database connection could not be established.", r.stdout[:120])

print(f"\nResult: {passed} passed, {failed} failed")
sys.exit(0 if failed == 0 else 1)
