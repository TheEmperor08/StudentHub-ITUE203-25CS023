<div align="center">
  <h1>🎓 Practical 2</h1>
  <h3>Semantic HTML5 Pages with Accessibility-Ready Structure</h3>
</div>

---

### 👨‍🎓 Student Information
- **Name:** Shreyas
- **ID:** 25CS023
- **Course:** ITUE203 - WEB DEVELOPMENT FRAMEWORKS
- **Year:** 2026-27

---

### 🎯 Objective
> Develop static HTML5 skeletons for at least 10 StudentHub pages using semantic tags and accessibility-friendly structure.

The pages are plain HTML5: **no CSS** (styling follows in Practical 3), **no JavaScript** and **no server**. Forms are skeletons only: their submit buttons are disabled and each form says that nothing is sent or saved. Pages marked **Sample data** contain demonstration content, not real records; the Admin and Directory pages use fictional entries only.

---

### 📄 Pages (17)
| # | Page | File | Group |
|---|---|---|---|
| 1 | Home | [`index.html`](index.html) | Public – required |
| 2 | About | [`about.html`](about.html) | Public – required |
| 3 | Register | [`register.html`](register.html) | Public – required |
| 4 | Login | [`login.html`](login.html) | Public – required |
| 5 | Dashboard | [`dashboard.html`](dashboard.html) | Student – required |
| 6 | Events | [`events.html`](events.html) | Public – required |
| 7 | Profile | [`profile.html`](profile.html) | Student – required |
| 8 | Contact | [`contact.html`](contact.html) | Public – required |
| 9 | Admin | [`admin.html`](admin.html) | Administration – required |
| 10 | FAQ | [`faq.html`](faq.html) | Public – required |
| 11 | Feedback | [`feedback.html`](feedback.html) | Public – required |
| 12 | Courses | [`courses.html`](courses.html) | Student |
| 13 | Attendance | [`attendance.html`](attendance.html) | Student |
| 14 | Assignments | [`assignments.html`](assignments.html) | Student |
| 15 | Results | [`results.html`](results.html) | Student |
| 16 | Notices | [`notifications.html`](notifications.html) | Student |
| 17 | Directory | [`directory.html`](directory.html) | Student |

---

### 🧱 Common Page Structure
Every page uses the same skeleton:

```text
<a href="#main-content">Skip to main content</a>
<header>
    logo (links to Home) + site name
    <nav aria-label="Main navigation">   all 17 pages, current page marked with aria-current="page"
    <nav aria-label="Breadcrumb">        e.g. Home > Dashboard > Attendance
</header>
<main id="main-content">
    <h1> page title, then <section> / <article> / <aside> with <h2>, <h3>
</main>
<footer> links to Contact, FAQ and Feedback; copyright </footer>
```

---

### ♿ Accessibility Checklist
| # | Check | Status | How it was checked |
|---|---|---|---|
| 1 | Every page declares `<!DOCTYPE html>`, `lang="en"`, UTF-8 charset, viewport and a unique `<title>` | ✅ | `source/check_pages.py` |
| 2 | Landmarks: one `<header>`, `<nav>`, exactly one `<main>` and a `<footer>` on every page; content grouped in `<section>` / `<article>` / `<aside>` | ✅ | `source/check_pages.py` |
| 3 | Exactly one `<h1>` per page and no skipped heading levels | ✅ | `source/check_pages.py` |
| 4 | Skip-to-content link is the first link and targets `<main id="main-content">` | ✅ | `source/check_pages.py` + screenshots |
| 5 | Main navigation lists all 17 pages; the current page has `aria-current="page"` (and is shown in bold) | ✅ | `source/check_pages.py` + screenshots |
| 6 | Breadcrumb navigation (`aria-label="Breadcrumb"`) with `aria-current="page"`; separators hidden from screen readers | ✅ | `source/check_pages.py` |
| 7 | Every form control has a `<label>`; radio groups use `<fieldset>` and `<legend>`; useful `autocomplete` values on login, register and profile fields | ✅ | `source/check_pages.py` |
| 8 | Every image has descriptive `alt` text (logo: "StudentHub logo – go to the Home page") | ✅ | `source/check_pages.py` |
| 9 | Data tables have a `<caption>` and `<th scope>` headers | ✅ | `source/check_pages.py` |
| 10 | All local links and in-page `#` links resolve; no `href="#"` placeholders; no external links | ✅ | `source/check_pages.py` |
| 11 | Keyboard friendly: only native links, buttons, form controls and `<details>`; no `tabindex` or click-only elements | ✅ | Code review |
| 12 | No non-working controls: submit buttons are `disabled` and each form explains why; Clear (reset) buttons and `<details>` work without JavaScript | ✅ | `source/check_pages.py` + screenshots |
| 13 | No inline styles, `<style>`, `<script>` or obsolete layout attributes (`cellpadding`, `align`, …) | ✅ | `source/check_pages.py` |
| 14 | Colour contrast and screen-reader behaviour | ⏳ Not tested | Needs a browser accessibility inspector or a screen reader |

`source/check_pages.py` is a local script (Python standard library only). It is **not** the official W3C validator. It checks the rules above, tag nesting and duplicate `id`s, but not every HTML content-model rule. Run it with:

```bash
python Practical-2/source/check_pages.py Practical-2
```

Tables keep `border="1"` so they stay readable without CSS; this attribute is obsolete but still allowed in HTML5.

---

### 📸 Screenshots
Browser screenshots of all 17 pages are in [`screenshots/browser/`](screenshots/browser/). See [`screenshots/README.md`](screenshots/README.md) for how they were made and for the VS Code source screenshots that still have to be added.

---

### 📂 Project Structure
```text
Practical-2/
├── index.html, about.html, events.html, faq.html, contact.html, feedback.html,
│   login.html, register.html                     # public pages
├── dashboard.html, profile.html, courses.html, attendance.html,
│   assignments.html, results.html, notifications.html, directory.html   # student area
├── admin.html                                    # administration
├── images/studenthub-logo.svg
├── screenshots/
│   ├── README.md
│   └── browser/01-home.png … 17-directory.png
├── source/check_pages.py                         # local structure, link and accessibility checks
└── README.md
```

---

### 💻 How to Run
1. Open `index.html` in a web browser (double-click the file). No server is needed.
2. Use the main navigation or the breadcrumb to move between pages.
3. Press **Tab** once on any page to reach the "Skip to main content" link.
