// Loading JSON with the Fetch API, plus a localStorage cache of the last successful response.

const CACHE_PREFIX = 'studenthub-p6-cache:';
const TIMEOUT_MS = 8000;

// Resolves after ms milliseconds, or rejects straight away if the request is cancelled.
const wait = (ms, signal) => new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener('abort', () => {
        clearTimeout(timer);
        reject(new DOMException('Request cancelled', 'AbortError'));
    }, { once: true });
});

// Fetches one dataset and checks the response. Throws an Error with a readable message on failure.
// options.simulateError requests a file that does not exist, so the real error path can be demonstrated.
export const fetchDataset = async (url, { signal, simulateError = false, delayMs = 0 } = {}) => {
    if (delayMs > 0) await wait(delayMs, signal);
    const target = simulateError ? url.replace(/\.json$/, '-missing.json') : url;
    const timeout = AbortSignal.timeout(TIMEOUT_MS);
    const combined = signal && AbortSignal.any ? AbortSignal.any([signal, timeout]) : (signal || timeout);

    let response;
    try {
        response = await fetch(target, { signal: combined, cache: 'no-store' });
    } catch (error) {
        if (error.name === 'AbortError' && signal?.aborted) throw error;          // cancelled by a newer request
        if (error.name === 'TimeoutError') throw new Error(`${target} took longer than ${TIMEOUT_MS / 1000} seconds`);
        throw new Error(`the network request for ${target} failed`);
    }
    if (!response.ok) throw new Error(`the server answered ${response.status} ${response.statusText} for ${target}`);

    let body;
    try {
        body = await response.json();
    } catch {
        throw new Error(`${target} is not valid JSON`);
    }
    if (!body || !Array.isArray(body.records)) throw new Error(`${target} has no "records" list`);
    return body;
};

// Cache helpers: localStorage can be full or blocked, so every call is wrapped in try/catch.
export const saveToCache = (name, body) => {
    try {
        localStorage.setItem(CACHE_PREFIX + name, JSON.stringify({ savedAt: new Date().toISOString(), body }));
        return true;
    } catch {
        return false;
    }
};

export const readFromCache = (name) => {
    try {
        const cached = JSON.parse(localStorage.getItem(CACHE_PREFIX + name));
        return cached && Array.isArray(cached.body?.records) ? cached : null;
    } catch {
        return null;
    }
};

export const clearCache = (names) => {
    try {
        names.forEach((name) => localStorage.removeItem(CACHE_PREFIX + name));
    } catch {
        /* storage blocked: nothing to clear */
    }
};
