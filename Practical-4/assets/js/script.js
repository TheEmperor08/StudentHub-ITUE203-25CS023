// StudentHub – Practical 4: DOM manipulation and event handling for six UI components.
// readPref / writePref / toggleTheme come from theme.js, which is loaded in <head>.
document.addEventListener('DOMContentLoaded', () => {

    // 1. Notification banner: dismissible, and the dismissal is remembered in localStorage
    const BANNER_KEY = 'sh_banner_dismissed';
    const banner = document.getElementById('notification-banner');
    const closeBannerBtn = document.getElementById('close-banner');
    if (banner && closeBannerBtn) {
        if (readPref(BANNER_KEY) === '1') banner.hidden = true;
        closeBannerBtn.addEventListener('click', () => {
            banner.hidden = true;
            writePref(BANNER_KEY, '1');
            document.getElementById('main-content').focus({ preventScroll: true });   // focus does not get lost
        });
    }

    // 2. Theme toggle button: switches and saves the theme; label and aria-pressed follow the state
    const themeToggleBtn = document.getElementById('theme-toggle');
    const showThemeState = () => {
        const dark = document.documentElement.getAttribute('data-theme') === 'dark';
        themeToggleBtn.textContent = dark ? 'Light mode' : 'Dark mode';
        themeToggleBtn.setAttribute('aria-pressed', String(dark));
    };
    if (themeToggleBtn) {
        showThemeState();
        themeToggleBtn.addEventListener('click', () => {
            window.toggleTheme();
            showThemeState();
        });
    }

    // 3. Hamburger menu (below 768px): toggles the link list; Escape closes it
    const hamburgerMenu = document.getElementById('hamburger-menu');
    const navLinks = document.getElementById('nav-links');
    const setMenu = (open) => {
        navLinks.classList.toggle('is-open', open);
        hamburgerMenu.setAttribute('aria-expanded', String(open));
    };
    if (hamburgerMenu && navLinks) {
        hamburgerMenu.addEventListener('click', () => setMenu(!navLinks.classList.contains('is-open')));
        navLinks.addEventListener('click', (e) => {
            if (e.target.closest('a')) setMenu(false);                          // close after choosing a link
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && navLinks.classList.contains('is-open')) {
                setMenu(false);
                hamburgerMenu.focus();
            }
        });
    }

    // 4. Modal popup: focus moves into the dialog, Tab stays inside, Escape / overlay / buttons close it
    const modal = document.getElementById('custom-modal');
    const openModalBtn = document.getElementById('open-modal-btn');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const modalOkBtn = document.getElementById('modal-ok-btn');
    let lastFocused = null;

    const openModal = () => {
        lastFocused = document.activeElement;
        modal.hidden = false;
        closeModalBtn.focus();
    };
    const closeModal = () => {
        modal.hidden = true;
        if (lastFocused) lastFocused.focus();
    };

    if (modal && openModalBtn && closeModalBtn && modalOkBtn) {
        openModalBtn.addEventListener('click', openModal);
        closeModalBtn.addEventListener('click', closeModal);
        modalOkBtn.addEventListener('click', closeModal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal();                                // click on the dark overlay
        });
        document.addEventListener('keydown', (e) => {
            if (modal.hidden) return;
            if (e.key === 'Escape') {
                closeModal();
            } else if (e.key === 'Tab') {                                       // keep focus inside the dialog
                const focusable = [...modal.querySelectorAll('button')];
                const first = focusable[0];
                const last = focusable[focusable.length - 1];
                if (e.shiftKey && document.activeElement === first) {
                    e.preventDefault();
                    last.focus();
                } else if (!e.shiftKey && document.activeElement === last) {
                    e.preventDefault();
                    first.focus();
                }
            }
        });
    }

    // 5. FAQ: one answer open at a time; aria-expanded and the hidden attribute follow the state
    const faqQuestions = document.querySelectorAll('.faq-question');
    faqQuestions.forEach((question) => {
        question.addEventListener('click', () => {
            const answer = document.getElementById(question.getAttribute('aria-controls'));
            const isOpen = question.getAttribute('aria-expanded') === 'true';

            // Close all others
            faqQuestions.forEach((q) => {
                q.setAttribute('aria-expanded', 'false');
                document.getElementById(q.getAttribute('aria-controls')).hidden = true;
            });

            if (!isOpen) {
                question.setAttribute('aria-expanded', 'true');
                answer.hidden = false;
            }
        });
    });

    // 6. Image/content slider: previous/next, dot buttons, auto-play every 5 s with a Pause button
    const slides = document.querySelectorAll('.slide');
    const viewport = document.getElementById('slider-viewport');
    const prevBtn = document.getElementById('slider-prev');
    const nextBtn = document.getElementById('slider-next');
    const pauseBtn = document.getElementById('slider-pause');
    const dotsBox = document.getElementById('slider-dots');
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let currentSlide = 0;
    let timer = null;

    const dots = [...slides].map((slide, i) => {
        const dot = document.createElement('button');
        dot.type = 'button';
        dot.className = 'slider-dot';
        dot.setAttribute('aria-label', `Show slide ${i + 1}`);
        dot.addEventListener('click', () => {
            stopAutoplay();
            showSlide(i);
        });
        dotsBox.appendChild(dot);
        return dot;
    });

    function showSlide(index) {
        currentSlide = (index + slides.length) % slides.length;
        slides.forEach((slide, i) => {
            slide.style.transform = `translateX(${100 * (i - currentSlide)}%)`;
            slide.setAttribute('aria-hidden', String(i !== currentSlide));
        });
        dots.forEach((dot, i) => dot.setAttribute('aria-current', String(i === currentSlide)));
    }

    function startAutoplay() {
        timer = setInterval(() => showSlide(currentSlide + 1), 5000);
        pauseBtn.textContent = 'Pause';
        viewport.setAttribute('aria-live', 'off');                            // do not announce automatic changes
    }

    function stopAutoplay() {
        clearInterval(timer);
        timer = null;
        pauseBtn.textContent = 'Play';
        viewport.setAttribute('aria-live', 'polite');                         // announce slides changed by the user
    }

    if (slides.length && prevBtn && nextBtn && pauseBtn) {
        showSlide(0);
        nextBtn.addEventListener('click', () => {
            stopAutoplay();
            showSlide(currentSlide + 1);
        });
        prevBtn.addEventListener('click', () => {
            stopAutoplay();
            showSlide(currentSlide - 1);
        });
        pauseBtn.addEventListener('click', () => (timer ? stopAutoplay() : startAutoplay()));
        if (reduceMotion) stopAutoplay(); else startAutoplay();
    }

    // Reset saved preferences (theme and banner) – useful when demonstrating the localStorage behaviour
    const resetBtn = document.getElementById('reset-prefs');
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            try {
                localStorage.removeItem(THEME_KEY);
                localStorage.removeItem(BANNER_KEY);
            } catch (e) { /* storage blocked: nothing to reset */ }
            window.location.reload();
        });
    }
});
