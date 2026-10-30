<?php
// StudentHub – Practical 7: JSON file storage with file locking.
declare(strict_types=1);

// The file lives in private/, which the web server does not serve (private/.htaccess for Apache,
// router.php for PHP's built-in server). P7_STORAGE_FILE lets the automated tests use a separate file.
function storage_file(): string
{
    $custom = getenv('P7_STORAGE_FILE');
    return is_string($custom) && $custom !== '' ? $custom : __DIR__ . '/../private/submissions.json';
}

const JSON_OPTIONS = JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_HEX_TAG | JSON_THROW_ON_ERROR;

// Turns the file contents into a list of records. Empty file -> []; damaged file -> null.
function decode_records(string $raw): ?array
{
    if (trim($raw) === '') {
        return [];
    }
    try {
        $data = json_decode($raw, true, 512, JSON_THROW_ON_ERROR);
    } catch (JsonException) {
        return null;
    }
    return is_array($data) && array_is_list($data) ? $data : null;
}

function next_id(array $records): string
{
    $max = 0;
    foreach ($records as $record) {
        if (is_array($record) && preg_match('/^SUB-(\d+)$/', (string) ($record['id'] ?? ''), $m)) {
            $max = max($max, (int) $m[1]);
        }
    }
    return sprintf('SUB-%04d', $max + 1);
}

// Adds one record. The whole read–modify–write happens under an exclusive lock (flock LOCK_EX),
// so two submissions at the same time cannot overwrite each other.
// A missing file or folder is created; a damaged file is kept as a .corrupt copy and a new list is started.
function append_submission(array $record, ?string $file = null): array
{
    $file ??= storage_file();
    $dir = dirname($file);
    if (!is_dir($dir) && !mkdir($dir, 0775, true) && !is_dir($dir)) {
        throw new RuntimeException('The storage folder could not be created.');
    }
    $handle = @fopen($file, 'c+');
    if ($handle === false) {
        throw new RuntimeException('The storage file could not be opened.');
    }
    try {
        if (!flock($handle, LOCK_EX)) {
            throw new RuntimeException('The storage file could not be locked.');
        }
        $raw = (string) stream_get_contents($handle);
        $records = decode_records($raw);
        if ($records === null) {
            $copy = $dir . '/submissions.corrupt-' . date('Ymd-His') . '.json';
            if (file_put_contents($copy, $raw) === false) {
                throw new RuntimeException('The storage file is damaged and could not be backed up.');
            }
            $records = [];
        }
        $record = ['id' => next_id($records)] + $record;
        $records[] = $record;
        $json = json_encode($records, JSON_OPTIONS) . "\n";
        if (!ftruncate($handle, 0) || !rewind($handle) || fwrite($handle, $json) !== strlen($json)) {
            throw new RuntimeException('The storage file could not be written.');
        }
        fflush($handle);
        return $record;
    } finally {
        flock($handle, LOCK_UN);
        fclose($handle);
    }
}

// Reads all records with a shared lock. Returns ['records' => [...], 'error' => message or null].
function read_submissions(?string $file = null): array
{
    $file ??= storage_file();
    if (!is_file($file)) {
        return ['records' => [], 'error' => null];
    }
    $handle = @fopen($file, 'r');
    if ($handle === false) {
        return ['records' => [], 'error' => 'The stored submissions could not be opened.'];
    }
    flock($handle, LOCK_SH);
    $raw = (string) stream_get_contents($handle);
    flock($handle, LOCK_UN);
    fclose($handle);
    $records = decode_records($raw);
    if ($records === null) {
        return ['records' => [], 'error' => 'The stored data file is damaged and cannot be read. It will be backed up and replaced on the next successful submission.'];
    }
    return ['records' => array_values(array_filter($records, 'is_array')), 'error' => null];
}

// Pretty JSON for the "stored data" view (escaped again by e() when it is printed).
function records_as_json(array $records): string
{
    return json_encode($records, JSON_OPTIONS);
}
