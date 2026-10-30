"""StudentHub - tests of migration 005 (stored contact inquiries, Practical 7).
Python 3, standard library only; reuses the helpers of test_001_practical8_foundation.py.

    python database\\tests\\test_005_inquiries.py                          # fixture + migrations 001-004
    python database\\tests\\test_005_inquiries.py --source-dump <dump.sql>  # a real dump in a disposable DB
    python database\\tests\\test_005_inquiries.py --verify-live --baseline-dump <dump taken before 005>
"""
import argparse, hashlib, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import test_001_practical8_foundation as T  # noqa: E402

MIG = T.ROOT / "database" / "migrations"
EARLIER = sorted(p for p in MIG.glob("0*.sql") if not p.name.endswith(".down.sql") and p.name[:3] < "005")
M005, DOWN005 = MIG / "005_inquiries.sql", MIG / "005_inquiries.down.sql"
LATER = sorted(p for p in MIG.glob("0*.sql") if not p.name.endswith(".down.sql") and p.name[:3] > "005")
TEST_DB, PRE_DB, FRESH_DB, LIVE_DB = "studenthub_mig005_test", "studenthub_mig005_pre", "studenthub_mig005_fresh", "studenthub_db"
check, info, mysql, scalar, run_file, structure, diff_structure = T.check, T.info, T.mysql, T.scalar, T.run_file, T.structure, T.diff_structure


def fp(db):
    out = {}
    for (t,) in mysql(f"SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA='{db}' AND TABLE_NAME NOT IN ('{T.MARKER}', 'inquiries', 'schema_migrations')", None):
        rows = mysql(f"SELECT * FROM `{t}` ORDER BY 1", db)
        out[t] = (len(rows), hashlib.sha256("\n".join("\t".join(r) for r in rows).encode()).hexdigest())
    return out


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
    if "005" in versions(db):
        run_file(DOWN005, db)


def upgrade_tests(dump):
    print("\n== Migration 005 on the source")
    prepare(TEST_DB, dump)
    before, data = structure(TEST_DB), fp(TEST_DB)
    rc, err = run_file(M005, TEST_DB)
    check("migration 005 runs without errors", rc == 0, err)
    after = structure(TEST_DB)
    d = {x.split(":")[0] for x in diff_structure(before, after)}
    check("the only structural change is the new inquiries table (columns, keys, FK, CHECK)", all("'inquiries'" in x or x == "tables inquiries" for x in d) and "tables inquiries" in d, str(sorted(d)))
    check("fk_inquiries_user -> users.id ON DELETE SET NULL", after["fks"].get(("inquiries", "fk_inquiries_user")) == ("user_id", "users", "id", "CASCADE", "SET NULL"))
    check("every row of every existing table is unchanged", fp(TEST_DB) == data)
    rc, err = run_file(M005, TEST_DB)
    check("running it again changes nothing", rc == 0 and structure(TEST_DB) == after, err)
    print("\n== Behaviour")
    rc, err = T.mysql_try("INSERT INTO inquiries (name, email, message) VALUES ('Too Short', 'x@example.com', 'short')", TEST_DB)
    check("a message under 10 characters is refused (chk_inquiries_message)", rc != 0 and "chk_inquiries_message" in err, err)
    uid = scalar("SELECT id FROM users ORDER BY id LIMIT 1", TEST_DB)
    if uid:
        mysql(f"INSERT INTO inquiries (user_id, name, email, message) VALUES ({uid}, 'Linked Person', 'linked@example.com', 'A question about the portal.')", TEST_DB)
        mysql(f"SET FOREIGN_KEY_CHECKS=1; DELETE FROM audit_logs WHERE user_id={uid}; DELETE FROM users WHERE id={uid}", TEST_DB)
        check("deleting an account keeps its inquiry (user_id becomes NULL)", scalar("SELECT IFNULL(user_id,'NULL') FROM inquiries WHERE email='linked@example.com'", TEST_DB) == "NULL")
    rc, err = T.mysql_try("INSERT INTO inquiries (user_id, name, email, message) VALUES (999999, 'Ghost', 'g@example.com', 'An inquiry from nobody.')", TEST_DB)
    check("an inquiry for a missing account is refused (fk_inquiries_user)", rc != 0 and "fk_inquiries_user" in err, err)
    print("\n== Rollback")
    rc, err = run_file(DOWN005, TEST_DB)
    check("rollback removes the table and the record; structure as before", rc == 0 and not diff_structure(before, structure(TEST_DB)) and "005" not in versions(TEST_DB), err)
    rc, err = run_file(M005, TEST_DB)
    check("migration 005 can be applied again", rc == 0 and not diff_structure(after, structure(TEST_DB)), err)


def precondition_tests(dump):
    print("\n== Preconditions")
    prepare(PRE_DB, dump)
    mysql("CREATE TABLE inquiries (id INT PRIMARY KEY, text TEXT)", PRE_DB)
    before = structure(PRE_DB)
    rc, err = run_file(M005, PRE_DB)
    check("a different inquiries table -> stopped with a message, nothing changed", rc != 0 and "different inquiries table" in err and structure(PRE_DB) == before, err)
    T.drop_disposable(PRE_DB)


def fresh_install_tests():
    print("\n== Fresh install")
    T.create_disposable(FRESH_DB)
    rc, err = run_file(T.DEMO, FRESH_DB)
    check("studenthub_demo.sql records 001-005", rc == 0 and versions(FRESH_DB)[:5] == ["001", "002", "003", "004", "005"], err)
    for m in LATER:
        run_file(m, TEST_DB)
    d = diff_structure(structure(TEST_DB), structure(FRESH_DB))
    check("fresh-install structure is identical to a database upgraded with the migrations", not d, "; ".join(d[:3]))
    T.drop_disposable(FRESH_DB)


def verify_live(baseline):
    print(f"\n== READ-ONLY verification of the live database {LIVE_DB} against the dump taken before migration 005")
    prepare(TEST_DB, baseline)
    rc, err = run_file(M005, TEST_DB)
    assert rc == 0, err
    check("live structure is identical to the baseline upgraded with 005", not diff_structure(structure(TEST_DB), structure(LIVE_DB)))
    check("every row of every other live table equals the baseline (accounts with password hashes, students, events, registrations, menu, audit log)",
          fp(LIVE_DB) == fp(TEST_DB))
    check("live database records migration 005", "005" in versions(LIVE_DB))
    T.drop_disposable(TEST_DB)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dump")
    ap.add_argument("--verify-live", action="store_true")
    ap.add_argument("--baseline-dump")
    a = ap.parse_args()
    print(f"StudentHub migration 005 tests (MySQL {T.MYSQL})")
    try:
        if a.verify_live:
            verify_live(a.baseline_dump)
        else:
            info("source: " + (a.source_dump and "dump " + pathlib.Path(a.source_dump).name or "fixture + migrations 001-004"))
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
