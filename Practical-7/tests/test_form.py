"""Server-side tests for Practical 7 (Python standard library only).

Starts XAMPP's PHP built-in server with router.php, sends real HTTP GET/POST requests (with the session
cookie and CSRF token, like a browser) and checks the responses and the JSON file.
The tests use their own storage file (P7_STORAGE_FILE), so private/submissions.json is never touched.

    python tests/test_form.py                (run from the Practical-7 folder)
"""
import http.cookiejar
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

P7 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHP = os.environ.get("PHP", r"C:\xampp\php\php.exe" if os.path.exists(r"C:\xampp\php\php.exe") else "php")
WORK = os.path.join(P7, "_tmp_p7_tests")                     # deleted at the end of the run
RESULTS = []


def check(label, ok, detail=""):
    RESULTS.append(bool(ok))
    print(f"{'PASS' if ok else 'FAIL'}  {label}{'  -> ' + detail if detail and not ok else ''}")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None                                           # keep 303 responses visible to the test


class Client:
    """A browser-like client: keeps the session cookie and reads the CSRF token from the form."""

    def __init__(self, base):
        self.base = base
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()), NoRedirect)

    def request(self, path, data=None):
        req = urllib.request.Request(self.base + path, data=data)
        try:
            with self.opener.open(req, timeout=10) as r:
                return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, {k.lower(): v for k, v in e.headers.items()}, e.read().decode("utf-8")

    def get(self, path):
        return self.request(path)

    def token(self):
        return re.search(r'name="csrf_token" value="([0-9a-f]{64})"', self.get("/index.php")[2]).group(1)

    def post(self, fields, token=True, raw=None):
        if token is True:
            fields = {**fields, "csrf_token": self.token()}
        elif isinstance(token, str):
            fields = {**fields, "csrf_token": token}
        body = raw if raw is not None else urllib.parse.urlencode(fields, doseq=True).encode()
        return self.request("/index.php", body)


class Server:
    def __init__(self, port, storage):
        self.base = f"http://127.0.0.1:{port}"
        self.storage = storage
        self.log_path = os.path.join(WORK, f"php-{port}.log")
        self.log = open(self.log_path, "w")
        self.proc = subprocess.Popen([PHP, "-S", f"127.0.0.1:{port}", "router.php"], cwd=P7,
                                     env={**os.environ, "P7_STORAGE_FILE": storage},
                                     stdout=self.log, stderr=subprocess.STDOUT)
        for _ in range(50):
            try:
                urllib.request.urlopen(self.base + "/index.php", timeout=1)
                return
            except Exception:
                time.sleep(0.1)
        raise RuntimeError("PHP server did not start")

    def stop(self):
        self.proc.terminate()
        self.proc.wait(timeout=10)
        self.log.close()
        return open(self.log_path, encoding="utf-8", errors="replace").read()


def records(server):
    if not os.path.exists(server.storage):
        return None
    with open(server.storage, encoding="utf-8") as fh:
        return json.load(fh)


VALID = {"name": "  Aarohi   Menon ", "email": "Aarohi.Menon@Example.com", "category": "timetable",
         "message": "When will the Semester 3 practical timetable be published?"}


def main():
    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK)
    main_server = Server(8617, os.path.join(WORK, "data", "submissions.json"))
    servers = [main_server]
    try:
        run_tests(main_server, servers)
    finally:
        logs = "".join(s.stop() for s in servers)
        problems = re.findall(r"PHP (Warning|Notice|Fatal error|Deprecated|Parse error)[^\n]*", logs)
        check("13. PHP server log has no warnings, notices or errors", not problems, "; ".join(problems[:3]))
        shutil.rmtree(WORK, ignore_errors=True)
    print(f"\n{sum(RESULTS)} of {len(RESULTS)} checks passed")
    return 0 if all(RESULTS) else 1


def run_tests(s, servers):
    c = Client(s.base)

    # 1. Form opens correctly
    status, headers, body = c.get("/index.php")
    check("1. Form opens: GET index.php returns 200 HTML", status == 200 and "text/html" in headers.get("content-type", ""))
    check("1. Form uses method=post and posts to index.php", re.search(r'<form action="index.php" method="post" novalidate>', body))
    check("1. Every field has a label (name, email, category, message)",
          all(f'<label for="{f}">' in body and f'id="{f}"' in body for f in ("name", "email", "category", "message")))
    check("1. Hidden CSRF token field present", re.search(r'type="hidden" name="csrf_token" value="[0-9a-f]{64}"', body))
    check("1. GET / also opens the form", c.get("/")[0] == 200)

    # 2. Empty submission
    status, _, body = c.post({"name": "", "email": "", "category": "", "message": ""})
    check("2. Empty submission: HTTP 422 with an error summary for 4 fields", status == 422 and "Please correct 4 fields" in body)
    check("2. Empty submission: one clear message per field",
          all(m in body for m in ("Please enter your full name.", "Please enter your email address.",
                                   "Please choose a category.", "Please enter your message.")))
    check("2. Empty submission: fields marked aria-invalid", body.count('aria-invalid="true"') == 4)
    check("2. Empty submission: nothing stored", records(s) is None)

    # 3. Invalid email
    for email in ("abc@", "name@domain", "a b@example.com", "@example.com", "x" * 95 + "@example.com"):
        status, _, body = c.post({**VALID, "email": email})
        check(f"3. Invalid email {email[:24]!r}: 422 with the email message only",
              status == 422 and "Please enter a valid email address" in body and "Please correct 1 field" in body)
    check("3. After an invalid email the other values stay filled in (sticky form)", 'value="Aarohi Menon"' in body and "Semester 3 practical timetable" in body)
    check("3. Nothing stored after invalid emails", records(s) is None)

    # 4. Invalid input
    cases = [
        ({"name": "R2D2"}, "Your name can contain only letters"),
        ({"name": "A"}, "Your name must be 2–60 characters long."),
        ({"name": "N" * 61}, "Your name must be 2–60 characters long."),
        ({"category": "hacker"}, "Please choose a category from the list."),
        ({"message": "Too short"}, "Your message must be at least 10 characters long."),
        ({"message": "M" * 1001}, "Your message must not be longer than 1000 characters."),
    ]
    for change, expected in cases:
        status, _, body = c.post({**VALID, **change})
        what = ", ".join(f"{k}={str(v)[:20]!r}" for k, v in change.items())
        check(f"4. Invalid input {what}: 422 with '{expected[:38]}'", status == 422 and expected in body)
    # name[]=... makes PHP receive an array instead of text (a tampered request)
    raw = urllib.parse.urlencode({**VALID, "csrf_token": c.token()}).replace("name=", "name%5B%5D=", 1).encode()
    status, _, body = c.post({}, token=False, raw=raw)
    check("4. Tampered request with name[] (an array): treated as empty, 422", status == 422 and "Please enter your full name." in body)
    token = c.token()
    raw = b"name=Bad%FF%FEname&email=a%40example.com&category=other&message=A+valid+message+text&csrf_token=" + token.encode()
    status, _, body = c.post({}, token=False, raw=raw)
    check("4. Invalid UTF-8 bytes in the name are rejected", status == 422 and "characters that are not allowed" in body)
    check("4. Nothing stored after invalid input", records(s) is None)

    # 5. Valid submission
    status, headers, _ = c.post(VALID)
    check("5. Valid submission: 303 redirect to index.php?status=sent (Post/Redirect/Get)",
          status == 303 and headers.get("location") == "index.php?status=sent")
    status, _, body = c.get("/index.php?status=sent")
    check("5. Success message shown with the name and reference SUB-0001",
          status == 200 and "Inquiry submitted successfully" in body and "Thank you, <strong>Aarohi Menon</strong>" in body and "SUB-0001" in body)
    check("5. Success message is shown only once (refresh does not repeat it)", "Inquiry submitted successfully" not in c.get("/index.php?status=sent")[2])

    # 6. JSON storage
    data = records(s)
    check("6. JSON file created and contains a list with 1 record", isinstance(data, list) and len(data) == 1)
    rec = data[0]
    check("6. Record fields: id, submitted_at, name, email, category, message (nothing else, no IP address)",
          list(rec) == ["id", "submitted_at", "name", "email", "category", "message"])
    check("6. Sanitised values stored: spaces tidied in the name, email in lower case",
          rec["name"] == "Aarohi Menon" and rec["email"] == "aarohi.menon@example.com" and rec["id"] == "SUB-0001")
    check("6. submitted_at is an ISO date-time in Indian time (+05:30)", re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+05:30", rec["submitted_at"]))
    check("6. File is pretty-printed JSON", open(s.storage, encoding="utf-8").read().startswith("[\n    {"))

    # 7. Multiple submissions (sequential and at the same time)
    for name in ("Eshan Kapoor", "Farah Siddiqui", "Karan Sethi"):
        c.post({**VALID, "name": name, "email": name.split()[0].lower() + "@example.com"})
    data = records(s)
    check("7. Three more submissions: 4 records, IDs SUB-0001 to SUB-0004 in order",
          [r["id"] for r in data] == [f"SUB-{n:04d}" for n in range(1, 5)])

    def submit_parallel(n):
        Client(s.base).post({**VALID, "name": f"Parallel Student {chr(65 + n)}", "email": f"p{n}@example.com"})
    threads = [threading.Thread(target=submit_parallel, args=(n,)) for n in range(10)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    data = records(s)
    ids = [r["id"] for r in data]
    check("7. 10 submissions at the same time: all 14 stored, file still valid JSON (flock)", len(data) == 14)
    check("7. All IDs unique: SUB-0001 to SUB-0014", sorted(ids) == [f"SUB-{n:04d}" for n in range(1, 15)])

    # 8. Safe display of submitted content
    attack = '<script>alert("XSS")</script> Marks < 40 & "quotes" are fine'
    c.post({**VALID, "name": "Anne-Marie O'Neil", "message": attack})
    success = c.get("/index.php?status=sent")[2]
    check("8. Success message escapes the apostrophe in the name", "Thank you, <strong>Anne-Marie O&#039;Neil</strong>" in success)
    page = c.get("/records.php")[2]
    check("8. records.php shows the script as text (&lt;script&gt;), never as a <script> tag",
          "&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;" in page and "<script>alert" not in page)
    check("8. records.php escapes < & and quotes in normal text", "Marks &lt; 40 &amp; &quot;quotes&quot;" in page)
    raw_file = open(s.storage, encoding="utf-8").read()
    check("8. JSON file stores < and > as \\u003C / \\u003E; decoded text is unchanged",
          "\\u003Cscript\\u003E" in raw_file and records(s)[-1]["message"] == attack)
    check("8. records.php lists all 15 records", "15 stored submissions" in page)
    status, _, body = c.post({**VALID, "name": '"><img src=x onerror=alert(1)>'})
    check("8. HTML in a rejected name is escaped when the form is shown again",
          status == 422 and "&quot;&gt;&lt;img src=x onerror=alert(1)&gt;" in body and "<img src=x" not in body)

    # 9. CSRF token
    count = len(records(s))
    status, _, body = c.post(VALID, token=False)
    check("9. POST without a CSRF token: 400 and a clear message", status == 400 and "form session has expired" in body)
    status, _, _ = c.post(VALID, token="0" * 64)
    check("9. POST with a wrong token: 400", status == 400)
    old = c.token()
    c.post(VALID, token=old)
    status, _, _ = c.post(VALID, token=old)
    check("9. A token cannot be reused after a successful submission", status == 400)
    check("9. Rejected requests stored nothing", len(records(s)) == count + 1)

    # 10. Missing and malformed storage file
    os.remove(s.storage)
    check("10. Missing JSON file: records.php shows 'No submissions yet'", "No submissions yet" in c.get("/records.php")[2])
    c.post(VALID)
    check("10. Missing JSON file is created again by the next submission", [r["id"] for r in records(s)] == ["SUB-0001"])
    with open(s.storage, "w", encoding="utf-8") as fh:
        fh.write("{ this is not valid JSON")
    check("10. Malformed JSON: records.php shows a clear error", "Stored data could not be read" in c.get("/records.php")[2])
    status, _, _ = c.post(VALID)
    backups = [f for f in os.listdir(os.path.dirname(s.storage)) if f.startswith("submissions.corrupt-")]
    check("10. Malformed JSON: submission still saved (303), file valid again with 1 record",
          status == 303 and len(records(s)) == 1)
    check("10. Malformed JSON: the damaged file is kept as a backup copy",
          len(backups) == 1 and open(os.path.join(os.path.dirname(s.storage), backups[0]), encoding="utf-8").read() == "{ this is not valid JSON")
    with open(s.storage, "w", encoding="utf-8") as fh:
        fh.write('{"not": "a list"}')
    status, _, _ = c.post(VALID)
    check("10. JSON that is not a list is also treated as damaged and replaced", status == 303 and len(records(s)) == 1)
    folder_server = Server(8618, os.path.join(WORK, "new-folder", "deeper", "submissions.json"))
    servers.append(folder_server)
    Client(folder_server.base).post(VALID)
    check("10. Missing storage folder is created on the first submission", records(folder_server) and len(records(folder_server)) == 1)

    # 11. Private files are not served
    for path in ("/private/submissions.json", "/private/.htaccess", "/PRIVATE/submissions.json", "/private%5Csubmissions.json",
                 "/includes/functions.php", "/tests/test_form.py", "/.gitignore", "/router.php"):
        check(f"11. {path} is blocked (403)", c.get(path)[0] == 403)

    # 12. Only POST stores data
    count = len(records(s))
    c.get("/index.php?" + urllib.parse.urlencode(VALID))
    check("12. A GET request with form data in the URL stores nothing", len(records(s)) == count)


if __name__ == "__main__":
    sys.exit(main())
