"""StudentHub - tests of migration 003 (event management, Practical 12).
Python 3, standard library only; reuses the helpers of test_001_practical8_foundation.py.

    python database\\tests\\test_003_event_management.py                          # fixture + migrations 001 and 002
    python database\\tests\\test_003_event_management.py --source-dump <dump.sql>  # a real dump in a disposable DB
    python database\\tests\\test_003_event_management.py --verify-live --baseline-dump <dump taken before 003>

Every disposable database carries a marker table and is dropped at the end; the live studenthub_db is only read.
"""
import argparse, hashlib, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import test_001_practical8_foundation as T  # noqa: E402

MIGRATIONS = T.ROOT / "database" / "migrations"
M001, M002 = MIGRATIONS / "001_practical8_foundation.sql", MIGRATIONS / "002_unique_enrollment_no.sql"
M003, DOWN003 = MIGRATIONS / "003_event_management.sql", MIGRATIONS / "003_event_management.down.sql"
LATER = sorted(p for p in MIGRATIONS.glob("0*.sql") if not p.name.endswith(".down.sql") and p.name[:3] > "003")
LATER_DOWN = [p.with_name(p.name[:-4] + ".down.sql") for p in reversed(LATER)]
TEST_DB, PRE_DB, FRESH_DB, LIVE_DB = "studenthub_mig003_test", "studenthub_mig003_pre", "studenthub_mig003_fresh", "studenthub_db"
check, info, mysql, scalar, run_file, structure, diff_structure = T.check, T.info, T.mysql, T.scalar, T.run_file, T.structure, T.diff_structure


def data_fingerprint(db, tables=None):
    out = {}
    for (t,) in mysql(f"SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA='{db}' AND TABLE_NAME <> '{T.MARKER}' ORDER BY 1"):
        if tables is None or t in tables:
            rows = mysql(f"SELECT * FROM `{t}` ORDER BY 1", db)
            out[t] = (len(rows), hashlib.sha256("\n".join("\t".join(r) for r in rows).encode()).hexdigest())
    return out


def event_columns(db):
    """the original events columns, as they were before 003"""
    return mysql("SELECT id, title, event_date, IFNULL(event_time,''), location, IFNULL(capacity,''), IFNULL(description,''), category, "
                 "IFNULL(poster,''), IFNULL(created_at,'') FROM events ORDER BY id", db)


def versions(db):
    return [r[0] for r in mysql("SELECT version FROM schema_migrations ORDER BY version", db)]


def prepare(db, dump):
    """disposable copy of the source in the state migration 003 expects (001 and 002 applied, nothing later)"""
    T.create_disposable(db)
    T.load_source(db, dump)
    have = versions(db) if mysql(f"SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA='{db}' AND TABLE_NAME='schema_migrations'") else []
    for migration in (M001, M002):
        if migration.name[:3] not in have:
            rc, err = run_file(migration, db)
            assert rc == 0, f"{migration.name}: {err}"
    if "003" in versions(db):
        for down in LATER_DOWN + [DOWN003]:
            rc, err = run_file(down, db)
            assert rc == 0, f"{down.name}: {err}"


def upgrade_tests(dump):
    print("\n== Migration 003 on the source")
    prepare(TEST_DB, dump)
    before = structure(TEST_DB)
    events_before = event_columns(TEST_DB)
    others = [t for t in before["tables"] if t not in ("events", "schema_migrations")]
    data_before = data_fingerprint(TEST_DB, others)
    categories = sorted({r[7] for r in events_before})
    info(f"events: {len(events_before)}, categories in use: {', '.join(categories)}")
    rc, err = run_file(M003, TEST_DB)
    check("migration 003 runs without errors", rc == 0, err)
    after = structure(TEST_DB)
    d = diff_structure(before, after)
    expected = {"tables event_categories", "columns ('event_categories', 'name')", "columns ('event_categories', 'description')",
                "columns ('events', 'status')", "columns ('events', 'updated_at')", "indexes ('event_categories', 'PRIMARY')",
                "indexes ('events', 'uq_events_poster')", "indexes ('events', 'idx_events_status')", "indexes ('events', 'idx_events_category')",
                "fks ('events', 'fk_events_category')"}
    added = {x.split(":")[0] for x in d}
    shifted = {x.split(":")[0] for x in d if x.startswith("columns ('events'") and "-> None" not in x and "None ->" not in x}
    check("structural changes: event_categories, events.status/updated_at, poster/status/category indexes and the category FK only",
          added - shifted == expected and all(x.startswith("columns ('events', ") for x in shifted), "; ".join(sorted(added - expected)))
    check("events.status ENUM('open','closed') NOT NULL DEFAULT 'open' after capacity; updated_at nullable after created_at",
          after["columns"][("events", "status")][1:4] == ("enum('open','closed')", "NO", "'open'")
          and int(after["columns"][("events", "status")][0]) == int(after["columns"][("events", "capacity")][0]) + 1
          and after["columns"][("events", "updated_at")][2] == "YES")
    check("fk_events_category -> event_categories.name ON UPDATE CASCADE, ON DELETE RESTRICT",
          after["fks"].get(("events", "fk_events_category")) == ("category", "event_categories", "name", "CASCADE", "RESTRICT"))
    check("every original event value is unchanged (titles, dates, times, locations, capacities, categories, posters)",
          event_columns(TEST_DB) == events_before)
    check("existing events are 'open' and have no update time yet", scalar("SELECT COUNT(*) FROM events WHERE status <> 'open' OR updated_at IS NOT NULL", TEST_DB) == "0")
    cats = [r[0] for r in mysql("SELECT name FROM event_categories ORDER BY name", TEST_DB)]
    check("event_categories = Practical 12's six categories + every category already used",
          set(cats) == {"Cultural", "Hackathon", "Seminar", "Sports", "Technical", "Workshop"} | set(categories), str(cats))
    check("all other tables unchanged (students, users with password hashes, registrations, audit log, menu)",
          data_fingerprint(TEST_DB, others) == data_before)
    check("schema_migrations records 003", versions(TEST_DB)[-1] == "003", str(versions(TEST_DB)))
    snap = (after, data_fingerprint(TEST_DB))
    rc, err = run_file(M003, TEST_DB)
    check("running it again changes nothing (idempotent)", rc == 0 and (structure(TEST_DB), data_fingerprint(TEST_DB)) == snap, err)

    print("\n== Behaviour")
    rc, err = T.mysql_try("INSERT INTO events (title, event_date, location, category) VALUES ('Bad category', '2027-01-01', 'X', 'No Such Category')", TEST_DB)
    check("an event with an unknown category is refused (fk_events_category)", rc != 0 and "fk_events_category" in err, err)
    rc, err = T.mysql_try("INSERT INTO events (title, event_date, location, category, status) VALUES ('Bad status', '2027-01-01', 'X', 'Workshop', 'maybe')", TEST_DB)
    check("an unknown status is refused or not stored as such", rc != 0 or scalar("SELECT COUNT(*) FROM events WHERE status='maybe'", TEST_DB) == "0", err)
    mysql("DELETE FROM events WHERE title='Bad status'", TEST_DB)
    mysql("INSERT INTO events (title, event_date, location, category, poster) VALUES ('Poster A', '2027-01-01', 'X', 'Workshop', 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.png')", TEST_DB)
    rc, err = T.mysql_try("INSERT INTO events (title, event_date, location, category, poster) VALUES ('Poster B', '2027-01-01', 'X', 'Workshop', 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.png')", TEST_DB)
    check("two events cannot share one poster (uq_events_poster); several events without a poster are fine", rc != 0 and "uq_events_poster" in err, err)
    rc, err = T.mysql_try("DELETE FROM event_categories WHERE name='Workshop'", TEST_DB)
    check("a category that is in use cannot be deleted (ON DELETE RESTRICT)", rc != 0, err)
    mysql("UPDATE event_categories SET name='Workshops' WHERE name='Workshop'", TEST_DB)
    check("renaming a category updates its events (ON UPDATE CASCADE)", scalar("SELECT COUNT(*) FROM events WHERE category='Workshop'", TEST_DB) == "0"
          and int(scalar("SELECT COUNT(*) FROM events WHERE category='Workshops'", TEST_DB)) >= 1)
    mysql("UPDATE event_categories SET name='Workshop' WHERE name='Workshops'", TEST_DB)
    mysql("UPDATE events SET location = 'Y' WHERE title = 'Poster A'", TEST_DB)
    check("updated_at is set automatically when an event changes", scalar("SELECT updated_at IS NOT NULL FROM events WHERE title='Poster A'", TEST_DB) == "1")
    mysql("DELETE FROM events WHERE title='Poster A'", TEST_DB)

    print("\n== Rollback (003_event_management.down.sql)")
    rc, err = run_file(DOWN003, TEST_DB)
    check("rollback runs without errors", rc == 0, err)
    d = diff_structure(before, structure(TEST_DB))
    check("structure after the rollback is identical to the structure before 003", not d, "; ".join(d[:3]))
    check("rollback keeps every original event value and removes the 003 record", event_columns(TEST_DB) == events_before and "003" not in versions(TEST_DB))
    rc, err = run_file(DOWN003, TEST_DB)
    check("rollback can run twice", rc == 0, err)
    rc, err = run_file(M003, TEST_DB)
    check("migration 003 can be applied again after the rollback", rc == 0 and not diff_structure(after, structure(TEST_DB)), err)
    return structure(TEST_DB)


def precondition_tests(dump):
    print("\n== Preconditions (nothing changes when one fails)")
    prepare(PRE_DB, dump)
    poster = "uploads/duplicate_poster.jpg"
    mysql(f"INSERT INTO events (title, event_date, location, category, poster) VALUES ('Dup 1', '2027-01-01', 'X', 'Workshop', '{poster}'), "
          f"('Dup 2', '2027-01-02', 'X', 'Workshop', '{poster}')", PRE_DB)
    before, data = structure(PRE_DB), data_fingerprint(PRE_DB)
    rc, err = run_file(M003, PRE_DB)
    check("two events with the same poster value -> stopped with a message, nothing changed",
          rc != 0 and "same poster" in err and structure(PRE_DB) == before and data_fingerprint(PRE_DB) == data, err)
    T.drop_disposable(PRE_DB)
    T.create_disposable(PRE_DB)
    T.load_source(PRE_DB, dump)
    if "002" not in (versions(PRE_DB) if mysql(f"SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA='{PRE_DB}' AND TABLE_NAME='schema_migrations'") else []):
        before = structure(PRE_DB)
        rc, err = run_file(M003, PRE_DB)
        check("a database without migrations 001/002 -> stopped ('apply migrations 001 and 002 first'), nothing changed",
              rc != 0 and "apply migrations 001 and 002" in err and structure(PRE_DB) == before, err)
    T.drop_disposable(PRE_DB)


def fresh_install_tests(upgraded):
    print("\n== Fresh install from database/studenthub_demo.sql")
    T.create_disposable(FRESH_DB)
    rc, err = run_file(T.DEMO, FRESH_DB)
    check("studenthub_demo.sql imports into an empty database and records 001, 002, 003 (+ later)",
          rc == 0 and versions(FRESH_DB)[:3] == ["001", "002", "003"], err)
    for later in LATER:
        rc, err = run_file(later, TEST_DB)
        assert rc == 0, f"{later.name}: {err}"
    d = diff_structure(structure(TEST_DB), structure(FRESH_DB))
    check("fresh-install structure is identical to a database upgraded with the migrations", not d, "; ".join(d[:4]))
    fresh = structure(FRESH_DB)
    rc, err = run_file(M003, FRESH_DB)
    check("migration 003 on a fresh install changes nothing", rc == 0 and structure(FRESH_DB) == fresh, err)
    T.drop_disposable(FRESH_DB)


def verify_live(baseline):
    print(f"\n== READ-ONLY verification of the live database {LIVE_DB} against the dump taken before migration 003")
    prepare(TEST_DB, baseline)
    events_before = event_columns(TEST_DB)
    others = ("users", "students", "registrations", "menu_items")
    data_before = data_fingerprint(TEST_DB, others)
    rc, err = run_file(M003, TEST_DB)
    assert rc == 0, err
    for later in LATER:
        if later.name[:3] in versions(LIVE_DB):
            rc, err = run_file(later, TEST_DB)
            assert rc == 0, f"{later.name}: {err}"
    d = diff_structure(structure(TEST_DB), structure(LIVE_DB))
    check("live structure is identical to the baseline upgraded with 003 in a disposable copy", not d, "; ".join(d[:4]))
    check("live database records migration 003", "003" in versions(LIVE_DB))
    check("every original live event value is unchanged", event_columns(LIVE_DB) == events_before)
    check("live users (with password hashes), students, registrations and menu items are unchanged", data_fingerprint(LIVE_DB, others) == data_before)
    info("live event categories: " + ", ".join(r[0] for r in mysql("SELECT name FROM event_categories ORDER BY name", LIVE_DB)))
    T.drop_disposable(TEST_DB)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dump")
    ap.add_argument("--verify-live", action="store_true")
    ap.add_argument("--baseline-dump")
    a = ap.parse_args()
    print(f"StudentHub migration 003 tests (MySQL {T.MYSQL})")
    try:
        if a.verify_live:
            if not a.baseline_dump:
                sys.exit("--verify-live needs --baseline-dump")
            verify_live(a.baseline_dump)
        else:
            info("source: " + (a.source_dump and "dump " + pathlib.Path(a.source_dump).name or "fixture " + T.FIXTURE.name + " + migrations 001, 002"))
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
