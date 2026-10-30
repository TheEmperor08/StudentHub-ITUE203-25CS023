// Loaded in <head>: applies the saved theme before the page is drawn, so there is no flash of the wrong theme.
const THEME_KEY = 'sh_theme';

function readPref(key) {
    try { return localStorage.getItem(key); } catch (e) { return null; }   // storage may be blocked
}

function writePref(key, value) {
    try { localStorage.setItem(key, value); } catch (e) { /* preference simply is not remembered */ }
}

document.documentElement.setAttribute('data-theme', readPref(THEME_KEY) === 'dark' ? 'dark' : 'light');

window.toggleTheme = () => {
    const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    writePref(THEME_KEY, next);
    return next;
};
