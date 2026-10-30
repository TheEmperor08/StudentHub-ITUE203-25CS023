// StudentHub – Practical 5: registration form validation with regular expressions,
// real-time feedback, a password strength meter and a Canvas CAPTCHA.
// This is a static page: nothing is sent to a server or saved.
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('registerForm');
    const summary = document.getElementById('form-summary');
    const success = document.getElementById('success-message');
    const announcer = document.getElementById('sr-announcer');
    form.noValidate = true;   // JavaScript shows its own messages; without JavaScript the browser's HTML5 checks still apply

    // Regular expressions
    const PATTERNS = {
        name: /^[A-Za-z][A-Za-z .'-]{2,49}$/,                                     // 3–50 chars, starts with a letter
        email: /^(?!.*\.\.)[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$/,
        mobile: /^[6-9]\d{9}$/,                                                   // Indian mobile: 10 digits, starts 6–9
        password: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9\s])\S{8,64}$/,
    };

    // The same rules drive the checklist, the strength meter and PATTERNS.password
    const PASSWORD_RULES = [
        { id: 'rule-length', test: (v) => /^\S{8,64}$/.test(v) },
        { id: 'rule-lower', test: (v) => /[a-z]/.test(v) },
        { id: 'rule-upper', test: (v) => /[A-Z]/.test(v) },
        { id: 'rule-digit', test: (v) => /\d/.test(v) },
        { id: 'rule-special', test: (v) => /[^A-Za-z0-9\s]/.test(v) },
    ];

    const value = (id) => document.getElementById(id).value;
    const radios = [...document.querySelectorAll('input[name="gender"]')];
    const controlsOf = (field) => (field === 'gender' ? radios : [document.getElementById(field)]);

    // Canvas CAPTCHA (client-side demonstration only – the code is visible to any script on the page)
    const CAPTCHA_CHARS = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789';                      // no 0/O, 1/I/L look-alikes
    const canvas = document.getElementById('captcha-canvas');
    const ctx = canvas.getContext('2d');
    let captchaCode = '';
    const randomInt = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;

    const drawCaptcha = () => {
        captchaCode = Array.from({ length: 5 }, () => CAPTCHA_CHARS[randomInt(0, CAPTCHA_CHARS.length - 1)]).join('');
        ctx.fillStyle = '#f1f5f9';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        for (let i = 0; i < 6; i++) {                                             // noise lines
            ctx.strokeStyle = `hsl(${randomInt(0, 360)}, 45%, 65%)`;
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.moveTo(randomInt(0, canvas.width), randomInt(0, canvas.height));
            ctx.lineTo(randomInt(0, canvas.width), randomInt(0, canvas.height));
            ctx.stroke();
        }
        ctx.font = 'bold 30px Consolas, "Courier New", monospace';
        ctx.textBaseline = 'middle';
        [...captchaCode].forEach((ch, i) => {                                     // each character slightly moved and rotated
            ctx.save();
            ctx.translate(28 + i * 36, 30 + randomInt(-5, 5));
            ctx.rotate((randomInt(-25, 25) * Math.PI) / 180);
            ctx.fillStyle = `hsl(${randomInt(200, 260)}, 60%, 25%)`;
            ctx.fillText(ch, -9, 0);
            ctx.restore();
        });
        for (let i = 0; i < 40; i++) {                                            // noise dots
            ctx.fillStyle = 'rgba(51, 65, 85, 0.35)';
            ctx.fillRect(randomInt(0, canvas.width), randomInt(0, canvas.height), 2, 2);
        }
    };

    // One validator per field: returns an error message, or '' when the value is valid
    const validators = {
        name: () => {
            const v = value('name').trim();
            if (!v) return 'Please enter your full name.';
            return PATTERNS.name.test(v) ? '' : 'Use 3–50 letters; only spaces, dots, apostrophes and hyphens are allowed.';
        },
        email: () => {
            const v = value('email').trim();
            if (!v) return 'Please enter your email address.';
            return PATTERNS.email.test(v) ? '' : 'Enter a valid email address, for example name@charusat.edu.in.';
        },
        mobile: () => {
            const v = value('mobile').trim();
            if (!v) return 'Please enter your mobile number.';
            if (!/^\d+$/.test(v)) return 'Use digits only.';
            if (v.length !== 10) return 'The mobile number must have exactly 10 digits.';
            return PATTERNS.mobile.test(v) ? '' : 'An Indian mobile number starts with 6, 7, 8 or 9.';
        },
        gender: () => (radios.some((r) => r.checked) ? '' : 'Please select your gender.'),
        course: () => (value('course') ? '' : 'Please select your course.'),
        year: () => (value('year') ? '' : 'Please select your year of study.'),
        password: () => {
            const v = value('password');
            if (!v) return 'Please create a password.';
            return PATTERNS.password.test(v) ? '' : 'The password does not meet all the rules listed above.';
        },
        cPassword: () => {
            const v = value('cPassword');
            if (!v) return 'Please re-enter your password.';
            return v === value('password') ? '' : 'The passwords do not match.';
        },
        captcha: () => {
            const v = value('captcha').trim();
            if (!v) return 'Please type the code shown in the image.';
            return v.toUpperCase() === captchaCode ? '' : 'The code does not match. Try again or press New code.';
        },
        terms: () => (document.getElementById('terms').checked ? '' : 'You must accept the Terms & Conditions.'),
    };
    const FIELDS = Object.keys(validators);
    const touched = new Set();                                                    // fields the user has already left or submitted

    // Shows the message next to the field and sets aria-invalid; returns true when valid
    const validate = (field) => {
        const message = validators[field]();
        document.getElementById(`${field}-error`).textContent = message;
        const group = document.getElementById(`${field}-group`);
        group.classList.toggle('has-error', Boolean(message));
        group.classList.toggle('is-valid', !message);
        controlsOf(field).forEach((el) => el.setAttribute('aria-invalid', String(Boolean(message))));
        return !message;
    };

    const clearField = (field) => {
        document.getElementById(`${field}-error`).textContent = '';
        document.getElementById(`${field}-group`).classList.remove('has-error', 'is-valid');
        controlsOf(field).forEach((el) => el.removeAttribute('aria-invalid'));
    };

    // Password strength meter and rules checklist
    const strengthBar = document.getElementById('strength-bar');
    const strengthText = document.getElementById('strength-text');
    const updateStrength = () => {
        const v = value('password');
        const met = PASSWORD_RULES.filter((rule) => {
            const ok = rule.test(v);
            const item = document.getElementById(rule.id);
            item.classList.toggle('met', ok);
            item.querySelector('.rule-state').textContent = ok ? 'met' : 'not met';
            return ok;
        }).length;
        let level = '';
        if (v) level = met === PASSWORD_RULES.length ? 'strong' : met >= 3 ? 'medium' : 'weak';
        if (strengthBar.dataset.level === level) return;                          // announce only when the level changes
        strengthBar.dataset.level = level;
        strengthText.dataset.level = level;
        strengthText.textContent = level ? `Strength: ${level[0].toUpperCase()}${level.slice(1)}` : '';
    };

    // Real-time validation: input (each key press or paste), change and blur
    FIELDS.forEach((field) => {
        controlsOf(field).forEach((el) => {
            const isText = el.tagName === 'INPUT' && ['text', 'email', 'tel', 'password'].includes(el.type);
            if (isText) {
                el.addEventListener('input', () => {
                    if (touched.has(field)) validate(field);
                });
                el.addEventListener('blur', () => {
                    if (el.value.trim() || touched.has(field)) {                 // do not flag a field the user only tabbed through
                        touched.add(field);
                        validate(field);
                    }
                });
            } else {
                el.addEventListener('change', () => {
                    touched.add(field);
                    validate(field);
                });
            }
        });
    });

    document.getElementById('password').addEventListener('input', () => {
        updateStrength();
        if (touched.has('cPassword')) validate('cPassword');                      // keep the match check up to date
    });

    document.getElementById('captcha-refresh').addEventListener('click', () => {
        drawCaptcha();
        document.getElementById('captcha').value = '';
        touched.delete('captcha');
        clearField('captcha');
        announcer.textContent = 'A new CAPTCHA code was drawn.';
        document.getElementById('captcha').focus();
    });

    // Submit: check every field, then show either the errors or the success message
    form.addEventListener('submit', (e) => {
        e.preventDefault();                                                       // static page: never submit
        FIELDS.forEach((field) => touched.add(field));
        const invalid = FIELDS.filter((field) => !validate(field));

        if (invalid.length) {
            success.hidden = true;
            summary.hidden = false;
            summary.textContent = `Please correct ${invalid.length} ${invalid.length === 1 ? 'field' : 'fields'} marked below.`;
            controlsOf(invalid[0])[0].focus();                                    // focus the first invalid field
            return;
        }

        summary.hidden = true;
        document.getElementById('success-name').textContent = value('name').trim();
        success.hidden = false;
        success.focus();
    });

    // Clear form: the reset event fires before the values are cleared, so tidy up afterwards
    form.addEventListener('reset', () => {
        setTimeout(() => {
            touched.clear();
            FIELDS.forEach(clearField);
            summary.hidden = true;
            success.hidden = true;
            updateStrength();
            drawCaptcha();
        }, 0);
    });

    drawCaptcha();
    updateStrength();
});
