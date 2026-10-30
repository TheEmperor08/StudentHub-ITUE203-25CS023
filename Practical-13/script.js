// StudentHub – Practical 13: asynchronous CRUD with the Fetch API. Every request goes to api.php and returns JSON;
// the page is never reloaded. Data from the server is always inserted with textContent (never innerHTML), so
// HTML or script inside an event title is displayed as plain text.
'use strict';

const API = 'api.php';
const $ = (id) => document.getElementById(id);
let currentList = null;      // AbortController of the running list request (stale searches are cancelled)
let searchTimer = null;
let events = [];

// ---------------------------------------------------------------- Fetch wrapper
// Sends a request, parses the JSON answer and throws an Error with the server's message for any non-OK response.
async function apiRequest(action, { method = 'GET', params = {}, body = null, signal } = {}) {
    const url = new URL(API, window.location.href);
    url.searchParams.set('action', action);
    Object.entries(params).forEach(([k, v]) => { if (v !== '' && v != null) url.searchParams.set(k, v); });
    const options = { method, signal, headers: { Accept: 'application/json' } };
    if (body !== null) {
        options.headers['Content-Type'] = 'application/json';
        options.headers['X-Requested-With'] = 'fetch';
        options.body = JSON.stringify(body);
    }
    let response;
    try {
        response = await fetch(url, options);
    } catch (err) {
        if (err.name === 'AbortError') throw err;
        throw new Error('The server could not be reached. Check that the PHP server is running.');
    }
    let data;
    try {
        data = await response.json();
    } catch {
        throw new Error(`The server sent an invalid response (HTTP ${response.status}).`);
    }
    if (!response.ok || !data.ok) {
        const error = new Error(data.error || `Request failed (HTTP ${response.status}).`);
        error.fields = data.errors || {};
        error.status = response.status;
        throw error;
    }
    return data;
}

// ---------------------------------------------------------------- UI helpers
function showMessage(text, type = 'success') {
    const box = $('message');
    box.textContent = text;
    box.className = `message message-${type}`;
    box.setAttribute('role', type === 'error' ? 'alert' : 'status');
    box.hidden = false;
}

function setLoading(on, text = 'Loading events…') {
    $('loading-text').textContent = text;
    $('loading').hidden = !on;
    document.body.classList.toggle('is-loading', on);
}

function formatDate(date, time) {
    const d = new Date(`${date}T${time}`);
    return d.toLocaleDateString('en-GB', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' })
        + ', ' + d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

function cell(row, text, className) {
    const td = row.insertCell();
    td.textContent = text;
    if (className) td.className = className;
    return td;
}

function renderRows(list, highlightId = null) {
    const tbody = $('event-rows');
    tbody.replaceChildren();
    if (list.length === 0) {
        const td = tbody.insertRow().insertCell();
        td.colSpan = 8;
        td.className = 'empty';
        td.textContent = 'No events match your search.';
        return;
    }
    for (const ev of list) {
        const tr = tbody.insertRow();
        tr.dataset.id = ev.event_id;
        if (ev.event_id === highlightId) tr.classList.add('highlight');
        cell(tr, ev.event_id);
        cell(tr, ev.title, 'title');
        cell(tr, ev.category).classList.add('nowrap');
        cell(tr, formatDate(ev.event_date, ev.start_time), 'nowrap');
        cell(tr, ev.venue);
        cell(tr, ev.capacity, 'num');
        const badge = document.createElement('span');
        badge.className = `badge badge-${ev.status}`;
        badge.textContent = ev.status === 'open' ? 'Open' : 'Closed';
        tr.insertCell().append(badge);
        const actions = tr.insertCell();
        actions.className = 'actions';
        for (const [label, cls, handler] of [['Edit', 'btn-secondary', () => openForm(ev)], ['Delete', 'btn-danger', () => confirmDelete(ev)]]) {
            const b = document.createElement('button');
            b.type = 'button';
            b.className = `btn btn-small ${cls}`;
            b.textContent = label;
            b.setAttribute('aria-label', `${label} ${ev.title}`);
            b.addEventListener('click', handler);
            actions.append(b);
        }
    }
}

// ---------------------------------------------------------------- READ (with search)
async function loadEvents(highlightId = null) {
    if (currentList) currentList.abort();
    currentList = new AbortController();
    const q = $('search').value.trim();
    const category = $('filter-category').value;
    setLoading(true, q ? `Searching for “${q}”…` : 'Loading events…');
    try {
        const data = await apiRequest('list', { params: { q, category }, signal: currentList.signal });
        events = data.events;
        renderRows(events, highlightId);
        $('summary').textContent = `Showing ${data.count} of ${data.total} events` + (q ? ` matching “${q}”` : '') + (category ? ` in ${category}` : '') + '.';
    } catch (err) {
        if (err.name === 'AbortError') return;     // a newer search replaced this one
        renderRows([]);
        $('summary').textContent = '';
        showMessage(err.message, 'error');
    } finally {
        setLoading(false);
    }
}

// Debounce: wait until the user stops typing for 350 ms before sending the search request
function onSearchInput() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => loadEvents(), 350);
}

// ---------------------------------------------------------------- CREATE / UPDATE
function clearFieldErrors() {
    document.querySelectorAll('[data-error-for]').forEach((p) => { p.textContent = ''; });
    document.querySelectorAll('#event-form [aria-invalid]').forEach((el) => el.removeAttribute('aria-invalid'));
}

function showFieldErrors(fields) {
    for (const [name, text] of Object.entries(fields)) {
        const p = document.querySelector(`[data-error-for="${CSS.escape(name)}"]`);
        const input = $(name);
        if (p) p.textContent = text;
        if (input) input.setAttribute('aria-invalid', 'true');
    }
}

function openForm(ev = null) {
    const form = $('event-form');
    form.reset();
    clearFieldErrors();
    $('event_id').value = ev ? ev.event_id : '';
    $('form-title').textContent = ev ? `Edit event #${ev.event_id}` : 'Add event';
    $('save-btn').textContent = ev ? 'Save changes' : 'Save event';
    if (ev) {
        for (const k of ['title', 'description', 'category', 'event_date', 'start_time', 'venue', 'capacity', 'status']) {
            $(k).value = ev[k];
        }
    }
    $('form-card').hidden = false;
    $('title').focus();
}

function closeForm() {
    $('form-card').hidden = true;
    $('event-form').reset();
    clearFieldErrors();
}

// Browser-side check before sending (the server validates again – it is the real check)
function clientErrors(data) {
    const e = {};
    if (data.title.trim().length < 3) e.title = 'Title must be at least 3 characters.';
    if (data.description.trim().length < 10) e.description = 'Description must be at least 10 characters.';
    if (!data.category) e.category = 'Category is required.';
    if (!data.event_date) e.event_date = 'Date is required.';
    if (!data.start_time) e.start_time = 'Start time is required.';
    if (data.venue.trim().length < 2) e.venue = 'Venue must be at least 2 characters.';
    if (!/^\d+$/.test(data.capacity) || +data.capacity < 1 || +data.capacity > 5000) e.capacity = 'Capacity must be 1–5000.';
    return e;
}

async function saveEvent(event) {
    event.preventDefault();
    clearFieldErrors();
    const data = Object.fromEntries(new FormData($('event-form')).entries());
    const isEdit = data.event_id !== '';
    const errors = clientErrors(data);
    if (Object.keys(errors).length) {
        showFieldErrors(errors);
        showMessage('Please correct the highlighted fields.', 'error');
        return;
    }
    if (!isEdit) delete data.event_id;
    const button = $('save-btn');
    button.disabled = true;
    setLoading(true, isEdit ? 'Saving changes…' : 'Adding event…');
    try {
        const result = await apiRequest(isEdit ? 'update' : 'create', { method: 'POST', body: data });
        closeForm();
        showMessage(result.message, 'success');
        await loadEvents(result.event.event_id);
    } catch (err) {
        showFieldErrors(err.fields || {});
        showMessage(err.message, 'error');
    } finally {
        button.disabled = false;
        setLoading(false);
    }
}

// ---------------------------------------------------------------- DELETE
let pendingDelete = null;

function confirmDelete(ev) {
    pendingDelete = ev;
    $('confirm-name').textContent = `“${ev.title}”`;
    $('confirm-dialog').showModal();
}

async function deleteConfirmed() {
    const ev = pendingDelete;
    $('confirm-dialog').close();
    if (!ev) return;
    setLoading(true, 'Deleting event…');
    try {
        const result = await apiRequest('delete', { method: 'POST', body: { event_id: ev.event_id } });
        const row = document.querySelector(`tr[data-id="${ev.event_id}"]`);
        if (row) row.remove();
        events = events.filter((e) => e.event_id !== ev.event_id);
        showMessage(result.message, 'success');
        await loadEvents();
    } catch (err) {
        showMessage(err.message, 'error');
    } finally {
        pendingDelete = null;
        setLoading(false);
    }
}

// ---------------------------------------------------------------- start
document.addEventListener('DOMContentLoaded', () => {
    $('new-event-btn').addEventListener('click', () => openForm());
    $('cancel-btn').addEventListener('click', closeForm);
    $('event-form').addEventListener('submit', saveEvent);
    $('search').addEventListener('input', onSearchInput);
    $('filter-category').addEventListener('change', () => loadEvents());
    $('confirm-yes').addEventListener('click', deleteConfirmed);
    $('confirm-no').addEventListener('click', () => { pendingDelete = null; $('confirm-dialog').close(); });
    loadEvents();
});
