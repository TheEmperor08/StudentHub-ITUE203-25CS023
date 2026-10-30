"""StudentHub - verifies that Practical-15/ is the final snapshot of the canonical application studenthub/ and that it works.

    python tests\\test_snapshot.py

1. tools/sync_practical15.py --check: every tracked file of studenthub/ is byte-for-byte identical in Practical-15/, no
   extra application files, every SHA-256 in Practical-15/SNAPSHOT.md matches.
2. The authentication suite (tests/test_auth.py) and the events API suite (tests/test_api.py) run against Practical-15/
   (STUDENTHUB_APP_DIR), on their own disposable databases.
"""
import os, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
passed = failed = 0
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def check(name, ok, detail=""):
    global passed, failed
    passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))


def main():
    print("StudentHub Practical 15 snapshot tests")
    r = subprocess.run([sys.executable, "tools/sync_practical15.py", "--check"], cwd=ROOT, capture_output=True, text=True)
    check("tools/sync_practical15.py --check: Practical-15/ is byte-for-byte identical to studenthub/ and SNAPSHOT.md matches",
          r.returncode == 0 and "snapshot OK" in r.stdout, r.stdout[-400:])
    tracked = subprocess.run(["git", "ls-files", "studenthub"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    manifest = (ROOT / "Practical-15" / "SNAPSHOT.md").read_text(encoding="utf-8")
    check(f"SNAPSHOT.md lists all {len(tracked)} tracked application files", all(p.split("/", 1)[1] in manifest for p in tracked))
    check("the snapshot folder has no separate database or configuration of its own (no schema.sql, no config files)",
          not any((ROOT / "Practical-15" / n).exists() for n in ("schema.sql", "config.local.php", ".env")))
    env = dict(os.environ, STUDENTHUB_APP_DIR=str(ROOT / "Practical-15"))
    for suite in ("test_auth.py", "test_api.py"):
        r = subprocess.run([sys.executable, f"tests/{suite}"], cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        m = re.search(r"Result: (\d+) passed, (\d+) failed", r.stdout)
        check(f"tests/{suite} against Practical-15/: {m.group(0) if m else 'no result'}", r.returncode == 0 and m is not None and m.group(2) == "0",
              (r.stdout + r.stderr)[-400:])
    print(f"\nResult: {passed} passed, {failed} failed, {passed + failed} checks")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
