// StudentHub – Practical 6: entry module. Connects the tabs and controls to the data, filter and render modules.
import { DATASETS, PAGE_SIZES, SLOW_NETWORK_MS } from './config.js';
import { fetchDataset, saveToCache, readFromCache, clearCache } from './api.js';
import { searchRecords, filterRecords, sortRecords, paginate, uniqueValues } from './filters.js';
import { renderTable, renderEmpty, renderPagination, renderStatus, fillSelect } from './render.js';

const $ = (id) => document.getElementById(id);
const tabs = [...document.querySelectorAll('[role="tab"]')];
const panel = $('data-panel');
const searchInput = $('search-input');
const filterSelect = $('filter-select');
const filterLabel = $('filter-label');
const sortSelect = $('sort-select');
const pageSizeSelect = $('page-size-select');
const controls = [searchInput, filterSelect, sortSelect, pageSizeSelect];
const status = $('status');
const summary = $('results-summary');
const tableArea = $('table-area');
const pagination = $('pagination');
const errorToggle = $('simulate-error');
const slowToggle = $('simulate-slow');
const announcer = $('announcer');

const params = new URLSearchParams(window.location.search);
if (params.get('fail') === '1') errorToggle.checked = true;                       // e.g. directory.html?fail=1

const state = { name: 'students', records: [], source: 'live', page: 1 };
let latestRequest = 0;
let controller = null;

const formatTime = (iso) => new Date(iso).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' });

// Applies search, filter, sort and pagination to the loaded records and redraws the view.
const update = (focusAction = null) => {
    const config = DATASETS[state.name];
    const sort = config.sorts.find((s) => s.value === sortSelect.value);
    const matches = sortRecords(
        filterRecords(searchRecords(state.records, searchInput.value, config.searchKeys), config.filter.key, filterSelect.value),
        sort,
    );
    const pageInfo = paginate(matches, state.page, Number(pageSizeSelect.value));
    state.page = pageInfo.page;

    if (!matches.length) {
        renderEmpty(tableArea, config, () => {
            searchInput.value = '';
            filterSelect.value = 'all';
            state.page = 1;
            update();
            searchInput.focus();
        });
        summary.textContent = `No ${config.plural} found (0 of ${state.records.length}).`;
    } else {
        renderTable(tableArea, config, pageInfo.items, { query: searchInput.value, sort, pageInfo });
        const source = state.source === 'live' ? `live data from ${config.url}` : 'saved copy (localStorage)';
        summary.textContent = `Showing ${pageInfo.from}–${pageInfo.to} of ${matches.length} ${config.plural}`
            + `${matches.length < state.records.length ? ` (filtered from ${state.records.length})` : ''} · ${source}`;
    }
    renderPagination(pagination, pageInfo, (page, action) => {
        state.page = page;
        update(action);
    });
    if (focusAction) {                                                             // keep keyboard focus in the pagination
        const target = pagination.querySelector(`[data-action="${focusAction}"]:not(:disabled)`)
            || pagination.querySelector('[aria-current="page"]');
        target?.focus();
    }
};

// Resets the controls for the selected dataset (filter options and sort options come from config.js).
const setUpControls = () => {
    const config = DATASETS[state.name];
    searchInput.value = '';
    const searchable = config.searchKeys.map((key) => config.columns.find((c) => c.key === key).label.toLowerCase());
    searchInput.placeholder = `Search by ${searchable.join(', ')}`;
    filterLabel.textContent = config.filter.label;
    fillSelect(filterSelect, [{ value: 'all', label: config.filter.all },
        ...uniqueValues(state.records, config.filter.key).map((v) => ({ value: v, label: v }))]);
    fillSelect(sortSelect, config.sorts);
    state.page = 1;
};

const setBusy = (busy) => {
    panel.setAttribute('aria-busy', String(busy));
    controls.forEach((control) => { control.disabled = busy; });
};

const showRecords = (records, source) => {
    state.records = records;
    state.source = source;
    setUpControls();
    update();
};

// Loads a dataset. Each call gets a number; a response is used only if no newer request has started,
// and the previous request is cancelled, so quickly switching tabs can never show the wrong data.
const load = async (name) => {
    const requestId = ++latestRequest;
    controller?.abort();
    controller = new AbortController();
    const config = DATASETS[name];
    state.name = name;
    state.records = [];
    filterLabel.textContent = config.filter.label;                                 // correct label while loading

    setBusy(true);
    tableArea.replaceChildren();
    pagination.replaceChildren();
    summary.textContent = '';
    renderStatus(status, { type: 'loading', title: `Loading ${config.plural}…`, message: `Fetching ${config.url}` });

    try {
        const delayMs = slowToggle.checked ? SLOW_NETWORK_MS : Number(params.get('delay')) || 0;
        const body = await fetchDataset(config.url, { signal: controller.signal, simulateError: errorToggle.checked, delayMs });
        if (requestId !== latestRequest) return;
        saveToCache(name, body);
        renderStatus(status);
        showRecords(body.records, 'live');
    } catch (error) {
        if (requestId !== latestRequest || error.name === 'AbortError') return;
        const cached = readFromCache(name);
        if (cached) {
            renderStatus(status, {
                type: 'cached',
                title: `Showing a saved copy from ${formatTime(cached.savedAt)}`,
                message: `The latest ${config.plural} could not be loaded: ${error.message}.`,
                onRetry: () => load(name),
            });
            showRecords(cached.body.records, 'cache');
        } else {
            const hint = window.location.protocol === 'file:' ? ' Open the page through the local server (see README.md).' : '';
            renderStatus(status, {
                type: 'error',
                title: `Could not load the ${config.plural}`,
                message: `Reason: ${error.message}.${hint}`,
                onRetry: () => load(name),
            });
            summary.textContent = `No ${config.plural} to show.`;
        }
    } finally {
        if (requestId === latestRequest) setBusy(false);
    }
};

// Tabs: click, or Left/Right/Home/End keys (WAI-ARIA tabs pattern with automatic activation)
const selectTab = (tab, moveFocus = false) => {
    tabs.forEach((t) => {
        const selected = t === tab;
        t.setAttribute('aria-selected', String(selected));
        t.tabIndex = selected ? 0 : -1;
    });
    panel.setAttribute('aria-labelledby', tab.id);
    if (moveFocus) tab.focus();
    load(tab.dataset.dataset);
};

tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => selectTab(tab));
    tab.addEventListener('keydown', (e) => {
        const moves = { ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: tabs.length - 1 };
        if (!(e.key in moves)) return;
        e.preventDefault();
        selectTab(tabs[(moves[e.key] + tabs.length) % tabs.length], true);
    });
});

searchInput.addEventListener('input', () => { state.page = 1; update(); });
[filterSelect, sortSelect, pageSizeSelect].forEach((select) => {
    select.addEventListener('change', () => { state.page = 1; update(); });
});

// Testing tools: changing an option reloads the current dataset straight away
[errorToggle, slowToggle].forEach((toggle) => toggle.addEventListener('change', () => load(state.name)));

$('clear-cache').addEventListener('click', () => {
    clearCache(Object.keys(DATASETS));
    announcer.textContent = 'Saved copies cleared from localStorage.';
});

fillSelect(pageSizeSelect, PAGE_SIZES.map((n) => ({ value: String(n), label: `${n} per page` })));
selectTab(tabs[0]);
