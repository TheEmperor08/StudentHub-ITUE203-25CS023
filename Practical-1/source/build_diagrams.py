"""Builds the Practical 1 planning diagrams for StudentHub as SVG (vector) and PNG (for the Word report).

Outputs (written to Practical-1/):
  sitemap.svg / sitemap.png                       - sitemap & navigation flow of the implemented app
  wireframe-1-dashboard-desktop.svg / .png        - low-fidelity wireframe: student dashboard (desktop)
  wireframe-2-home-login-desktop.svg / .png       - low-fidelity wireframes: home page and login (desktop)
  wireframe-3-mobile.svg / .png                   - low-fidelity wireframes: mobile dashboard, nav drawer, login

Run from the repository root:  python Practical-1/source/build_diagrams.py
Requires Pillow and the Windows fonts Segoe UI / Consolas (falls back to Arial).
"""
import os
from xml.sax.saxutils import escape
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FONT_DIR = r"C:\Windows\Fonts"
FONT_FILES = {"regular": ["segoeui.ttf", "arial.ttf"], "bold": ["segoeuib.ttf", "arialbd.ttf"], "mono": ["consola.ttf", "arial.ttf"]}
SVG_FONTS = {"regular": "'Segoe UI', Arial, sans-serif", "bold": "'Segoe UI', Arial, sans-serif", "mono": "Consolas, 'Courier New', monospace"}

STUDENT, ROLL = "Shreyas", "25CS023"
SUBTITLE = f"Practical 1 · ITUE203 Web Development Frameworks · {STUDENT} ({ROLL}) · CSPIT, CHARUSAT · 2026-27"


class Canvas:
    """Draws the same shapes into an SVG document and a Pillow image."""

    def __init__(self, width, height, scale=2, background="#ffffff"):
        self.w, self.h, self.s = width, height, scale
        self.svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" font-family="{SVG_FONTS["regular"]}">',
            f'<rect width="{width}" height="{height}" fill="{background}"/>',
        ]
        self.img = Image.new("RGB", (width * scale, height * scale), background)
        self.draw = ImageDraw.Draw(self.img)
        self.fonts = {}

    # ---------- primitives ----------
    def _font(self, kind, size):
        key = (kind, size)
        if key not in self.fonts:
            for name in FONT_FILES[kind]:
                path = os.path.join(FONT_DIR, name)
                if os.path.exists(path):
                    self.fonts[key] = ImageFont.truetype(path, round(size * self.s))
                    break
        return self.fonts[key]

    def _p(self, *values):
        return [v * self.s for v in values]

    def _dashed(self, x1, y1, x2, y2, color, width, dash):
        length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        if length == 0:
            return
        on, off = dash
        dx, dy = (x2 - x1) / length, (y2 - y1) / length
        pos = 0.0
        while pos < length:
            end = min(pos + on, length)
            self.draw.line(self._p(x1 + dx * pos, y1 + dy * pos, x1 + dx * end, y1 + dy * end), fill=color, width=width)
            pos += on + off

    def rect(self, x, y, w, h, fill="#ffffff", stroke="#333333", sw=1.5, r=8, dash=None):
        dash_attr = f' stroke-dasharray="{dash[0]} {dash[1]}"' if dash else ""
        self.svg.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill or "none"}" '
            f'stroke="{stroke or "none"}" stroke-width="{sw}"{dash_attr}/>'
        )
        box = self._p(x, y, x + w, y + h)
        if fill:
            self.draw.rounded_rectangle(box, radius=r * self.s, fill=fill)
        if stroke:
            width = max(1, round(sw * self.s))
            if dash:
                for (ax, ay, bx, by) in [(x, y, x + w, y), (x + w, y, x + w, y + h), (x + w, y + h, x, y + h), (x, y + h, x, y)]:
                    self._dashed(ax, ay, bx, by, stroke, width, dash)
            else:
                self.draw.rounded_rectangle(box, radius=r * self.s, outline=stroke, width=width)

    def circle(self, cx, cy, r, fill="#ffffff", stroke="#333333", sw=1.5):
        self.svg.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill or "none"}" stroke="{stroke or "none"}" stroke-width="{sw}"/>')
        self.draw.ellipse(self._p(cx - r, cy - r, cx + r, cy + r), fill=fill, outline=stroke, width=max(1, round(sw * self.s)) if stroke else 0)

    def line(self, points, color="#333333", sw=1.5, dash=None, arrow=False):
        pts = " ".join(f"{x},{y}" for x, y in points)
        dash_attr = f' stroke-dasharray="{dash[0]} {dash[1]}"' if dash else ""
        self.svg.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{sw}"{dash_attr} stroke-linejoin="round"/>')
        width = max(1, round(sw * self.s))
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            if dash:
                self._dashed(x1, y1, x2, y2, color, width, dash)
            else:
                self.draw.line(self._p(x1, y1, x2, y2), fill=color, width=width)
        if arrow:
            (x1, y1), (x2, y2) = points[-2], points[-1]
            length = max(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5, 1)
            ux, uy = (x2 - x1) / length, (y2 - y1) / length
            size = 9
            tri = [(x2, y2), (x2 - ux * size - uy * size * 0.55, y2 - uy * size + ux * size * 0.55),
                   (x2 - ux * size + uy * size * 0.55, y2 - uy * size - ux * size * 0.55)]
            self.svg.append('<polygon points="' + " ".join(f"{px:.1f},{py:.1f}" for px, py in tri) + f'" fill="{color}"/>')
            self.draw.polygon([(px * self.s, py * self.s) for px, py in tri], fill=color)

    def text(self, x, y, value, size=14, kind="regular", color="#111111", anchor="start"):
        svg_anchor = {"start": "start", "middle": "middle", "end": "end"}[anchor]
        pil_anchor = {"start": "lm", "middle": "mm", "end": "rm"}[anchor]
        weight = ' font-weight="700"' if kind == "bold" else ""
        family = f' font-family="{SVG_FONTS[kind]}"' if kind == "mono" else ""
        self.svg.append(
            f'<text x="{x}" y="{y}" font-size="{size}"{weight}{family} fill="{color}" '
            f'text-anchor="{svg_anchor}" dominant-baseline="central">{escape(value)}</text>'
        )
        self.draw.text((x * self.s, y * self.s), value, font=self._font(kind, size), fill=color, anchor=pil_anchor)

    # ---------- wireframe helpers ----------
    def menu_icon(self, cx, cy, size=14, color="#222222"):
        for dy in (-size / 3, 0, size / 3):
            self.line([(cx - size / 2, cy + dy), (cx + size / 2, cy + dy)], color=color, sw=2.2)

    def close_icon(self, cx, cy, size=12, color="#222222"):
        h = size / 2
        self.line([(cx - h, cy - h), (cx + h, cy + h)], color=color, sw=2.2)
        self.line([(cx + h, cy - h), (cx - h, cy + h)], color=color, sw=2.2)

    def moon_icon(self, cx, cy, r=6, color="#333333", bg="#ececec"):
        self.circle(cx, cy, r, fill=color, stroke=None)
        self.circle(cx + r * 0.55, cy - r * 0.35, r * 0.85, fill=bg, stroke=None)

    def bar(self, x, y, w, h=8, fill="#c9c9c9"):
        self.rect(x, y, w, h, fill=fill, stroke=None, r=h / 2)

    def image_box(self, x, y, w, h, label=None):
        self.rect(x, y, w, h, fill="#efefef", stroke="#8a8a8a", sw=1.2, r=4)
        self.line([(x, y), (x + w, y + h)], color="#b3b3b3", sw=1)
        self.line([(x + w, y), (x, y + h)], color="#b3b3b3", sw=1)
        if label:
            self.rect(x + w / 2 - 70, y + h / 2 - 13, 140, 26, fill="#ffffff", stroke="#8a8a8a", sw=1, r=4)
            self.text(x + w / 2, y + h / 2, label, size=12, color="#444444", anchor="middle")

    def callout(self, cx, cy, number):
        self.circle(cx, cy, 13, fill="#111111", stroke=None)
        self.text(cx, cy, str(number), size=13, kind="bold", color="#ffffff", anchor="middle")

    def browser(self, x, y, w, h, url):
        self.rect(x, y, w, h, fill="#ffffff", stroke="#444444", sw=2, r=10)
        self.rect(x, y, w, 34, fill="#e4e4e4", stroke=None, r=10)
        self.rect(x, y + 20, w, 14, fill="#e4e4e4", stroke=None, r=0)
        self.line([(x, y + 34), (x + w, y + 34)], color="#444444", sw=1.5)
        for i in range(3):
            self.circle(x + 18 + i * 16, y + 17, 5, fill="#bdbdbd", stroke=None)
        self.rect(x + 76, y + 8, min(420, w - 100), 18, fill="#ffffff", stroke="#9e9e9e", sw=1, r=9)
        self.text(x + 88, y + 17, url, size=11, kind="mono", color="#555555")
        return x, y + 34

    def phone(self, x, y, w, h):
        self.rect(x - 8, y - 8, w + 16, h + 16, fill="#f5f5f5", stroke="#444444", sw=2, r=26)
        self.rect(x, y, w, h, fill="#ffffff", stroke="#9e9e9e", sw=1, r=16)

    def title_band(self, title, subtitle, dark=True):
        fill, fg, sub = ("#0b1437", "#ffffff", "#c7d2fe") if dark else ("#f1f1f1", "#111111", "#555555")
        self.rect(0, 0, self.w, 92, fill=fill, stroke=None, r=0)
        self.text(40, 34, title, size=26, kind="bold", color=fg)
        self.text(40, 66, subtitle, size=14, color=sub)

    def save(self, basename):
        svg_path = os.path.join(OUT_DIR, basename + ".svg")
        png_path = os.path.join(OUT_DIR, basename + ".png")
        with open(svg_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(self.svg + ["</svg>"]) + "\n")
        self.img.save(png_path, optimize=True)
        print("wrote", os.path.relpath(svg_path), "and", os.path.relpath(png_path))


# =====================================================================
# 1. Sitemap & navigation flow
# =====================================================================
KINDS = {
    "public":  ("#ffffff", "#334155"),
    "student": ("#eef0ff", "#4f46e5"),
    "admin":   ("#f3edff", "#7c3aed"),
    "error":   ("#fdeceb", "#b42318"),
}


def page_box(c, cx, y, w, title, filename, kind, note=None):
    fill, stroke = KINDS[kind]
    h = 64 if note else 52
    c.rect(cx - w / 2, y, w, h, fill=fill, stroke=stroke, sw=1.8, r=10)
    c.text(cx, y + 18, title, size=15, kind="bold", color="#0f172a", anchor="middle")
    c.text(cx, y + 36, filename, size=12, kind="mono", color="#475569", anchor="middle")
    if note:
        c.text(cx, y + 53, note, size=11, color="#64748b", anchor="middle")
    return y + h


def build_sitemap():
    c = Canvas(1800, 1120)
    c.title_band("StudentHub — Sitemap & Navigation Flow", SUBTITLE)
    c.text(1760, 50, "Reflects the implemented application in studenthub/", size=13, color="#c7d2fe", anchor="end")

    # Legend
    lx, ly = 40, 122
    for label, kind in [("Public page", "public"), ("Student area (login required)", "student"),
                        ("Admin only (role = admin)", "admin"), ("Access control / error", "error")]:
        fill, stroke = KINDS[kind]
        c.rect(lx, ly - 10, 28, 20, fill=fill, stroke=stroke, sw=1.8, r=5)
        c.text(lx + 38, ly, label, size=13, color="#334155")
        lx += 50 + len(label) * 7.2
    c.line([(lx, ly), (lx + 44, ly)], color="#475569", sw=1.6, dash=(6, 4), arrow=True)
    c.text(lx + 54, ly, "Automatic redirect / role check", size=13, color="#334155")
    c.text(1760, ly, "15 screens + logout action (requirement: minimum 10 pages)", size=13, kind="bold", color="#0f172a", anchor="end")

    # Public layer
    home_bottom = page_box(c, 900, 160, 260, "Home Portal", "index.php", "public", "banner · slider · FAQ · guidelines modal")
    tops = {"login": 560, "register": 900, "contact": 1240}
    for cx in tops.values():
        c.line([(900, home_bottom), (900, home_bottom + 22), (cx, home_bottom + 22), (cx, 270)], color="#334155", sw=1.6, arrow=True)
    login_bottom = page_box(c, 560, 270, 240, "Login", "login.php", "public", "username or email + password")
    register_bottom = page_box(c, 900, 270, 240, "Register", "register.php", "public", "creates account + student record")
    page_box(c, 1240, 270, 240, "Contact Us", "contact.php", "public", "inquiry form (also in sidebar)")

    # Role-based landing pages
    dash_bottom = page_box(c, 560, 392, 260, "Student Dashboard", "dashboard.php", "student")
    admin_bottom = page_box(c, 1490, 392, 280, "Admin Console", "admin_dashboard.php", "admin")
    page_box(c, 1150, 392, 230, "Access Denied", "403.php", "error")
    c.line([(560, login_bottom), (560, 392)], color="#4f46e5", sw=1.8, dash=(6, 4), arrow=True)
    c.text(572, 362, "role = student", size=12, color="#4f46e5")
    c.line([(560, 352), (1490, 352), (1490, 392)], color="#7c3aed", sw=1.8, dash=(6, 4), arrow=True)
    c.text(1500, 372, "role = admin", size=12, color="#7c3aed")
    c.line([(900, register_bottom), (900, 418), (690, 418)], color="#4f46e5", sw=1.6, dash=(6, 4), arrow=True)
    c.text(795, 436, "auto-login after sign-up", size=12, color="#4f46e5", anchor="middle")
    c.line([(1350, 418), (1265, 418)], color="#b42318", sw=1.6, dash=(6, 4), arrow=True)
    c.text(1307, 434, "role ≠ admin", size=12, color="#b42318", anchor="middle")

    # Student area panel
    c.rect(40, 480, 1140, 610, fill="#f8f9ff", stroke="#c7c9f5", sw=1.5, r=16)
    c.text(64, 506, "Student area — sidebar navigation (every page redirects to Login without a session)", size=15, kind="bold", color="#3730a3")
    c.line([(560, dash_bottom), (560, 480)], color="#4f46e5", sw=1.8, arrow=True)
    groups = [
        ("OVERVIEW", [("Dashboard", "dashboard.php", "stat cards · timetable · events"),
                      ("My Profile", "profile.php", "details · change password")]),
        ("ACADEMICS", [("Courses", "courses.php", "6 subjects · 21 credits"),
                       ("Attendance", "attendance.php", "subject table · leave form"),
                       ("Assignments", "assignments.php", "status · submission notice"),
                       ("Results", "results.php", "CGPA / SGPA (sample data)"),
                       ("Achievements", "achievements.php", "badges · record form")]),
        ("CAMPUS", [("Notices", "notifications.php", "events from database"),
                    ("Directory", "directory.php", "student list · live search"),
                    ("Help & Contact", "contact.php", "department info · inquiry")]),
        ("ACCOUNT", [("Home Portal", "index.php", "public landing page"),
                     ("Logout", "logout.php", "ends session → Login"),
                     ("Admin Console", "admin_dashboard.php", "link shown to admins only")]),
    ]
    for i, (group, pages) in enumerate(groups):
        cx = 190 + i * 280
        c.text(cx, 546, group, size=13, kind="bold", color="#4f46e5", anchor="middle")
        y = 566
        for title, filename, note in pages:
            kind = "admin" if title == "Admin Console" else "student"
            page_box(c, cx, y, 250, title, filename, kind, note)
            y += 78
    c.text(64, 1066, "Planned Faculty role (from the Practical 1 plan) is not implemented in the main application.", size=12, color="#64748b")

    # Admin area panel
    c.rect(1220, 480, 540, 610, fill="#faf7ff", stroke="#d8ccfb", sw=1.5, r=16)
    c.text(1244, 506, "Admin area — role = admin", size=15, kind="bold", color="#5b21b6")
    c.line([(1490, admin_bottom), (1490, 480)], color="#7c3aed", sw=1.8, arrow=True)
    c.text(1490, 546, "ADMIN CONSOLE TABS", size=13, kind="bold", color="#7c3aed", anchor="middle")
    tabs = [("Overview", "?tab=overview", "live counters · role-based quick links"),
            ("Students", "?tab=students", "add · search · filter · delete · CSV export"),
            ("Events", "?tab=events", "publish event · poster upload · delete"),
            ("Users", "?tab=users", "accounts · roles · last login"),
            ("Audit Logs", "?tab=audits", "security trail (logins, 403s, changes)")]
    y = 566
    for title, filename, note in tabs:
        page_box(c, 1490, y, 480, title, "admin_dashboard.php" + filename, "admin", note)
        y += 78
    c.rect(1250, 966, 480, 64, fill="#ffffff", stroke="#7c3aed", sw=1.4, r=10, dash=(6, 4))
    c.text(1490, 986, "Shortcut URLs redirect to the matching tab", size=13, kind="bold", color="#5b21b6", anchor="middle")
    c.text(1490, 1010, "students.php · events.php · users.php · audit_logs.php", size=12, kind="mono", color="#475569", anchor="middle")
    c.save("sitemap")


# =====================================================================
# 2. Low-fidelity wireframes (greyscale on purpose)
# =====================================================================
G_DARK, G_MID, G_LIGHT, G_LINE = "#9a9a9a", "#d4d4d4", "#ececec", "#444444"


def notes_column(c, x, y, notes, width=270):
    for number, title, lines in notes:
        c.callout(x + 13, y + 10, number)
        c.text(x + 36, y + 10, title, size=14, kind="bold")
        for j, line in enumerate(lines):
            c.text(x + 36, y + 32 + j * 19, line, size=12, color="#444444")
        y += 44 + 19 * len(lines)


def sidebar_wire(c, x, y, w, h, items=12):
    c.rect(x, y, w, h, fill=G_MID, stroke=None, r=0)
    c.rect(x + 16, y + 16, 30, 30, fill=G_DARK, stroke=None, r=8)
    c.text(x + 56, y + 31, "StudentHub", size=14, kind="bold", color="#222222")
    c.rect(x + 12, y + 60, w - 24, 50, fill=G_LIGHT, stroke=None, r=8)
    c.circle(x + 36, y + 85, 14, fill=G_DARK, stroke=None)
    c.bar(x + 58, y + 76, 90, 8, fill="#a8a8a8")
    c.bar(x + 58, y + 90, 60, 6)
    yy = y + 128
    for i in range(items):
        if i in (0, 2, 7, 10):
            c.bar(x + 16, yy, 60, 5, fill="#b0b0b0")
            yy += 16
        active = i == 0
        if active:
            c.rect(x + 8, yy - 4, w - 16, 26, fill="#b8b8b8", stroke=None, r=6)
        c.rect(x + 18, yy + 2, 13, 13, fill=G_DARK, stroke=None, r=3)
        c.bar(x + 40, yy + 5, 80 + (i * 13) % 40, 7, fill="#9d9d9d" if active else "#b5b5b5")
        yy += 30
    c.rect(x + 12, y + h - 52, w - 24, 34, fill=G_LIGHT, stroke="#9e9e9e", sw=1, r=8)
    c.moon_icon(x + w / 2 - 44, y + h - 35, color="#333333", bg=G_LIGHT)
    c.text(x + w / 2 + 8, y + h - 35, "Dark mode", size=12, color="#333333", anchor="middle")


def build_dashboard_wireframe():
    c = Canvas(1600, 1060)
    c.title_band("Low-fidelity wireframe — Student Dashboard (desktop ≥ 1025 px)", SUBTITLE, dark=False)
    bx, by = c.browser(40, 116, 1200, 900, "localhost:8000/studenthub/dashboard.php")
    sidebar_wire(c, bx, by, 220, 866)
    cx, cw = bx + 244, 932

    # Hero header
    c.rect(cx, by + 24, cw, 150, fill=G_DARK, stroke=None, r=14)
    c.bar(cx + 28, by + 50, 120, 7, fill="#c4c4c4")
    c.text(cx + 28, by + 82, f"Welcome back, {STUDENT}", size=24, kind="bold", color="#ffffff")
    for i, label in enumerate([f"Enrollment {ROLL}", "B.Tech CSE (3rd Semester)", "A7 Building, Room 506"]):
        c.rect(cx + 28 + i * 210, by + 112, 196, 28, fill="#b5b5b5", stroke=None, r=14)
        c.text(cx + 40 + i * 210, by + 126, label, size=12, color="#222222")
    for i, label in enumerate(["Timetable", "Results"]):
        c.rect(cx + cw - 250 + i * 122, by + 104, 110, 38, fill="#ffffff" if i == 0 else "#b5b5b5", stroke=None, r=8)
        c.text(cx + cw - 195 + i * 122, by + 123, label, size=13, kind="bold", color="#222222", anchor="middle")

    c.rect(cx, by + 190, 150, 20, fill=G_LIGHT, stroke="#8a8a8a", sw=1, r=10, dash=(4, 3))
    c.text(cx + 75, by + 200, "Sample / demo data", size=11, color="#333333", anchor="middle")
    c.bar(cx + 164, by + 197, 420, 7)

    # Stat cards
    card_w = (cw - 48) / 4
    for i, label in enumerate(["ATTENDANCE", "CGPA", "CREDITS", "ASSIGNMENTS"]):
        x = cx + i * (card_w + 16)
        c.rect(x, by + 226, card_w, 124, fill="#ffffff", stroke=G_LINE, sw=1.4, r=12)
        c.text(x + 16, by + 248, label, size=11, kind="bold", color="#555555")
        c.rect(x + card_w - 50, by + 238, 34, 34, fill=G_MID, stroke=None, r=9)
        c.bar(x + 16, by + 280, 90, 18, fill="#9d9d9d")
        c.bar(x + 16, by + 312, card_w - 32, 7, fill=G_MID)
        c.bar(x + 16, by + 330, 70, 6)

    # Timetable card
    ty = by + 370
    c.rect(cx, ty, cw, 290, fill="#ffffff", stroke=G_LINE, sw=1.4, r=12)
    c.rect(cx + 20, ty + 18, 28, 28, fill=G_MID, stroke=None, r=8)
    c.text(cx + 58, ty + 32, "Semester 3 Timetable", size=16, kind="bold")
    c.bar(cx + 20, ty + 60, 360, 7)
    gx, gy, gw = cx + 20, ty + 82, cw - 40
    c.rect(gx, gy, gw, 190, fill=None, stroke="#8a8a8a", sw=1, r=6)
    c.rect(gx, gy, gw, 30, fill=G_LIGHT, stroke=None, r=6)
    for row in range(1, 6):
        c.line([(gx, gy + 30 + (row - 1) * 32), (gx + gw, gy + 30 + (row - 1) * 32)], color="#c4c4c4", sw=1)
    for col in range(1, 6):
        c.line([(gx + col * gw / 6, gy), (gx + col * gw / 6, gy + 190)], color="#c4c4c4", sw=1)
    for col in range(6):
        c.bar(gx + col * gw / 6 + 12, gy + 12, 70, 6, fill="#a8a8a8")
        for row in range(5):
            c.bar(gx + col * gw / 6 + 12, gy + 44 + row * 32, 60 + (row * 17 + col * 11) % 50, 6)

    # Upcoming events
    ey = by + 680
    c.rect(cx + 2, ey, 26, 26, fill=G_MID, stroke=None, r=8)
    c.text(cx + 38, ey + 13, "Upcoming Events", size=16, kind="bold")
    for i in range(2):
        x = cx + i * (cw / 2 + 8)
        c.rect(x, ey + 40, cw / 2 - 8, 110, fill="#ffffff", stroke=G_LINE, sw=1.4, r=12)
        c.rect(x + 16, ey + 56, 50, 58, fill=G_LIGHT, stroke="#8a8a8a", sw=1, r=8)
        c.rect(x + 16, ey + 56, 50, 18, fill=G_DARK, stroke=None, r=8)
        c.text(x + 41, ey + 95, "22", size=18, kind="bold", anchor="middle")
        c.bar(x + 82, ey + 62, 200, 9, fill="#9d9d9d")
        c.bar(x + 82, ey + 84, 300, 6)
        c.bar(x + 82, ey + 100, 160, 6)

    for number, (x, y) in enumerate([(bx + 220, by + 40), (cx + cw - 10, by + 30), (cx + cw - 10, by + 232),
                                     (cx + cw - 10, ty + 10), (cx + cw - 10, ey + 46), (bx + 220, by + 830)], start=1):
        c.callout(x, y, number)

    notes_column(c, 1270, 140, [
        (1, "Sidebar navigation", ["Brand, user card (name + roll no.)", "Groups: Overview, Academics,", "Campus, Account; active page marked"]),
        (2, "Welcome header", ["Greeting, enrollment and course chips", "Quick buttons: Timetable, Results"]),
        (3, "Summary cards", ["Attendance, CGPA, credits,", "assignments – labelled sample data"]),
        (4, "Weekly timetable", ["Table on desktop; becomes", "stacked cards on phones"]),
        (5, "Upcoming events", ["Read from the events table,", "date badge + venue"]),
        (6, "Theme toggle", ["Light / dark theme,", "remembered in the browser"]),
    ])
    c.save("wireframe-1-dashboard-desktop")


def build_home_login_wireframe():
    c = Canvas(1600, 940)
    c.title_band("Low-fidelity wireframes — Home page and Login (desktop)", SUBTITLE, dark=False)

    # Home page
    bx, by = c.browser(40, 116, 760, 790, "localhost:8000/studenthub/index.php")
    c.rect(bx, by, 760, 26, fill=G_DARK, stroke=None, r=0)
    c.text(bx + 380, by + 13, "Announcement banner   ×", size=11, color="#ffffff", anchor="middle")
    c.rect(bx, by + 26, 760, 220, fill=G_MID, stroke=None, r=0)
    c.rect(bx + 20, by + 42, 26, 26, fill=G_DARK, stroke=None, r=7)
    c.text(bx + 56, by + 55, "StudentHub", size=14, kind="bold")
    for i in range(5):
        c.bar(bx + 300 + i * 70, by + 52, 50, 7, fill="#9d9d9d")
    c.rect(bx + 664, by + 44, 76, 24, fill=G_LIGHT, stroke="#8a8a8a", sw=1, r=6)
    c.text(bx + 702, by + 56, "Theme", size=11, anchor="middle")
    c.text(bx + 24, by + 112, "StudentHub – CSPIT", size=24, kind="bold")
    c.bar(bx + 24, by + 140, 380, 8, fill="#a8a8a8")
    c.bar(bx + 24, by + 156, 300, 8, fill="#a8a8a8")
    for i, label in enumerate(["Sign In", "Create Account"]):
        c.rect(bx + 24 + i * 120, by + 182, 110, 34, fill="#ffffff" if i == 0 else G_LIGHT, stroke="#8a8a8a", sw=1, r=8)
        c.text(bx + 79 + i * 120, by + 199, label, size=12, kind="bold", anchor="middle")
    c.rect(bx + 470, by + 88, 266, 130, fill=G_LIGHT, stroke="#8a8a8a", sw=1, r=10)
    c.text(bx + 486, by + 108, "At a glance", size=13, kind="bold")
    for i in range(3):
        c.bar(bx + 486, by + 134 + i * 24, 210, 7)
    mx, mw = bx + 20, 500
    c.rect(mx, by + 262, mw, 80, fill="#ffffff", stroke=G_LINE, sw=1.3, r=10)
    c.text(mx + 16, by + 280, "Welcome card", size=13, kind="bold")
    c.bar(mx + 16, by + 300, 440, 6)
    c.rect(mx + 16, by + 312, 160, 22, fill=G_MID, stroke=None, r=6)
    c.text(mx + 96, by + 323, "Portal Guidelines (modal)", size=10, anchor="middle")
    c.image_box(mx, by + 356, mw, 150, "Image slider  ‹  ›")
    c.rect(mx, by + 520, mw, 90, fill="#ffffff", stroke=G_LINE, sw=1.3, r=10)
    for i in range(3):
        x = mx + 14 + i * 162
        c.rect(x, by + 534, 150, 62, fill=G_LIGHT, stroke=None, r=8)
        c.rect(x + 10, by + 542, 20, 20, fill=G_DARK, stroke=None, r=6)
        c.bar(x + 10, by + 572, 110, 6)
    c.rect(mx, by + 622, mw, 96, fill="#ffffff", stroke=G_LINE, sw=1.3, r=10)
    c.text(mx + 16, by + 638, "Quick FAQ (accordion)", size=13, kind="bold")
    for i in range(3):
        c.rect(mx + 14, by + 652 + i * 20, mw - 28, 16, fill=G_LIGHT, stroke=None, r=4)
    c.rect(bx + 536, by + 262, 204, 300, fill="#ffffff", stroke=G_LINE, sw=1.3, r=10)
    c.text(bx + 552, by + 282, "Campus alerts", size=13, kind="bold")
    for i in range(3):
        c.rect(bx + 550, by + 302 + i * 62, 176, 52, fill=G_LIGHT, stroke=None, r=8)
        c.bar(bx + 560, by + 314 + i * 62, 80, 6, fill="#a8a8a8")
        c.bar(bx + 560, by + 330 + i * 62, 140, 6)

    # Login page
    lx, ly = c.browser(840, 116, 720, 470, "localhost:8000/studenthub/login.php")
    c.rect(lx, ly, 300, 436, fill=G_DARK, stroke=None, r=0)
    c.rect(lx + 24, ly + 26, 26, 26, fill="#e0e0e0", stroke=None, r=7)
    c.text(lx + 60, ly + 39, "StudentHub", size=14, kind="bold", color="#ffffff")
    c.text(lx + 24, ly + 150, "Your campus, in one place.", size=17, kind="bold", color="#ffffff")
    c.bar(lx + 24, ly + 178, 230, 7, fill="#c4c4c4")
    for i in range(3):
        c.rect(lx + 24, ly + 210 + i * 40, 26, 26, fill="#bdbdbd", stroke=None, r=7)
        c.bar(lx + 60, ly + 220 + i * 40, 170, 7, fill="#c4c4c4")
    c.rect(lx + 360, ly + 50, 300, 330, fill="#ffffff", stroke=G_LINE, sw=1.4, r=14)
    c.text(lx + 382, ly + 82, "Sign in", size=20, kind="bold")
    c.bar(lx + 382, ly + 106, 200, 6)
    for i, label in enumerate(["Username or Email Address", "Password"]):
        c.text(lx + 382, ly + 140 + i * 70, label, size=12, kind="bold", color="#333333")
        c.rect(lx + 382, ly + 152 + i * 70, 256, 34, fill="#ffffff", stroke="#8a8a8a", sw=1, r=7)
    c.rect(lx + 382, ly + 300, 256, 38, fill=G_DARK, stroke=None, r=8)
    c.text(lx + 510, ly + 319, "Sign In to StudentHub →", size=13, kind="bold", color="#ffffff", anchor="middle")
    c.bar(lx + 440, ly + 356, 140, 6)
    c.circle(lx + 690, ly + 22, 13, fill=G_LIGHT, stroke="#8a8a8a", sw=1)

    notes_column(c, 850, 620, [
        (1, "Home: public landing page", ["Banner, hero with sign-in buttons, slider, FAQ and", "guidelines modal (Practical 4 interactions)"]),
        (2, "Login: split layout", ["Brand panel + form card; register and 403 pages", "reuse the same layout"]),
    ])
    c.callout(bx + 748, by + 40, 1)
    c.callout(lx + 650, ly + 60, 2)
    c.save("wireframe-2-home-login-desktop")


def build_mobile_wireframe():
    c = Canvas(1600, 960)
    c.title_band("Low-fidelity wireframes — Mobile (≤ 1024 px): dashboard, navigation drawer, login", SUBTITLE, dark=False)
    pw, ph, top = 330, 680, 140

    def topbar(x, y, open_state=False):
        c.rect(x, y, pw, 52, fill=G_DARK, stroke=None, r=0)
        c.rect(x + 12, y + 9, 34, 34, fill="#bdbdbd", stroke=None, r=8)
        if open_state:
            c.close_icon(x + 29, y + 26)
        else:
            c.menu_icon(x + 29, y + 26)
        c.rect(x + 58, y + 14, 24, 24, fill="#e0e0e0", stroke=None, r=7)
        c.text(x + 92, y + 26, "StudentHub", size=14, kind="bold", color="#ffffff")
        c.circle(x + pw - 29, y + 26, 16, fill="#bdbdbd", stroke=None)

    # A. Dashboard
    ax = 60
    c.phone(ax, top, pw, ph)
    topbar(ax, top)
    c.rect(ax + 12, top + 66, pw - 24, 150, fill=G_DARK, stroke=None, r=12)
    c.text(ax + 26, top + 96, f"Welcome back, {STUDENT}", size=16, kind="bold", color="#ffffff")
    for i in range(2):
        c.rect(ax + 26, top + 116 + i * 30, 180 - i * 30, 22, fill="#b5b5b5", stroke=None, r=11)
    c.rect(ax + 26, top + 176, 130, 30, fill="#ffffff", stroke=None, r=7)
    c.rect(ax + 164, top + 176, 130, 30, fill="#b5b5b5", stroke=None, r=7)
    for i in range(4):
        x = ax + 12 + (i % 2) * ((pw - 32) / 2 + 8)
        y = top + 228 + (i // 2) * 92
        c.rect(x, y, (pw - 32) / 2, 82, fill="#ffffff", stroke=G_LINE, sw=1.3, r=10)
        c.bar(x + 12, y + 14, 70, 6, fill="#a8a8a8")
        c.bar(x + 12, y + 32, 60, 14, fill="#9d9d9d")
        c.bar(x + 12, y + 58, (pw - 32) / 2 - 24, 6)
    c.text(ax + 14, top + 432, "Timetable → stacked cards", size=13, kind="bold")
    for i in range(2):
        y = top + 448 + i * 112
        c.rect(ax + 12, y, pw - 24, 100, fill="#ffffff", stroke=G_LINE, sw=1.3, r=10)
        c.rect(ax + 12, y, pw - 24, 24, fill=G_LIGHT, stroke=None, r=10)
        for r in range(4):
            c.bar(ax + 24, y + 8 + r * 24, 60, 6, fill="#a8a8a8")
            c.bar(ax + 130, y + 8 + r * 24, 140 - r * 15, 6)

    # B. Drawer open
    bx = 635
    c.phone(bx, top, pw, ph)
    topbar(bx, top, open_state=True)
    c.rect(bx, top + 52, pw, ph - 52, fill="#e6e6e6", stroke=None, r=0)
    for i in range(6):
        c.bar(bx + 260, top + 90 + i * 70, 50, 6, fill="#d0d0d0")
    c.rect(bx, top + 52, 250, ph - 52, fill=G_MID, stroke=None, r=0)
    c.rect(bx + 12, top + 66, 226, 50, fill=G_LIGHT, stroke=None, r=8)
    c.circle(bx + 36, top + 91, 14, fill=G_DARK, stroke=None)
    c.text(bx + 58, top + 84, STUDENT, size=13, kind="bold")
    c.text(bx + 58, top + 101, ROLL, size=11, color="#444444")
    yy = top + 132
    for i in range(12):
        if i in (0, 2, 7, 10):
            c.bar(bx + 16, yy, 60, 5, fill="#b0b0b0")
            yy += 16
        if i == 0:
            c.rect(bx + 8, yy - 4, 234, 26, fill="#b8b8b8", stroke=None, r=6)
        c.rect(bx + 18, yy + 2, 13, 13, fill=G_DARK, stroke=None, r=3)
        c.bar(bx + 40, yy + 5, 90 + (i * 13) % 40, 7, fill="#b5b5b5")
        yy += 30
    c.text(bx + pw / 2, top + ph + 34, "Tap the menu / close button, the backdrop or Esc to close", size=12, color="#444444", anchor="middle")

    # C. Login
    cx = 1210
    c.phone(cx, top, pw, ph)
    c.rect(cx, top, pw, 110, fill=G_DARK, stroke=None, r=16)
    c.rect(cx + 18, top + 20, 26, 26, fill="#e0e0e0", stroke=None, r=7)
    c.text(cx + 54, top + 33, "StudentHub", size=14, kind="bold", color="#ffffff")
    c.text(cx + 18, top + 78, "Your campus, in one place.", size=15, kind="bold", color="#ffffff")
    c.circle(cx + pw - 30, top + 140, 16, fill=G_LIGHT, stroke="#8a8a8a", sw=1)
    c.rect(cx + 14, top + 168, pw - 28, 330, fill="#ffffff", stroke=G_LINE, sw=1.4, r=12)
    c.text(cx + 32, top + 198, "Sign in", size=18, kind="bold")
    for i, label in enumerate(["Username or Email", "Password"]):
        c.text(cx + 32, top + 236 + i * 70, label, size=12, kind="bold", color="#333333")
        c.rect(cx + 32, top + 248 + i * 70, pw - 64, 34, fill="#ffffff", stroke="#8a8a8a", sw=1, r=7)
    c.rect(cx + 32, top + 398, pw - 64, 38, fill=G_DARK, stroke=None, r=8)
    c.text(cx + pw / 2, top + 417, "Sign In →", size=13, kind="bold", color="#ffffff", anchor="middle")
    c.bar(cx + 90, top + 460, 150, 6)

    for i, label in enumerate(["A · Dashboard (drawer closed)", "B · Navigation drawer open", "C · Login (brand panel collapses)"]):
        c.text([ax, bx, cx][i] + pw / 2, top - 24, label, size=15, kind="bold", anchor="middle")
    c.save("wireframe-3-mobile")


if __name__ == "__main__":
    build_sitemap()
    build_dashboard_wireframe()
    build_home_login_wireframe()
    build_mobile_wireframe()
