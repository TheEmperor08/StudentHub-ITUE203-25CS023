<div align="center">
  <h1>🎓 Practical 3</h1>
  <h3>Responsive UI Design using CSS Grid, Flexbox & Bootstrap</h3>
</div>

---

### 👨‍🎓 Student Information
- **Name:** Shreyas
- **ID:** 25CS023
- **Course:** ITUE203 - WEB DEVELOPMENT FRAMEWORKS
- **Year:** 2026-27

---

### 🎯 Demonstrations
| Technique | Pages | Purpose | Layout code |
|---|---|---|---|
| **Flexbox** | Home [`index.html`](index.html), About [`about.html`](about.html) | Navigation that wraps, hero with text and alerts side by side, card rows that wrap from 1 to 2 to 3–4 per row | [`assets/css/flex.css`](assets/css/flex.css), header/footer in [`assets/css/base.css`](assets/css/base.css) |
| **CSS Grid** | Dashboard [`dashboard.html`](dashboard.html), Events [`events.html`](events.html) | Page layouts with `grid-template-areas`; card grids with `repeat(auto-fit / auto-fill, minmax())` | [`assets/css/grid.css`](assets/css/grid.css) |
| **Bootstrap 5.3** | Registration [`register.html`](register.html) (also [`login.html`](login.html)) | Responsive navbar with collapse menu, grid (`row`, `col-12 col-md-6`), form components | [`assets/css/bootstrap-custom.css`](assets/css/bootstrap-custom.css), [`vendor/bootstrap-5.3.3/`](vendor/bootstrap-5.3.3/) |

- **Mobile-first:** base styles target phones; `min-width` breakpoints at **768px** (tablet) and **1024px** (desktop). Bootstrap uses its `md` (768px) and `lg` breakpoints.
- **Navigation:** all pages are linked by the same navigation bar. Accessibility features: skip link, breadcrumb, `aria-current` and labelled form fields.
- **Static demo:** forms have disabled submit buttons and say that nothing is sent. Content marked **Sample data** is demonstration content only.

---

### 🚀 How to Open on Another Computer
1. Copy the whole `Practical-3` folder (keep the folder structure).
2. Double-click `index.html` to open it in Chrome or Edge.

No internet connection, PHP, XAMPP, database, npm or build step is needed. All paths are relative.

To view the three layouts, press **F12** and then **Ctrl+Shift+M**, and set the width to **375**, **768** or **1280**.

**Required supporting files:** `assets/css/*.css`, `assets/images/studenthub-logo.svg`, and `vendor/bootstrap-5.3.3/` (official Bootstrap 5.3.3 CSS + JS bundle, MIT licence, stored locally). The pages use system fonts; no web fonts are downloaded.

---

### 📸 Screenshots
| Folder | Contents |
|---|---|
| [`screenshots/mobile/`](screenshots/mobile/) | 375px: `index-mobile.png`, `about-mobile.png`, `dashboard-mobile.png`, `events-mobile.png`, `register-mobile.png`, `login-mobile.png` |
| [`screenshots/tablet/`](screenshots/tablet/) | 768px: same six pages (`*-tablet.png`) |
| [`screenshots/desktop/`](screenshots/desktop/) | 1280px: same six pages (`*-desktop.png`) |
| [`screenshots/source-code/`](screenshots/source-code/) | Source evidence: `flexbox-css.png`, `flexbox-html.png`, `grid-css.png`, `grid-html.png`, `bootstrap-html.png`, `bootstrap-css.png` |

- **Browser screenshots:** real full-page renders by Microsoft Edge 156 (headless). Edge's headless window cannot be narrower than about 500px, so each page was loaded in a frame of exactly 375, 768 or 1280 CSS pixels, and the page's media queries respond to that width.
- **Source evidence images:** exact lines from the files, shown with their real line numbers and rendered in Edge. They are not VS Code screenshots.

---

### ✅ Tests
| Test | Result |
|---|---|
| [`source/check_pages.py`](source/check_pages.py): structure, headings, labels, skip link, navigation and breadcrumb, local links, no inline styles or external URLs, mobile-first CSS, Bootstrap file hashes | All pages pass |
| Layout checks inside Edge at 375 / 768 / 1280px (computed CSS: `display: grid` / `flex`, column counts, flex direction, cards per row, Bootstrap CSS and JS loaded, menu button only below 768px) | 57 of 57 pass |
| Horizontal overflow (page `scrollWidth` vs viewport) at all three widths | None, 18 of 18 renders |
| [`source/contrast_check.py`](source/contrast_check.py) (WCAG 2.1 contrast) | 27 of 27 colour pairs pass |
| All screenshots opened and inspected | Readable, correctly rendered |

**Not tested:** real phones and tablets, browsers other than Edge, screen readers, manual keyboard use, and the official W3C validator.

```bash
python Practical-3/source/check_pages.py
python Practical-3/source/contrast_check.py
```
