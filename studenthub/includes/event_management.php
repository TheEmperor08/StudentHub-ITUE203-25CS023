<?php
// StudentHub – event management (Practical 12 integrated into the portal; also used by the Practical 13 JSON API).
//
// The events are the portal's own studenthub_db.events rows (categories in event_categories, registrations in
// registrations – migrations 001 and 003):
//   list / filter       event_filters() + event_filter_sql(): one parameterised WHERE clause for the console and the API
//   add / edit          validate_event() + save_event(): server-side validation; the capacity can never drop below the
//                       seats already taken (checked while the event row is locked)
//   delete              delete_event(): only events without registrations (history is kept – close the event instead)
//   posters             validate_poster() / store_poster(): JPEG, PNG or WebP only, at most 2 MB, MIME type of the content,
//                       real image structure, no embedded PHP; stored under a random name in the upload folder, which is
//                       not reachable over HTTP; delivered only by poster.php
// Event registrations themselves are handled by includes/event_registration.php (transaction, capacity, duplicates).
// Requires mysqli in exception mode (the PHP 8.1+ default).

const EVENT_STATUSES       = ['open' => 'Open', 'closed' => 'Closed'];
const EVENTS_PER_PAGE      = 10;
const EVENT_FIELDS         = ['title', 'category', 'event_date', 'event_time', 'location', 'capacity', 'status', 'description'];
const POSTER_MAX_BYTES     = 2 * 1024 * 1024;
const POSTER_MAX_PIXELS    = 6000;
const POSTER_EXTENSIONS    = ['jpg' => 'image/jpeg', 'jpeg' => 'image/jpeg', 'png' => 'image/png', 'webp' => 'image/webp'];
const POSTER_IMAGE_TYPES   = [IMAGETYPE_JPEG => 'jpg', IMAGETYPE_PNG => 'png', IMAGETYPE_WEBP => 'webp'];
const POSTER_NAME_PATTERN  = '/^[a-f0-9]{32}\.(jpg|png|webp)$/';

// ---------------------------------------------------------------- categories, filters and lists
function event_categories(mysqli $db): array
{
    return array_column($db->query('SELECT name FROM event_categories ORDER BY name')->fetch_all(MYSQLI_NUM), 0);
}

function event_id_from($value): int
{
    return is_string($value) && preg_match('/^[1-9][0-9]{0,9}$/', $value) && (int) $value <= 2147483647 ? (int) $value : 0;
}

// List options from the query string; unknown values are ignored (never used in SQL)
function event_filters(array $query, array $categories): array
{
    $text = fn (string $key): string => is_string($query[$key] ?? null) && mb_check_encoding($query[$key], 'UTF-8') ? trim($query[$key]) : '';
    $category = $text('category');
    $status = $text('status');
    $when = $text('when');
    $page = $text('page');
    return [
        'q'        => mb_substr($text('q'), 0, 100),
        'category' => in_array($category, $categories, true) ? $category : '',
        'status'   => isset(EVENT_STATUSES[$status]) ? $status : '',
        'when'     => in_array($when, ['upcoming', 'past'], true) ? $when : '',
        'page'     => preg_match('/^[1-9][0-9]{0,5}$/', $page) ? (int) $page : 1,
    ];
}

// WHERE clause with ? placeholders; the search text matches title, location and description (% and _ literally)
function event_filter_sql(array $filters): array
{
    $where = [];
    $types = '';
    $params = [];
    if ($filters['q'] !== '') {
        $like = '%' . addcslashes($filters['q'], '\\%_') . '%';
        $where[] = '(e.title LIKE ? OR e.location LIKE ? OR e.description LIKE ?)';
        $types .= 'sss';
        array_push($params, $like, $like, $like);
    }
    if ($filters['category'] !== '') {
        $where[] = 'e.category = ?';
        $types .= 's';
        $params[] = $filters['category'];
    }
    if ($filters['status'] !== '') {
        $where[] = 'e.status = ?';
        $types .= 's';
        $params[] = $filters['status'];
    }
    if ($filters['when'] === 'upcoming') {
        $where[] = 'e.event_date >= CURDATE()';
    } elseif ($filters['when'] === 'past') {
        $where[] = 'e.event_date < CURDATE()';
    }
    return [$where ? ' WHERE ' . implode(' AND ', $where) : '', $types, $params];
}

const EVENT_COLUMNS = "e.id, e.title, e.category, e.event_date, e.event_time, e.location, e.capacity, e.status, e.description, e.poster,
        e.created_at, e.updated_at,
        (SELECT COUNT(*) FROM registrations r WHERE r.event_id = e.id AND r.status <> 'cancelled') AS seats_taken,
        (SELECT COUNT(*) FROM registrations r WHERE r.event_id = e.id) AS registrations_total";

function event_count(mysqli $db, array $filters): int
{
    [$where, $types, $params] = event_filter_sql($filters);
    $stmt = $db->prepare('SELECT COUNT(*) FROM events e' . $where);
    if ($types !== '') {
        $stmt->bind_param($types, ...$params);
    }
    $stmt->execute();
    return (int) $stmt->get_result()->fetch_row()[0];
}

// Matching events by date (upcoming first when filtered, otherwise newest date first). $limit = null returns all.
function event_list(mysqli $db, array $filters, ?int $limit = null, int $offset = 0): array
{
    [$where, $types, $params] = event_filter_sql($filters);
    $order = $filters['when'] === 'upcoming' ? 'e.event_date ASC, e.event_time ASC, e.id ASC' : 'e.event_date DESC, e.event_time DESC, e.id DESC';
    $sql = 'SELECT ' . EVENT_COLUMNS . ' FROM events e' . $where . ' ORDER BY ' . $order;
    if ($limit !== null) {
        $sql .= ' LIMIT ? OFFSET ?';
        $types .= 'ii';
        array_push($params, $limit, $offset);
    }
    $stmt = $db->prepare($sql);
    if ($types !== '') {
        $stmt->bind_param($types, ...$params);
    }
    $stmt->execute();
    return $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
}

function find_event(mysqli $db, int $id): ?array
{
    $stmt = $db->prepare('SELECT ' . EVENT_COLUMNS . ' FROM events e WHERE e.id = ?');
    $stmt->bind_param('i', $id);
    $stmt->execute();
    return $stmt->get_result()->fetch_assoc() ?: null;
}

function event_list_url(array $filters, array $extra = []): string
{
    $params = ['tab' => 'events'];
    foreach (['q', 'category', 'status', 'when'] as $key) {
        if ($filters[$key] !== '') {
            $params[$key] = $filters[$key];
        }
    }
    return 'admin_dashboard.php?' . http_build_query(array_merge($params, $extra));
}

// Registrations of one event with the student record (newest first)
function event_registrations(mysqli $db, int $event_id): array
{
    $stmt = $db->prepare('SELECT r.registration_id, r.status, r.registered_at, s.id AS student_id, s.enrollment_no, s.name, s.course, s.status AS student_status
                          FROM registrations r JOIN students s ON s.id = r.student_id WHERE r.event_id = ? ORDER BY r.registered_at DESC, r.registration_id DESC');
    $stmt->bind_param('i', $event_id);
    $stmt->execute();
    return $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
}

// "12 / 40" or "12 / no limit"
function event_seats_label(array $event): string
{
    return (int) $event['seats_taken'] . ' / ' . ($event['capacity'] !== null ? (int) $event['capacity'] : 'no limit');
}

function event_when_label(array $event): string
{
    $date = date('d M Y', strtotime((string) $event['event_date']));
    return $event['event_time'] !== null ? $date . ', ' . substr((string) $event['event_time'], 0, 5) : $date;
}

// ---------------------------------------------------------------- add and edit
// Returns [clean values, errors by field]. $existing is the stored event when editing (null when adding).
function validate_event(array $input, array $categories, ?array $existing = null): array
{
    $errors = [];
    $raw = [];
    foreach (EVENT_FIELDS as $field) {
        $value = $input[$field] ?? '';
        if (!is_string($value) || !mb_check_encoding($value, 'UTF-8')) {
            $errors[$field] = 'This field contains characters that are not allowed.';
            $value = '';
        }
        $raw[$field] = trim($value);
    }
    $clean = [
        'title'       => (string) preg_replace('/\s+/u', ' ', $raw['title']),
        'category'    => $raw['category'],
        'event_date'  => $raw['event_date'],
        'event_time'  => $raw['event_time'] === '' ? null : $raw['event_time'],
        'location'    => (string) preg_replace('/\s+/u', ' ', $raw['location']),
        'capacity'    => $raw['capacity'] === '' ? null : $raw['capacity'],
        'status'      => $raw['status'] === '' ? 'open' : $raw['status'],
        'description' => str_replace("\r\n", "\n", $raw['description']),
    ];
    if (!isset($errors['title'])) {
        $length = mb_strlen($clean['title'], 'UTF-8');
        if ($length === 0) {
            $errors['title'] = 'Please enter the event title.';
        } elseif ($length < 3 || $length > 150) {
            $errors['title'] = 'The title must be 3–150 characters long.';
        }
    }
    if (!isset($errors['category']) && !in_array($clean['category'], $categories, true)) {
        $errors['category'] = 'Please select a category from the list.';
    }
    if (!isset($errors['event_date'])) {
        $d = DateTime::createFromFormat('!Y-m-d', $clean['event_date']);
        if ($clean['event_date'] === '') {
            $errors['event_date'] = 'Please choose the event date.';
        } elseif ($d === false || $d->format('Y-m-d') !== $clean['event_date'] || (int) $d->format('Y') < 2000 || (int) $d->format('Y') > 2100) {
            $errors['event_date'] = 'Please enter a valid date (YYYY-MM-DD).';
        }
    }
    if (!isset($errors['event_time']) && $clean['event_time'] !== null) {
        if (preg_match('/^([01][0-9]|2[0-3]):[0-5][0-9](:[0-5][0-9])?$/', $clean['event_time'])) {
            $clean['event_time'] = substr($clean['event_time'], 0, 5) . ':00';
        } else {
            $errors['event_time'] = 'Please enter a valid time (HH:MM) or leave it empty.';
        }
    }
    if (!isset($errors['location'])) {
        $length = mb_strlen($clean['location'], 'UTF-8');
        if ($length === 0) {
            $errors['location'] = 'Please enter the location.';
        } elseif ($length < 2 || $length > 150) {
            $errors['location'] = 'The location must be 2–150 characters long.';
        }
    }
    if (!isset($errors['capacity']) && $clean['capacity'] !== null) {
        if (!preg_match('/^[1-9][0-9]{0,4}$/', $clean['capacity']) || (int) $clean['capacity'] > 65535) {
            $errors['capacity'] = 'The capacity must be a whole number from 1 to 65535, or empty for no limit.';
        } else {
            $clean['capacity'] = (int) $clean['capacity'];
            if ($existing !== null && $clean['capacity'] < (int) $existing['seats_taken']) {
                $errors['capacity'] = 'The capacity cannot be lower than the ' . (int) $existing['seats_taken'] . ' seats already taken.';
            }
        }
    }
    if (!isset($errors['status']) && !isset(EVENT_STATUSES[$clean['status']])) {
        $errors['status'] = 'Please choose Open or Closed.';
    }
    if (!isset($errors['description']) && mb_strlen($clean['description'], 'UTF-8') > 2000) {
        $errors['description'] = 'The description can have at most 2000 characters.';
    }
    return [$clean, $errors];
}

// Adds ($id = null) or updates an event. $poster is a freshly stored poster name or null (= keep the current poster).
// Returns ['id', 'old_poster'] or ['errors' => [...]]. The caller deletes old_poster after success.
function save_event(mysqli $db, array $clean, ?int $id = null, ?string $poster = null): array
{
    $db->begin_transaction();
    try {
        $old_poster = null;
        if ($id === null) {
            $stmt = $db->prepare('INSERT INTO events (title, category, event_date, event_time, location, capacity, status, description, poster)
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)');
            $stmt->bind_param('sssssisss', $clean['title'], $clean['category'], $clean['event_date'], $clean['event_time'], $clean['location'],
                              $clean['capacity'], $clean['status'], $clean['description'], $poster);
            $stmt->execute();
            $id = (int) $stmt->insert_id;
        } else {
            // lock the event, then re-check the capacity against the seats taken at this moment
            $stmt = $db->prepare('SELECT poster FROM events WHERE id = ? FOR UPDATE');
            $stmt->bind_param('i', $id);
            $stmt->execute();
            $row = $stmt->get_result()->fetch_assoc();
            if ($row === null) {
                $db->rollback();
                return ['errors' => ['title' => 'This event no longer exists.']];
            }
            if ($clean['capacity'] !== null) {
                $stmt = $db->prepare("SELECT COUNT(*) FROM registrations WHERE event_id = ? AND status <> 'cancelled' LOCK IN SHARE MODE");
                $stmt->bind_param('i', $id);
                $stmt->execute();
                $taken = (int) $stmt->get_result()->fetch_row()[0];
                if ($clean['capacity'] < $taken) {
                    $db->rollback();
                    return ['errors' => ['capacity' => "The capacity cannot be lower than the $taken seats already taken."]];
                }
            }
            $new_poster = $poster ?? $row['poster'];
            $stmt = $db->prepare('UPDATE events SET title = ?, category = ?, event_date = ?, event_time = ?, location = ?, capacity = ?,
                                  status = ?, description = ?, poster = ? WHERE id = ?');
            $stmt->bind_param('sssssisssi', $clean['title'], $clean['category'], $clean['event_date'], $clean['event_time'], $clean['location'],
                              $clean['capacity'], $clean['status'], $clean['description'], $new_poster, $id);
            $stmt->execute();
            $old_poster = $poster !== null ? $row['poster'] : null;
        }
        $db->commit();
        return ['id' => $id, 'old_poster' => $old_poster];
    } catch (mysqli_sql_exception $e) {
        $db->rollback();
        if ($e->getCode() === 1452) {                                   // the category was removed meanwhile
            return ['errors' => ['category' => 'Please select a category from the list.']];
        }
        throw $e;
    }
}

// Deletes an event that has no registrations at all (registration history is never destroyed).
// Returns ['ok' => true, 'poster' => name|null] or ['ok' => false, 'error' => message].
function delete_event(mysqli $db, int $id): array
{
    $db->begin_transaction();
    try {
        $stmt = $db->prepare('SELECT poster FROM events WHERE id = ? FOR UPDATE');
        $stmt->bind_param('i', $id);
        $stmt->execute();
        $row = $stmt->get_result()->fetch_assoc();
        if ($row === null) {
            $db->rollback();
            return ['ok' => false, 'error' => 'That event was not found.'];
        }
        $stmt = $db->prepare('SELECT COUNT(*) FROM registrations WHERE event_id = ? LOCK IN SHARE MODE');
        $stmt->bind_param('i', $id);
        $stmt->execute();
        $registrations = (int) $stmt->get_result()->fetch_row()[0];
        if ($registrations > 0) {
            $db->rollback();
            return ['ok' => false, 'error' => "This event has $registrations registration(s) and cannot be deleted, so that the registration history is kept. Close the event instead."];
        }
        $stmt = $db->prepare('DELETE FROM events WHERE id = ?');
        $stmt->bind_param('i', $id);
        $stmt->execute();
        $db->commit();
        return ['ok' => true, 'poster' => $row['poster']];
    } catch (mysqli_sql_exception $e) {
        $db->rollback();
        throw $e;
    }
}

// ---------------------------------------------------------------- posters
// Upload folder (outside the reach of HTTP on Apache: uploads/.htaccess denies access and disables PHP).
// STUDENTHUB_UPLOAD_DIR overrides it (used by the tests, so the real folder is never touched).
function poster_dir(): string
{
    return rtrim(getenv('STUDENTHUB_UPLOAD_DIR') ?: dirname(__DIR__) . DIRECTORY_SEPARATOR . 'uploads', '\\/');
}

// 'ok' (a stored poster file), 'missing' (a value that is not a stored poster: an older path or a deleted file) or 'none'
function event_poster_state(array $event): string
{
    if ($event['poster'] === null || $event['poster'] === '') {
        return 'none';
    }
    return poster_path((string) $event['poster']) !== null ? 'ok' : 'missing';
}

// Checks one entry of $_FILES. Returns ['ok' => true, 'tmp', 'ext'] or ['ok' => false, 'error', 'none' => bool].
function validate_poster($file): array
{
    if (!is_array($file) || !isset($file['error']) || is_array($file['error'])) {
        return ['ok' => false, 'none' => true, 'error' => 'No poster was chosen.'];
    }
    switch ((int) $file['error']) {
        case UPLOAD_ERR_OK:
            break;
        case UPLOAD_ERR_NO_FILE:
            return ['ok' => false, 'none' => true, 'error' => 'No poster was chosen.'];
        case UPLOAD_ERR_INI_SIZE:
        case UPLOAD_ERR_FORM_SIZE:
            return ['ok' => false, 'none' => false, 'error' => 'The poster is too large. The maximum size is 2 MB.'];
        case UPLOAD_ERR_PARTIAL:
            return ['ok' => false, 'none' => false, 'error' => 'The poster was only partly uploaded. Please try again.'];
        default:
            error_log('StudentHub poster upload error code ' . (int) $file['error']);
            return ['ok' => false, 'none' => false, 'error' => 'The server could not receive the poster. Please try again later.'];
    }
    $tmp = (string) ($file['tmp_name'] ?? '');
    if ($tmp === '' || !is_uploaded_file($tmp)) {
        return ['ok' => false, 'none' => false, 'error' => 'The poster upload was not valid.'];
    }
    $size = filesize($tmp);
    if ($size === false || $size === 0) {
        return ['ok' => false, 'none' => false, 'error' => 'The poster file is empty.'];
    }
    if ($size > POSTER_MAX_BYTES) {
        return ['ok' => false, 'none' => false, 'error' => sprintf('The poster is %.1f MB. The maximum size is 2 MB.', $size / 1048576)];
    }
    $extension = strtolower(pathinfo((string) ($file['name'] ?? ''), PATHINFO_EXTENSION));
    if (!isset(POSTER_EXTENSIONS[$extension])) {
        return ['ok' => false, 'none' => false, 'error' => 'Invalid file type. Only JPEG, PNG and WebP images (.jpg, .jpeg, .png, .webp) are allowed.'];
    }
    $content = @file_get_contents($tmp);
    if ($content === false || strlen($content) !== $size) {
        return ['ok' => false, 'none' => false, 'error' => 'Invalid file type. The file could not be read as an image.'];
    }
    $mime = (new finfo(FILEINFO_MIME_TYPE))->buffer($content);
    if (!in_array($mime, POSTER_EXTENSIONS, true)) {
        return ['ok' => false, 'none' => false, 'error' => 'Invalid file type. The file content is not a JPEG, PNG or WebP image.'];
    }
    if ($mime !== POSTER_EXTENSIONS[$extension]) {
        return ['ok' => false, 'none' => false, 'error' => 'The file extension does not match its content (.' . $extension . ' file containing ' . $mime . ').'];
    }
    $info = @getimagesizefromstring($content);
    if ($info === false || !isset(POSTER_IMAGE_TYPES[$info[2]]) || image_type_to_mime_type($info[2]) !== $mime
        || !poster_structure_ok($content, POSTER_IMAGE_TYPES[$info[2]])) {
        return ['ok' => false, 'none' => false, 'error' => 'The poster is not a valid image or is damaged.'];
    }
    if ($info[0] < 1 || $info[1] < 1 || $info[0] > POSTER_MAX_PIXELS || $info[1] > POSTER_MAX_PIXELS) {
        return ['ok' => false, 'none' => false, 'error' => 'The poster must be between 1 and ' . POSTER_MAX_PIXELS . ' pixels wide and high.'];
    }
    if (stripos($content, '<?php') !== false || stripos($content, '<?=') !== false) {
        return ['ok' => false, 'none' => false, 'error' => 'The poster was rejected because it contains embedded code.'];
    }
    return ['ok' => true, 'tmp' => $tmp, 'ext' => POSTER_IMAGE_TYPES[$info[2]]];
}

// getimagesize() reads only the header: PNG – every chunk up to IEND with a correct CRC; JPEG – start and end markers;
// WebP – the RIFF length matches the file. Rejects truncated or damaged files.
function poster_structure_ok(string $data, string $ext): bool
{
    $length = strlen($data);
    if ($ext === 'png') {
        $pos = 8;
        while ($pos + 12 <= $length) {
            $chunk_length = unpack('N', substr($data, $pos, 4))[1];
            $type = substr($data, $pos + 4, 4);
            if ($chunk_length > $length - $pos - 12) {
                return false;
            }
            if (crc32($type . substr($data, $pos + 8, $chunk_length)) !== unpack('N', substr($data, $pos + 8 + $chunk_length, 4))[1]) {
                return false;
            }
            if ($type === 'IEND') {
                return true;
            }
            $pos += 12 + $chunk_length;
        }
        return false;
    }
    if ($ext === 'jpg') {
        return strncmp($data, "\xFF\xD8\xFF", 3) === 0 && strrpos($data, "\xFF\xD9") > 2;
    }
    if ($ext === 'webp') {
        $riff = unpack('V', substr($data, 4, 4))[1] ?? 0;
        return strncmp($data, 'RIFF', 4) === 0 && substr($data, 8, 4) === 'WEBP' && $riff >= 12 && $riff + 8 <= $length;
    }
    return false;
}

// Moves a validated upload into the upload folder under a new random name (the original name is never used)
function store_poster(array $valid): ?string
{
    $dir = poster_dir();
    if (!is_dir($dir) && !mkdir($dir, 0755, true)) {
        error_log('StudentHub: poster folder missing and could not be created');
        return null;
    }
    do {
        $name = bin2hex(random_bytes(16)) . '.' . $valid['ext'];
    } while (file_exists($dir . DIRECTORY_SEPARATOR . $name));
    if (!move_uploaded_file($valid['tmp'], $dir . DIRECTORY_SEPARATOR . $name)) {
        error_log('StudentHub: move_uploaded_file failed for a poster');
        return null;
    }
    @chmod($dir . DIRECTORY_SEPARATOR . $name, 0644);
    return $name;
}

// Full path of a stored poster, or null if the name is not exactly "<32 hex>.<jpg|png|webp>" or the file is missing.
// Older values such as "uploads/odoo_hackathon.jpg" or "../db.php" never pass, so no other file can be reached.
function poster_path(string $name): ?string
{
    if (!preg_match(POSTER_NAME_PATTERN, $name)) {
        return null;
    }
    $dir = realpath(poster_dir());
    $path = $dir === false ? false : realpath($dir . DIRECTORY_SEPARATOR . $name);
    return ($path !== false && dirname($path) === $dir && is_file($path)) ? $path : null;
}

// Deletes a stored poster that no event uses any more (only valid names inside the upload folder)
function delete_poster_file(mysqli $db, ?string $name): bool
{
    if ($name === null || ($path = poster_path($name)) === null) {
        return false;
    }
    $stmt = $db->prepare('SELECT COUNT(*) FROM events WHERE poster = ?');
    $stmt->bind_param('s', $name);
    $stmt->execute();
    return (int) $stmt->get_result()->fetch_row()[0] === 0 && @unlink($path);
}

// Removes a freshly stored poster again when the database step failed
function discard_new_poster(?string $name): void
{
    if ($name !== null && ($path = poster_path($name)) !== null) {
        @unlink($path);
    }
}
