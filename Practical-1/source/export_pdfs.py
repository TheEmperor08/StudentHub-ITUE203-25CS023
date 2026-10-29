"""Exports the existing Practical 1 diagrams (PNG renders of the SVG originals) to A4 landscape PDFs.

    python Practical-1/source/export_pdfs.py

Writes Practical-1/PRAC_1_Sitemap_25CS023.pdf (1 page) and Practical-1/PRAC_1_Wireframes_25CS023.pdf (3 pages).
Images are stored losslessly (Flate), so lines and text in the diagrams stay sharp. Needs Pillow.
"""
import os
import zlib

from PIL import Image

P1 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE_W, PAGE_H = 841.89, 595.28          # A4 landscape, points
MARGIN, FOOTER = 28, 22
AUTHOR = "Shreyas (25CS023)"


def pdf_text(s):
    return s.encode("cp1252").replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def write_pdf(out_name, title, pages):
    """pages: list of (png file name, footer caption)."""
    objs = []

    def add(body):
        objs.append(body)
        return len(objs)

    catalog = add(None)
    page_tree = add(None)
    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    kids = []
    for n, (png, caption) in enumerate(pages, 1):
        im = Image.open(os.path.join(P1, png)).convert("RGB")
        w, h = im.size
        data = zlib.compress(im.tobytes(), 9)
        img = add(b"<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace /DeviceRGB "
                  b"/BitsPerComponent 8 /Filter /FlateDecode /Length %d >>\nstream\n" % (w, h, len(data))
                  + data + b"\nendstream")
        area_w, area_h = PAGE_W - 2 * MARGIN, PAGE_H - 2 * MARGIN - FOOTER
        scale = min(area_w / w, area_h / h)
        dw, dh = w * scale, h * scale
        x = (PAGE_W - dw) / 2
        y = MARGIN + FOOTER + (area_h - dh) / 2
        footer = f"ITUE203 Web Development Frameworks – Practical 1 – {AUTHOR} – {caption} – Page {n} of {len(pages)}"
        content = (b"q %.2f 0 0 %.2f %.2f %.2f cm /Im1 Do Q\n" % (dw, dh, x, y)
                   + b"BT /F1 8 Tf 0.36 0.39 0.47 rg %.2f %.2f Td (" % (MARGIN, MARGIN) + pdf_text(footer) + b") Tj ET\n")
        stream = add(b"<< /Length %d >>\nstream\n" % len(content) + content + b"endstream")
        kids.append(add(b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %.2f %.2f] /Contents %d 0 R "
                        b"/Resources << /XObject << /Im1 %d 0 R >> /Font << /F1 %d 0 R >> >> >>"
                        % (page_tree, PAGE_W, PAGE_H, stream, img, font)))
    objs[catalog - 1] = b"<< /Type /Catalog /Pages %d 0 R >>" % page_tree
    objs[page_tree - 1] = (b"<< /Type /Pages /Count %d /Kids [" % len(kids)
                           + b" ".join(b"%d 0 R" % k for k in kids) + b"] >>")
    info = add(b"<< /Title (" + pdf_text(title) + b") /Author (" + pdf_text(AUTHOR)
               + b") /Subject (ITUE203 Practical 1) /Producer (Practical-1/source/export_pdfs.py) >>")

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root %d 0 R /Info %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, catalog, info, xref)
    with open(os.path.join(P1, out_name), "wb") as fh:
        fh.write(out)
    print("wrote", out_name, f"({len(pages)} page{'s' if len(pages) > 1 else ''}, {len(out) // 1024} KB)")


write_pdf("PRAC_1_Sitemap_25CS023.pdf", "StudentHub – Sitemap & Navigation Flow",
          [("sitemap.png", "Sitemap")])
write_pdf("PRAC_1_Wireframes_25CS023.pdf", "StudentHub – Low-Fidelity Wireframes",
          [("wireframe-1-dashboard-desktop.png", "Wireframe 1: Student dashboard (desktop)"),
           ("wireframe-2-home-login-desktop.png", "Wireframe 2: Home page and login (desktop)"),
           ("wireframe-3-mobile.png", "Wireframe 3: Mobile screens")])
