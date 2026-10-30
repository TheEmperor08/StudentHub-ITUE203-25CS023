// Building the table, pagination and status messages with DOM methods (textContent, never innerHTML with data).

const el = (tag, props = {}, children = []) => {
    const node = document.createElement(tag);
    Object.entries(props).forEach(([key, value]) => {
        if (key === 'text') node.textContent = value;
        else if (key === 'className') node.className = value;
        else node.setAttribute(key, value);
    });
    children.forEach((child) => node.append(child));
    return node;
};

// Wraps every match of the search query in <mark>, so search results are easy to see.
const highlight = (value, query) => {
    const q = query.trim().toLowerCase();
    if (!q) return [value];
    const parts = [];
    let rest = value;
    let index = rest.toLowerCase().indexOf(q);
    while (index !== -1) {
        parts.push(rest.slice(0, index), el('mark', { text: rest.slice(index, index + q.length) }));
        rest = rest.slice(index + q.length);
        index = rest.toLowerCase().indexOf(q);
    }
    parts.push(rest);
    return parts;
};

export const renderTable = (container, config, items, { query, sort, pageInfo }) => {
    const caption = el('caption', {
        text: `${config.label} – sample data (page ${pageInfo.page} of ${pageInfo.totalPages})`,
    });
    const headRow = el('tr', {}, config.columns.map((column) => {
        const th = el('th', { scope: 'col', text: column.label });
        if (column.numeric) th.className = 'num';
        if (sort?.key === column.key) th.setAttribute('aria-sort', sort.dir === 1 ? 'ascending' : 'descending');
        return th;
    }));
    const rows = items.map((record) => el('tr', {}, config.columns.map((column) => {
        const raw = record[column.key];
        const shown = column.format ? column.format(raw) : String(raw);
        const searchable = config.searchKeys.includes(column.key);
        return el('td', { 'data-label': column.label, className: column.numeric ? 'num' : '' },
            searchable ? highlight(shown, query) : [shown]);
    })));
    container.replaceChildren(el('table', { className: 'data-table' }, [caption, el('thead', {}, [headRow]), el('tbody', {}, rows)]));
};

export const renderEmpty = (container, config, onClear) => {
    const button = el('button', { type: 'button', className: 'btn btn-secondary', text: 'Clear search and filter' });
    button.addEventListener('click', onClear);
    container.replaceChildren(el('div', { className: 'empty-state' }, [
        el('p', { text: `No ${config.plural} match your search and filter.` }), button,
    ]));
};

// Pagination: Previous, numbered pages and Next. onPage(page, action) is called with the new page number.
export const renderPagination = (nav, { page, totalPages }, onPage) => {
    if (totalPages <= 1) {
        nav.replaceChildren();
        return;
    }
    const button = (label, target, action, extra = {}) => {
        const b = el('button', { type: 'button', className: 'page-btn', text: label, 'data-action': action, ...extra });
        b.addEventListener('click', () => onPage(target, action));
        return b;
    };
    const prev = button('‹ Previous', page - 1, 'prev', { 'aria-label': 'Previous page' });
    prev.disabled = page === 1;
    const numbers = Array.from({ length: totalPages }, (_, i) => {
        const n = i + 1;
        return button(String(n), n, `page-${n}`, { 'aria-label': `Page ${n}`, ...(n === page ? { 'aria-current': 'page' } : {}) });
    });
    const next = button('Next ›', page + 1, 'next', { 'aria-label': 'Next page' });
    next.disabled = page === totalPages;
    nav.replaceChildren(prev, ...numbers, next);
};

// Status area: loading, error (with Retry) and cached-copy notices. type '' clears it.
export const renderStatus = (status, { type = '', title = '', message = '', onRetry = null } = {}) => {
    if (!type) {
        status.replaceChildren();
        status.className = 'status';
        return;
    }
    status.className = `status status-${type}`;
    status.setAttribute('role', type === 'error' ? 'alert' : 'status');           // errors are announced at once
    const children = [];
    if (type === 'loading') children.push(el('span', { className: 'spinner', 'aria-hidden': 'true' }));
    const textBox = el('div', { className: 'status-text' }, [el('strong', { text: title })]);
    if (message) textBox.append(el('p', { text: message }));
    children.push(textBox);
    if (onRetry) {
        const retry = el('button', { type: 'button', className: 'btn btn-primary', id: 'retry-btn', text: 'Retry' });
        retry.addEventListener('click', onRetry);
        children.push(retry);
    }
    status.replaceChildren(...children);
};

export const fillSelect = (select, options) => {
    select.replaceChildren(...options.map(({ value, label }) => el('option', { value, text: label })));
};
