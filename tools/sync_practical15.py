"""StudentHub - makes Practical-15/ an exact snapshot of the canonical application studenthub/ (Practical 15).

    python tools\\sync_practical15.py            # copy, remove stale app files, write Practical-15/SNAPSHOT.md
    python tools\\sync_practical15.py --check    # only verify (exit code 1 if the snapshot differs)

Only files tracked by Git in studenthub/ are copied (uploaded posters and other local files are never copied).
Practical-15/README.md and Practical-15/SNAPSHOT.md are the only files of the snapshot folder that are not application files.
The previous independently kept copy of Practical 15 remains available in the Git history.
"""
import argparse, hashlib, pathlib, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC, DST = ROOT / "studenthub", ROOT / "Practical-15"
OWN = {"README.md", "SNAPSHOT.md"}


def tracked():
    out = subprocess.run(["git", "ls-files", "-z", "studenthub"], cwd=ROOT, capture_output=True, check=True).stdout.decode("utf-8")
    return sorted(pathlib.PurePosixPath(p).relative_to("studenthub").as_posix() for p in out.split("\0") if p)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def differences(files):
    problems = []
    for rel in files:
        a, b = SRC / rel, DST / rel
        if not b.is_file():
            problems.append(f"missing in Practical-15: {rel}")
        elif a.read_bytes() != b.read_bytes():
            problems.append(f"differs: {rel}")
    wanted = set(files) | OWN
    for p in DST.rglob("*"):
        rel = p.relative_to(DST).as_posix()
        if p.is_file() and rel not in wanted and not (rel.startswith("uploads/") and rel not in ("uploads/.htaccess", "uploads/.gitkeep")):
            problems.append(f"extra file in Practical-15: {rel}")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    files = tracked()
    if not a.check:
        for rel in files:
            target = DST / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SRC / rel, target)
        wanted = set(files) | OWN
        for p in sorted(DST.rglob("*"), reverse=True):
            rel = p.relative_to(DST).as_posix()
            if p.is_file() and rel not in wanted and not rel.startswith("uploads/"):
                p.unlink()
            elif p.is_dir() and not any(p.iterdir()):
                p.rmdir()
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        lines = ["# Practical 15 snapshot manifest", "",
                 "`Practical-15/` is an exact copy of the canonical application `studenthub/` (all files tracked by Git), made with",
                 "`python tools/sync_practical15.py` and verified with `python tools/sync_practical15.py --check` and `tests/test_snapshot.py`.",
                 f"Base commit when the copy was made: `{commit}` (the copied files may include changes committed together with this manifest).", "",
                 f"{len(files)} files, SHA-256:", "", "```"]
        lines += [f"{sha(SRC / rel)}  {rel}" for rel in files]
        lines += ["```", ""]
        (DST / "SNAPSHOT.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
        print(f"Practical-15 synchronised: {len(files)} files")
    problems = differences(files)
    manifest = (DST / "SNAPSHOT.md").read_text(encoding="utf-8") if (DST / "SNAPSHOT.md").exists() else ""
    stale = [rel for rel in files if f"{sha(SRC / rel)}  {rel}" not in manifest]
    for p in problems + [f"not in SNAPSHOT.md (or other hash): {rel}" for rel in stale]:
        print("DIFF ", p)
    print("snapshot OK" if not problems and not stale else f"snapshot differs: {len(problems) + len(stale)} problem(s)")
    return 1 if problems or stale else 0


if __name__ == "__main__":
    sys.exit(main())
