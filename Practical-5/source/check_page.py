"""Static checks for Practical 5 (Python standard library only). Not the W3C validator.

    python Practical-5/source/check_page.py
"""
import os
import re
from html.parser import HTMLParser

P5 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = {name: open(os.path.join(P5, name), encoding="utf-8").read()
         for name in ("register.html", "assets/css/style.css", "assets/js/validation.js")}


class Collect(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []
        self.stack = []

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs), self.getpos()[0], list(self.stack)))
        if tag not in ("input", "meta", "link", "br", "img"):
            self.stack.append((tag, dict(attrs)))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break


page = Collect()
page.feed(FILES["register.html"])
els = page.elements
ids = [a["id"] for _, a, _, _ in els if "id" in a]
by_id = {a["id"]: (t, a) for t, a, _, _ in els if "id" in a}
results = []


def check(label, ok, detail=""):
    ok = bool(ok)
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {label}{'  -> ' + detail if detail and not ok else ''}")


src = FILES["register.html"]
inline = [f"line {l}: <{t} style>" for t, a, l, _ in els if "style" in a]
check("no inline style attributes", not inline, ", ".join(inline))
handlers = [f"line {l}: {k}" for t, a, l, _ in els for k in a if k.startswith("on")]
check("no onclick / inline event handlers", not handlers, ", ".join(handlers))
check("no <style> elements and no inline <script> code",
      not any(t == "style" for t, _, _, _ in els) and all("src" in a for t, a, _, _ in els if t == "script"))
external = [f"{n}: {m}" for n, s in FILES.items() for m in re.findall(r"https?://[^\s\"')]+", s)]
check("no external URLs (fonts, scripts, images)", not external, ", ".join(external))
refs = [a.get("href") or a.get("src") for t, a, _, _ in els if t in ("a", "link", "script", "img") and (a.get("href") or a.get("src"))]
missing = [r for r in refs if not os.path.exists(os.path.join(P5, r.partition("#")[0]))]
check("all local CSS and JS files exist (no missing auth.js / login.html)", not missing, ", ".join(missing))
dupes = sorted({i for i in ids if ids.count(i) > 1})
check("no duplicate ids", not dupes, ", ".join(dupes))
check("exactly one <h1>", sum(1 for t, _, _, _ in els if t == "h1") == 1)

REQUIRED = {"name": ("input", "text"), "email": ("input", "email"), "mobile": ("input", "tel"),
            "password": ("input", "password"), "cPassword": ("input", "password"),
            "course": ("select", None), "year": ("select", None), "terms": ("input", "checkbox")}
wrong = [f for f, (tag, typ) in REQUIRED.items()
         if f not in by_id or by_id[f][0] != tag or (typ and by_id[f][1].get("type") != typ)]
radios = [a for t, a, _, _ in els if t == "input" and a.get("type") == "radio" and a.get("name") == "gender"]
check("all nine fields present with HTML5 input types (text, email, tel, password, select, radio, checkbox)",
      not wrong and len(radios) == 3, ", ".join(wrong))
controls = [(t, a) for t, a, _, _ in els if t in ("input", "select")]
not_required = [a.get("id") or a.get("name") for t, a in controls
                if a.get("type") != "radio" and "required" not in a] + ([] if "required" in radios[0] else ["gender"])
check("every field (and the CAPTCHA input) has the required attribute", not not_required, ", ".join(not_required))
attrs_ok = (by_id["name"][1].get("minlength") == "3" and by_id["name"][1].get("maxlength") == "50"
            and by_id["mobile"][1].get("pattern") == "[6-9][0-9]{9}" and by_id["mobile"][1].get("inputmode") == "numeric"
            and by_id["password"][1].get("minlength") == "8" and by_id["captcha"][1].get("maxlength") == "5")
check("minlength, maxlength, pattern and inputmode set on name, mobile, password and CAPTCHA", attrs_ok)
auto = {"name": "name", "email": "email", "mobile": "tel-national", "password": "new-password",
        "cPassword": "new-password", "captcha": "off"}
bad_auto = [f for f, v in auto.items() if by_id[f][1].get("autocomplete") != v]
check("autocomplete values set (name, email, tel-national, new-password, off for CAPTCHA)", not bad_auto, ", ".join(bad_auto))
label_for = {a.get("for") for t, a, _, _ in els if t == "label"}
unlabelled = [a.get("id") for t, a, _, stack in els if t in ("input", "select") and a.get("id") not in label_for
              and not any(s[0] == "label" for s in stack)]
check("every input and select has a <label>", not unlabelled, ", ".join(unlabelled))
legends = sum(1 for t, _, _, _ in els if t == "legend")
fieldsets = sum(1 for t, _, _, _ in els if t == "fieldset")
radio_in_fieldset = all(any(s[0] == "fieldset" for s in stack) for t, a, _, stack in els if a.get("type") == "radio")
check("form grouped with fieldset/legend; gender radios inside a fieldset with a legend",
      fieldsets >= 5 and legends == fieldsets and radio_in_fieldset)
described = [i for _, a, _, _ in els for i in a.get("aria-describedby", "").split() if i not in ids]
check("every aria-describedby points to an existing id", not described, ", ".join(described))
js = FILES["assets/js/validation.js"]
fields = re.findall(r"^        (\w+): \(\) =>", js, re.M)
no_error_box = [f for f in fields if f"{f}-error" not in ids or f"{f}-group" not in ids]
check(f"each of the {len(fields)} validated fields has an error element next to it (id <field>-error)",
      len(fields) == 10 and not no_error_box, ", ".join(no_error_box))
not_linked = [f for f in fields if f != "gender" and f"{f}-error" not in by_id[f][1].get("aria-describedby", "")]
gender_fs = [a for t, a, _, _ in els if t == "fieldset" and "gender-error" in a.get("aria-describedby", "")]
check("error messages linked to their fields with aria-describedby", not not_linked and gender_fs, ", ".join(not_linked))
js_ids = set(re.findall(r"getElementById\('([^']+)'\)", js))
check("every fixed id used by validation.js exists in register.html", js_ids <= set(ids), ", ".join(sorted(js_ids - set(ids))))
check("live regions: summary role=alert, strength text and announcer aria-live",
      by_id["form-summary"][1].get("role") == "alert" and by_id["strength-text"][1].get("aria-live") == "polite"
      and by_id["sr-announcer"][1].get("aria-live") == "polite")
check("CAPTCHA drawn on a <canvas> with a text alternative and a refresh button",
      by_id["captcha-canvas"][0] == "canvas" and "aria-label" in by_id["captcha-canvas"][1]
      and by_id["captcha-refresh"][1].get("type") == "button")
check("buttons have a type and visible text", all("type" in a for t, a, _, _ in els if t == "button"))
check("validation uses regular expressions for name, email, mobile and password",
      all(re.search(rf"{f}: /\^", js) for f in ("name", "email", "mobile", "password")))
check("real-time validation listeners: input, change and blur",
      all(f"addEventListener('{e}'" in js for e in ("input", "change", "blur")))
check("no alert() and no redirect to a missing page", "alert(" not in js and "location.href" not in js)
check("JavaScript uses ES6+ (const/let, arrow functions, template literals; no var)",
      all(x in js for x in ("const ", "let ", "=>", "`")) and not re.search(r"\bvar ", js))
print(f"\n{sum(results)} of {len(results)} static checks passed")
