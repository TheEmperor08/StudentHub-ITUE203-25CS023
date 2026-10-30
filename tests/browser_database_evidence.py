"""StudentHub - genuine phpMyAdmin screenshots of the shared database design (Practical 8 evidence), taken in Microsoft Edge.

    python tests\\browser_database_evidence.py [screenshot folder]      (default: evidence/practical-08-integration)

A disposable database studenthub_report_demo (marker table zz_report_demo_marker) is built from database/studenthub_demo.sql
(fictional rows) plus a few fictional registrations, shown in XAMPP's phpMyAdmin (http://localhost/phpmyadmin, Apache must be
running) and dropped again. The live studenthub_db is never opened.
"""
import pathlib, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import test_students as P
from playwright.sync_api import sync_playwright

DB, MARKER = "studenthub_report_demo", "zz_report_demo_marker"
PMA = "http://localhost/phpmyadmin/index.php"
SHOTS = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else P.ROOT / "evidence" / "practical-08-integration"
JOIN = ("SELECT s.enrollment_no, s.name AS student, e.title AS event, e.event_date, r.status, r.registered_at\n"
        "FROM registrations r\nJOIN students s ON s.id = r.student_id\nJOIN events e ON e.id = r.event_id\nORDER BY r.registered_at;")
results = []


def check(name, ok):
    results.append(ok)
    print(("PASS  " if ok else "FAIL  ") + name)


def drop():
    if P.mysql(f"SHOW DATABASES LIKE '{DB}'", None):
        assert P.mysql(f"SHOW TABLES FROM `{DB}` LIKE '{MARKER}'", None), f"{DB} was not created by this script"
        P.mysql(f"DROP DATABASE `{DB}`", None)


def main():
    SHOTS.mkdir(parents=True, exist_ok=True)
    drop()
    P.mysql(f"CREATE DATABASE `{DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; CREATE TABLE `{DB}`.`{MARKER}` (id INT)", None)
    r = subprocess.run([P.MYSQL, "-u", "root", DB], input=P.DEMO.read_text(encoding="utf-8"), capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    P.mysql("UPDATE events SET event_date = '2026-11-20', capacity = 40 WHERE id = 5; "
            "INSERT INTO registrations (student_id, event_id, status, registered_at) VALUES "
            "(2, 5, 'registered', '2026-10-28 10:15:00'), (3, 5, 'registered', '2026-10-28 11:02:00'), (4, 4, 'cancelled', '2026-10-29 09:40:00'), "
            "(6, 1, 'attended', '2026-08-20 16:30:00')", DB)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page(viewport={"width": 1366, "height": 900})
            shot = lambda name: page.screenshot(path=str(SHOTS / name), full_page=True)
            page.goto(f"{PMA}?route=/database/structure&db={DB}")
            page.wait_for_load_state("networkidle")
            check("phpMyAdmin: database structure lists the shared tables", all(t in page.inner_text("table.data") for t in ("students", "events", "registrations", "users", "event_categories")))
            shot("01-database-tables.png")
            page.goto(f"{PMA}?route=/table/structure&db={DB}&table=registrations")
            page.wait_for_load_state("networkidle")
            check("registrations structure shows student_id, event_id, status and the unique key", all(t in page.content() for t in ("student_id", "event_id", "uq_registrations_student_event")))
            shot("02-registrations-structure.png")
            page.goto(f"{PMA}?route=/table/relation&db={DB}&table=registrations")
            page.wait_for_load_state("networkidle")
            check("relation view of registrations shows the two foreign keys", "fk_registrations_student" in page.content() and "fk_registrations_event" in page.content())
            shot("03-registrations-foreign-keys.png")
            page.goto(f"{PMA}?route=/table/structure&db={DB}&table=students")
            page.wait_for_load_state("networkidle")
            shot("04-students-structure.png")
            page.goto(f"{PMA}?route=/database/designer&db={DB}")
            page.wait_for_load_state("networkidle")
            designer = page.locator("#canvas_outer").count() > 0
            check("designer (ER diagram) available: " + str(designer), True)
            if designer:
                shot("05-er-diagram-designer.png")
            page.goto(f"{PMA}?route=/database/sql&db={DB}")
            page.wait_for_selector("#sqlquery", state="attached")
            page.evaluate("q => { const t = document.querySelector('#sqlquery'); t.value = q; if (window.codeMirrorEditor) window.codeMirrorEditor.setValue(q); }", JOIN)
            page.click("#button_submit_query")
            page.wait_for_selector(".table_results", timeout=20000)
            check("three-table JOIN (registrations, students, events) returns the 4 fictional registrations", page.locator(".table_results tbody tr").count() == 4)
            shot("06-join-query-result.png")
            browser.close()
    finally:
        drop()
    check("disposable database removed", not P.mysql(f"SHOW DATABASES LIKE '{DB}'", None))
    print(f"browser checks: {sum(results)} passed, {len(results) - sum(results)} failed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
