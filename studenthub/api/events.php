<?php
// StudentHub – events JSON API (Practical 13 integrated into the portal). Used by the Event Finder page
// (events_live.php + assets/js/events-live.js) through the Fetch API. Same database connection, same login session and
// the same event and registration rules as the rest of the portal (includes/event_management.php, event_registration.php).
//
//   GET  api/events.php?action=list[&q=][&category=][&status=open|closed][&when=upcoming|past]   signed-in users
//   GET  api/events.php?action=get&id=5                                                          signed-in users
//   POST api/events.php?action=create | update | delete      administrators (events.manage)       body: JSON event / {"id": 5}
//   POST api/events.php?action=register | cancel             students with a linked record         body: {"event_id": 5}
//
// Every response is JSON {"ok": true|false, ...} with a fitting status code: 200, 201, 400 (bad request), 401 (not signed
// in), 403 (role or CSRF), 404, 405 (wrong method, with Allow), 409 (conflict: duplicate, full, closed, has registrations),
// 415 (POST without application/json), 422 (validation, with "errors" per field), 500/503 (general message only – the
// details go to the server log). POST requests must carry the session's CSRF token in the X-CSRF-Token header.

const STUDENTHUB_API = true;                                 // db.php answers its own failures in JSON
require_once dirname(__DIR__) . '/db.php';
require_once dirname(__DIR__) . '/includes/auth.php';
require_once dirname(__DIR__) . '/includes/event_management.php';
require_once dirname(__DIR__) . '/includes/event_registration.php';
require_once dirname(__DIR__) . '/audit_logger.php';

final class ApiError extends Exception
{
    public function __construct(int $status, string $message, public array $fields = [])
    {
        parent::__construct($message, $status);
    }
}

// The single exit point: status code, JSON headers and the JSON body
function api_respond(int $status, array $body): void
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    header('X-Content-Type-Options: nosniff');
    echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT);
    exit;
}

// Central error handling: expected problems are ApiError; anything else is logged and answered with a general 500
set_exception_handler(function (Throwable $e): void {
    if ($e instanceof ApiError) {
        api_respond($e->getCode(), ['ok' => false, 'error' => $e->getMessage()] + ($e->fields ? ['errors' => $e->fields] : []));
    }
    error_log('StudentHub API error: ' . get_class($e) . ' [' . $e->getCode() . '] ' . $e->getMessage() . ' in ' . $e->getFile() . ':' . $e->getLine());
    api_respond(500, ['ok' => false, 'error' => 'The server could not complete the request. Please try again later.']);
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

// POST: JSON body, CSRF header; returns the decoded object
function json_body(array $user): array
{
    global $conn;
    $type = strtolower(trim(explode(';', (string) ($_SERVER['CONTENT_TYPE'] ?? ''))[0]));
    if ($type !== 'application/json') {
        throw new ApiError(415, 'Send the request body as JSON (Content-Type: application/json).');
    }
    if (!csrf_is_valid($_SERVER['HTTP_X_CSRF_TOKEN'] ?? null)) {
        log_audit($conn, $user['id'], $user['username'], 'CSRF_REJECTED', 'API POST ' . ($_GET['action'] ?? '') . ' without a valid token', 'SECURITY_BLOCK');
        throw new ApiError(403, 'Security check failed. Reload the page and try again.');
    }
    $raw = file_get_contents('php://input');
    if (strlen((string) $raw) > 20000) {
        throw new ApiError(400, 'The request body is too large.');
    }
    $data = json_decode((string) $raw, true);
    if (!is_array($data) || array_is_list($data) && $data !== []) {
        throw new ApiError(400, 'The request body must be a JSON object.');
    }
    return $data;
}

function require_api_permission(array $user, string $permission): void
{
    global $conn;
    if (!role_can($user['role'], $permission)) {
        log_audit($conn, $user['id'], $user['username'], 'ACCESS_DENIED', "API: role '{$user['role']}' lacks permission '$permission'", 'SECURITY_BLOCK');
        throw new ApiError(403, 'Your account is not allowed to do this.');
    }
}

function body_id(array $body, string $key): int
{
    $value = $body[$key] ?? null;
    return event_id_from(is_int($value) ? (string) $value : $value);
}

// One event as JSON (only what the page needs; the poster as a URL of poster.php, never a file name)
function api_event(array $ev, ?string $mine): array
{
    $capacity = $ev['capacity'] !== null ? (int) $ev['capacity'] : null;
    return [
        'id' => (int) $ev['id'], 'title' => $ev['title'], 'category' => $ev['category'], 'event_date' => $ev['event_date'],
        'event_time' => $ev['event_time'] !== null ? substr($ev['event_time'], 0, 5) : null, 'when' => event_when_label($ev),
        'location' => $ev['location'], 'description' => (string) $ev['description'], 'capacity' => $capacity,
        'seats_taken' => (int) $ev['seats_taken'], 'seats_left' => $capacity === null ? null : max(0, $capacity - (int) $ev['seats_taken']),
        'status' => $ev['status'], 'is_past' => $ev['event_date'] < date('Y-m-d'),
        'poster_url' => event_poster_state($ev) === 'ok' ? 'poster.php?event=' . (int) $ev['id'] : null,
        'registrations_total' => (int) $ev['registrations_total'], 'my_registration' => $mine,
    ];
}

// Event fields from a JSON body as strings (numbers allowed for capacity; anything else stays and fails validation)
function event_input(array $body): array
{
    $input = [];
    foreach (EVENT_FIELDS as $field) {
        $value = $body[$field] ?? '';
        $input[$field] = is_int($value) ? (string) $value : ($value === null ? '' : $value);
    }
    return $input;
}

const REGISTRATION_STATUS = [
    EventRegistrationException::EVENT_NOT_FOUND => 404, EventRegistrationException::STUDENT_NOT_FOUND => 404,
    EventRegistrationException::STUDENT_INACTIVE => 403, EventRegistrationException::DUPLICATE => 409,
    EventRegistrationException::EVENT_FULL => 409, EventRegistrationException::EVENT_CLOSED => 409,
    EventRegistrationException::EVENT_PAST => 409, EventRegistrationException::NOT_REGISTERED => 409,
];

// ---------------------------------------------------------------- authentication (no redirects: JSON 401)
start_secure_session();
send_security_headers(true);
[$user, $reason] = validate_session();
if ($user === null) {
    throw new ApiError(401, match ($reason) {
        'timeout'         => 'Your session ended because you were inactive. Please sign in again.',
        'access_disabled' => 'Your access to StudentHub is currently disabled. Please contact the administrator.',
        default           => 'Please sign in to use StudentHub.',
    });
}
require_api_permission($user, 'portal.view');
$categories = event_categories($conn);
$student = $user['role'] === 'student' ? linked_student($conn, $user['id']) : null;
$action = is_string($_GET['action'] ?? null) ? $_GET['action'] : '';

switch ($action) {
    case 'list':
        require_method('GET');
        $filters = event_filters($_GET, $categories);
        $mine = $student !== null ? student_registration_map($conn, (int) $student['id']) : [];
        $events = array_map(fn ($ev) => api_event($ev, $mine[(int) $ev['id']] ?? null), event_list($conn, $filters, 100));
        api_respond(200, ['ok' => true, 'count' => count($events), 'events' => $events,
            'filters' => array_intersect_key($filters, array_flip(['q', 'category', 'status', 'when'])),
            'can_manage' => role_can($user['role'], 'events.manage'), 'can_register' => $student !== null]);

    case 'get':
        require_method('GET');
        $event = ($id = event_id_from($_GET['id'] ?? '')) > 0 ? find_event($conn, $id) : null;
        if ($event === null) {
            throw new ApiError(404, 'That event was not found.');
        }
        $mine = $student !== null ? student_registration_map($conn, (int) $student['id']) : [];
        api_respond(200, ['ok' => true, 'event' => api_event($event, $mine[$id] ?? null)]);

    case 'create':
    case 'update':
        require_method('POST');
        require_api_permission($user, 'events.manage');
        $body = json_body($user);
        $existing = null;
        if ($action === 'update' && ($existing = ($id = body_id($body, 'id')) > 0 ? find_event($conn, $id) : null) === null) {
            throw new ApiError(404, 'That event was not found.');
        }
        [$clean, $errors] = validate_event(event_input($body), $categories, $existing);
        $saved = $errors ? ['errors' => $errors] : save_event($conn, $clean, $existing ? (int) $existing['id'] : null);
        if (isset($saved['errors'])) {
            throw new ApiError(422, 'Please correct the highlighted fields.', $saved['errors']);
        }
        log_audit($conn, $user['id'], $user['username'], $existing ? 'UPDATE_EVENT' : 'CREATE_EVENT',
            ($existing ? 'Updated' : 'Created') . " event ID {$saved['id']} ({$clean['title']}) via the events API", 'SUCCESS');
        api_respond($existing ? 200 : 201, ['ok' => true, 'event' => api_event(find_event($conn, $saved['id']), null),
            'message' => $existing ? "Event “{$clean['title']}” was updated." : "Event “{$clean['title']}” was published."]);

    case 'delete':
        require_method('POST');
        require_api_permission($user, 'events.manage');
        $body = json_body($user);
        $event = ($id = body_id($body, 'id')) > 0 ? find_event($conn, $id) : null;
        if ($event === null) {
            throw new ApiError(404, 'That event was not found.');
        }
        $deleted = delete_event($conn, $id);
        if (!$deleted['ok']) {
            throw new ApiError(409, $deleted['error']);
        }
        delete_poster_file($conn, $deleted['poster']);
        log_audit($conn, $user['id'], $user['username'], 'DELETE_EVENT', "Deleted event ID $id ({$event['title']}) via the events API", 'SUCCESS');
        api_respond(200, ['ok' => true, 'id' => $id, 'message' => "Event “{$event['title']}” was deleted."]);

    case 'register':
    case 'cancel':
        require_method('POST');
        $body = json_body($user);
        if ($student === null) {
            throw new ApiError(403, 'Event registration is available to students with a linked student record.');
        }
        $event = ($id = body_id($body, 'event_id')) > 0 ? find_event($conn, $id) : null;
        if ($event === null) {
            throw new ApiError(404, 'That event was not found.');
        }
        try {
            if ($action === 'register') {
                $registration = register_student_for_event($conn, (int) $student['id'], $id);
                log_audit($conn, $user['id'], $user['username'], 'EVENT_REGISTER', "Registered for event ID $id (registration ID $registration) via the events API", 'SUCCESS');
                $message = "You are registered for “{$event['title']}”.";
            } else {
                $registration = cancel_event_registration($conn, (int) $student['id'], $id);
                log_audit($conn, $user['id'], $user['username'], 'EVENT_REGISTRATION_CANCEL', "Cancelled registration ID $registration for event ID $id via the events API", 'SUCCESS');
                $message = "Your registration for “{$event['title']}” was cancelled.";
            }
        } catch (EventRegistrationException $e) {
            throw new ApiError(REGISTRATION_STATUS[$e->reason] ?? 409, $e->getMessage());
        }
        $mine = student_registration_map($conn, (int) $student['id']);
        api_respond($action === 'register' ? 201 : 200, ['ok' => true, 'message' => $message, 'event' => api_event(find_event($conn, $id), $mine[$id] ?? null)]);

    default:
        throw new ApiError(400, 'Unknown action. Use list, get, create, update, delete, register or cancel.');
}
