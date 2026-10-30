<?php
// StudentHub – Practical 13: JSON API for the event CRUD page (index.html + script.js).
//
//   GET  api.php?action=list[&q=text][&category=Workshop]   list events (search in title, venue, category, description)
//   GET  api.php?action=get&id=5                           one event
//   POST api.php?action=create                             body: JSON event (success: 200 + the saved event)
//   POST api.php?action=update                             body: JSON event with event_id
//   POST api.php?action=delete                             body: {"event_id": 5}
//
// Every response is JSON {"ok": true|false, ...}. Errors use a fitting status code (400, 404, 405, 415, 422, 500) and
// never contain SQL or connection details. POST requests must send Content-Type: application/json and the header
// X-Requested-With: fetch – a plain HTML form on another site cannot do that, so it cannot change data here.
// All SQL uses MySQLi prepared statements.
declare(strict_types=1);
require_once __DIR__ . '/db.php';

const CATEGORIES = ['Cultural', 'Hackathon', 'Seminar', 'Sports', 'Technical', 'Workshop'];
const STATUSES = ['open', 'closed'];
const EVENT_COLUMNS = 'event_id, title, description, category, event_date, start_time, venue, capacity, status, created_at, updated_at';

final class ApiError extends Exception
{
    public function __construct(int $status, string $message, public array $fields = [])
    {
        parent::__construct($message, $status);
    }
}

// The single exit point: sends the status code, JSON headers and the JSON body
function respond(int $status, array $body): never
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    header('X-Content-Type-Options: nosniff');
    echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT);
    exit;
}

// Centralized error handling: expected problems are ApiError, everything else is logged and answered with 500
set_exception_handler(function (Throwable $e): void {
    if ($e instanceof ApiError) {
        $body = ['ok' => false, 'error' => $e->getMessage()];
        if ($e->fields) {
            $body['errors'] = $e->fields;
        }
        respond($e->getCode(), $body);
    }
    error_log('Practical 13 API error: ' . get_class($e) . ' [' . $e->getCode() . '] ' . $e->getMessage());
    respond(500, ['ok' => false, 'error' => 'The server could not complete the request. Please try again later.']);
});
set_error_handler(function (int $severity, string $message, string $file, int $line): bool {
    throw new ErrorException($message, 0, $severity, $file, $line);
});

function require_method(string $method): void
{
    if ($_SERVER['REQUEST_METHOD'] !== $method) {
        header('Allow: ' . $method);
        throw new ApiError(405, "This action needs a $method request.");
    }
}

// Reads and checks the JSON body of a POST request
function json_body(): array
{
    if (stripos($_SERVER['CONTENT_TYPE'] ?? '', 'application/json') !== 0) {
        throw new ApiError(415, 'Send the data as JSON (Content-Type: application/json).');
    }
    if (($_SERVER['HTTP_X_REQUESTED_WITH'] ?? '') !== 'fetch') {
        throw new ApiError(400, 'Missing X-Requested-With header.');
    }
    $raw = file_get_contents('php://input');
    if (strlen($raw) > 20000) {
        throw new ApiError(400, 'The request is too large.');
    }
    try {
        $object = json_decode($raw, false, 8, JSON_THROW_ON_ERROR);
    } catch (JsonException) {
        throw new ApiError(400, 'The request body is not valid JSON.');
    }
    if (!$object instanceof stdClass) {                             // [1,2,3], "text" or 5 are valid JSON but not an object
        throw new ApiError(400, 'The request body must be a JSON object.');
    }
    return json_decode($raw, true, 8, JSON_THROW_ON_ERROR);
}

function event_id(mixed $value): int
{
    if (is_int($value) && $value > 0) {
        return $value;
    }
    if (is_string($value) && ctype_digit($value) && strlen($value) <= 10 && (int) $value > 0) {
        return (int) $value;
    }
    throw new ApiError(400, 'A valid event_id is required.');
}

// Server-side validation of all fields. Returns clean values or throws 422 with one message per field.
function validate_event(array $in): array
{
    $str = fn (string $k): string => is_string($in[$k] ?? null) ? trim($in[$k]) : (is_int($in[$k] ?? null) ? (string) $in[$k] : '');
    $e = [
        'title'       => preg_replace('/\s+/u', ' ', $str('title')) ?? '',
        'description' => $str('description'),
        'category'    => $str('category'),
        'event_date'  => $str('event_date'),
        'start_time'  => $str('start_time'),
        'venue'       => preg_replace('/\s+/u', ' ', $str('venue')) ?? '',
        'capacity'    => $str('capacity'),
        'status'      => $str('status'),
    ];
    $err = [];
    $len = fn (string $k): int => mb_strlen($e[$k]);

    if ($e['title'] === '') {
        $err['title'] = 'Title is required.';
    } elseif ($len('title') < 3 || $len('title') > 120) {
        $err['title'] = 'Title must be 3–120 characters.';
    }
    if ($e['description'] === '') {
        $err['description'] = 'Description is required.';
    } elseif ($len('description') < 10 || $len('description') > 1000) {
        $err['description'] = 'Description must be 10–1000 characters.';
    }
    if (!in_array($e['category'], CATEGORIES, true)) {
        $err['category'] = $e['category'] === '' ? 'Category is required.' : 'Choose a category from the list.';
    }
    $d = DateTime::createFromFormat('!Y-m-d', $e['event_date']);
    if ($e['event_date'] === '') {
        $err['event_date'] = 'Date is required.';
    } elseif (!$d || $d->format('Y-m-d') !== $e['event_date'] || $e['event_date'] < '2000-01-01' || $e['event_date'] > '2100-12-31') {
        $err['event_date'] = 'Enter a valid date (YYYY-MM-DD).';
    }
    if ($e['start_time'] === '') {
        $err['start_time'] = 'Start time is required.';
    } elseif (!preg_match('/^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$/', $e['start_time'])) {
        $err['start_time'] = 'Enter a valid time (HH:MM).';
    } else {
        $e['start_time'] = substr($e['start_time'], 0, 5);
    }
    if ($e['venue'] === '') {
        $err['venue'] = 'Venue is required.';
    } elseif ($len('venue') < 2 || $len('venue') > 120) {
        $err['venue'] = 'Venue must be 2–120 characters.';
    }
    if ($e['capacity'] === '') {
        $err['capacity'] = 'Capacity is required.';
    } elseif (!ctype_digit($e['capacity']) || (int) $e['capacity'] < 1 || (int) $e['capacity'] > 5000) {
        $err['capacity'] = 'Capacity must be a whole number from 1 to 5000.';
    } else {
        $e['capacity'] = (int) $e['capacity'];
    }
    if (!in_array($e['status'], STATUSES, true)) {
        $err['status'] = 'Status must be open or closed.';
    }
    if ($err) {
        throw new ApiError(422, 'Please correct the highlighted fields.', $err);
    }
    return $e;
}

function find_event(mysqli $db, int $id): array
{
    $stmt = $db->prepare('SELECT ' . EVENT_COLUMNS . ' FROM events WHERE event_id = ?');
    $stmt->bind_param('i', $id);
    $stmt->execute();
    $row = $stmt->get_result()->fetch_assoc();
    if (!$row) {
        throw new ApiError(404, 'Event not found. It may have been deleted already.');
    }
    return format_event($row);
}

function format_event(array $row): array
{
    $row['event_id'] = (int) $row['event_id'];
    $row['capacity'] = (int) $row['capacity'];
    $row['start_time'] = substr($row['start_time'], 0, 5);
    return $row;
}

// ---------------------------------------------------------------- routing
$action = is_string($_GET['action'] ?? null) ? $_GET['action'] : '';
$db = get_db();

switch ($action) {
    case 'list':
        require_method('GET');
        $q = is_string($_GET['q'] ?? null) ? mb_substr(trim($_GET['q']), 0, 100) : '';
        $category = is_string($_GET['category'] ?? null) && in_array($_GET['category'], CATEGORIES, true) ? $_GET['category'] : '';
        $sql = 'SELECT ' . EVENT_COLUMNS . ' FROM events WHERE 1 = 1';
        $types = '';
        $params = [];
        if ($q !== '') {
            $like = '%' . addcslashes($q, '\\%_') . '%';             // the user's % and _ are searched literally
            $sql .= ' AND (title LIKE ? OR venue LIKE ? OR category LIKE ? OR description LIKE ?)';
            $types .= 'ssss';
            array_push($params, $like, $like, $like, $like);
        }
        if ($category !== '') {
            $sql .= ' AND category = ?';
            $types .= 's';
            $params[] = $category;
        }
        $stmt = $db->prepare($sql . ' ORDER BY event_date, start_time, event_id');
        if ($types !== '') {
            $stmt->bind_param($types, ...$params);
        }
        $stmt->execute();
        $events = array_map('format_event', $stmt->get_result()->fetch_all(MYSQLI_ASSOC));
        $total = $db->prepare('SELECT COUNT(*) FROM events');
        $total->execute();
        respond(200, ['ok' => true, 'count' => count($events), 'total' => (int) $total->get_result()->fetch_row()[0],
                      'query' => $q, 'category' => $category, 'categories' => CATEGORIES, 'events' => $events]);

    case 'get':
        require_method('GET');
        respond(200, ['ok' => true, 'event' => find_event($db, event_id($_GET['id'] ?? null))]);

    case 'create':
        require_method('POST');
        $e = validate_event(json_body());
        $stmt = $db->prepare('INSERT INTO events (title, description, category, event_date, start_time, venue, capacity, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)');
        $stmt->bind_param('ssssssis', $e['title'], $e['description'], $e['category'], $e['event_date'], $e['start_time'], $e['venue'], $e['capacity'], $e['status']);
        $stmt->execute();
        respond(200, ['ok' => true, 'message' => 'Event “' . $e['title'] . '” was added.', 'event' => find_event($db, $stmt->insert_id)]);

    case 'update':
        require_method('POST');
        $body = json_body();
        $id = event_id($body['event_id'] ?? null);
        find_event($db, $id);                                       // 404 if it no longer exists
        $e = validate_event($body);
        $stmt = $db->prepare('UPDATE events SET title = ?, description = ?, category = ?, event_date = ?, start_time = ?, venue = ?, capacity = ?, status = ? WHERE event_id = ?');
        $stmt->bind_param('ssssssisi', $e['title'], $e['description'], $e['category'], $e['event_date'], $e['start_time'], $e['venue'], $e['capacity'], $e['status'], $id);
        $stmt->execute();
        respond(200, ['ok' => true, 'message' => 'Event “' . $e['title'] . '” was updated.', 'event' => find_event($db, $id)]);

    case 'delete':
        require_method('POST');
        $id = event_id(json_body()['event_id'] ?? null);
        $event = find_event($db, $id);
        $stmt = $db->prepare('DELETE FROM events WHERE event_id = ?');
        $stmt->bind_param('i', $id);
        $stmt->execute();
        respond(200, ['ok' => true, 'message' => 'Event “' . $event['title'] . '” was deleted.', 'deleted_id' => $id]);

    default:
        throw new ApiError(400, 'Unknown action. Use list, get, create, update or delete.');
}
