"""StudentHub - tests of migration 002 (UNIQUE students.enrollment_no, Practical 11 student management).
Python 3, standard library only; reuses the helpers of test_001_practical8_foundation.py.

    python database\\tests\\test_002_unique_enrollment_no.py                          # fixture (fictional data) + migration 001
    python database\\tests\\test_002_unique_enrollment_no.py --source-dump <dump.sql>  # a real dump, restored into a disposable DB
    python database\\tests\\test_002_unique_enrollment_no.py --verify-live --baseline-dump <dump taken before 002>
                                                                                      # READ-ONLY check of the live database

Every disposable database carries a marker table and is dropped at the end; the live studenthub_db is only read.
"""
import argparse, hashlib, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import test_001_practical8_foundation as T  # noqa: E402

MIGRATION_002 = T.ROOT / "database" / "migrations" / "002_unique_enrollment_no.sql"
ROLLBACK_002 = T.ROOT / "database" / "migrations" / "002_unique_enrollment_no.down.sql"
TEST_DB, PRE_DB, FRESH_DB, LIVE_DB = "studenthub_mig002_test", "studenthub_mig002_pre", "studenthub_mig002_fresh", "studenthub_db"
INDEX = ("students", "uq_students_enrollment_no")
# migrations after 002 (studenthub_demo.sql already contains them) and their rollbacks, newest first
LATER = sorted(p for p in (T.ROOT / "database" / "migrations").glob("0*.sql") if not p.name.endswith(".down.sql") and p.name[:3] > "002")
LATER_DOWN = [p.with_name(p.name[:-4] + ".down.sql") for p in reversed(LATER)]
check, info, mysql, scalar, run_file, structure, diff_structure = T.check, T.info, T.mysql, T.scalar, T.run_file, T.structure, T.diff_structure


def data_fingerprint(db):
    """row count + sha256 of every row of every table (the marker table excluded)"""
    out = {}
    for (t,) in mysql(f"SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA='{db}' AND TABLE_NAME <> '{T.MARKER}' ORDER BY 1"):
        rows = mysql(f"SELECT * FROM `{t}` ORDER BY 1", db)
        out[t] = (len(rows), hashlib.sha256("\n".join("\t".join(r) for r in rows).encode()).hexdigest())
    return out


def versions(db):
    return [r[0] for r in mysql("SELECT version FROM schema_migrations ORDER BY version", db)]


def prepare(db, dump):
    """disposable copy of the source at the state migration 002 expects (migration 001 applied)"""
    T.create_disposable(db)
    T.load_source(db, dump)
    if not mysql(f"SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA='{db}' AND TABLE_NAME='schema_migrations'") or "001" not in versions(db):
        rc, err = run_file(T.MIGRATION, db)
        assert rc == 0, err
    if "002" in versions(db):                         # a dump taken after 002: start from the state before it
        for down in LATER_DOWN + [ROLLBACK_002]:
            rc, err = run_file(down, db)
            assert rc == 0, f"{down.name}: {err}"


def upgrade_tests(dump):
    print("\n== Migration 002 on the source")
    prepare(TEST_DB, dump)
    before, data_before = structure(TEST_DB), data_fingerprint(TEST_DB)
    numbers = scalar("SELECT COUNT(enrollment_no) FROM students", TEST_DB)
    info(f"students: {scalar('SELECT COUNT(*) FROM students', TEST_DB)} records, {numbers} with an enrollment number")
    rc, err = run_file(MIGRATION_002, TEST_DB)
    check("migration 002 runs without errors", rc == 0, err)
    after = structure(TEST_DB)
    d = diff_structure(before, after)
    check("the only structural change is the new UNIQUE index on students.enrollment_no",
          d == [f"indexes {INDEX}: None -> ('0', 'enrollment_no')"], "; ".join(d[:4]))
    data_after = data_fingerprint(TEST_DB)
    check("every row of every table is unchanged (enrollment numbers, statuses, courses, links, hashes)",
          {t: v for t, v in data_after.items() if t != "schema_migrations"} == {t: v for t, v in data_before.items() if t != "schema_migrations"})
    check("schema_migrations records 002 (001 kept)", versions(TEST_DB)[:2] == ["001", "002"], str(versions(TEST_DB)))
    rc, err = run_file(MIGRATION_002, TEST_DB)
    check("running it again changes nothing (idempotent)", rc == 0 and structure(TEST_DB) == after and data_fingerprint(TEST_DB) == data_after, err)

    print("\n== Behaviour of the index")
    existing = scalar("SELECT enrollment_no FROM students WHERE enrollment_no IS NOT NULL ORDER BY id LIMIT 1", TEST_DB)
    rc, err = T.mysql_try(f"INSERT INTO students (enrollment_no, name, email, course, gender) VALUES ('{existing}', 'Dup', 'mig002.dup1@example.com', 'Data Science', 'Male')", TEST_DB)
    check("a second record with the same enrollment number is refused", rc != 0 and "uq_students_enrollment_no" in err, err)
    rc, err = T.mysql_try(f"INSERT INTO students (enrollment_no, name, email, course, gender) VALUES ('{existing.lower()}', 'Dup', 'mig002.dup2@example.com', 'Data Science', 'Male')", TEST_DB)
    check("... also in another letter case (case-insensitive collation)", rc != 0 and "uq_students_enrollment_no" in err, err)
    rc, err = T.mysql_try("INSERT INTO students (enrollment_no, name, email, course, gender) VALUES (NULL, 'No Number A', 'mig002.null1@example.com', 'Data Science', 'Male'),"
                          " (NULL, 'No Number B', 'mig002.null2@example.com', 'Data Science', 'Male')", TEST_DB)
    check("several records without an enrollment number (NULL, legacy) are still allowed", rc == 0, err)
    mysql("DELETE FROM students WHERE email LIKE 'mig002.null_@example.com'", TEST_DB)
    check("data unchanged after the behaviour checks", data_fingerprint(TEST_DB) == data_after)

    print("\n== Rollback (002_unique_enrollment_no.down.sql)")
    rc, err = run_file(ROLLBACK_002, TEST_DB)
    check("rollback runs without errors", rc == 0, err)
    check("structure after the rollback is identical to the structure before 002", not diff_structure(before, structure(TEST_DB)), "; ".join(diff_structure(before, structure(TEST_DB))[:3]))
    check("rollback removes the 002 record and changes no data", "002" not in versions(TEST_DB)
          and {t: v for t, v in data_fingerprint(TEST_DB).items() if t != "schema_migrations"} == {t: v for t, v in data_before.items() if t != "schema_migrations"})
    rc, err = run_file(ROLLBACK_002, TEST_DB)
    check("rollback can run twice", rc == 0, err)
    rc, err = run_file(MIGRATION_002, TEST_DB)
    check("migration 002 can be applied again after the rollback", rc == 0 and structure(TEST_DB) == after, err)
    return after


def precondition_tests(dump):
    print("\n== Preconditions (nothing changes when one fails)")
    prepare(PRE_DB, dump)
    first = scalar("SELECT enrollment_no FROM students WHERE enrollment_no IS NOT NULL ORDER BY id LIMIT 1", PRE_DB)
    mysql(f"INSERT INTO students (enrollment_no, name, email, course, gender) VALUES ('{first.lower()}', 'Duplicate Number', 'mig002.pre@example.com', 'Data Science', 'Male')", PRE_DB)
    before, data_before = structure(PRE_DB), data_fingerprint(PRE_DB)
    rc, err = run_file(MIGRATION_002, PRE_DB)
    check("duplicate enrollment numbers (other letter case) -> stopped with a message", rc != 0 and "used by more than one student" in err, err)
    check("... no index added, no data changed, 002 not recorded", structure(PRE_DB) == before and data_fingerprint(PRE_DB) == data_before and "002" not in versions(PRE_DB))
    T.drop_disposable(PRE_DB)

    T.create_disposable(PRE_DB)
    rc, err = run_file(T.FIXTURE, PRE_DB)
    assert rc == 0, err
    before = structure(PRE_DB)
    rc, err = run_file(MIGRATION_002, PRE_DB)
    check("a database without migration 001 -> stopped ('apply migration 001 first'), nothing changed",
          rc != 0 and "apply migration 001" in err and structure(PRE_DB) == before, err)
    T.drop_disposable(PRE_DB)


def fresh_install_tests(upgraded):
    print("\n== Fresh install from database/studenthub_demo.sql")
    T.create_disposable(FRESH_DB)
    rc, err = run_file(T.DEMO, FRESH_DB)
    check("studenthub_demo.sql imports into an empty database and records 001, 002 and the later migrations",
          rc == 0 and versions(FRESH_DB) == ["001", "002"] + [p.name[:3] for p in LATER], err)
    fresh = structure(FRESH_DB)
    for later in LATER:                              # the demo file contains the later migrations too
        rc, err = run_file(later, TEST_DB)
        assert rc == 0, f"{later.name}: {err}"
    upgraded = structure(TEST_DB)
    d = diff_structure(upgraded, fresh)
    check("fresh-install structure is identical to a database upgraded with 001 + 002 (+ the later migrations)", not d, "; ".join(d[:4]))
    rc, err = run_file(MIGRATION_002, FRESH_DB)
    check("migration 002 on a fresh install changes nothing", rc == 0 and structure(FRESH_DB) == fresh, err)
    # a database created from an earlier demo file (001 only): importing the current file is refused (apply the migrations)
    for down in LATER_DOWN + [ROLLBACK_002]:
        run_file(down, FRESH_DB)
    before = structure(FRESH_DB)
    rc, err = run_file(T.DEMO, FRESH_DB)
    check("importing the demo file into a database made by its earlier version is refused (points to the migrations), nothing changed",
          rc != 0 and "earlier version" in err and structure(FRESH_DB) == before, err)
    T.drop_disposable(FRESH_DB)


def verify_live(baseline):
    print(f"\n== READ-ONLY verification of the live database {LIVE_DB} against the dump taken before migration 002")
    prepare(TEST_DB, baseline)
    data_before = data_fingerprint(TEST_DB)
    global TEST_BASE
    TEST_BASE = PRE_DB                               # an untouched copy of the baseline for the events comparison
    T.create_disposable(PRE_DB)
    T.load_source(PRE_DB, baseline)
    rc, err = run_file(MIGRATION_002, TEST_DB)
    assert rc == 0, err
    for later in LATER:                              # later migrations that the live database has as well
        if later.name[:3] in versions(LIVE_DB):
            rc, err = run_file(later, TEST_DB)
            assert rc == 0, f"{later.name}: {err}"
    reference = structure(TEST_DB)
    d = diff_structure(reference, structure(LIVE_DB))
    check("live structure is identical to the baseline upgraded with 002 in a disposable copy", not d, "; ".join(d[:4]))
    check("live database records migration 002", "002" in versions(LIVE_DB), str(versions(LIVE_DB)))
    live = data_fingerprint(LIVE_DB)
    # events: compare the columns that existed before the later migrations (003 adds status and updated_at)
    original_events = "SELECT id, title, event_date, IFNULL(event_time,''), location, IFNULL(capacity,''), IFNULL(description,''), category, IFNULL(poster,'') FROM events ORDER BY id"
    for fp, db in ((live, LIVE_DB), (data_before, None)):
        rows = mysql(original_events, db or TEST_BASE)
        fp["events"] = (len(rows), hashlib.sha256("\n".join("\t".join(r) for r in rows).encode()).hexdigest())
    same = [t for t in ("users", "students", "events", "registrations", "menu_items") if live.get(t) == data_before.get(t)]
    check("live users (with password hashes), students, events, registrations and menu items are unchanged", len(same) == 5,
          str({t: (data_before.get(t), live.get(t)) for t in ("users", "students", "events", "registrations", "menu_items") if t not in same}))
    info("live rows: " + ", ".join(f"{t} {live[t][0]}" for t in sorted(live)))
    T.drop_disposable(TEST_DB)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dump")
    ap.add_argument("--verify-live", action="store_true")
    ap.add_argument("--baseline-dump")
    a = ap.parse_args()
    print(f"StudentHub migration 002 tests (MySQL {T.MYSQL})")
    try:
        if a.verify_live:
            if not a.baseline_dump:
                sys.exit("--verify-live needs --baseline-dump")
            verify_live(a.baseline_dump)
        else:
            T.info("source: " + (a.source_dump and "dump " + pathlib.Path(a.source_dump).name or "fixture " + T.FIXTURE.name + " + migration 001"))
            upgraded = upgrade_tests(a.source_dump)
            precondition_tests(a.source_dump)
            fresh_install_tests(upgraded)
    finally:
        for name in (TEST_DB, PRE_DB, FRESH_DB):
            T.drop_disposable(name)
        check("all disposable databases removed", not any(T.db_exists(n) for n in (TEST_DB, PRE_DB, FRESH_DB)))
    print(f"\nResult: {T.passed} passed, {T.failed} failed, {T.passed + T.failed} checks")
    return 1 if T.failed else 0


if __name__ == "__main__":
    sys.exit(main())
