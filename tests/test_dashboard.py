"""StudentHub - tests of the admin dashboard, role-based navigation, account status and audit log (Practical 14).
Python 3, standard library only.

    python tests\\test_dashboard.py                        # disposable DB built from database/studenthub_demo.sql
    python tests\\test_dashboard.py --source-dump X.sql    # disposable DB restored from a mysqldump (missing migrations applied)
"""
import argparse, html, pathlib, re, secrets, subprocess, sys, tempfile, urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import test_students as P  # noqa: E402

PORT = 8739
MIGRATIONS = P.ROOT / "database" / "migrations"
check, info, mysql, scalar, q = P.check, P.info, P.mysql, P.scalar, P.q
ACCOUNTS = {}
ADMIN_LINKS = ("admin_dashboard.php?tab=students", "admin_dashboard.php?tab=events", "admin_dashboard.php?tab=audits")


def login(name):
    b = P.Browser(PORT)
    b.login(name, ACCOUNTS[name])
    return b, b.token("dashboard.php")


def audit(action):
    return int(scalar(f"SELECT COUNT(*) FROM audit_logs WHERE action={q(action)}"))


def nav_links(page):
    m = re.search(r'<nav id="app-nav".*?</nav>', page, re.S)
    return [html.unescape(h) for h in re.findall(r'<a href="([^"]+)"', m.group(0))] if m else []


def flash_of(page):
    m = re.search(r'<div class="alert alert-(success|danger)[^"]*"[^>]*>\s*<i[^>]*></i>\s*<div>(.*?)</div>', page, re.S)
    return ({"success": "success", "danger": "error"}[m.group(1)], html.unescape(m.group(2))) if m else None


def stat(page, name):
    m = re.search(r'data-stat="' + name + r'">.*?<h2[^>]*>(\d+)</h2>\s*<span class="small text-muted">(.*?)</span>', page, re.S)
    return (int(m.group(1)), html.unescape(m.group(2))) if m else None


def overview_tests(a):
    print("\n== Live statistics and latest registrations")
    st, _, page = a.request("admin_dashboard.php")
    sc = lambda sql: int(scalar(sql))
    expected = {
        "students": (sc("SELECT COUNT(*) FROM students"), f"{sc(chr(83)+'ELECT COUNT(*) FROM students WHERE COALESCE(TRIM(status),\'\') <> \'Inactive\'')} active · {sc(chr(83)+'ELECT COUNT(*) FROM students WHERE TRIM(status)=\'Inactive\'')} inactive"),
        "events": (sc("SELECT COUNT(*) FROM events"), f"{sc('SELECT COUNT(*) FROM events WHERE event_date >= CURDATE()')} upcoming · {sc(chr(83)+'ELECT COUNT(*) FROM events WHERE event_date >= CURDATE() AND status=' + chr(39) + 'open' + chr(39))} open"),
        "registrations": (sc("SELECT COUNT(*) FROM registrations WHERE status='registered'"), None),
        "user": (sc("SELECT COUNT(*) FROM users"), None),
        "audit": (sc("SELECT COUNT(*) FROM audit_logs"), None),
    }
    got = {k: stat(page, k) for k in expected}
    check("overview (200) shows five live counters matching the database (students, events, registrations, accounts, audit log)",
          st == 200 and all(got[k] is not None and got[k][0] == v[0] and (v[1] is None or got[k][1] == v[1]) for k, v in expected.items()), str(got))
    check("the accounts counter splits by role and counts disabled accounts",
          got["user"] and f"{sc(chr(83)+'ELECT COUNT(*) FROM users WHERE role=' + chr(39) + 'admin' + chr(39))} admin · " in got["user"][1] and "disabled" in got["user"][1])
    rows = mysql("SELECT s.name, e.title FROM registrations r JOIN students s ON s.id=r.student_id JOIN events e ON e.id=r.event_id ORDER BY r.registered_at DESC, r.registration_id DESC LIMIT 5")
    table = re.search(r'id="latest-registrations".*?<tbody>(.*?)</tbody>', page, re.S).group(1)
    shown = [(html.unescape(n).strip(), html.unescape(t)) for n, t in re.findall(r'<td class="fw-semibold">(.*?) <span.*?</td>\s*<td class="small">(.*?)</td>', table, re.S)]
    check(f"latest event registrations: the newest {len(rows)} (student + event), newest first", shown == [tuple(r) for r in rows] and len(rows) >= 3, f"{shown} vs {rows}")
    newest = [r[0] for r in mysql("SELECT username FROM users ORDER BY created_at DESC, id DESC LIMIT 5")]
    box = re.search(r'id="newest-accounts">(.*?)</ul>', page, re.S).group(1)
    check("newest accounts: the five latest accounts with role badges", [html.unescape(u).strip() for u in re.findall(r'</i>(.*?)\s*<span class="badge badge-role', box)] == newest)
    shown_ids = len(re.findall(r"<tr>", re.search(r'id="recent-activity".*?</table>', page, re.S).group(0))) - 1
    check("recent activity table shows the newest audit entries (up to 6)", shown_ids == min(6, int(scalar("SELECT COUNT(*) FROM audit_logs"))) and shown_ids >= 1, str(shown_ids))


def navigation_tests():
    print("\n== Role-based navigation (menu_items, migration 004)")
    links = {}
    for name in ("p14_student", "p14_editor", "p14_admin"):
        b, _ = login(name)
        links[name] = nav_links(b.request("dashboard.php")[2])
    check("student: sidebar has no admin links (no Shortcuts to the console)", not any(l.startswith("admin_dashboard.php") for l in links["p14_student"]), str(links["p14_student"]))
    check("editor: no admin links either (editors get no admin rights)", not any(l.startswith("admin_dashboard.php") for l in links["p14_editor"]), str(links["p14_editor"]))
    check("admin: Shortcuts to the Admin Console and its tabs, taken from menu_items",
          "admin_dashboard.php" in links["p14_admin"] and all(l in links["p14_admin"] for l in ADMIN_LINKS))
    every = [l for ls in links.values() for l in ls]
    check("no link to a missing page (faculty.php) or outside the portal (../Practical-13) for any role",
          "faculty.php" not in every and not any(l.startswith("../") for l in every))
    mysql("INSERT INTO menu_items (title, link, min_role, icon) VALUES ('Shortcut <img src=x onerror=alert(1)>', 'attendance.php?view=x', 'student', 'bi-star\" onmouseover=\"alert(1)')")
    b, _ = login("p14_student")
    page = b.request("dashboard.php")[2]
    check("menu titles and icons from the database are HTML-escaped in the sidebar",
          "Shortcut &lt;img src=x onerror=alert(1)&gt;" in page and "<img src=x" not in page and 'onmouseover="alert(1)"' not in page)
    mysql("DELETE FROM menu_items WHERE link='attendance.php?view=x'")
    a, _ = login("p14_admin")
    page = a.request("admin_dashboard.php")[2]
    box = re.search(r"Navigation for your role \(admin\):.*?</div>\s*</div>", page, re.S)
    check("the console's navigation box lists exactly the admin's menu rows (existing pages only)",
          box is not None and "faculty.php" not in box.group(0) and all(l.replace("&", "&amp;") in box.group(0) for l in ADMIN_LINKS))


def access_tests():
    print("\n== Consistent access-denied page")
    for name in ("p14_student", "p14_editor"):
        b, t = login(name)
        before = audit("ACCESS_DENIED")
        results = [b.request(f"admin_dashboard.php?tab={tab}") for tab in ("overview", "students", "events", "users", "audits")]
        same = all(st == 403 and "Access Denied" in pg and "HTTP 403 Forbidden" in pg for st, _, pg in results)
        check(f"{name.split('_')[1]}: every Admin Console tab -> the same HTTP 403 'Access Denied' page, each attempt audit-logged",
              same and audit("ACCESS_DENIED") == before + 5)
        st, _, _ = b.request("admin_dashboard.php", {"csrf_token": t, "action": "disable_user", "id": scalar("SELECT id FROM users WHERE username='p14_admin'")})
        check(f"{name.split('_')[1]}: disabling an account via POST -> 403, nothing changed", st == 403 and scalar("SELECT status FROM users WHERE username='p14_admin'") == "active")


def account_tests(a, token):
    print("\n== Account status (disable / enable)")
    eid = scalar("SELECT id FROM users WHERE username='p14_editor'")
    e, _ = login("p14_editor")
    check("the editor is signed in", e.request("dashboard.php")[0] == 200)
    st, _, page = a.request("admin_dashboard.php?tab=users")
    check("users tab lists status and Disable/Enable/Delete POST forms with CSRF tokens (none for the own account)",
          st == 200 and 'id="user-table"' in page and 'value="disable_user"' in page and not P.post_forms_without_token(page)
          and "Current session" in page)
    a.request(f"admin_dashboard.php?tab=users&action=disable_user&id={eid}")
    st, _, _ = a.request("admin_dashboard.php", {"action": "disable_user", "id": eid})
    check("GET with action=disable_user and a POST without token change nothing (403 for the POST)", st == 403 and scalar(f"SELECT status FROM users WHERE id={eid}") == "active")
    before = audit("USER_DISABLED")
    st, _, _ = a.request("admin_dashboard.php", {"csrf_token": token, "action": "disable_user", "id": eid})
    check("disable -> 303, status 'disabled', USER_DISABLED audit entry, message", st == 303 and scalar(f"SELECT status FROM users WHERE id={eid}") == "disabled"
          and audit("USER_DISABLED") == before + 1 and "was disabled" in (flash_of(a.request("admin_dashboard.php?tab=users")[2]) or ("", ""))[1])
    st, hd, _ = e.request("dashboard.php")
    check("the disabled editor's open session ends at the next request (login page, status=access_disabled, SESSION_REVOKED)",
          st == 303 and hd.get("Location") == "login.php?status=access_disabled"
          and scalar("SELECT details FROM audit_logs WHERE action='SESSION_REVOKED' ORDER BY id DESC LIMIT 1") == "Session ended: the account is disabled.")
    b = P.Browser(PORT)
    st, _, page = b.login("p14_editor", ACCOUNTS["p14_editor"])
    check("sign-in of the disabled account with the correct password is refused (403, generic message, LOGIN_DENIED)",
          st == 403 and "Your access to StudentHub is currently disabled" in page
          and scalar("SELECT details FROM audit_logs WHERE action='LOGIN_DENIED' ORDER BY id DESC LIMIT 1") == "Sign-in refused: the account is disabled.")
    st, _, page = P.Browser(PORT).login("p14_editor", "Wrong!Pass123")
    check("a wrong password for the disabled account gets the normal message (status not revealed)", st == 401 and "Invalid username/email or password." in page)
    a.request("admin_dashboard.php", {"csrf_token": token, "action": "disable_user", "id": eid})
    check("disabling it again -> 'already disabled'", "already disabled" in (flash_of(a.request("admin_dashboard.php?tab=users")[2]) or ("", ""))[1])
    me = scalar("SELECT id FROM users WHERE username='p14_admin'")
    a.request("admin_dashboard.php", {"csrf_token": token, "action": "disable_user", "id": me})
    check("an administrator cannot disable the own account", scalar(f"SELECT status FROM users WHERE id={me}") == "active"
          and "cannot disable your own account" in (flash_of(a.request("admin_dashboard.php?tab=users")[2]) or ("", ""))[1])
    sid = scalar("SELECT id FROM users WHERE username='p14_student'")
    a.request("admin_dashboard.php", {"csrf_token": token, "action": "disable_user", "id": sid})
    st, _, _ = P.Browser(PORT).login("p14_student", ACCOUNTS["p14_student"])
    check("a disabled student account cannot sign in either (also with a linked active student record)", st == 403)
    before = audit("USER_ENABLED")
    a.request("admin_dashboard.php", {"csrf_token": token, "action": "enable_user", "id": eid})
    a.request("admin_dashboard.php", {"csrf_token": token, "action": "enable_user", "id": sid})
    st, hd, _ = P.Browser(PORT).login("p14_editor", ACCOUNTS["p14_editor"])
    check("enable -> status 'active', USER_ENABLED entries, the editor signs in again", st == 303 and hd.get("Location") == "dashboard.php"
          and audit("USER_ENABLED") == before + 2 and scalar(f"SELECT status FROM users WHERE id={eid}") == "active")
    a.request("admin_dashboard.php", {"csrf_token": token, "action": "disable_user", "id": "999999"})
    check("an unknown account id -> 'not found'", "not found" in (flash_of(a.request("admin_dashboard.php?tab=users")[2]) or ("", ""))[1])
    tmp = scalar("SELECT id FROM users WHERE username='p14_temp'")
    before = audit("DELETE_USER")
    a.request("admin_dashboard.php", {"csrf_token": token, "action": "delete_user", "id": tmp})
    check("deleting another account works and is audit-logged with the username", scalar(f"SELECT COUNT(*) FROM users WHERE id={tmp}") == "0"
          and audit("DELETE_USER") == before + 1 and "(p14_temp, student)" in scalar("SELECT details FROM audit_logs WHERE action='DELETE_USER' ORDER BY id DESC LIMIT 1"))


def audit_tests(a):
    print("\n== Audit log filters")
    def rows(params):
        _, _, page = a.request("admin_dashboard.php?tab=audits&" + urllib.parse.urlencode(params))
        table = re.search(r'id="audit-table".*?<tbody>(.*?)</tbody>', page, re.S).group(1)
        return re.findall(r'<td><span class="text-muted fw-bold">#(\d+)</span></td>', table)
    for label, params, where in (("action USER_DISABLED", {"audit_action": "USER_DISABLED"}, "action='USER_DISABLED'"),
                                 ("status SECURITY_BLOCK", {"audit_status": "SECURITY_BLOCK"}, "status='SECURITY_BLOCK'"),
                                 ("user contains 'p14_ed'", {"audit_user": "p14_ed"}, "username LIKE '%p14\\_ed%'"),
                                 ("action + status", {"audit_action": "LOGIN_DENIED", "audit_status": "SECURITY_BLOCK"}, "action='LOGIN_DENIED' AND status='SECURITY_BLOCK'")):
        want = [r[0] for r in mysql(f"SELECT id FROM audit_logs WHERE {where} ORDER BY id DESC LIMIT 100")]
        check(f"filter {label} -> exactly the matching entries (newest first)", rows(params) == want and len(want) >= 1, f"{rows(params)[:5]} vs {want[:5]}")
    total = [r[0] for r in mysql("SELECT id FROM audit_logs ORDER BY id DESC LIMIT 100")]
    check("unknown action/status values are ignored; SQL in the user filter is text", rows({"audit_action": "X' OR '1'='1", "audit_status": "nope"}) == total
          and rows({"audit_user": "' OR '1'='1"}) == [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dump")
    args = ap.parse_args()
    print(f"StudentHub admin dashboard tests - Practical 14 (PHP {P.PHP}, MySQL {P.MYSQL})")
    info("source: " + (pathlib.Path(args.source_dump).name if args.source_dump else "database/studenthub_demo.sql"))
    live_before = P.live_fingerprint()
    live_menu = mysql("SELECT * FROM menu_items ORDER BY id", P.LIVE_DB)
    workdir = tempfile.mkdtemp(prefix="p14-")
    server = None
    try:
        P.create_test_db(args.source_dump)
        for m in sorted(MIGRATIONS.glob("0*.sql")):
            if not m.name.endswith(".down.sql") and scalar(f"SELECT COUNT(*) FROM schema_migrations WHERE version='{m.name[:3]}'") == "0":
                r = subprocess.run([P.MYSQL, "-u", "root", P.TEST_DB], input=m.read_text(encoding="utf-8"), capture_output=True, text=True, encoding="utf-8")
                assert r.returncode == 0, r.stderr
                info(f"{m.name} applied to the disposable copy")
        for name, role in (("p14_admin", "admin"), ("p14_admin2", "admin"), ("p14_editor", "editor"), ("p14_student", "student"), ("p14_temp", "student")):
            ACCOUNTS[name] = secrets.token_urlsafe(12) + "A1!"
            P.create_account(name, f"{name}@example.com", role, ACCOUNTS[name])
        uid = scalar("SELECT id FROM users WHERE username='p14_student'")
        mysql(f"INSERT INTO students (user_id, enrollment_no, name, email, course, gender, semester, status) VALUES ({uid}, '26IT301', 'Dashboard Student', 'p14_student@example.com', 'Information Technology', 'Male', 1, 'Active')")
        mysql("INSERT INTO events (title, category, event_date, location, status) VALUES ('Dash Event A', 'Workshop', DATE_ADD(CURDATE(), INTERVAL 5 DAY), 'Lab', 'open'), "
              "('Dash Event B', 'Seminar', DATE_ADD(CURDATE(), INTERVAL 6 DAY), 'Hall', 'closed')")
        sids = [r[0] for r in mysql("SELECT id FROM students ORDER BY id LIMIT 3")]
        evs = [r[0] for r in mysql("SELECT id FROM events WHERE title LIKE 'Dash Event%' ORDER BY id")]
        mysql("INSERT INTO registrations (student_id, event_id, status, registered_at) VALUES "
              f"({sids[0]}, {evs[0]}, 'registered', NOW() - INTERVAL 3 HOUR), ({sids[1]}, {evs[0]}, 'cancelled', NOW() - INTERVAL 2 HOUR), ({sids[2]}, {evs[1]}, 'attended', NOW() - INTERVAL 1 HOUR)")
        server = P.Server(PORT, workdir, {"DB_NAME": P.TEST_DB})
        a, token = login("p14_admin")
        overview_tests(a)
        navigation_tests()
        access_tests()
        account_tests(a, token)
        audit_tests(a)
        problems = [l for l in server.logged().splitlines() if re.search(r"PHP (Warning|Notice|Fatal|Deprecated|Parse)", l)]
        check("no PHP warnings, notices or fatal errors in the server log", not problems, "; ".join(problems[:3]))
    finally:
        if server:
            server.stop()
        P.drop_test_db()
    print("\n== Clean-up")
    check("disposable database removed", not mysql(f"SHOW DATABASES LIKE '{P.TEST_DB}'", None))
    check("the live studenthub_db was not touched", P.live_fingerprint() == live_before and mysql("SELECT * FROM menu_items ORDER BY id", P.LIVE_DB) == live_menu)
    print(f"\nResult: {P.passed} passed, {P.failed} failed, {P.passed + P.failed} checks")
    return 1 if P.failed else 0


if __name__ == "__main__":
    sys.exit(main())
