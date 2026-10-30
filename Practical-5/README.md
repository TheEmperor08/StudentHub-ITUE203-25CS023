<div align="center">
  <h1>🎓 Practical 5</h1>
  <h3>Registration Form with Frontend Validation and User-Friendly Error Handling</h3>
</div>

---

### 👨‍🎓 Student Information
- **Name:** Shreyas
- **ID:** 25CS023
- **Course:** ITUE203 - WEB DEVELOPMENT FRAMEWORKS
- **Year:** 2026-27

---

### 🎯 Objective
> Create a student registration form with HTML5 input types and JavaScript validation (regular expressions) for name, email, mobile number, password, confirm password, course, year, gender and terms acceptance, with clear error messages, a password strength checker, real-time validation and a Canvas CAPTCHA.

---

### 🚀 How to Run
Double-click [`register.html`](register.html) to open it in Chrome or Edge. No server or internet connection is needed: the page uses one local CSS file, one local JavaScript file and system fonts.

> **Static page:** the form does not submit or save any data. When every field is valid, a success message appears on the page; nothing is sent to a server or stored in the browser.

---

### ✅ Validation Rules
| Field | HTML5 attributes | JavaScript rule (regular expression) | Example error message |
|---|---|---|---|
| Full name | `type="text"`, `required`, `minlength="3"`, `maxlength="50"`, `pattern`, `autocomplete="name"` | `/^[A-Za-z][A-Za-z .'-]{2,49}$/` – starts with a letter; letters, spaces, `.` `'` `-` | Use 3–50 letters; only spaces, dots, apostrophes and hyphens are allowed. |
| Email | `type="email"`, `required`, `maxlength="100"`, `autocomplete="email"` | `/^(?!.*\.\.)[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$/` – no `..`, a domain with a dot | Enter a valid email address, for example name@charusat.edu.in. |
| Mobile | `type="tel"`, `inputmode="numeric"`, `required`, `minlength`/`maxlength="10"`, `pattern="[6-9][0-9]{9}"` | `/^[6-9]\d{9}$/` – Indian mobile: 10 digits starting with 6–9 | An Indian mobile number starts with 6, 7, 8 or 9. |
| Gender | radio buttons in a `fieldset` with `legend`, `required` | one option selected | Please select your gender. |
| Course | `select`, `required` | an option selected | Please select your course. |
| Year of study | `select`, `required` | an option selected | Please select your year of study. |
| Password | `type="password"`, `required`, `minlength="8"`, `maxlength="64"`, `autocomplete="new-password"` | `/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9\s])\S{8,64}$/` – 8–64 characters, no spaces, lowercase, uppercase, number, any special character | The password does not meet all the rules listed above. |
| Confirm password | `type="password"`, `required`, `autocomplete="new-password"` | must equal the password | The passwords do not match. |
| CAPTCHA | `required`, `maxlength="5"`, `autocomplete="off"` | equals the code on the canvas, not case-sensitive | The code does not match. Try again or press New code. |
| Terms | checkbox, `required` | must be ticked | You must accept the Terms & Conditions. |

**Error handling**
- Each message appears directly below its field. It is linked to the field with `aria-describedby`, and the field gets `aria-invalid="true"` and a red border. Valid fields get a green border.
- On submit, a summary such as "Please correct 3 fields marked below." is announced to screen readers (`role="alert"`), and focus moves to the first invalid field.
- **Real-time validation:**
  - A field is checked when you leave it (`blur`); after that it is re-checked on every key press (`input`).
  - Selects, radio buttons and checkboxes are checked on `change`.
  - Tabbing through an empty field does not flag it.
  - Changing the password re-checks the confirmation.
- **Password strength:**
  - Five rules, shown as a checklist that ticks as you type.
  - 0–2 rules met: **Weak**; 3–4: **Medium**; all 5: **Strong**. Strong is exactly the same as "valid".
  - The level is also announced to screen readers.
- **Canvas CAPTCHA:**
  - A random 5-character code (no look-alikes such as 0/O or 1/I/L) drawn with rotation, noise lines and dots.
  - **New code** draws a fresh code.
  - ⚠️ It is a **client-side demonstration only, not real security**: the code is checked in the browser, so a script can read it. A visual CAPTCHA also cannot be used by blind users; a real site would verify on the server and offer an accessible alternative.
- **Clear form** resets all fields, messages and the meter, and draws a new code.

---

### 📂 Files
```text
Practical-5/
├── register.html                 # form markup: fieldsets, labels, HTML5 attributes (no inline CSS or JS)
├── assets/css/style.css          # styles (from the original page), contrast-safe colours, mobile layout
├── assets/js/validation.js       # regular expressions, real-time validation, strength meter, Canvas CAPTCHA
├── screenshots/                  # Edge screenshots of the test cases
└── source/check_page.py, contrast_check.py
```

---

### 🧪 Test Results
| Test | How | Result |
|---|---|---|
| Static checks: all 9 fields with HTML5 types and `required`; `minlength`/`maxlength`/`pattern`/`inputmode`/`autocomplete`; labels, fieldsets and legends; `aria-describedby` targets; no inline CSS/JS, no external URLs, no missing files | [`source/check_page.py`](source/check_page.py) | 24 of 24 pass |
| Colour contrast (WCAG 2.1: 4.5:1 text, 3:1 borders and focus outline) | [`source/contrast_check.py`](source/contrast_check.py) | 19 of 19 pass |
| Validation test cases in Microsoft Edge 156 (headless) | Values set and real `input` / `change` / `blur` / `click` events dispatched to the page's own listeners; messages, `aria-invalid`, focus and the success message checked; page errors and `console.error` recorded in every run | **103 of 103 checks pass**, no console errors |

**Validation test cases (all passed in Edge)**

| Field | Invalid inputs tested | Valid inputs tested |
|---|---|---|
| Name | `Ab`, `R2D2`, empty | `Riya Shah`, `Anne-Marie O'Neil`, `␣␣Riya Shah␣␣` (trimmed) |
| Email | `abc`, `abc@`, `abc@charusat`, `a..b@charusat.edu.in` | `name@charusat.edu.in`, `first.last+wdf@gmail.com` |
| Mobile | `98765` (length), `98765abcde` (digits only), `5876543210` (must start 6–9), `0000000000`, `98765432101` | `9876543210`, `6123456789` |
| Password | `abc`, `password1`, `Password1`, `Pass word1!` (space) | `Abcdef1#`, `Str0ng!Pass` |
| Confirm password | different password, empty | same password |
| Course / Year | "-- Select --" | B.Tech - IT / 4th Year |
| Gender / Terms | none selected / unticked | Other / ticked |
| CAPTCHA | `WRONG`, empty, the old code after **New code** | correct code in lowercase and uppercase |

**Other cases tested:**
- **Empty submit:** all 10 messages shown, summary "Please correct 10 fields marked below.", focus on Full name, page not reloaded.
- **Password strength:** `abc` and `abcdefgh` show Weak; `abcdefg1`, `Abcdefg1` and `Abc 1#xyzw` show Medium; `Abcdef1#` shows Strong.
- **Real-time validation:** errors appear on `blur`, clear while typing, and the confirmation is re-checked when the password changes.
- **CAPTCHA:**
  - a wrong code blocks submit;
  - **New code** draws a different code and clears the input.
- **Full valid submit:** success message shown and focused; no navigation, nothing in localStorage, sessionStorage or cookies.
- **Clear form:** resets every message and state.
- **Keyboard:** focusable controls follow the visual order with no positive `tabindex`, and submit focuses the first invalid field (for example, the first gender radio button).
- **375px:** no horizontal scrolling, with or without error messages.

**Screenshots** ([`screenshots/`](screenshots/), real Edge renders made with the same scripted inputs):
- `empty-errors.png`, `invalid-inputs.png`, `live-validation.png`
- `password-weak.png`, `password-medium.png`, `password-strong.png`
- `captcha-wrong.png`, `captcha-correct.png`, `success.png`
- `mobile-375.png`, `mobile-375-errors.png`

In the screenshot runs only, the strength bar's 0.3 s width animation is switched off, so the bar is captured at its final width.

**Not tested:** physical mouse/keyboard use by a person (events were dispatched by script; real Tab-key movement was not simulated), screen readers, browsers other than Edge, real phones and the W3C validator.

```bash
python Practical-5/source/check_page.py
python Practical-5/source/contrast_check.py
```
