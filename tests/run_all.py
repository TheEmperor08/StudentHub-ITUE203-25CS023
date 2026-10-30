"""StudentHub - runs the complete test suite of the integrated portal and prints one summary.

    python tests\\run_all.py                    # database + HTTP suites + Practical 15 snapshot
    python tests\\run_all.py --browser PYTHON   # also the Microsoft Edge suites (PYTHON = interpreter with Playwright)

Every suite uses its own disposable database (and a temporary poster folder); the live studenthub_db is only read.
"""
import argparse, pathlib, re, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[1]
SUITES = [
    ("Practical 8 – migration 001 and portal", "database/tests/test_001_practical8_foundation.py"),
    ("Practical 11 – migration 002", "database/tests/test_002_unique_enrollment_no.py"),
    ("Practical 12 – migration 003", "database/tests/test_003_event_management.py"),
    ("Practical 14 – migration 004", "database/tests/test_004_admin_dashboard.py"),
    ("Practical 7 – migration 005", "database/tests/test_005_inquiries.py"),
    ("Practicals 9/10 – registration, login, sessions, RBAC", "tests/test_auth.py"),
    ("Practical 11 – student management", "tests/test_students.py"),
    ("Practical 12 – events, posters, registration", "tests/test_events.py"),
    ("Practical 13 – JSON API, Event Finder", "tests/test_api.py"),
    ("Practical 14 – admin dashboard", "tests/test_dashboard.py"),
    ("Practicals 5–7 – validation, Data Explorer, inquiries", "tests/test_forms.py"),
    ("Practical 15 – snapshot", "tests/test_snapshot.py"),
]
BROWSER = [
    ("Edge – registration, login, RBAC", "tests/browser_auth.py"),
    ("Edge – student management", "tests/browser_students.py"),
    ("Edge – inactive student login", "tests/browser_inactive_login.py"),
    ("Edge – event management", "tests/browser_events.py"),
    ("Edge – Event Finder (Fetch API)", "tests/browser_api.py"),
    ("Edge – admin dashboard", "tests/browser_dashboard.py"),
    ("Edge – Practicals 5–7", "tests/browser_forms.py"),
    ("Edge – end-to-end (Practical 15)", "tests/browser_e2e.py"),
]


def run(python, script, extra=()):
    start = time.time()
    r = subprocess.run([python, script, *extra], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    found = re.findall(r"(?:Result|browser checks): (\d+) passed, (\d+) failed", r.stdout)    # the suite's own (last) summary line
    ok, bad = (int(found[-1][0]), int(found[-1][1])) if found else (0, 1)
    return ok, bad, r.returncode, round(time.time() - start), [l for l in r.stdout.splitlines() if l.startswith("FAIL")]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--browser", metavar="PYTHON", help="interpreter with Playwright for the Edge suites")
    ap.add_argument("--shots", default=None, help="screenshot folder for the Edge suites (default: a temporary folder)")
    a = ap.parse_args()
    jobs = [(n, s, sys.executable, ()) for n, s in SUITES]
    if a.browser:
        import tempfile
        shots = a.shots or tempfile.mkdtemp(prefix="studenthub-shots-")
        jobs += [(n, s, a.browser, (shots,)) for n, s in BROWSER]
    total_ok = total_bad = 0
    print(f"{'Suite':58} {'passed':>7} {'failed':>7} {'time':>6}")
    for name, script, python, extra in jobs:
        ok, bad, rc, secs, fails = run(python, script, extra)
        total_ok, total_bad = total_ok + ok, total_bad + bad + (1 if rc and not bad else 0)
        print(f"{name:58} {ok:7} {bad:7} {secs:5}s" + ("" if rc == 0 else "  <-- exit code " + str(rc)))
        for f in fails[:5]:
            print("    " + f)
    print(f"{'TOTAL':58} {total_ok:7} {total_bad:7}")
    return 1 if total_bad else 0


if __name__ == "__main__":
    sys.exit(main())
