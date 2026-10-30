// StudentHub – real-time registration validation (Practical 5 integrated into the portal's register.php).
// The same rules as the server (includes/registration.php, password_problems()) are checked with regular expressions while
// the user types; a password strength meter shows how strong the password is. The form is not sent while a rule is broken.
// The server still checks everything again – this script only gives earlier, friendlier feedback.
(() => {
    'use strict';
    const form = document.querySelector('form[action="register.php"]');
    if (!form) return;
    const NAME = /^\p{L}[\p{L}\p{M} .'-]*$/u;
    const USERNAME = /^[A-Za-z][A-Za-z0-9_]*$/;
    const EMAIL = /^[^\s@<>()[\]\\,;:"]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$/;
    const touched = new Set();

    const value = (name) => (form.elements[name] && form.elements[name].value) || '';
    const byteLength = (text) => new TextEncoder().encode(text).length;

    // Missing password rules, worded like the server's password_problems()
    function passwordProblems(pw) {
        const problems = [];
        if (pw.length < 8) problems.push('at least 8 characters');
        if (byteLength(pw) > 72) problems.push('at most 72 characters');
        if (!/[A-Z]/.test(pw)) problems.push('an uppercase letter');
        if (!/[a-z]/.test(pw)) problems.push('a lowercase letter');
        if (!/[0-9]/.test(pw)) problems.push('a number');
        if (!/[^A-Za-z0-9]/.test(pw)) problems.push('a special character');
        return problems;
    }

    // One message per field (null = valid), the same texts as the server
    const rules = {
        name() {
            const v = value('name').trim().replace(/\s+/g, ' ');
            if (!v) return 'Please enter your full name.';
            if (v.length < 2 || v.length > 100) return 'The name must be 2–100 characters long.';
            return NAME.test(v) ? null : 'Use letters, spaces, apostrophes, dots and hyphens only.';
        },
        username() {
            const v = value('username').trim();
            if (!v) return 'Please choose a username.';
            if (v.length < 3 || v.length > 30) return 'The username must be 3–30 characters long.';
            return USERNAME.test(v) ? null : 'Start with a letter; then use letters, numbers and underscores only.';
        },
        email() {
            const v = value('email').trim();
            if (!v) return 'Please enter your email address.';
            return v.length <= 100 && EMAIL.test(v) ? null : 'Please enter a valid email address, e.g. name@example.com.';
        },
        gender: () => (form.querySelector('input[name="gender"]:checked') ? null : 'Please choose Male, Female or Other.'),
        course: () => (value('course') ? null : 'Please select a course from the list.'),
        adm_year: () => (value('adm_year') ? null : 'Please select an admission year from the list.'),
        password() {
            const pw = value('password');
            if (!pw) return 'Please choose a password.';
            const problems = passwordProblems(pw);
            return problems.length ? 'The password needs ' + problems.join(', ') + '.' : null;
        },
        confirm_password() {
            if (rules.password()) return null;                       // first fix the password itself
            return value('confirm_password') === value('password') ? null : 'The passwords do not match.';
        },
        agree: () => (form.elements.agree.checked ? null : 'Please accept the Terms & Conditions.'),
    };

    // The message element under a field: the server's <p class="field-error" id="x-error"> or a new one
    function errorElement(field) {
        let el = document.getElementById(field + '-error');
        if (!el) {
            el = document.createElement('p');
            el.className = 'field-error';
            el.id = field + '-error';
            const anchor = field === 'agree' ? form.querySelector('.terms-group') : (form.elements[field].length ? form.elements[field][0] : form.elements[field]).closest('.form-group');
            if (field === 'agree') anchor.after(el); else anchor.append(el);
        }
        return el;
    }

    function show(field, message) {
        const input = form.elements[field];
        const inputs = input instanceof RadioNodeList ? [...input] : [input];
        if (!message && !document.getElementById(field + '-error')) return;
        const el = errorElement(field);
        el.textContent = message || '';
        el.hidden = !message;
        inputs.forEach((i) => {
            if (message) {
                i.setAttribute('aria-invalid', 'true');
                if (!(i.getAttribute('aria-describedby') || '').includes(el.id)) i.setAttribute('aria-describedby', ((i.getAttribute('aria-describedby') || '') + ' ' + el.id).trim());
            } else {
                i.removeAttribute('aria-invalid');
            }
        });
    }

    function check(field) {
        const message = rules[field]();
        show(field, message);
        return message === null;
    }

    // Password strength meter (independent of the pass/fail rules above)
    const meter = document.createElement('div');
    meter.className = 'strength';
    meter.innerHTML = '<span class="strength-bar"><span></span></span><span class="strength-label" aria-live="polite"></span>';
    document.getElementById('password-help').after(meter);
    const LEVELS = [['', ''], ['Very weak', 'very-weak'], ['Weak', 'weak'], ['Fair', 'fair'], ['Good', 'good'], ['Strong', 'strong']];
    function updateMeter() {
        const pw = value('password');
        let score = 0;
        if (pw.length >= 8) score++;
        if (pw.length >= 12) score++;
        if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score++;
        if (/[0-9]/.test(pw)) score++;
        if (/[^A-Za-z0-9]/.test(pw)) score++;
        if (pw && score === 0) score = 1;
        const [label, cls] = LEVELS[pw ? Math.max(1, score) : 0];
        meter.dataset.level = cls;
        meter.querySelector('.strength-bar span').style.width = (pw ? Math.max(1, score) * 20 : 0) + '%';
        meter.querySelector('.strength-label').textContent = pw ? 'Password strength: ' + label : '';
    }

    // Real-time: after a field was left once, it is re-checked on every change
    for (const field of Object.keys(rules)) {
        const input = form.elements[field];
        const inputs = input instanceof RadioNodeList ? [...input] : [input];
        inputs.forEach((i) => {
            i.addEventListener('blur', () => { touched.add(field); check(field); });
            i.addEventListener(i.type === 'radio' || i.type === 'checkbox' || i.tagName === 'SELECT' ? 'change' : 'input', () => {
                if (field === 'password') { updateMeter(); if (touched.has('confirm_password')) check('confirm_password'); }
                if (touched.has(field) || i.type === 'radio' || i.type === 'checkbox' || i.tagName === 'SELECT') check(field);
            });
        });
    }

    form.addEventListener('submit', (event) => {
        const invalid = Object.keys(rules).filter((field) => !check(field));
        invalid.forEach((field) => touched.add(field));
        if (invalid.length) {
            event.preventDefault();
            const first = form.elements[invalid[0]];
            (first instanceof RadioNodeList ? first[0] : first).focus();
        }
    });
    updateMeter();
})();
