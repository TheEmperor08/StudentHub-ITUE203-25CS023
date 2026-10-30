<div align="center">
  <h1>🎓 Practical 4</h1>
  <h3>JavaScript DOM Manipulation, Event Handling, and UI Interactivity</h3>
</div>

---

### 👨‍🎓 Student Information
- **Name:** Shreyas
- **ID:** 25CS023
- **Course:** ITUE203 - WEB DEVELOPMENT FRAMEWORKS
- **Year:** 2026-27

---

### 🎯 Objective
> Add dynamic UI components (collapsible FAQ, modal popup, image/content slider, notification banner, hamburger menu, light/dark theme switcher) using JavaScript ES6+, DOM manipulation and event handling.

---

### 🚀 How to Run
Double-click [`index.html`](index.html) to open it in Chrome or Edge. It works offline: no server or internet connection is needed, and it uses only local images and system fonts.

---

### 🎬 Demonstrating the Six Components
| # | Component | How to demonstrate | Code in [`assets/js/script.js`](assets/js/script.js) |
|---|---|---|---|
| 1 | **Collapsible FAQ** | Click a question in *Quick FAQ*. It opens; clicking another question opens that one and closes the first. | FAQ block: `click` listeners toggle `hidden` and `aria-expanded` |
| 2 | **Modal popup** | Click **View portal guidelines**. Close it with ×, **I understand**, a click on the dark background, or **Escape**. **Tab** stays inside the dialog, and focus returns to the button afterwards. | Modal block: `openModal()` / `closeModal()`, `keydown` for Escape and Tab |
| 3 | **Image/content slider** | Use **‹ ›**, the three dots, and **Pause/Play**. The slider auto-advances every 5 s. | Slider block: `showSlide()`, `setInterval`, dots created with `createElement` |
| 4 | **Notification banner** | Click × on the purple banner at the top, then reload: it stays hidden (saved in `localStorage`). | Banner block: `sh_banner_dismissed` key |
| 5 | **Hamburger menu** | Make the window narrower than 768px (or press **F12** → **Ctrl+Shift+M** → width 375). Click **☰ Menu**; **Escape** or choosing a link closes it. | Hamburger block: `classList.toggle('is-open')`, `aria-expanded` |
| 6 | **Light/dark theme** | Click **Dark mode** in the header, then reload: the dark theme is restored. | [`assets/js/theme.js`](assets/js/theme.js) applies the saved theme in `<head>` before the page is drawn; `sh_theme` key |

- **Reset saved preferences** (footer) clears the saved theme and banner state and reloads, ready for the next demonstration.
- **Transitions:** cards lift on hover; buttons, theme colours and the FAQ "+" icon animate.
- **Reduced motion:** if the computer has *Animation effects* turned off (Windows Settings → Accessibility → Visual effects), the browser reports "reduce motion". The slider then **starts paused** (press **Play**), and sliding or lifting movement is switched off; colour transitions stay. This is the case on the PC used to develop this practical.

---

### 📂 Files
```text
Practical-4/
├── index.html                    # page structure and the six components (no inline CSS or JS)
├── assets/css/style.css          # all styles, light/dark colour variables, transitions
├── assets/js/theme.js            # localStorage helpers + theme restore (loaded in <head>)
├── assets/js/script.js           # DOM selection, event listeners, the six components
├── assets/images/                # logo and three local slide images (SVG)
├── screenshots/                  # Edge screenshots of the components working
└── source/check_page.py, contrast_check.py
```

---

### ✅ Test Results
| Test | How | Result |
|---|---|---|
| Static checks: no inline styles, `onclick` or `<style>`; no external URLs; all local files and `#links` exist; no duplicate ids; one `<h1>`; every id used by the JS exists; labelled buttons; image `alt`; ES6+ syntax | [`source/check_page.py`](source/check_page.py) | 15 of 15 pass |
| Colour contrast, light and dark theme (WCAG 2.1: 4.5:1 text, 3:1 dots and focus outline) | [`source/contrast_check.py`](source/contrast_check.py) | 22 of 22 pass, after the dark-theme slider dots were lightened (they measured 2.98:1) |
| All six components, in Microsoft Edge 156 (headless) | Scripted clicks and key presses (`click()`, `keydown` Escape / Tab / Shift+Tab) dispatched to the page's own listeners; resulting DOM state, focus and `localStorage` checked | 56 of 56 checks pass |
| Theme and banner persistence after reload | Page loaded again in a new Edge session with the same browser profile | Dark theme and dismissed banner restored |
| Browser console | Page errors, failed file loads and `console.error` recorded in every test run | No errors |
| Hamburger menu at 375px | Page loaded in a frame exactly 375px wide | Opens, closes with Escape and with a link; no horizontal overflow |

**Screenshots** ([`screenshots/`](screenshots/)): `page-desktop.png`, `page-mobile.png`, `faq.png`, `modal.png`, `slider.png`, `menu.png`, `banner-dismissed-after-reload.png`, `dark-theme-after-reload.png`. They are real Edge renders, made with the same scripted clicks.

**Not tested:** physical mouse and keyboard use by a person, screen readers, browsers other than Edge, real phones, and the W3C validator. Native button activation with Enter/Space was not simulated; the components use real `<button>` elements, which browsers activate with the keyboard.

```bash
python Practical-4/source/check_page.py
python Practical-4/source/contrast_check.py
```
