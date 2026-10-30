// Dataset definitions: where each JSON file is, and how its records are shown, searched, filtered and sorted.
// Adding a new dataset only needs a new entry here (and a JSON file with a "records" array).

const formatDate = (iso) =>
    new Date(`${iso}T00:00:00`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });

export const DATASETS = {
    students: {
        label: 'Students',
        plural: 'students',
        url: 'data/students.json',
        columns: [
            { key: 'id', label: 'Student ID' },
            { key: 'name', label: 'Name' },
            { key: 'branch', label: 'Branch' },
            { key: 'semester', label: 'Semester', numeric: true },
            { key: 'cpi', label: 'CPI', numeric: true, format: (v) => v.toFixed(2) },
        ],
        searchKeys: ['id', 'name', 'branch'],
        filter: { key: 'branch', label: 'Branch', all: 'All branches' },
        sorts: [
            { value: 'default', label: 'Student ID (default)' },
            { value: 'name-asc', label: 'Name (A–Z)', key: 'name', dir: 1 },
            { value: 'name-desc', label: 'Name (Z–A)', key: 'name', dir: -1 },
            { value: 'cpi-desc', label: 'CPI (high to low)', key: 'cpi', dir: -1 },
            { value: 'cpi-asc', label: 'CPI (low to high)', key: 'cpi', dir: 1 },
            { value: 'semester-asc', label: 'Semester (1 to 7)', key: 'semester', dir: 1 },
        ],
    },
    events: {
        label: 'Events',
        plural: 'events',
        url: 'data/events.json',
        columns: [
            { key: 'title', label: 'Event' },
            { key: 'date', label: 'Date', format: formatDate },
            { key: 'venue', label: 'Venue' },
            { key: 'category', label: 'Category' },
        ],
        searchKeys: ['title', 'venue', 'category'],
        filter: { key: 'category', label: 'Category', all: 'All categories' },
        sorts: [
            { value: 'default', label: 'Default order' },
            { value: 'date-asc', label: 'Date (soonest first)', key: 'date', dir: 1 },
            { value: 'date-desc', label: 'Date (latest first)', key: 'date', dir: -1 },
            { value: 'title-asc', label: 'Event (A–Z)', key: 'title', dir: 1 },
            { value: 'title-desc', label: 'Event (Z–A)', key: 'title', dir: -1 },
        ],
    },
    faqs: {
        label: 'FAQs',
        plural: 'FAQs',
        url: 'data/faqs.json',
        columns: [
            { key: 'question', label: 'Question' },
            { key: 'answer', label: 'Answer' },
            { key: 'category', label: 'Category' },
        ],
        searchKeys: ['question', 'answer', 'category'],
        filter: { key: 'category', label: 'Category', all: 'All categories' },
        sorts: [
            { value: 'default', label: 'Default order' },
            { value: 'question-asc', label: 'Question (A–Z)', key: 'question', dir: 1 },
            { value: 'question-desc', label: 'Question (Z–A)', key: 'question', dir: -1 },
            { value: 'category-asc', label: 'Category (A–Z)', key: 'category', dir: 1 },
        ],
    },
};

export const PAGE_SIZES = [5, 10, 15];
export const SLOW_NETWORK_MS = 3000;          // "Simulate a slow network" testing option
