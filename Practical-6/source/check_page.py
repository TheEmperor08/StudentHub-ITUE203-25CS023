"""Static checks for Practical 6 (Python standard library only). Not the W3C validator.

    python source/check_page.py          (run from the Practical-6 folder)
"""
import json
import os
import re
from html.parser import HTMLParser

P6 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS_DIR = os.path.join(P6, "assets", "js")
def read(rel, mode="r"):
    with open(os.path.join(P6, rel), mode, **({} if "b" in mode else {"encoding": "utf-8"})) as fh:
        return fh.read()


HTML = read("directory.html")
CSS = read("assets/css/style.css")
JS = {name: read(f"assets/js/{name}") for name in sorted(os.listdir(JS_DIR)) if name.endswith(".js")}
DATA = {name: json.loads(read(f"data/{name}.json")) for name in ("students", "events", "faqs")}


class Collect(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []
        self.stack = []

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs), list(self.stack)))
        if tag not in ("input", "meta", "link", "br", "img"):
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.stack:
            del self.stack[len(self.stack) - 1 - self.stack[::-1].index(tag):]


page = Collect()
page.feed(HTML)
els = page.elements
ids = [a["id"] for _, a, _ in els if "id" in a]
by_id = {a["id"]: (t, a) for t, a, _ in els if "id" in a}
results = []


def check(label, ok, detail=""):
    ok = bool(ok)
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {label}{'  -> ' + detail if detail and not ok else ''}")


# Page structure
check("no inline style attributes", not any("style" in a for _, a, _ in els))
check("no onclick / inline event handlers", not any(k.startswith("on") for _, a, _ in els for k in a))
check("no <style> elements and no inline <script> code", not any(t == "style" for t, _, _ in els)
      and all("src" in a for t, a, _ in els if t == "script"))
everything = {"directory.html": HTML, "style.css": CSS, **JS, **{f"{n}.json": json.dumps(d) for n, d in DATA.items()}}
external = [f"{n}: {m}" for n, s in everything.items() for m in re.findall(r"https?://[^\s\"'<)]+", s)
            if not m.startswith("http://127.0.0.1")]
check("no external URLs (no CDN, fonts or images from the internet)", not external, ", ".join(external))
refs = [a.get("href") or a.get("src") for t, a, _ in els if t in ("link", "script") and (a.get("href") or a.get("src"))]
check("all CSS and JS files referenced by the page exist", all(os.path.exists(os.path.join(P6, r)) for r in refs))
check("main.js is loaded as an ES module", any(t == "script" and a.get("type") == "module" and a.get("src") == "assets/js/main.js" for t, a, _ in els))
imports = [(n, m) for n, s in JS.items() for m in re.findall(r"from '\./([\w-]+\.js)'", s)]
check(f"every ES module import resolves ({len(imports)} imports)", imports and all(m in JS for _, m in imports))
modules = ["config.js", "api.js", "filters.js", "render.js"]
check("code split into modules: config, api, filters, render (export) and main (import)",
      all("export " in JS[m] for m in modules) and "import " in JS["main.js"])
dupes = sorted({i for i in ids if ids.count(i) > 1})
check("no duplicate ids; exactly one <h1>", not dupes and sum(t == "h1" for t, _, _ in els) == 1, ", ".join(dupes))
used = set(re.findall(r"\$\('([\w-]+)'\)", JS["main.js"])) | set(re.findall(r"getElementById\('([\w-]+)'\)", JS["file-check.js"]))
check("every id used by the JavaScript exists in directory.html", used <= set(ids), ", ".join(sorted(used - set(ids))))
targets = [i for _, a, _ in els for k in ("aria-controls", "aria-labelledby") for i in a.get(k, "").split()]
check("every aria-controls / aria-labelledby points to an existing id", all(t in ids for t in targets))
tabs = [a for t, a, _ in els if a.get("role") == "tab"]
check("tabs: tablist, 3 tabs with aria-selected/aria-controls, one tabpanel",
      any(a.get("role") == "tablist" for _, a, _ in els) and len(tabs) == 3
      and all("aria-selected" in a and a.get("aria-controls") == "data-panel" for a in tabs)
      and by_id["data-panel"][1].get("role") == "tabpanel")
label_for = {a.get("for") for t, a, _ in els if t == "label"}
unlabelled = [a.get("id") for t, a, stack in els if t in ("input", "select") and a.get("id") not in label_for and "label" not in stack]
check("every input and select has a label", not unlabelled, ", ".join(unlabelled))
check("all buttons have type=\"button\"", all(a.get("type") == "button" for t, a, _ in els if t == "button"))
check("status and results summary are live regions", by_id["status"][1].get("aria-live") == "polite"
      and by_id["results-summary"][1].get("aria-live") == "polite")

# Data files
for name, data in DATA.items():
    records = data.get("records", [])
    keys = {tuple(sorted(r)) for r in records}
    rec_ids = [r.get("id") for r in records]
    check(f"{name}.json: labelled sample data, {len(records)} records (>= 15), same fields, unique ids",
          data.get("sampleData") is True and data.get("description", "").startswith("SAMPLE DATA")
          and len(records) >= 15 and len(keys) == 1 and len(set(rec_ids)) == len(rec_ids))
students = DATA["students"]["records"]
check("students use fictional IDs DEMO-001 to DEMO-015 (no university roll numbers)",
      [s["id"] for s in students] == [f"DEMO-{n:03d}" for n in range(1, 16)])
all_data = json.dumps(DATA)
check("no real-format roll numbers (e.g. 25CS023) anywhere in the data", not re.search(r"\b\d{2}[A-Z]{2}\d{3}\b", all_data))
check("FAQs name no individual (no Dr./Prof./Mr./Ms.); HOD answer is role-based",
      not re.search(r"\b(Dr|Prof|Mr|Mrs|Ms)\.", all_data) and any("Head of Department (HOD)" in f["answer"] for f in DATA["faqs"]["records"]))
config_keys = re.findall(r"\{ key: '(\w+)', label", JS["config.js"])
record_keys = set().union(*(set(d["records"][0]) for d in DATA.values()))
check("every column in config.js exists in the JSON records", config_keys and set(config_keys) <= record_keys,
      ", ".join(sorted(set(config_keys) - record_keys)))
check("FAQs have a category field (so the filter works for FAQs)", all("category" in f for f in DATA["faqs"]["records"]))

# JavaScript behaviour that can be checked in the source
api, main, render = JS["api.js"], JS["main.js"], JS["render.js"]
check("Fetch API: response.ok checked, JSON parsed, records validated",
      "await fetch(" in api and "response.ok" in api and "response.json()" in api and "Array.isArray(body.records)" in api)
check("localStorage cache wrapped in try/catch (save, read, clear)",
      api.count("try {") >= 3 and "localStorage.setItem" in api and "localStorage.getItem" in api)
check("race-condition guard: request id + AbortController",
      "requestId !== latestRequest" in main and "controller?.abort()" in main and "new AbortController()" in main)
check("rendering uses DOM methods, never innerHTML", not re.search(r"\.(innerHTML|outerHTML)\s*\+?=|insertAdjacentHTML", "".join(JS.values())) and "textContent" in render)
check("JavaScript uses ES6+ (const/let, arrow functions, template literals; no var)",
      all(re.search(r"\bvar\b", s) is None for s in JS.values()) and "=>" in main and "`" in main)
bat = read("start-server.bat", "rb")
check("start-server.bat runs Python's http.server and has Windows (CRLF) line endings",
      b"-m http.server" in bat and b"\r\n" in bat and b"\n" not in bat.replace(b"\r\n", b""))
print(f"\n{sum(results)} of {len(results)} static checks passed")
