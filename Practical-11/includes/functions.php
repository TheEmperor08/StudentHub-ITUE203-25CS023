<?php
// StudentHub – Practical 11: shared helpers for every page – session, security headers, one-time form tokens
// (CSRF + duplicate-submission protection), flash messages, validation, the search/filter query and the layout.
declare(strict_types=1);

require_once dirname(__DIR__) . '/db.php';

const COURSES = ['Computer Engineering', 'Computer Science', 'Data Science', 'Electronics & Communication',
                 'Information Technology'];
const STATUSES = ['active' => 'Active', 'inactive' => 'Inactive'];
const PER_PAGE = 10;
const NAME_PATTERN = "/^\\p{L}[\\p{L} .'\\-]{1,99}$/u";   // letters, spaces, dot, apostrophe, hyphen; 2–100 characters

function e(mixed $value): string
{
    return htmlspecialchars((string) $value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

// Session cookie: not readable by JavaScript, not sent with requests from other sites, strict mode
function start_app(): void
{
    if (session_status() !== PHP_SESSION_ACTIVE) {
        ini_set('session.use_strict_mode', '1');
        ini_set('session.use_only_cookies', '1');
        session_name('P11SESSID');
        session_set_cookie_params([
            'lifetime' => 0,
            'path'     => '/',
            'secure'   => !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off',
            'httponly' => true,
            'samesite' => 'Strict',
        ]);
        session_start();
    }
    header("Content-Security-Policy: default-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'; object-src 'none'");
    header('X-Frame-Options: DENY');
    header('X-Content-Type-Options: nosniff');
    header('Referrer-Policy: same-origin');
    header('Cache-Control: no-store');
}

// Any database failure that is not handled on the page ends here: the details go to the PHP error log and the
// user sees a general message (no SQL, table names or connection details).
set_exception_handler(function (Throwable $exception): void {
    error_log('Practical 11 error: ' . get_class($exception) . ' [' . $exception->getCode() . '] ' . $exception->getMessage());
    if (!headers_sent()) {
        http_response_code(503);
        header('Content-Type: text/html; charset=utf-8');
    }
    page_start('Service unavailable');
    echo '<div class="alert alert-error" role="alert">The student database is not available right now. Please make sure MySQL is running and try again.</div>', "\n",
         '<p><a class="btn btn-secondary" href="index.php">Back to the student list</a></p>', "\n";
    page_end();
});

// ---------------------------------------------------------------- one-time form tokens
// Every form gets a new random token that is remembered in the session. A POST is accepted only if it carries a
// token this session issued (CSRF protection) and that token has not been used before (a form that is submitted
// twice – double click, Back + resend – is refused the second time).
function form_token(): string
{
    $token = bin2hex(random_bytes(32));
    $_SESSION['form_tokens'][$token] = time();
    if (count($_SESSION['form_tokens']) > 50) {                  // keep only the 50 newest open forms
        $_SESSION['form_tokens'] = array_slice($_SESSION['form_tokens'], -50, null, true);
    }
    return $token;
}

function use_form_token(mixed $submitted): bool
{
    if (!is_string($submitted) || !preg_match('/^[0-9a-f]{64}$/', $submitted)
        || !isset($_SESSION['form_tokens'][$submitted])) {
        return false;
    }
    unset($_SESSION['form_tokens'][$submitted]);
    return true;
}

// A rejected token: back to the list with an error message (HTTP 303 after a POST)
function reject_invalid_token(): never
{
    flash('error', 'The form could not be processed because it has expired or was already submitted. Check the student list and try again.');
    redirect('index.php');
}

// ---------------------------------------------------------------- messages and redirects
function flash(string $type, string $message, ?int $student_id = null): void
{
    $_SESSION['flash'] = ['type' => $type, 'message' => $message, 'student_id' => $student_id];
}

function take_flash(): ?array
{
    $flash = $_SESSION['flash'] ?? null;
    unset($_SESSION['flash']);
    return is_array($flash) ? $flash : null;
}

function redirect(string $location): never
{
    header('Location: ' . $location, true, 303);
    exit;
}

// ---------------------------------------------------------------- validation
// Returns [clean data, errors per field]. The same rules are repeated in the HTML form (required, maxlength,
// pattern, type="email", min/max) so the browser can warn early, but only this check is trusted.
function validate_student(array $input): array
{
    $data = [
        'full_name' => preg_replace('/\s+/u', ' ', trim((string) ($input['full_name'] ?? ''))) ?? '',
        'email'     => strtolower(trim((string) ($input['email'] ?? ''))),
        'course'    => trim((string) ($input['course'] ?? '')),
        'semester'  => trim((string) ($input['semester'] ?? '')),
    ];
    $errors = [];

    if ($data['full_name'] === '') {
        $errors['full_name'] = 'Full name is required.';
    } elseif (mb_strlen($data['full_name']) > 100 || !preg_match(NAME_PATTERN, $data['full_name'])) {
        $errors['full_name'] = 'Use 2–100 letters; spaces, dots, apostrophes and hyphens are allowed.';
    }

    if ($data['email'] === '') {
        $errors['email'] = 'Email is required.';
    } elseif (strlen($data['email']) > 254 || filter_var($data['email'], FILTER_VALIDATE_EMAIL) === false) {
        $errors['email'] = 'Enter a valid email address, for example name@example.com.';
    }

    if ($data['course'] === '') {
        $errors['course'] = 'Please select a course.';
    } elseif (!in_array($data['course'], COURSES, true)) {
        $errors['course'] = 'Please select a course from the list.';
    }

    if ($data['semester'] === '') {
        $errors['semester'] = 'Please select a semester.';
    } elseif (!ctype_digit($data['semester']) || (int) $data['semester'] < 1 || (int) $data['semester'] > 8) {
        $errors['semester'] = 'Semester must be a number from 1 to 8.';
    } else {
        $data['semester'] = (int) $data['semester'];
    }
    return [$data, $errors];
}

// True if another student (any status – inactive records keep their email) already uses this email
function email_taken(mysqli $db, string $email, int $except_id = 0): bool
{
    $stmt = $db->prepare('SELECT COUNT(*) FROM students WHERE email = ? AND student_id <> ?');
    $stmt->bind_param('si', $email, $except_id);
    $stmt->execute();
    return (int) $stmt->get_result()->fetch_row()[0] > 0;
}

function find_student(mysqli $db, int $id): ?array
{
    $stmt = $db->prepare('SELECT * FROM students WHERE student_id = ?');
    $stmt->bind_param('i', $id);
    $stmt->execute();
    return $stmt->get_result()->fetch_assoc() ?: null;
}

// Positive integer from a request value, otherwise 0
function positive_id(mixed $value): int
{
    return is_string($value) && ctype_digit($value) && strlen($value) <= 10 ? (int) $value : 0;
}

// ---------------------------------------------------------------- search, filter and pagination
// Reads the list options from the query string. Unknown courses/statuses are ignored instead of being used in SQL.
function list_filters(array $query): array
{
    $q = trim((string) (is_string($query['q'] ?? null) ? $query['q'] : ''));
    $course = is_string($query['course'] ?? null) ? $query['course'] : '';
    $status = is_string($query['status'] ?? null) ? $query['status'] : '';
    return [
        'q'      => mb_substr($q, 0, 100),
        'course' => in_array($course, COURSES, true) ? $course : '',
        'status' => isset(STATUSES[$status]) ? $status : '',
    ];
}

// Builds the WHERE clause with ? placeholders. The search text is matched against name, email and course with
// LIKE; % and _ typed by the user are escaped so they are searched literally.
function filter_sql(array $filters): array
{
    $where = [];
    $types = '';
    $params = [];
    if ($filters['q'] !== '') {
        $like = '%' . addcslashes($filters['q'], '\\%_') . '%';
        $where[] = '(full_name LIKE ? OR email LIKE ? OR course LIKE ?)';
        $types .= 'sss';
        array_push($params, $like, $like, $like);
    }
    if ($filters['course'] !== '') {
        $where[] = 'course = ?';
        $types .= 's';
        $params[] = $filters['course'];
    }
    if ($filters['status'] !== '') {
        $where[] = 'status = ?';
        $types .= 's';
        $params[] = $filters['status'];
    }
    return [$where ? ' WHERE ' . implode(' AND ', $where) : '', $types, $params];
}

function count_students(mysqli $db, array $filters): int
{
    [$where, $types, $params] = filter_sql($filters);
    $stmt = $db->prepare('SELECT COUNT(*) FROM students' . $where);
    if ($types !== '') {
        $stmt->bind_param($types, ...$params);
    }
    $stmt->execute();
    return (int) $stmt->get_result()->fetch_row()[0];
}

// Matching students, most recently changed first. $limit = null returns every match (used by the CSV export).
function fetch_students(mysqli $db, array $filters, ?int $limit = null, int $offset = 0): array
{
    [$where, $types, $params] = filter_sql($filters);
    $sql = 'SELECT student_id, full_name, email, course, semester, status, created_at, updated_at, deleted_at
            FROM students' . $where . ' ORDER BY updated_at DESC, student_id DESC';
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

// index.php / export.php URL for the given filters and page number (empty filters and page 1 are left out)
function list_url(string $script, array $filters, int $page = 1): string
{
    $params = array_filter($filters, fn ($value) => $value !== '');
    if ($page > 1) {
        $params['page'] = $page;
    }
    return $script . ($params ? '?' . http_build_query($params) : '');
}

// ---------------------------------------------------------------- layout
function status_badge(string $status): string
{
    return '<span class="badge badge-' . e($status) . '">' . e(STATUSES[$status] ?? $status) . '</span>';
}

function course_options(string $selected, string $placeholder): string
{
    $html = '<option value="">' . e($placeholder) . '</option>';
    foreach (COURSES as $course) {
        $html .= '<option value="' . e($course) . '"' . ($course === $selected ? ' selected' : '') . '>' . e($course) . '</option>';
    }
    return $html;
}

function render_flash(?array $flash): void
{
    if ($flash) {
        $class = $flash['type'] === 'success' ? 'alert-success' : 'alert-error';
        $role = $flash['type'] === 'success' ? 'status' : 'alert';
        echo '<div class="alert ', $class, '" role="', $role, '">', e($flash['message']), '</div>', "\n";
    }
}

function page_start(string $title, string $active = ''): void
{
    $nav = ['index.php' => 'Student list', 'add.php' => 'Add student'];
    echo '<!DOCTYPE html>', "\n", '<html lang="en">', "\n", '<head>', "\n",
         '    <meta charset="UTF-8">', "\n",
         '    <meta name="viewport" content="width=device-width, initial-scale=1.0">', "\n",
         '    <title>', e($title), ' - StudentHub Practical 11</title>', "\n",
         '    <link rel="icon" href="favicon.svg" type="image/svg+xml">', "\n",
         '    <link rel="stylesheet" href="style.css">', "\n",
         '    <script src="app.js" defer></script>', "\n",
         '</head>', "\n", '<body>', "\n",
         '<header class="site-header">', "\n", '    <div class="container header-row">', "\n",
         '        <div>', "\n",
         '            <p class="brand">StudentHub · Practical 11</p>', "\n",
         '            <h1>', e($title), '</h1>', "\n",
         '        </div>', "\n",
         '        <nav class="main-nav" aria-label="Main">';
    foreach ($nav as $href => $label) {
        echo '<a href="', $href, '"', $href === $active ? ' aria-current="page"' : '', '>', $label, '</a>';
    }
    echo '</nav>', "\n", '    </div>', "\n", '</header>', "\n", '<main class="container" id="main">', "\n";
}

function page_end(): void
{
    echo '</main>', "\n",
         '<footer class="site-footer"><div class="container"><p>&copy; <time datetime="2026">2026</time> StudentHub – ITUE203 Practical 11 by Shreyas (25CS023). All student records are fictional.</p></div></footer>', "\n",
         '</body>', "\n", '</html>', "\n";
}

// The add and edit pages share this form. $values are the current field values, $errors the messages per field,
// $hidden extra hidden fields (the record ID on the edit page).
function student_form(string $action, string $button, array $values, array $errors, array $hidden = []): void
{
    $field_error = function (string $field) use ($errors): string {
        return isset($errors[$field])
            ? '<p class="field-error" id="' . $field . '-error">' . e($errors[$field]) . '</p>' : '';
    };
    $invalid = fn (string $field): string => isset($errors[$field])
        ? ' aria-invalid="true" aria-describedby="' . $field . '-error"' : '';

    echo '<form class="card student-form" method="post" action="', e($action), '">', "\n",
         '    <input type="hidden" name="form_token" value="', e(form_token()), '">', "\n";
    foreach ($hidden as $name => $value) {
        echo '    <input type="hidden" name="', e($name), '" value="', e($value), '">', "\n";
    }
    echo '    <div class="form-grid">', "\n",
         '        <div class="form-field">', "\n",
         '            <label for="full_name">Full name</label>', "\n",
         '            <input type="text" id="full_name" name="full_name" required minlength="2" maxlength="100" autocomplete="name"',
         ' pattern="\p{L}[\p{L} .\'\-]{1,99}" title="2–100 letters; spaces, dots, apostrophes and hyphens are allowed"',
         ' value="', e($values['full_name'] ?? ''), '"', $invalid('full_name'), '>', "\n",
         '            ', $field_error('full_name'), "\n",
         '        </div>', "\n",
         '        <div class="form-field">', "\n",
         '            <label for="email">Email</label>', "\n",
         '            <input type="email" id="email" name="email" required maxlength="254" autocomplete="email"',
         ' value="', e($values['email'] ?? ''), '"', $invalid('email'), '>', "\n",
         '            ', $field_error('email'), "\n",
         '        </div>', "\n",
         '        <div class="form-field">', "\n",
         '            <label for="course">Course</label>', "\n",
         '            <select id="course" name="course" required', $invalid('course'), '>',
         course_options((string) ($values['course'] ?? ''), 'Select a course'), '</select>', "\n",
         '            ', $field_error('course'), "\n",
         '        </div>', "\n",
         '        <div class="form-field">', "\n",
         '            <label for="semester">Semester</label>', "\n",
         '            <select id="semester" name="semester" required', $invalid('semester'), '><option value="">Select a semester</option>';
    for ($s = 1; $s <= 8; $s++) {
        echo '<option value="', $s, '"', (string) ($values['semester'] ?? '') === (string) $s ? ' selected' : '', '>Semester ', $s, '</option>';
    }
    echo '</select>', "\n",
         '            ', $field_error('semester'), "\n",
         '        </div>', "\n",
         '    </div>', "\n",
         '    <div class="form-actions">', "\n",
         '        <button type="submit" class="btn btn-primary">', e($button), '</button>', "\n",
         '        <a class="btn btn-secondary" href="index.php">Cancel</a>', "\n",
         '    </div>', "\n",
         '</form>', "\n";
}
