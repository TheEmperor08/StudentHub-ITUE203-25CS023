// Search, filter, sort and pagination as pure functions: they never change the original array,
// so the same records can be re-filtered every time a control changes.

const text = (value) => String(value).toLowerCase();

// Search: keep records where any of the listed fields contains the query (case-insensitive).
export const searchRecords = (records, query, keys) => {
    const q = text(query.trim());
    if (!q) return records;
    return records.filter((record) => keys.some((key) => text(record[key]).includes(q)));
};

// Filter: keep records whose field equals the chosen value ('all' keeps everything).
export const filterRecords = (records, key, value) =>
    value === 'all' ? records : records.filter((record) => String(record[key]) === value);

// Sort: numbers numerically, everything else alphabetically (ISO dates sort correctly as text).
export const sortRecords = (records, sort) => {
    if (!sort || !sort.key) return records;
    const { key, dir } = sort;
    return [...records].sort((a, b) => {
        const x = a[key];
        const y = b[key];
        const result = typeof x === 'number' && typeof y === 'number'
            ? x - y
            : String(x).localeCompare(String(y), 'en', { sensitivity: 'base' });
        return result * dir;
    });
};

// Pagination: returns the records for one page plus the numbers needed for the controls.
export const paginate = (records, page, perPage) => {
    const totalPages = Math.max(1, Math.ceil(records.length / perPage));
    const current = Math.min(Math.max(1, page), totalPages);
    const start = (current - 1) * perPage;
    return {
        items: records.slice(start, start + perPage),
        page: current,
        totalPages,
        from: records.length ? start + 1 : 0,
        to: Math.min(start + perPage, records.length),
    };
};

// Distinct values of a field, sorted, for the filter dropdown.
export const uniqueValues = (records, key) =>
    [...new Set(records.map((record) => String(record[key])))].sort((a, b) => a.localeCompare(b));
