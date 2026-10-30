// StudentHub – Practical 9: client-side validation and password strength indicator.
// This only helps the user; register.php checks every rule again on the server.
'use strict';

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('register-form');
    if (!form) {
        return;                                  // success page: no form
    }
    form.noValidate = true;                      // show our own messages instead of the browser's pop-ups

    const field = (id) => document.getElementById(id);
    const bytes = (text) => new TextEncoder().encode(text).length;

    // Same rules as password_problems() in includes/registration.php
    const passwordRules = {
        length: (p) => p.length >= 8 && bytes(p) <= 72,
        upper: (p) => /[A-Z]/.test(p),
        lower: (p) => /[a-z]/.test(p),
        number: (p) => /[0-9]/.test(p),
        special: (p) => /[^A-Za-z0-9]/.test(p),
    };

    // Each check returns an error message, or '' when the value is valid (same messages as the server)
    const checks = {
        full_name: (v) => {
            v = v.trim().replace(/\s+/g, ' ');
            if (v === '') return 'Full name is required.';
            if (v.length < 2 || v.length > 100) return 'Full name must be 2 to 100 characters long.';
            if (!/^\p{L}[\p{L}\p{M} .'-]*$/u.test(v)) return 'Full name may contain only letters, spaces, apostrophes, hyphens and full stops.';
            return '';
        },
        username: (v) => {
            v = v.trim();
            if (v === '') return 'Username is required.';
            if (v.length < 3 || v.length > 30) return 'Username must be 3 to 30 characters long.';
            if (!/^[A-Za-z][A-Za-z0-9_]*$/.test(v)) return 'Username must start with a letter and contain only letters, numbers and underscores.';
            return '';
        },
        email: (v) => {
            v = v.trim();
            if (v === '') return 'Email address is required.';
            if (v.length > 254 || field('email').validity.typeMismatch || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) {
                return 'Enter a valid email address, for example name@example.com.';
            }
            return '';
        },
        password: (v) => {
            if (v === '') return 'Password is required.';
            const missing = Object.keys(passwordRules).filter((rule) => !passwordRules[rule](v));
            return missing.length ? 'Password does not meet all the rules listed below.' : '';
        },
        confirm_password: (v) => {
            if (v === '') return 'Please confirm your password.';
            return v !== field('password').value ? 'Passwords do not match.' : '';
        },
        terms: () => (field('terms').checked ? '' : 'You must accept the terms and conditions.'),
    };

    function showError(id, message) {
        const input = field(id);
        input.closest('.field').classList.toggle('has-error', message !== '');
        field(`${id}-error`).textContent = message;
        if (message) {
            input.setAttribute('aria-invalid', 'true');
        } else {
            input.removeAttribute('aria-invalid');
        }
    }

    const validate = (id) => {
        const message = checks[id](field(id).value);
        showError(id, message);
        return message === '';
    };

    // Validate a field when the user leaves it, and again while typing once it has shown an error
    Object.keys(checks).forEach((id) => {
        const input = field(id);
        input.addEventListener('blur', () => { if (input.value !== '' || input.type === 'checkbox') validate(id); });
        input.addEventListener(input.type === 'checkbox' ? 'change' : 'input', () => {
            if (input.getAttribute('aria-invalid') === 'true') validate(id);
            if (id === 'password' && field('confirm_password').value !== '') validate('confirm_password');
        });
    });

    // Password strength indicator: rules met plus a bonus for length
    const strength = field('strength');
    const fill = field('strength-fill');
    const label = field('strength-label');
    const levels = [
        { text: 'Very weak', css: 'very-weak' },
        { text: 'Weak', css: 'weak' },
        { text: 'Fair', css: 'fair' },
        { text: 'Good', css: 'good' },
        { text: 'Strong', css: 'strong' },
    ];
    field('password').addEventListener('input', (event) => {
        const p = event.target.value;
        strength.hidden = p === '';
        let met = 0;
        Object.keys(passwordRules).forEach((rule) => {
            const ok = passwordRules[rule](p);
            met += ok ? 1 : 0;
            document.querySelector(`[data-rule="${rule}"]`).classList.toggle('met', ok);
        });
        const allMet = met === Object.keys(passwordRules).length;
        const score = allMet ? (p.length >= 12 ? 4 : 3) : Math.min(met, 2) - (p.length < 8 ? 1 : 0);
        const level = levels[Math.max(0, score)];
        fill.className = level.css;
        fill.style.width = `${(Math.max(0, score) + 1) * 20}%`;
        label.textContent = `Password strength: ${level.text}`;
    });

    form.addEventListener('submit', (event) => {
        const invalid = Object.keys(checks).filter((id) => !validate(id));
        if (invalid.length) {
            event.preventDefault();
            field(invalid[0]).focus();
        }
    });

    // After a server-side error, move the keyboard focus to the error summary
    const alertBox = document.getElementById('form-alert');
    if (alertBox) {
        alertBox.focus();
    }
});
