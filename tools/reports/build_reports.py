"""StudentHub - builds the corrected practical reports into submission-reports/ (DOCX, and PDF with Microsoft Word).

    python tools\\reports\\build_reports.py               # all reports p05 ... p15 (DOCX only)
    python tools\\reports\\build_reports.py 11 12 --pdf   # selected reports, plus PDF export through Word (Windows)

Each report is a module tools/reports/pNN.py with META = {number, title, tech, supersedes, replaces_note} and build(r).
The original reports in the Practical-N folders are never changed; submission-reports/INDEX.md lists what replaces what.
"""
import argparse, importlib, pathlib, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from report_lib import OUT_DIR, ROOT, Report, report_file  # noqa: E402


def to_pdf(docx):
    pdf = docx.with_suffix(".pdf")
    ps = ("$w = New-Object -ComObject Word.Application; $w.Visible = $false; "
          f"$d = $w.Documents.Open('{docx}', $false, $true); $d.ExportAsFixedFormat('{pdf}', 17); $d.Close($false); $w.Quit()")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    if r.returncode or not pdf.exists():
        raise RuntimeError(f"PDF export failed for {docx.name}: {r.stderr[-300:]}")
    return pdf


def write_index(modules):
    lines = ["# Corrected ITUE203 practical reports – index", "",
             "These files are the corrected submissions for manual upload after checking. They describe each practical as part of the",
             "one integrated StudentHub portal (`studenthub/`, database `studenthub_db`). The original reports are **not** changed and stay",
             "in their `Practical-N/` folders. Nothing has been uploaded to Microsoft Teams automatically.", "",
             "| Practical | Corrected report (DOCX / PDF) | Supersedes | Why it was replaced |", "|---|---|---|---|"]
    for m in modules:
        meta = m.META
        name = report_file(meta["number"], meta["supersedes"])[:-5]
        lines.append(f"| {meta['number']} | `{name}.docx` / `{name}.pdf` | {f"`{meta['supersedes']}`" if meta['supersedes'] else '— (no earlier report)'} | {meta['replaces_note']} |")
    lines += ["", "Practicals 1–4 were not rewritten: their reports describe planning, static pages, layout and DOM features that are",
              "unchanged in the integrated portal (see TEST_REPORT.md, section 12).", ""]
    (OUT_DIR / "INDEX.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("numbers", nargs="*", type=int)
    ap.add_argument("--pdf", action="store_true")
    a = ap.parse_args()
    available = sorted(int(p.stem[1:]) for p in HERE.glob("p[0-9][0-9].py"))
    selected = a.numbers or available
    for n in selected:
        mod = importlib.import_module(f"p{n:02d}")
        meta = mod.META
        r = Report(meta["number"], meta["title"], meta["tech"], meta["supersedes"])
        mod.build(r)
        out = r.save()
        print(f"built {out.relative_to(ROOT)} ({r.figure_no} figures)")
        if a.pdf:
            print(f"      {to_pdf(out).relative_to(ROOT)}")
    write_index([importlib.import_module(f"p{n:02d}") for n in available])
    print(f"index: {(OUT_DIR / 'INDEX.md').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
