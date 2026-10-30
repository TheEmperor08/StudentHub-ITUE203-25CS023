"""StudentHub - checks the corrected reports in submission-reports/ (run after build_reports.py).

    python tools\\reports\\check_reports.py

For every pNN module: the DOCX exists, every figure path used in the module exists in the repository (only evidence/
screenshots), every excerpt marker is found in its source file, no placeholder markers (TODO, lorem ipsum, XXX, TBD, FIXME) is in the
document, and the PDF (if exported) exists and is newer than the DOCX. Prints the page count of each PDF.
"""
import pathlib, re, sys
from docx import Document

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "submission-reports"
problems = []
for mod in sorted(HERE.glob("p[0-9][0-9].py")):
    n = int(mod.stem[1:])
    src = mod.read_text(encoding="utf-8")
    docx = next((d for d in (OUT / f"PRAC_{n}_ITUE203_25CS023_corrected.docx", OUT / f"PRAC_{n}_ITUE203_25CS023.docx") if d.exists()), OUT / f"PRAC_{n}_ITUE203_25CS023_corrected.docx")
    if not docx.exists():
        problems.append(f"P{n}: {docx.name} missing")
        continue
    figures = re.findall(r'figure\(\s*["\']([^"\']+)["\']', src)
    for f in figures:
        if not f.startswith("evidence/") or not (ROOT / f).is_file():
            problems.append(f"P{n}: figure not a genuine evidence file: {f}")
    for file, start, end in re.findall(r'excerpt\(\s*["\']([^"\']+)["\']\s*,\s*["\']((?:[^"\'\\]|\\.)*)["\']\s*,\s*["\']((?:[^"\'\\]|\\.)*)["\']', src):
        text = (ROOT / file).read_text(encoding="utf-8") if (ROOT / file).is_file() else None
        if text is None or start.encode().decode("unicode_escape") not in text:
            problems.append(f"P{n}: excerpt marker not found: {file} :: {start[:40]}")
    d = Document(str(docx))
    body = "\n".join(p.text for p in d.paragraphs) + "\n".join(c.text for t in d.tables for row in t.rows for c in row.cells)
    for bad in ("TODO", "lorem ipsum", "XXX", "TBD", "[placeholder]", "<placeholder>", "FIXME"):
        if bad.lower() in body.lower():
            problems.append(f"P{n}: placeholder text '{bad}' found")
    pdf = docx.with_suffix(".pdf")
    pages = "no PDF"
    if pdf.exists():
        pages = f"{len(re.findall(rb'/Type\s*/Page[^s]', pdf.read_bytes()))} pages"
        if pdf.stat().st_mtime < docx.stat().st_mtime:
            problems.append(f"P{n}: PDF is older than the DOCX")
    print(f"P{n:>2}: {len(d.inline_shapes):>2} images, {len(d.tables):>2} tables, {sum(1 for p in d.paragraphs if p.style.name.startswith('Heading'))} headings, {pages}")
for p in problems:
    print("PROBLEM", p)
print("all reports OK" if not problems else f"{len(problems)} problem(s)")
sys.exit(1 if problems else 0)
