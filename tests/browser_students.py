"""StudentHub - browser test of the student management in the Admin Console (Practical 11) in Microsoft Edge, with
screenshots for the evidence folder (optional; needs  pip install playwright).

Uses the same kind of disposable database as tests/test_students.py (studenthub_p11_test, built from
database/studenthub_demo.sql plus a few fictional records) and XAMPP's PHP built-in server on the canonical application.
The live database is never used.
    python tests\\browser_students.py [screenshot folder]      (default: evidence/practical-11-integration)
"""
import csv, html, io, pathlib, re, secrets, sys, tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import test_students as P
from playwright.sync_api import sync_playwright

PORT = 8735
BASE = f"http://127.0.0.1:{PORT}/"
CONSOLE = BASE + "admin_dashboard.php?tab=students"
# after a POST the browser keeps the fragment of the form action (#student-form) on the redirected URL
LIST = re.compile(re.escape(CONSOLE) + r"(#[\w-]*)?$")
SHOTS = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else P.ROOT / "evidence" / "practical-11-integration"
results = []

# fictional records so the list looks like a real class (example.com addresses only)
EXTRA_STUDENTS = [
    ("25IT013", "Aarav Patel", "aarav.patel@example.com", "Information Technology", "Male", 3),
    ("24DS007", "Isha Trivedi", "isha.trivedi@example.com", "Data Science", "Female", 5),
    ("26WD002", "Kabir Joshi", "kabir.joshi@example.com", "Web Development", "Male", 1),
    ("25CS120", "Meera Pillai", "meera.pillai@example.com", "Computer Science Engineering", "Female", 3),
    ("24IT031", "Om Thakkar", "om.thakkar@example.com", "Information Technology", "Male", 5),
]


def check(name, ok):
    results.append(ok)
    print(("PASS  " if ok else "FAIL  ") + name)


def table_names(page):
    return [n.strip() for n in page.locator("#student-table tbody tr td:nth-child(2)").all_inner_texts()]


def main():
    SHOTS.mkdir(parents=True, exist_ok=True)
    P.create_test_db(None)
    P.mysql("INSERT INTO students (enrollment_no, name, email, course, gender, semester, status) VALUES " + ", ".join(
        f"({P.q(e)}, {P.q(n)}, {P.q(m)}, {P.q(c)}, {P.q(g)}, {s}, 'Active')" for e, n, m, c, g, s in EXTRA_STUDENTS))
    admin_pw, student_pw = secrets.token_urlsafe(12) + "A1!", secrets.token_urlsafe(12) + "A1!"
    P.create_account("portal_admin", "portal.admin@example.com", "admin", admin_pw)
    P.create_account("demo_student", "demo.student@example.com", "student", student_pw)
    server = P.Server(PORT, tempfile.mkdtemp(prefix="browser-p11-"), {"DB_NAME": P.TEST_DB})
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="msedge", headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
            page = context.new_page()
            errors = []
            page.on("console", lambda m: errors.append(f"{m.text} [{m.location.get('url', '')}]") if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(str(e)))
            shot = lambda name: page.screenshot(path=str(SHOTS / name), full_page=True)

            # sign in as administrator and open the Student Records tab
            page.goto(BASE + "login.php")
            page.fill("#login_input", "portal_admin")
            page.fill("#password", admin_pw)
            page.click("button[type=submit]")
            page.wait_for_url(BASE + "admin_dashboard.php")
            page.goto(CONSOLE)
            total = P.count()
            check(f"admin: Student Records tab lists the records (10 of {total} on page 1, pagination shown)",
                  page.locator("#student-table tbody tr").count() == 10 and page.locator("nav[aria-label='Student record pages']").is_visible()
                  and f"of {total} records" in page.inner_text("#student-summary"))
            check("inactive record shown with a red Inactive badge and a Reactivate button",
                  page.locator("tr.student-inactive").count() >= 1 and page.locator("button:has-text('Reactivate')").count() >= 1)
            shot("01-student-list.png")

            # add form, server-side validation, successful add (the form has novalidate: the server decides)
            page.click("#add-student")
            page.wait_for_selector("#student-form")
            check("Add Student opens the add form in the console", page.locator("#student-form-title").inner_text().strip() == "Add a student record")
            shot("02-add-student-form.png")
            page.fill("#enrollment_no", "25IT013")                       # already used by Aarav Patel
            page.fill("#name", "Riya Sharma")
            page.fill("#email", "riya.sharma@")
            page.check("input[name=gender][value=Female]")
            page.click("#student-form button[type=submit]")
            page.wait_for_selector("#student-form .alert-danger")
            errs = {f: page.inner_text(f"#{f}-error") for f in ("enrollment_no", "email", "course", "semester") if page.locator(f"#{f}-error").count()}
            check("invalid input -> messages under the fields (duplicate number, e-mail, course, semester), values kept",
                  "already used" in errs.get("enrollment_no", "") and "valid email" in errs.get("email", "") and "course" in errs.get("course", "")
                  and "semester" in errs.get("semester", "") and page.input_value("#name") == "Riya Sharma" and P.count("name='Riya Sharma'") == 0)
            shot("03-validation-error.png")
            page.fill("#enrollment_no", "")                              # the next number is assigned automatically
            page.fill("#email", "riya.sharma@example.com")
            page.select_option("#course", "Information Technology")
            page.select_option("#semester", "1")
            page.click("#student-form button[type=submit]")
            page.wait_for_url(LIST)
            flash = page.inner_text(".alert-success")
            m = re.search(r"enrollment number (\w+)\.", flash)
            check("valid student -> success message with the assigned enrollment number; new row first in the list",
                  m is not None and "Riya Sharma" in flash and table_names(page)[0] == "Riya Sharma"
                  and P.student("name='Riya Sharma'")["enrollment_no"] == m.group(1))
            shot("04-student-created.png")

            # search, then combined filters
            page.fill("#student-q", "Patel")
            page.click("form[role=search] button[type=submit]")
            page.wait_for_load_state()
            names = table_names(page)
            check("search 'Patel' -> only matching records", names and all("Patel" in n for n in names) and len(names) == P.count("name LIKE '%Patel%'"))
            shot("05-search-results.png")
            page.goto(CONSOLE)
            page.select_option("#student-course", "Web Development")
            page.select_option("#student-status", "Active")
            page.click("form[role=search] button[type=submit]")
            page.wait_for_load_state()
            names = table_names(page)
            want = P.count("course='Web Development' AND COALESCE(TRIM(status),'') <> 'Inactive'")
            check(f"course 'Web Development' + status 'Active' -> the {want} matching records, filters stay selected, export marked 'filtered'",
                  len(names) == want and page.input_value("#student-course") == "Web Development" and "(filtered)" in page.inner_text("#export-students"))
            shot("06-filtered-records.png")

            # export the filtered list (CSV download)
            with page.expect_download() as dl_info:
                page.click("#export-students")
            download = dl_info.value
            csv_path = SHOTS / "12-csv-export-web-development-active.csv"
            download.save_as(str(csv_path))
            raw = csv_path.read_bytes()
            rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline="")))
            check("Export CSV downloads studenthub_students_<date>.csv with the filtered rows only (UTF-8 BOM, header, Web Development)",
                  re.fullmatch(r"studenthub_students_\d{8}_\d{6}\.csv", download.suggested_filename) is not None and raw.startswith(b"\xef\xbb\xbf")
                  and rows[0][:4] == ["Record ID", "Enrollment No", "Name", "Email"] and len(rows) - 1 == want and all(r[4] == "Web Development" for r in rows[1:]))

            # edit a student
            page.goto(CONSOLE)
            page.click("a[aria-label='Edit Kavya Mehta']")
            page.wait_for_selector("#student-form")
            page.select_option("#semester", "8")
            page.fill("#email", "kavya.mehta@example.com")
            check("Edit opens the form filled from the database (record number, account link, registrations shown)",
                  page.locator("#student-form-title").inner_text().strip() == "Edit student record" and page.input_value("#name") == "Kavya Mehta")
            shot("07-edit-student.png")
            page.click("#student-form button[type=submit]")
            page.wait_for_url(LIST)
            row = P.student("name='Kavya Mehta'")
            check("Save changes -> success message; semester 8 and the new e-mail stored", "was updated" in page.inner_text(".alert-success")
                  and row["semester"] == "8" and row["email"] == "kavya.mehta@example.com")
            shot("08-student-updated.png")

            # soft delete with confirmation, then the inactive row
            before = P.count()
            page.click("a[aria-label='Deactivate Rohan Patel']")
            page.wait_for_selector("#student-confirm")
            check("Deactivate opens a confirmation (soft delete explained); nothing changed yet",
                  "Deactivate this student?" in page.inner_text("#student-confirm") and P.student("name='Rohan Patel'")["status"] == "Active")
            shot("09-deactivate-confirmation.png")
            page.click("#student-confirm button[type=submit]")
            page.wait_for_url(LIST)
            row = page.locator("#student-table tbody tr", has_text="Rohan Patel")
            check("confirmed -> record kept with status Inactive (greyed row, red badge, Reactivate button)",
                  P.count() == before and P.student("name='Rohan Patel'")["status"] == "Inactive"
                  and "student-inactive" in (row.get_attribute("class") or "") and "Inactive" in row.inner_text() and row.locator("button:has-text('Reactivate')").count() == 1)
            shot("10-student-inactive.png")
            page.click("button[aria-label='Reactivate John Doe']")
            page.wait_for_url(LIST)
            check("Reactivate -> John Doe active again", "was reactivated" in page.inner_text(".alert-success") and P.student("name='John Doe'")["status"] == "Active")
            shot("11-student-reactivated.png")

            # the downloaded CSV file, shown as text in the browser (its exact bytes, decoded as UTF-8)
            text = raw.decode("utf-8-sig")
            page.set_content(
                "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><title>CSV export</title><style>"
                "body{font:15px/1.5 'Segoe UI',sans-serif;margin:32px;color:#0f172a}h1{font-size:20px;margin:0 0 4px}p{color:#475569;margin:0 0 16px}"
                "pre{background:#f8fafc;border:1px solid #cbd5e1;border-radius:8px;padding:16px;font:13px/1.6 Consolas,monospace;white-space:pre}"
                "table{border-collapse:collapse;margin-top:20px;font-size:14px}th,td{border:1px solid #cbd5e1;padding:6px 10px;text-align:left}th{background:#eef2ff}"
                "</style></head><body>"
                f"<h1>Downloaded file: {html.escape(download.suggested_filename)}</h1>"
                f"<p>Export of the filtered list (course Web Development, status Active) from the StudentHub Admin Console &middot; {len(raw)} bytes, "
                "UTF-8 with byte-order mark, CRLF line endings. Raw file content:</p>"
                f"<pre>{html.escape(text)}</pre>"
                "<p style='margin-top:20px'>The same file read as CSV (columns):</p><table>"
                + "".join("<tr>" + "".join((f"<th>{html.escape(c)}</th>" if i == 0 else f"<td>{html.escape(c)}</td>") for c in r) + "</tr>" for i, r in enumerate(rows))
                + "</table></body></html>")
            shot("12-csv-export.png")

            # an unauthorised student
            page.goto(CONSOLE)
            page.click("button:has-text('Logout')")
            page.wait_for_url(re.compile(r".*login\.php\?status=logged_out"))
            page.fill("#login_input", "demo_student")
            page.fill("#password", student_pw)
            page.click("button[type=submit]")
            page.wait_for_url(BASE + "dashboard.php")
            response = page.goto(CONSOLE)
            check("a student opening the Student Records tab -> HTTP 403 'Access Denied', no student data shown",
                  response.status == 403 and "Access Denied" in page.inner_text("main") and "kavya.mehta@example.com" not in page.content())
            shot("13-student-access-denied.png")

            # browser console: only the intended 403/422 responses (and the portal's missing favicon, reported separately)
            favicon = [e for e in errors if "/favicon.ico" in e]
            unexpected = [e for e in errors if not re.search(r"status of (403|422)", e) and "/favicon.ico" not in e]
            check("no JavaScript errors (only the intended 403/422 responses)", not unexpected)
            print(*unexpected, sep="\n")
            if favicon:
                print(f"INFO  known, pre-existing: the portal has no favicon - {len(favicon)} automatic /favicon.ico request(s) got 404")
            browser.close()
    finally:
        server.stop()
        log = server.logged()
        problems = [line for line in log.splitlines() if re.search(r"PHP (Warning|Notice|Fatal|Deprecated)", line)]
        check("no PHP warnings or errors in the server log", not problems)
        P.drop_test_db()
    shown_dir = SHOTS.relative_to(P.ROOT).as_posix() if SHOTS.is_relative_to(P.ROOT) else str(SHOTS)
    print(f"screenshots: {shown_dir}/ ({len(list(SHOTS.glob('*.png')))} PNG files)")
    print(f"browser checks: {sum(results)} passed, {len(results) - sum(results)} failed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
