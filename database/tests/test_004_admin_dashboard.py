"""StudentHub - tests of migration 004 (admin dashboard: menu roles and links, users.status, role check - Practical 14).
Python 3, standard library only; reuses the helpers of test_001_practical8_foundation.py.

    python database\\tests\\test_004_admin_dashboard.py                          # fixture + migrations 001-003
    python database\\tests\\test_004_admin_dashboard.py --source-dump <dump.sql>  # a real dump in a disposable DB
    python database\\tests\\test_004_admin_dashboard.py --verify-live --baseline-dump <dump taken before 004>
"""
import argparse, hashlib, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import test_001_practical8_foundation as T  # noqa: E402

MIG = T.ROOT / "database" / "migrations"
EARLIER = [MIG / "001_practical8_foundation.sql", MIG / "002_unique_enrollment_no.sql", MIG / "003_event_management.sql"]
M004, DOWN004 = MIG / "004_admin_dashboard.sql", MIG / "004_admin_dashboard.down.sql"
LATER = sorted(p for p in MIG.glob("0*.sql") if not p.name.endswith(".down.sql") and p.name[:3] > "004")
TEST_DB, PRE_DB, FRESH_DB, LIVE_DB = "studenthub_mig004_test", "studenthub_mig004_pre", "studenthub_mig004_fresh", "studenthub_db"
check, info, mysql, scalar, run_file, structure, diff_structure = T.check, T.info, T.mysql, T.scalar, T.run_file, T.structure, T.diff_structure
PROTECTED = ("students", "events", "registrations", "event_categories", "audit_logs")


def fp(db, tables):
    out = {}
    for t in tables:
        rows = mysql(f"SELECT * FROM `{t}` ORDER BY 1", db)
        out[t] = (len(rows), hashlib.sha256("\n".join("\t".join(r) for r in rows).encode()).hexdigest())
    return out


def users_core(db):
    return mysql("SELECT id, username, email, password, role, IFNULL(created_at,''), IFNULL(last_login,'') FROM users ORDER BY id", db)


def versions(db):
    return [r[0] for r in mysql("SELECT version FROM schema_migrations ORDER BY version", db)]


def prepare(db, dump):
    T.create_disposable(db)
    T.load_source(db, dump)
    have = versions(db) if mysql(f"SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA='{db}' AND TABLE_NAME='schema_migrations'") else []
    for m in EARLIER:
        if m.name[:3] not in have:
            rc, err = run_file(m, db)
            assert rc == 0, f"{m.name}: {err}"
    if "004" in versions(db):
        rc, err = run_file(DOWN004, db)
        assert rc == 0, err


def upgrade_tests(dump):
    print("\n== Migration 004 on the source")
    prepare(TEST_DB, dump)
    before, data_before, users_before = structure(TEST_DB), fp(TEST_DB, PROTECTED), users_core(TEST_DB)
    menu_before = mysql("SELECT id, title, link, min_role FROM menu_items ORDER BY id", TEST_DB)
    rc, err = run_file(M004, TEST_DB)
    check("migration 004 runs without errors", rc == 0, err)
    after = structure(TEST_DB)
    d = {x.split(":")[0] for x in diff_structure(before, after)}
    check("structural changes: users.status (+ shifted users columns), chk_users_role and menu_items.min_role only",
          d - {x for x in d if x.startswith("columns ('users'")} == {"columns ('menu_items', 'min_role')", "checks ('users', 'chk_users_role')"}
          and "columns ('users', 'status')" in d, str(sorted(d)))
    check("menu_items.min_role is ENUM('student','editor','admin') NOT NULL DEFAULT 'student'",
          after["columns"][("menu_items", "min_role")][1:4] == ("enum('student','editor','admin')", "NO", "'student'"))
    menu = mysql("SELECT id, title, link, min_role FROM menu_items ORDER BY id", TEST_DB)
    expected = []
    for i, title, link, role in menu_before:
        role = "student" if role == "user" else role
        if link == "../Practical-13/index.html":
            title, link, role = "Event Finder (Fetch API)", "events_live.php", "student"
        elif link == "student_dashboard.php" and title.startswith("My Profile"):
            link = "profile.php"
        elif link == "student_dashboard.php" and title == "Student Dashboard":
            link = "dashboard.php"
        elif link == "student_dashboard.php#events":
            link = "notifications.php"
        elif link == "student_dashboard.php#attendance":
            link = "attendance.php"
        expected.append([i, title, link, role])
    check("menu rows: 'user' -> 'student', standalone/anchor links -> the integrated pages, every other row unchanged", menu == expected, str(menu))
    check("no menu link points outside the portal any more", scalar("SELECT COUNT(*) FROM menu_items WHERE link LIKE '../%'", TEST_DB) == "0")
    check("users: every account active; ids, names, e-mails, password hashes, roles unchanged",
          scalar("SELECT COUNT(*) FROM users WHERE status <> 'active'", TEST_DB) == "0" and users_core(TEST_DB) == users_before)
    check("students, events, registrations, categories and the audit log unchanged", fp(TEST_DB, PROTECTED) == data_before)
    rc, err = T.mysql_try("UPDATE users SET role = 'superuser' ORDER BY id LIMIT 1", TEST_DB)
    check("an invalid role is refused (chk_users_role)", rc != 0 and "chk_users_role" in err, err)
    rc, err = T.mysql_try("UPDATE users SET status = 'banned' ORDER BY id LIMIT 1", TEST_DB)
    check("an invalid status is refused or not stored", rc != 0 or scalar("SELECT COUNT(*) FROM users WHERE status = 'banned'", TEST_DB) == "0")
    snap = (after, fp(TEST_DB, PROTECTED + ("menu_items", "users")))
    rc, err = run_file(M004, TEST_DB)
    check("running it again changes nothing (idempotent)", rc == 0 and (structure(TEST_DB), fp(TEST_DB, PROTECTED + ("menu_items", "users"))) == snap, err)
    print("\n== Rollback (004_admin_dashboard.down.sql)")
    rc, err = run_file(DOWN004, TEST_DB)
    check("rollback restores the previous structure and keeps every account", rc == 0 and not diff_structure(before, structure(TEST_DB))
          and users_core(TEST_DB) == users_before and "004" not in versions(TEST_DB), err)
    check("rollback maps 'student' back to 'user' in the menu", scalar("SELECT COUNT(*) FROM menu_items WHERE min_role = 'user'", TEST_DB)
          == str(sum(1 for r in expected if r[3] == "student")))
    rc, err = run_file(M004, TEST_DB)
    check("migration 004 can be applied again after the rollback", rc == 0 and not diff_structure(after, structure(TEST_DB)), err)


def precondition_tests(dump):
    print("\n== Preconditions")
    prepare(PRE_DB, dump)
    mysql("SET SESSION sql_mode=''; INSERT INTO users (username, email, password, role) VALUES ('odd_role', 'odd.role@example.com', 'x', 'guest')", PRE_DB)
    before = structure(PRE_DB)
    rc, err = run_file(M004, PRE_DB)
    check("an account with an unknown role -> stopped with a message, nothing changed", rc != 0 and "role other than" in err and structure(PRE_DB) == before, err)
    T.drop_disposable(PRE_DB)


def fresh_install_tests():
    print("\n== Fresh install")
    T.create_disposable(FRESH_DB)
    rc, err = run_file(T.DEMO, FRESH_DB)
    check("studenthub_demo.sql records 001-004 (+ later)", rc == 0 and versions(FRESH_DB)[:4] == ["001", "002", "003", "004"], err)
    for m in LATER:
        run_file(m, TEST_DB)
    d = diff_structure(structure(TEST_DB), structure(FRESH_DB))
    check("fresh-install structure is identical to a database upgraded with the migrations", not d, "; ".join(d[:3]))
    check("the demo menu uses only student/editor/admin and integrated links",
          scalar("SELECT COUNT(*) FROM menu_items WHERE link LIKE '../%' OR link LIKE '%#%'", FRESH_DB) == "0")
    T.drop_disposable(FRESH_DB)


def verify_live(baseline):
    print(f"\n== READ-ONLY verification of the live database {LIVE_DB} against the dump taken before migration 004")
    prepare(TEST_DB, baseline)
    data_before, users_before = fp(TEST_DB, ("students", "registrations", "event_categories")), users_core(TEST_DB)
    rc, err = run_file(M004, TEST_DB)
    assert rc == 0, err
    d = diff_structure(structure(TEST_DB), structure(LIVE_DB))
    check("live structure is identical to the baseline upgraded with 004", not d, "; ".join(d[:3]))
    check("live menu equals the migrated baseline menu", mysql("SELECT * FROM menu_items ORDER BY id", LIVE_DB) == mysql("SELECT * FROM menu_items ORDER BY id", TEST_DB))
    check("live accounts (incl. password hashes) unchanged and active; students, registrations, categories unchanged",
          users_core(LIVE_DB) == users_before and scalar("SELECT COUNT(*) FROM users WHERE status <> 'active'", LIVE_DB) == "0"
          and fp(LIVE_DB, ("students", "registrations", "event_categories")) == data_before)
    check("live database records migration 004", "004" in versions(LIVE_DB))
    T.drop_disposable(TEST_DB)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dump")
    ap.add_argument("--verify-live", action="store_true")
    ap.add_argument("--baseline-dump")
    a = ap.parse_args()
    print(f"StudentHub migration 004 tests (MySQL {T.MYSQL})")
    try:
        if a.verify_live:
            verify_live(a.baseline_dump)
        else:
            info("source: " + (a.source_dump and "dump " + pathlib.Path(a.source_dump).name or "fixture + migrations 001-003"))
            upgrade_tests(a.source_dump)
            precondition_tests(a.source_dump)
            fresh_install_tests()
    finally:
        for name in (TEST_DB, PRE_DB, FRESH_DB):
            T.drop_disposable(name)
        check("all disposable databases removed", not any(T.db_exists(n) for n in (TEST_DB, PRE_DB, FRESH_DB)))
    print(f"\nResult: {T.passed} passed, {T.failed} failed, {T.passed + T.failed} checks")
    return 1 if T.failed else 0


if __name__ == "__main__":
    sys.exit(main())
