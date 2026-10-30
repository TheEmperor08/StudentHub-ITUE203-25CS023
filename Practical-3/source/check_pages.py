"""Local structure, link, accessibility and CSS-organisation checks for the Practical 3 pages
(Python standard library only). Not the W3C validator: it checks only the rules coded below.

    python Practical-3/source/check_pages.py
"""
import base64
import hashlib
import os
import re
from html.parser import HTMLParser

P3 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = {  # page -> files it must load (the technique it demonstrates)
    "index.html": ["assets/css/base.css", "assets/css/flex.css"],
    "about.html": ["assets/css/base.css", "assets/css/flex.css"],
    "dashboard.html": ["assets/css/base.css", "assets/css/grid.css"],
    "events.html": ["assets/css/base.css", "assets/css/grid.css"],
    "register.html": ["vendor/bootstrap-5.3.3/css/bootstrap.min.css", "assets/css/bootstrap-custom.css",
                      "vendor/bootstrap-5.3.3/js/bootstrap.bundle.min.js"],
    "login.html": ["vendor/bootstrap-5.3.3/css/bootstrap.min.css", "assets/css/bootstrap-custom.css",
                   "vendor/bootstrap-5.3.3/js/bootstrap.bundle.min.js"],
}
CSS = ["assets/css/base.css", "assets/css/flex.css", "assets/css/grid.css", "assets/css/bootstrap-custom.css"]
CSS_MUST_CONTAIN = {
    "assets/css/flex.css": ["display: flex", "flex-wrap: wrap", "flex-direction", "@media (min-width: 768px)"],
    "assets/css/grid.css": ["display: grid", "grid-template-areas", "repeat(auto-fit", "repeat(auto-fill",
                            "@media (min-width: 1024px)"],
}
# Published Subresource Integrity hashes of Bootstrap 5.3.3 (getbootstrap.com)
VENDOR_SRI = {
    "vendor/bootstrap-5.3.3/css/bootstrap.min.css": "sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH",
    "vendor/bootstrap-5.3.3/js/bootstrap.bundle.min.js": "sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz",
}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.elements, self.errors = [], [], []
        self.label_depth = 0
        self.title = ""
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        line = self.getpos()[0]
        self.elements.append((tag, a, line, self.label_depth > 0))
        if tag == "label":
            self.label_depth += 1
        if tag == "title":
            self.in_title = True
        if tag not in VOID:
            self.stack.append((tag, line))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if tag == "label":
            self.label_depth -= 1
        if tag == "title":
            self.in_title = False
        if not self.stack or self.stack[-1][0] != tag:
            self.errors.append(f"line {self.getpos()[0]}: unexpected </{tag}>")
        else:
            self.stack.pop()

    def handle_data(self, data):
        if self.in_title:
            self.title += data


def parse(name):
    p = Page()
    p.src = open(os.path.join(P3, name), encoding="utf-8").read()
    p.feed(p.src)
    return p


def check_page(name, p, pages):
    errs = list(p.errors)
    if p.stack:
        errs.append(f"unclosed elements {p.stack}")
    els = p.elements
    tags = [e[0] for e in els]
    attrs_of = lambda t: [e[1] for e in els if e[0] == t]
    if not p.src.startswith("<!DOCTYPE html>"):
        errs.append("missing doctype")
    if attrs_of("html")[0].get("lang") != "en":
        errs.append("html lang")
    if not any("charset" in a for a in attrs_of("meta")):
        errs.append("no charset")
    if not any(a.get("name") == "viewport" for a in attrs_of("meta")):
        errs.append("no viewport meta")
    if not p.title.strip():
        errs.append("empty title")
    for t in ("header", "nav", "main", "footer"):
        if t not in tags:
            errs.append(f"no <{t}>")
    if tags.count("main") != 1 or attrs_of("main")[0].get("id") != "main-content":
        errs.append("needs exactly one <main id=main-content>")
    if attrs_of("a")[0].get("href") != "#main-content":
        errs.append("skip link is not the first link")
    # headings
    levels = [int(t[1]) for t in tags if re.fullmatch(r"h[1-6]", t)]
    if levels.count(1) != 1:
        errs.append(f"h1 count {levels.count(1)}")
    for a, b in zip(levels, levels[1:]):
        if b > a + 1:
            errs.append(f"heading jump h{a}->h{b}")
    # ids, labels, images
    ids = [e[1]["id"] for e in els if "id" in e[1]]
    if len(ids) != len(set(ids)):
        errs.append("duplicate ids")
    label_for = {e[1].get("for") for e in els if e[0] == "label"}
    for tag, a, line, wrapped in els:
        if tag in ("input", "select", "textarea", "meter") and a.get("type") not in ("submit", "reset", "button", "hidden"):
            if not wrapped and a.get("id") not in label_for:
                errs.append(f"line {line}: <{tag}> without label")
        if tag == "img" and "alt" not in a:
            errs.append(f"line {line}: img without alt attribute")
        if "style" in a:
            errs.append(f"line {line}: inline style attribute")
        if tag == "style":
            errs.append(f"line {line}: <style> element")
        if tag == "form" and "action" in a:
            errs.append(f"line {line}: form with action")
        if tag == "button" and a.get("type") == "submit" and "disabled" not in a:
            errs.append(f"line {line}: enabled submit button")
        if tag == "table" and not any(e[0] == "caption" for e in els):
            errs.append("table without caption")
        if tag == "th" and "scope" not in a:
            errs.append(f"line {line}: th without scope")
    for f in label_for:
        if f not in ids:
            errs.append(f"label for={f} has no target")
    # no external resources: the pages work offline
    if re.search(r"(src|href)=\"(https?:)?//", p.src):
        errs.append("external URL in page")
    # local references (links, stylesheets, scripts, images) must exist
    refs = [(a.get("href") or a.get("src")) for t, a, _, _ in els if t in ("a", "link", "script", "img") and (a.get("href") or a.get("src"))]
    for ref in refs:
        if ref.startswith("mailto:"):
            continue
        target, _, frag = ref.partition("#")
        if target and not os.path.exists(os.path.join(P3, target)):
            errs.append(f"broken reference {ref}")
        elif frag and frag not in (re.findall(r'id="([^"]+)"', pages[target or name].src) if (target or name) in pages else []):
            errs.append(f"missing fragment {ref}")
    for f in PAGES[name]:
        if f not in refs:
            errs.append(f"does not load {f}")
    # navigation: main nav links all six pages, aria-current on this page only
    nav = re.search(r'<nav[^>]*aria-label="Main navigation"[^>]*>(.*?)</nav>', p.src, re.S)
    if not nav:
        errs.append("no main navigation")
    else:
        hrefs = re.findall(r'href="([^"]+)"', nav.group(1))
        missing = set(PAGES) - set(hrefs)
        if missing:
            errs.append(f"main nav misses {sorted(missing)}")
        current = re.findall(r'href="([^"]+)"[^>]*aria-current="page"', nav.group(1))
        if current != [name]:
            errs.append(f"aria-current in main nav = {current}")
    crumb = re.search(r'aria-label="Breadcrumb"[^>]*>(.*?)</nav>', p.src, re.S)
    if not crumb or 'aria-current="page"' not in crumb.group(1):
        errs.append("breadcrumb without aria-current")
    return errs


def check_css():
    errs = []
    for f in CSS:
        css = open(os.path.join(P3, f), encoding="utf-8").read()
        if re.search(r"https?://|@import", css):
            errs.append(f"{f}: external resource or @import")
        if "!important" in css:
            errs.append(f"{f}: !important")
        if re.search(r"@media[^{]*max-width", css):
            errs.append(f"{f}: max-width media query (not mobile-first)")
        for needle in CSS_MUST_CONTAIN.get(f, []):
            if needle not in css:
                errs.append(f"{f}: missing '{needle}'")
    for f, sri in VENDOR_SRI.items():
        digest = "sha384-" + base64.b64encode(hashlib.sha384(open(os.path.join(P3, f), "rb").read()).digest()).decode()
        if digest != sri:
            errs.append(f"{f}: hash does not match Bootstrap 5.3.3")
    return errs


pages = {n: parse(n) for n in PAGES}
ok = True
for name, p in pages.items():
    errs = check_page(name, p, pages)
    ok &= not errs
    print(f"{'OK  ' if not errs else 'FAIL'} {name}")
    for e in errs:
        print("       -", e)
css_errs = check_css()
ok &= not css_errs
print(f"{'OK  ' if not css_errs else 'FAIL'} CSS files and Bootstrap vendor files")
for e in css_errs:
    print("       -", e)
print("ALL CHECKS PASSED" if ok else "CHECKS FAILED")
