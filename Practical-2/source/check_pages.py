"""Local structural, link and accessibility checks for the Practical 2 pages (Python standard library only).
Not the W3C validator: it checks only the rules coded below. Usage: python Practical-2/source/check_pages.py Practical-2"""
import os
import re
import sys
from html.parser import HTMLParser

DIR = sys.argv[1]
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
NOT_IN_P = {"address", "article", "aside", "blockquote", "details", "div", "dl", "fieldset", "figure", "footer", "form",
            "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "main", "nav", "ol", "p", "section", "table", "ul"}
OBSOLETE = {"cellpadding", "cellspacing", "align", "bgcolor", "valign", "style", "onclick"}
EXPECTED = ["index.html", "about.html", "events.html", "faq.html", "contact.html", "feedback.html", "login.html",
            "register.html", "dashboard.html", "profile.html", "courses.html", "attendance.html", "assignments.html",
            "results.html", "notifications.html", "directory.html", "admin.html"]


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errors, self.elements = [], [], []
        self.ids, self.labels_for, self.controls, self.links, self.headings = [], set(), [], [], []
        self.text_target = None
        self.title = ""
        self.label_depth = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        line = self.getpos()[0]
        self.elements.append((tag, a, line, [t for t, _ in self.stack]))
        if "p" in [t for t, _ in self.stack[-1:]] and tag in NOT_IN_P:
            self.errors.append(f"line {line}: <{tag}> inside <p>")
        for bad in OBSOLETE & set(a):
            self.errors.append(f"line {line}: attribute {bad} on <{tag}>")
        if tag == "table" and "width" in a:
            self.errors.append(f"line {line}: width on <table>")
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "label":
            self.label_depth += 1
            if "for" in a:
                self.labels_for.add(a["for"])
        if tag in ("input", "select", "textarea") and a.get("type") not in ("submit", "reset", "button", "hidden"):
            self.controls.append((tag, a, line, self.label_depth > 0))
        if tag == "a" and "href" in a:
            self.links.append((a["href"], line))
        if re.fullmatch(r"h[1-6]", tag):
            self.headings.append((int(tag[1]), line))
        if tag == "title":
            self.text_target = "title"
        if tag not in VOID:
            self.stack.append((tag, line))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if tag == "label":
            self.label_depth -= 1
        if not self.stack or self.stack[-1][0] != tag:
            self.errors.append(f"line {self.getpos()[0]}: unexpected </{tag}>, open: {self.stack[-1] if self.stack else None}")
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i][0] == tag:
                    del self.stack[i:]
                    break
        else:
            self.stack.pop()
        if tag == "title":
            self.text_target = None

    def handle_data(self, data):
        if self.text_target == "title":
            self.title += data


def parse(path):
    p = Page()
    src = open(path, encoding="utf-8").read()
    p.feed(src)
    p.close()
    p.src = src
    return p


pages = {f: parse(os.path.join(DIR, f)) for f in EXPECTED if os.path.exists(os.path.join(DIR, f))}
results = {}
for f in EXPECTED:
    errs = []
    if f not in pages:
        results[f] = ["MISSING FILE"]
        continue
    p = pages[f]
    errs += p.errors
    if p.stack:
        errs.append(f"unclosed elements: {p.stack}")
    if not p.src.startswith("<!DOCTYPE html>"):
        errs.append("missing <!DOCTYPE html>")
    tags = [e[0] for e in p.elements]
    html = next(e for e in p.elements if e[0] == "html")
    if html[1].get("lang") != "en":
        errs.append("html lang missing")
    if not any(e[0] == "meta" and "charset" in e[1] for e in p.elements):
        errs.append("no meta charset")
    if not any(e[0] == "meta" and e[1].get("name") == "viewport" for e in p.elements):
        errs.append("no viewport meta")
    if not p.title.strip():
        errs.append("empty title")
    for t in ("header", "nav", "main", "footer"):
        if t not in tags:
            errs.append(f"no <{t}>")
    if tags.count("main") != 1:
        errs.append("main count != 1")
    if not ("section" in tags or "article" in tags):
        errs.append("no section/article")
    for t in ("script", "style", "link", "div"):
        if t in tags:
            errs.append(f"<{t}> present")
    # headings
    levels = [h for h, _ in p.headings]
    if levels.count(1) != 1:
        errs.append(f"h1 count = {levels.count(1)}")
    for (a, _), (b, line) in zip(p.headings, p.headings[1:]):
        if b > a + 1:
            errs.append(f"line {line}: heading jumps h{a} -> h{b}")
    # ids
    dup = {i for i in p.ids if p.ids.count(i) > 1}
    if dup:
        errs.append(f"duplicate ids {dup}")
    # skip link: first link in body, target is main
    first_a = next((e for e in p.elements if e[0] == "a"), (None, {}, 0, []))
    main = next((e for e in p.elements if e[0] == "main"), (None, {}, 0, []))
    if first_a[1].get("href") != "#main-content" or main[1].get("id") != "main-content":
        errs.append("skip link / main id wrong")
    # images
    for tag, a, line, _ in p.elements:
        if tag == "img" and not a.get("alt", "").strip():
            errs.append(f"line {line}: img without alt")
        if tag == "img" and not os.path.exists(os.path.join(DIR, a.get("src", ""))):
            errs.append(f"line {line}: img src missing {a.get('src')}")
    # form labels
    for tag, a, line, wrapped in p.controls:
        if not wrapped and a.get("id") not in p.labels_for:
            errs.append(f"line {line}: <{tag} name={a.get('name')}> has no label")
    for lab in p.labels_for:
        if lab not in p.ids:
            errs.append(f"label for={lab} has no matching id")
    # forms: no action, submit disabled
    for tag, a, line, _ in p.elements:
        if tag == "form" and "action" in a:
            errs.append(f"line {line}: form has action")
        if tag == "button" and a.get("type") == "submit" and "disabled" not in a:
            errs.append(f"line {line}: enabled submit button")
        if tag == "button" and a.get("type") not in ("submit", "reset"):
            errs.append(f"line {line}: button without submit/reset type")
        if tag == "table":
            if "caption" not in [e[0] for e in p.elements if e[2] > line][:1]:
                errs.append(f"line {line}: table without caption first")
        if tag == "th" and "scope" not in a:
            errs.append(f"line {line}: th without scope")
    # navigation: main nav lists every page, aria-current only on this page
    m = re.search(r'<nav aria-label="Main navigation">(.*?)</nav>', p.src, re.S)
    nav_links = m.group(1) if m else ""
    if not m:
        errs.append("no main navigation")
    hrefs = re.findall(r'href="([^"]+)"', nav_links)
    if sorted(hrefs) != sorted(EXPECTED):
        errs.append(f"main nav links differ: {sorted(set(EXPECTED) ^ set(hrefs))}")
    current = re.findall(r'href="([^"]+)" aria-current="page"', nav_links)
    if current != [f]:
        errs.append(f"aria-current in main nav = {current}")
    crumb = re.search(r'<nav aria-label="Breadcrumb">(.*?)</nav>', p.src, re.S)
    if not crumb or 'aria-current="page"' not in crumb.group(1):
        errs.append("breadcrumb missing aria-current")
    # links
    for href, line in p.links:
        if href.startswith(("http:", "https:")):
            errs.append(f"line {line}: external link {href}")
            continue
        if href.startswith("mailto:"):
            continue
        if href == "#":
            errs.append(f"line {line}: empty # link")
            continue
        target, _, frag = href.partition("#")
        tf = target or f
        if tf not in pages:
            errs.append(f"line {line}: broken link {href}")
        elif frag and frag not in pages[tf].ids:
            errs.append(f"line {line}: missing fragment {href}")
    results[f] = errs

ok = True
for f in EXPECTED:
    status = "OK" if not results[f] else "FAIL"
    ok &= not results[f]
    p = pages.get(f)
    extra = ""
    if p:
        tags = [e[0] for e in p.elements]
        extra = (f"  links={len(p.links)} controls={len(p.controls)} imgs={tags.count('img')} "
                 f"sections={tags.count('section')} articles={tags.count('article')} asides={tags.count('aside')}")
    print(f"{status:4} {f:20}{extra}")
    for e in results[f]:
        print("       -", e)
others = sorted(x for x in os.listdir(DIR) if x.endswith(".html") and x not in EXPECTED)
print("unexpected html files:", others)
print("ALL CHECKS PASSED" if ok and not others else "CHECKS FAILED")
