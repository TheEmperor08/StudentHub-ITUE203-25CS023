// StudentHub – Event Finder (Practical 13): lists, searches and changes events through the JSON API api/events.php with
// the Fetch API, without reloading the page. Loading, success and error states are shown in the page; every value from
// the server is inserted with textContent (never as HTML). State-changing requests send the CSRF token in X-CSRF-Token.
(() => {
    'use strict';
    const API = 'api/events.php';
    const root = document.getElementById('main-content');
    const token = document.querySelector('meta[name="csrf-token"]').content;
    const canManage = root.dataset.canManage === '1';
    const canRegister = root.dataset.canRegister === '1';
    const filters = document.getElementById('event-filters');
    const results = document.getElementById('event-results');
    const loading = document.getElementById('live-loading');
    const summary = document.getElementById('live-summary');
    const message = document.getElementById('live-message');
    const dialog = document.getElementById('event-dialog');
    const form = document.getElementById('event-form');
    let timer = null;
    let controller = null;
    let events = [];

    // ------------------------------------------------------------ helpers
    function el(tag, attrs = {}, ...children) {
        const node = document.createElement(tag);
        for (const [key, value] of Object.entries(attrs)) {
            if (key === 'class') node.className = value;
            else if (key === 'text') node.textContent = value;
            else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
            else node.setAttribute(key, value);
        }
        children.flat().forEach((c) => c && node.append(c));
        return node;
    }

    function icon(name) {
        return el('i', { class: 'bi ' + name, 'aria-hidden': 'true' });
    }

    function showMessage(type, text) {
        message.className = 'live-message alert-' + (type === 'success' ? 'success' : 'error');
        message.replaceChildren(icon(type === 'success' ? 'bi-check-circle-fill' : 'bi-exclamation-triangle-fill'), el('p', { text }));
        message.hidden = false;
    }

    // One API call. Returns {status, data}; network failures and non-JSON answers become an error object.
    async function api(action, { method = 'GET', params = {}, body = null, signal } = {}) {
        const url = API + '?' + new URLSearchParams({ action, ...params });
        const headers = { Accept: 'application/json' };
        if (body !== null) {
            headers['Content-Type'] = 'application/json';
            headers['X-CSRF-Token'] = token;
        }
        let response;
        try {
            response = await fetch(url, { method, headers, body: body === null ? undefined : JSON.stringify(body), credentials: 'same-origin', signal });
        } catch (error) {
            if (error.name === 'AbortError') throw error;
            return { status: 0, data: { ok: false, error: 'The server could not be reached. Check your connection and try again.' } };
        }
        let data;
        try {
            data = await response.json();
        } catch {
            data = { ok: false, error: 'The server sent an unexpected answer (HTTP ' + response.status + ').' };
        }
        if (response.status === 401) {
            data.error = (data.error || 'Please sign in again.') + ' Reload the page to sign in.';
        }
        return { status: response.status, data };
    }

    // ------------------------------------------------------------ list
    async function load() {
        if (controller) controller.abort();
        const current = controller = new AbortController();
        const params = Object.fromEntries(new FormData(filters));
        results.setAttribute('aria-busy', 'true');
        loading.hidden = false;
        try {
            const { status, data } = await api('list', { params, signal: current.signal });
            if (!data.ok) {
                renderError(data.error || 'The events could not be loaded (HTTP ' + status + ').');
                return;
            }
            events = data.events;
            render();
            summary.textContent = data.count === 0 ? 'No events match your search.' : data.count + (data.count === 1 ? ' event found.' : ' events found.');
        } catch (error) {
            if (error.name !== 'AbortError') renderError('The events could not be loaded.');
        } finally {
            if (current === controller) {                  // a newer search has not replaced this one
                results.setAttribute('aria-busy', 'false');
                loading.hidden = true;
            }
        }
    }

    function renderError(text) {
        summary.textContent = '';
        results.replaceChildren(el('div', { class: 'alert-error live-error', role: 'alert' },
            icon('bi-exclamation-triangle-fill'), el('p', { text }),
            el('button', { type: 'button', class: 'btn-secondary btn-sm', onclick: load, text: 'Try again' })));
    }

    function render() {
        if (events.length === 0) {
            results.replaceChildren(el('p', { class: 'section-note live-empty', text: 'No events found. Try another search or filter.' }));
            return;
        }
        results.replaceChildren(...events.map(card));
    }

    function card(ev) {
        const date = new Date(ev.event_date + 'T00:00:00');
        const seats = ev.capacity === null ? ev.seats_taken + ' registered · no seat limit' : ev.seats_taken + ' of ' + ev.capacity + ' seats taken';
        const body = el('div', { class: 'notice-body' },
            el('h3', { text: ev.title }),
            el('p', { text: ev.description || 'Campus event organised at CSPIT, CHARUSAT.' }),
            el('div', { class: 'notice-meta' },
                el('span', {}, icon('bi-calendar3'), ' ' + ev.when),
                el('span', {}, icon('bi-geo-alt'), ' ' + ev.location),
                el('span', {}, icon('bi-people'), ' ' + seats),
                el('mark', { text: ev.category }),
                el('span', { class: 'badge ' + (ev.status === 'open' ? 'badge-success' : 'badge-neutral'), text: ev.status === 'open' ? 'Open' : 'Closed' })),
            actions(ev));
        return el('article', { class: 'notice event-card', 'data-id': String(ev.id) },
            el('div', { class: 'date-badge', 'aria-hidden': 'true' },
                el('span', { class: 'month', text: date.toLocaleString('en', { month: 'short' }) }),
                el('span', { class: 'day', text: String(date.getDate()).padStart(2, '0') })),
            ev.poster_url ? el('img', { class: 'event-poster', src: ev.poster_url, alt: 'Poster: ' + ev.title, width: '120', height: '120' }) : null,
            body);
    }

    function actions(ev) {
        const box = el('div', { class: 'event-actions' });
        if (canManage) {
            box.append(el('button', { type: 'button', class: 'btn-secondary btn-sm', 'aria-label': 'Edit ' + ev.title, onclick: () => openDialog(ev) }, icon('bi-pencil'), ' Edit'),
                el('button', { type: 'button', class: 'btn-secondary btn-sm btn-danger-text', 'aria-label': 'Delete ' + ev.title, onclick: () => remove(ev) }, icon('bi-trash'), ' Delete'),
                el('span', { class: 'badge badge-neutral', text: ev.registrations_total + ' registration(s)' }));
        }
        if (canRegister) {
            if (ev.my_registration === 'registered') {
                box.append(el('span', { class: 'badge badge-success' }, icon('bi-check2-circle'), ' You are registered'),
                    el('button', { type: 'button', class: 'btn-secondary btn-sm', onclick: () => change('cancel', ev) }, 'Cancel registration'));
            } else if (ev.my_registration === 'attended') {
                box.append(el('span', { class: 'badge badge-success', text: 'Attended' }));
            } else if (ev.is_past) {
                box.append(el('span', { class: 'badge badge-neutral', text: 'Event has taken place' }));
            } else if (ev.status !== 'open') {
                box.append(el('span', { class: 'badge badge-neutral', text: 'Registration closed' }));
            } else if (ev.seats_left === 0) {
                box.append(el('span', { class: 'badge badge-warning', text: 'Event full' }));
            } else {
                box.append(el('button', { type: 'button', class: 'btn-sm', onclick: () => change('register', ev) }, icon('bi-person-plus'), ' Register'));
            }
        }
        return box.childElementCount ? box : null;
    }

    // ------------------------------------------------------------ student: register / cancel
    async function change(action, ev) {
        const { data } = await api(action, { method: 'POST', body: { event_id: ev.id } });
        showMessage(data.ok ? 'success' : 'error', data.ok ? data.message : data.error);
        load();
    }

    // ------------------------------------------------------------ admin: create / edit / delete
    function clearErrors() {
        form.querySelectorAll('.field-error').forEach((e) => { e.textContent = ''; });
        form.querySelectorAll('[aria-invalid]').forEach((e) => e.removeAttribute('aria-invalid'));
    }

    function openDialog(ev = null) {
        clearErrors();
        form.reset();
        document.getElementById('event-dialog-title').textContent = ev ? 'Edit event' : 'New event';
        form.elements.id.value = ev ? ev.id : '';
        if (ev) {
            for (const field of ['title', 'category', 'status', 'event_date', 'location', 'description']) form.elements[field].value = ev[field] ?? '';
            form.elements.event_time.value = ev.event_time ?? '';
            form.elements.capacity.value = ev.capacity ?? '';
        }
        dialog.showModal();
        form.elements.title.focus();
    }

    async function save(event) {
        event.preventDefault();
        clearErrors();
        const values = Object.fromEntries(new FormData(form));
        const id = values.id;
        delete values.id;
        const action = id ? 'update' : 'create';
        if (id) values.id = Number(id);
        const button = document.getElementById('event-save');
        button.disabled = true;
        const { status, data } = await api(action, { method: 'POST', body: values });
        button.disabled = false;
        if (status === 422 && data.errors) {
            for (const [field, text] of Object.entries(data.errors)) {
                const target = document.getElementById('f-' + field + '-error');
                if (target) target.textContent = text;
                if (form.elements[field]) form.elements[field].setAttribute('aria-invalid', 'true');
            }
            const first = form.querySelector('[aria-invalid="true"]');
            if (first) first.focus();
            return;
        }
        if (!data.ok) {
            dialog.close();
            showMessage('error', data.error);
            return;
        }
        dialog.close();
        showMessage('success', data.message);
        load();
    }

    async function remove(ev) {
        if (!window.confirm('Delete “' + ev.title + '”? This cannot be undone.')) return;
        const { data } = await api('delete', { method: 'POST', body: { id: ev.id } });
        showMessage(data.ok ? 'success' : 'error', data.ok ? data.message : data.error);
        load();
    }

    // ------------------------------------------------------------ wiring
    filters.addEventListener('submit', (e) => { e.preventDefault(); load(); });
    filters.elements.q.addEventListener('input', () => {        // debounce: one request 300 ms after the last key press
        clearTimeout(timer);
        timer = setTimeout(load, 300);
    });
    for (const name of ['category', 'status', 'when']) filters.elements[name].addEventListener('change', load);
    if (canManage) {
        document.getElementById('new-event').addEventListener('click', () => openDialog());
        document.getElementById('event-cancel').addEventListener('click', () => dialog.close());
        form.addEventListener('submit', save);
    }
    load();
})();
