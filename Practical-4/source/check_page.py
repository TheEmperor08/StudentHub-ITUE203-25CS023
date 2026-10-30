"""Static checks for Practical 4 (Python standard library only). Not the W3C validator.

    python Practical-4/source/check_page.py
"""
import os
import re
from html.parser import HTMLParser

P4 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = {name: open(os.path.join(P4, name), encoding="utf-8").read()
         for name in ("index.html", "assets/css/style.css", "assets/js/theme.js", "assets/js/script.js")}


class Collect(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs), self.getpos()[0]))


page = Collect()
page.feed(FILES["index.html"])
els = page.elements
ids = [a["id"] for _, a, _ in els if "id" in a]
results = []


def check(label, ok, detail=""):
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {label}{'  -> ' + detail if detail and not ok else ''}")


inline = [f"line {l}: <{t} style>" for t, a, l in els if "style" in a]
check("no inline style attributes", not inline, ", ".join(inline))
handlers = [f"line {l}: {k}" for t, a, l in els for k in a if k.startswith("on")]
check("no onclick / inline event handlers", not handlers, ", ".join(handlers))
check("no <style> elements (CSS in assets/css/style.css)", not any(t == "style" for t, _, _ in els))
external = [f"{n}: {m}" for n, s in FILES.items() for m in re.findall(r"https?://[^\s\"')]+", s)]
check("no external URLs (fonts, images, scripts)", not external, ", ".join(external))
refs = [a.get("href") or a.get("src") for t, a, _ in els if t in ("a", "link", "script", "img") and (a.get("href") or a.get("src"))]
refs += [os.path.join("assets/css", u) for u in re.findall(r"url\(['\"]?([^'\")]+)", FILES["assets/css/style.css"])]
missing = []
for ref in refs:
    target, _, frag = ref.partition("#")
    if target and not os.path.exists(os.path.join(P4, target)):
        missing.append(ref)
    elif frag and frag not in ids:
        missing.append(ref)
check("all local links, images, CSS and JS files exist (incl. #fragments)", not missing, ", ".join(missing))
dupes = sorted({i for i in ids if ids.count(i) > 1})
check("no duplicate ids", not dupes, ", ".join(dupes))
h1 = sum(1 for t, _, _ in els if t == "h1")
check("exactly one <h1>", h1 == 1, f"{h1} found")
js_ids = set(re.findall(r"getElementById\('([^']+)'\)", FILES["assets/js/script.js"]))
check("every id used by script.js exists in index.html", js_ids <= set(ids), ", ".join(sorted(js_ids - set(ids))))
controls = [a["aria-controls"] for _, a, _ in els if "aria-controls" in a]
check("every aria-controls points to an existing id", all(c in ids for c in controls))
check("skip link targets <main id=main-content>", any(t == "main" and a.get("id") == "main-content" for t, a, _ in els)
      and any(t == "a" and a.get("href") == "#main-content" for t, a, _ in els))
check("every image has an alt attribute", all("alt" in a for t, a, _ in els if t == "img"))
src = FILES["index.html"]
unnamed = [b for b in re.findall(r"<button\b([^>]*)>(.*?)</button>", src, re.S)
           if "aria-label" not in b[0] and not re.sub(r"<[^>]+>|&[#\w]+;|\s", "", b[1])]
check("every button has visible text or an aria-label", not unnamed)
check("all buttons have type=\"button\"", all(a.get("type") == "button" for t, a, _ in els if t == "button"))
check("theme saved and restored with localStorage", "localStorage.setItem(key, value)" in FILES["assets/js/theme.js"]
      and "readPref(THEME_KEY)" in FILES["assets/js/theme.js"])
check("JavaScript uses ES6+ (const/let, arrow functions, template literals)",
      all(x in FILES["assets/js/script.js"] for x in ("const ", "let ", "=>", "`")) and "var " not in FILES["assets/js/script.js"])
print(f"\n{sum(results)} of {len(results)} static checks passed")
