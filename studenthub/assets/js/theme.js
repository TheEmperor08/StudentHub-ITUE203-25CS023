// theme.js — light/dark theme (persisted), mobile navigation drawer and stackable tables.
// Loaded in <head> so the saved theme is applied before the page paints.
(function () {
    function readTheme() {
        try { return localStorage.getItem('sh_theme') || 'light'; } catch (e) { return 'light'; }
    }
    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        document.documentElement.setAttribute('data-bs-theme', theme); // Bootstrap 5.3 pages
    }
    function syncThemeButtons() {
        const dark = document.documentElement.getAttribute('data-theme') === 'dark';
        const icon = dark ? 'bi-sun' : 'bi-moon-stars';
        document.querySelectorAll('.theme-toggle-nav').forEach(function (btn) {
            btn.setAttribute('aria-pressed', String(dark));
            if (btn.classList.contains('theme-toggle-icon')) {
                btn.setAttribute('aria-label', dark ? 'Switch to light mode' : 'Switch to dark mode');
                btn.innerHTML = '<i class="bi ' + icon + '" aria-hidden="true"></i>';
            } else {
                btn.innerHTML = '<i class="bi ' + icon + '" aria-hidden="true"></i> <span>' + (dark ? 'Light mode' : 'Dark mode') + '</span>';
            }
        });
    }

    applyTheme(readTheme());

    window.toggleTheme = function () {
        const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        applyTheme(next);
        try { localStorage.setItem('sh_theme', next); } catch (e) { /* storage unavailable: theme lasts for this page only */ }
        syncThemeButtons();
    };

    function setupNavDrawer() {
        const toggle = document.querySelector('.nav-toggle');
        const nav = document.getElementById('app-nav');
        const backdrop = document.querySelector('.nav-backdrop');
        if (!toggle || !nav) return;

        function setOpen(open) {
            document.body.classList.toggle('nav-open', open);
            toggle.setAttribute('aria-expanded', String(open));
            toggle.setAttribute('aria-label', open ? 'Close navigation menu' : 'Open navigation menu');
            toggle.innerHTML = open ? '<i class="bi bi-x-lg" aria-hidden="true"></i>' : '<i class="bi bi-list" aria-hidden="true"></i>';
            if (backdrop) backdrop.hidden = !open;
            if (open) {
                const current = nav.querySelector('a[aria-current="page"]') || nav.querySelector('a');
                if (current) current.focus();
            }
        }

        toggle.addEventListener('click', function () {
            setOpen(!document.body.classList.contains('nav-open'));
        });
        if (backdrop) backdrop.addEventListener('click', function () { setOpen(false); });
        nav.addEventListener('click', function (e) { if (e.target.closest('a')) setOpen(false); });
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && document.body.classList.contains('nav-open')) {
                setOpen(false);
                toggle.focus();
            }
        });
        // Close the drawer if the window grows back to desktop width
        window.addEventListener('resize', function () {
            if (window.innerWidth > 1024 && document.body.classList.contains('nav-open')) setOpen(false);
        });
    }

    // Copy column headings onto each cell so tables can become stacked cards on phones
    function makeTablesStackable() {
        document.querySelectorAll('.table-wrap table').forEach(function (table) {
            const headings = Array.prototype.map.call(table.querySelectorAll('thead th'), function (th) {
                return th.textContent.trim();
            });
            if (!headings.length) return;
            table.querySelectorAll('tbody tr, tfoot tr').forEach(function (row) {
                let column = 0;
                Array.prototype.forEach.call(row.children, function (cell) {
                    // Cells spanning several columns (e.g. a "Total" label) get no single heading
                    const label = cell.colSpan > 1 ? '' : (headings[column] || '');
                    if (!cell.hasAttribute('data-label')) cell.setAttribute('data-label', label);
                    column += cell.colSpan || 1;
                });
            });
            table.classList.add('is-stacked');
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        syncThemeButtons();
        setupNavDrawer();
        makeTablesStackable();
    });
})();
