<?php
// StudentHub – Practical 12: shared helpers – secure session, security headers, CSRF token, administrator guard,
// flash messages, event validation and the Bootstrap page layout. Every page includes this file first.
declare(strict_types=1);

require_once dirname(__DIR__) . '/db.php';
require_once __DIR__ . '/upload.php';

const STATUSES = ['open' => 'Open', 'closed' => 'Closed'];
const TITLE_MAX = 150;
const VENUE_MAX = 150;
const DESCRIPTION_MAX = 2000;

function e(mixed $value): string
{
    return htmlspecialchars((string) $value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

// Session cookie: HttpOnly, SameSite=Strict, HTTPS-only on HTTPS, strict mode (only IDs created by the server).
// Every page also sends security headers; no-store keeps protected pages out of the browser cache.
function start_app(): void
{
    if (session_status() !== PHP_SESSION_ACTIVE) {
        ini_set('session.use_strict_mode', '1');
        ini_set('session.use_only_cookies', '1');
        ini_set('session.use_trans_sid', '0');
        session_name('P12SESSID');
        session_set_cookie_params([
            'lifetime' => 0,
            'path'     => '/',
            'secure'   => !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off',
            'httponly' => true,
            'samesite' => 'Strict',
        ]);
        session_start();
    }
    header("Content-Security-Policy: default-src 'self'; img-src 'self' blob: data:; form-action 'self'; frame-ancestors 'none'; base-uri 'none'; object-src 'none'");
    header('X-Frame-Options: DENY');
    header('X-Content-Type-Options: nosniff');
    header('Referrer-Policy: same-origin');
    header('Cache-Control: no-store, no-cache, must-revalidate, private');
}

// Unhandled errors (for example MySQL stopped): details go to the PHP error log, the user sees a general message
set_exception_handler(function (Throwable $exception): void {
    error_log('Practical 12 error: ' . get_class($exception) . ' [' . $exception->getCode() . '] ' . $exception->getMessage());
    if (!headers_sent()) {
        http_response_code(503);
        header('Content-Type: text/html; charset=utf-8');
    }
    page_start('Service unavailable');
    echo '<div class="alert alert-danger" role="alert">The event database is not available right now. Please make sure MySQL is running and try again.</div>', "\n";
    page_end();
});

// ---------------------------------------------------------------- CSRF
function csrf_token(): string
{
    if (!isset($_SESSION['csrf_token']) || !is_string($_SESSION['csrf_token'])) {
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['csrf_token'];
}

function csrf_is_valid(mixed $submitted): bool
{
    $expected = $_SESSION['csrf_token'] ?? null;
    return is_string($expected) && is_string($submitted) && $submitted !== '' && hash_equals($expected, $submitted);
}

function csrf_field(): string
{
    return '<input type="hidden" name="csrf_token" value="' . e(csrf_token()) . '">';
}

// ---------------------------------------------------------------- administrator session
function current_admin(): ?array
{
    $admin = $_SESSION['admin'] ?? null;
    return is_array($admin) && isset($admin['id'], $admin['name'], $admin['email']) ? $admin : null;
}

function session_timeout_seconds(): int
{
    return max(1, (int) app_config()['session_timeout']);
}

// Clears the session data, expires the cookie in the browser and deletes the session on the server
function end_session(): void
{
    $_SESSION = [];
    $params = session_get_cookie_params();
    setcookie(session_name(), '', ['expires' => time() - 42000, 'path' => $params['path'], 'domain' => $params['domain'],
                                   'secure' => $params['secure'], 'httponly' => $params['httponly'], 'samesite' => $params['samesite']]);
    session_destroy();
}

// Every event page calls this before doing anything. Not logged in → HTTP 401 "Access denied" page (nothing is
// read or changed); idle longer than the timeout → session ended and back to the login page.
function require_admin(): array
{
    start_app();
    $admin = current_admin();
    if ($admin !== null && time() - (int) ($_SESSION['last_activity'] ?? 0) > session_timeout_seconds()) {
        end_session();
        redirect('login.php?status=timeout');
    }
    if ($admin === null) {
        http_response_code(401);
        page_start('Access denied');
        echo '<div class="card border-danger shadow-sm mx-auto access-card">', "\n",
             '  <div class="card-body p-4">', "\n",
             '    <h2 class="h4 text-danger mb-3">Access denied</h2>', "\n",
             '    <p class="mb-2">Event management is restricted to authorized administrators. You are not logged in, so this page was refused by the server (HTTP 401).</p>', "\n",
             '    <p class="text-secondary small mb-4">No event data was shown or changed.</p>', "\n",
             '    <a class="btn btn-primary" href="login.php">Go to administrator login</a>', "\n",
             '  </div>', "\n", '</div>', "\n";
        page_end();
        exit;
    }
    $_SESSION['last_activity'] = time();
    return $admin;
}

// ---------------------------------------------------------------- messages and redirects
function flash(string $type, string $message, ?int $event_id = null): void
{
    $_SESSION['flash'] = ['type' => $type, 'message' => $message, 'event_id' => $event_id];
}

function take_flash(): ?array
{
    $flash = $_SESSION['flash'] ?? null;
    unset($_SESSION['flash']);
    return is_array($flash) ? $flash : null;
}

function render_flash(?array $flash): void
{
    if ($flash) {
        $ok = $flash['type'] === 'success';
        echo '<div class="alert ', $ok ? 'alert-success' : 'alert-danger', '" role="', $ok ? 'status' : 'alert', '">', e($flash['message']), '</div>', "\n";
    }
}

function redirect(string $location): never
{
    header('Location: ' . $location, true, 303);
    exit;
}

// A POST larger than post_max_size arrives with empty $_POST and $_FILES; recognise it instead of
// reporting a confusing CSRF error.
function post_too_large(): bool
{
    return $_SERVER['REQUEST_METHOD'] === 'POST' && empty($_POST) && empty($_FILES)
        && (int) ($_SERVER['CONTENT_LENGTH'] ?? 0) > 0;
}

// ---------------------------------------------------------------- events
// Categories come from the event_categories table (the foreign key target of events.category)
function categories(mysqli $db): array
{
    static $list = null;
    if ($list === null) {
        $stmt = $db->prepare('SELECT category_name FROM event_categories ORDER BY category_name');
        $stmt->execute();
        $list = array_column($stmt->get_result()->fetch_all(MYSQLI_NUM), 0);
    }
    return $list;
}

function find_event(mysqli $db, int $id): ?array
{
    $stmt = $db->prepare('SELECT * FROM events WHERE event_id = ?');
    $stmt->bind_param('i', $id);
    $stmt->execute();
    return $stmt->get_result()->fetch_assoc() ?: null;
}

function positive_id(mixed $value): int
{
    return is_string($value) && ctype_digit($value) && strlen($value) <= 10 ? (int) $value : 0;
}

// Returns [clean data, errors per field]. The HTML form repeats the rules (required, maxlength, type=date/time) for
// early feedback, but only this server-side check is trusted.
function validate_event(array $input, array $categories): array
{
    $text = fn (string $key): string => trim((string) (is_string($input[$key] ?? null) ? $input[$key] : ''));
    $data = [
        'event_title' => preg_replace('/\s+/u', ' ', $text('event_title')) ?? '',
        'description' => str_replace("\r\n", "\n", $text('description')),
        'category'    => $text('category'),
        'event_date'  => $text('event_date'),
        'event_time'  => $text('event_time'),
        'venue'       => preg_replace('/\s+/u', ' ', $text('venue')) ?? '',
        'status'      => $text('status'),
    ];
    $errors = [];

    if ($data['event_title'] === '') {
        $errors['event_title'] = 'Event title is required.';
    } elseif (mb_strlen($data['event_title']) < 3 || mb_strlen($data['event_title']) > TITLE_MAX) {
        $errors['event_title'] = 'The title must be 3–' . TITLE_MAX . ' characters long.';
    }
    if ($data['description'] === '') {
        $errors['description'] = 'Description is required.';
    } elseif (mb_strlen($data['description']) < 10 || mb_strlen($data['description']) > DESCRIPTION_MAX) {
        $errors['description'] = 'The description must be 10–' . DESCRIPTION_MAX . ' characters long.';
    }
    if ($data['category'] === '') {
        $errors['category'] = 'Please select a category.';
    } elseif (!in_array($data['category'], $categories, true)) {
        $errors['category'] = 'Please select a category from the list.';
    }
    $date = DateTime::createFromFormat('!Y-m-d', $data['event_date']);
    if ($data['event_date'] === '') {
        $errors['event_date'] = 'Event date is required.';
    } elseif (!$date || $date->format('Y-m-d') !== $data['event_date'] || $data['event_date'] < '2000-01-01' || $data['event_date'] > '2100-12-31') {
        $errors['event_date'] = 'Enter a valid date (YYYY-MM-DD).';
    }
    if ($data['event_time'] === '') {
        $errors['event_time'] = 'Event time is required.';
    } elseif (!preg_match('/^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$/', $data['event_time'])) {
        $errors['event_time'] = 'Enter a valid time (HH:MM).';
    } else {
        $data['event_time'] = substr($data['event_time'], 0, 5);
    }
    if ($data['venue'] === '') {
        $errors['venue'] = 'Venue is required.';
    } elseif (mb_strlen($data['venue']) < 2 || mb_strlen($data['venue']) > VENUE_MAX) {
        $errors['venue'] = 'The venue must be 2–' . VENUE_MAX . ' characters long.';
    }
    if (!isset(STATUSES[$data['status']])) {
        $errors['status'] = 'Please choose Open or Closed.';
    }
    return [$data, $errors];
}

function status_badge(string $status): string
{
    return '<span class="badge rounded-pill ' . ($status === 'open' ? 'text-bg-success' : 'text-bg-secondary') . '">'
        . e(STATUSES[$status] ?? $status) . '</span>';
}

function poster_url(string $filename): string
{
    return 'poster.php?file=' . rawurlencode($filename);
}

function format_date(string $date): string
{
    return date('D, d M Y', strtotime($date));
}

function format_time(string $time): string
{
    return date('h:i A', strtotime($time));
}

// ---------------------------------------------------------------- layout
function page_start(string $title, string $active = ''): void
{
    $admin = current_admin();
    echo '<!DOCTYPE html>', "\n", '<html lang="en">', "\n", '<head>', "\n",
         '    <meta charset="UTF-8">', "\n",
         '    <meta name="viewport" content="width=device-width, initial-scale=1.0">', "\n",
         '    <title>', e($title), ' - StudentHub Practical 12</title>', "\n",
         '    <link rel="icon" href="assets/favicon.svg" type="image/svg+xml">', "\n",
         '    <link rel="stylesheet" href="assets/vendor/bootstrap.min.css">', "\n",
         '    <link rel="stylesheet" href="assets/app.css">', "\n",
         '    <script src="assets/app.js" defer></script>', "\n",
         '</head>', "\n", '<body class="bg-body-tertiary">', "\n",
         '<nav class="navbar navbar-expand-md navbar-dark app-navbar shadow-sm">', "\n",
         '  <div class="container">', "\n",
         '    <a class="navbar-brand fw-semibold" href="index.php">StudentHub <span class="fw-light">Events</span></a>', "\n";
    if ($admin) {
        $links = ['index.php' => 'All events', 'add.php' => 'Add event'];
        echo '    <div class="navbar-nav me-auto">';
        foreach ($links as $href => $label) {
            echo '<a class="nav-link', $href === $active ? ' active" aria-current="page' : '', '" href="', $href, '">', $label, '</a>';
        }
        echo '</div>', "\n",
             '    <div class="d-flex align-items-center gap-3">', "\n",
             '      <span class="navbar-text text-white small">Admin: <strong>', e($admin['name']), '</strong></span>', "\n",
             '      <form method="post" action="logout.php" class="m-0">', csrf_field(), '<button type="submit" class="btn btn-sm btn-outline-light">Log out</button></form>', "\n",
             '    </div>', "\n";
    }
    echo '  </div>', "\n", '</nav>', "\n",
         '<main class="container py-4" id="main">', "\n",
         '<h1 class="h3 mb-3">', e($title), '</h1>', "\n";
}

function page_end(): void
{
    echo '</main>', "\n",
         '<footer class="container pb-4 text-secondary small">&copy; <time datetime="2026">2026</time> StudentHub – ITUE203 Practical 12 by Shreyas (25CS023). All events and accounts are fictional.</footer>', "\n",
         '</body>', "\n", '</html>', "\n";
}

// The add and edit pages share this form. $event = current values, $errors = messages per field,
// $current_poster = existing poster on the edit page (kept if no new file is chosen).
function event_form(string $action, string $button, array $event, array $errors, array $categories, ?string $current_poster = null): void
{
    $invalid = fn (string $f): string => isset($errors[$f]) ? ' is-invalid' : '';
    $feedback = fn (string $f): string => isset($errors[$f]) ? '<div class="invalid-feedback d-block" id="' . $f . '-error">' . e($errors[$f]) . '</div>' : '';
    $value = fn (string $f): string => e($event[$f] ?? '');
    $poster_help = $current_poster
        ? 'Optional. Leave empty to keep the current poster. JPEG, PNG or WebP, max 2 MB.'
        : 'Required. JPEG, PNG or WebP image, max 2 MB.';
    ?>
<form class="card shadow-sm event-form" method="post" action="<?= e($action) ?>" enctype="multipart/form-data">
  <div class="card-body p-4">
    <?= csrf_field() ?>
<?php if (isset($event['event_id'])): ?>
    <input type="hidden" name="event_id" value="<?= (int) $event['event_id'] ?>">
<?php endif; ?>
    <div class="row g-3">
      <div class="col-md-8">
        <label class="form-label fw-semibold" for="event_title">Event title</label>
        <input class="form-control<?= $invalid('event_title') ?>" id="event_title" name="event_title" required minlength="3" maxlength="<?= TITLE_MAX ?>" value="<?= $value('event_title') ?>">
        <?= $feedback('event_title') ?>
      </div>
      <div class="col-md-4">
        <label class="form-label fw-semibold" for="category">Category</label>
        <select class="form-select<?= $invalid('category') ?>" id="category" name="category" required>
          <option value="">Select a category</option>
<?php foreach ($categories as $category): ?>
          <option value="<?= e($category) ?>"<?= ($event['category'] ?? '') === $category ? ' selected' : '' ?>><?= e($category) ?></option>
<?php endforeach; ?>
        </select>
        <?= $feedback('category') ?>
      </div>
      <div class="col-12">
        <label class="form-label fw-semibold" for="description">Description</label>
        <textarea class="form-control<?= $invalid('description') ?>" id="description" name="description" rows="3" required minlength="10" maxlength="<?= DESCRIPTION_MAX ?>"><?= $value('description') ?></textarea>
        <?= $feedback('description') ?>
      </div>
      <div class="col-sm-6 col-md-3">
        <label class="form-label fw-semibold" for="event_date">Date</label>
        <input class="form-control<?= $invalid('event_date') ?>" type="date" id="event_date" name="event_date" required min="2000-01-01" max="2100-12-31" value="<?= $value('event_date') ?>">
        <?= $feedback('event_date') ?>
      </div>
      <div class="col-sm-6 col-md-3">
        <label class="form-label fw-semibold" for="event_time">Time</label>
        <input class="form-control<?= $invalid('event_time') ?>" type="time" id="event_time" name="event_time" required value="<?= e(substr((string) ($event['event_time'] ?? ''), 0, 5)) ?>">
        <?= $feedback('event_time') ?>
      </div>
      <div class="col-md-4">
        <label class="form-label fw-semibold" for="venue">Venue</label>
        <input class="form-control<?= $invalid('venue') ?>" id="venue" name="venue" required minlength="2" maxlength="<?= VENUE_MAX ?>" value="<?= $value('venue') ?>">
        <?= $feedback('venue') ?>
      </div>
      <div class="col-md-2">
        <span class="form-label fw-semibold d-block">Status</span>
<?php foreach (STATUSES as $key => $label): ?>
        <div class="form-check">
          <input class="form-check-input<?= $invalid('status') ?>" type="radio" name="status" id="status-<?= $key ?>" value="<?= $key ?>"<?= ($event['status'] ?? 'open') === $key ? ' checked' : '' ?>>
          <label class="form-check-label" for="status-<?= $key ?>"><?= $label ?></label>
        </div>
<?php endforeach; ?>
        <?= $feedback('status') ?>
      </div>
      <div class="col-md-8">
        <label class="form-label fw-semibold" for="poster">Event poster</label>
        <input class="form-control<?= $invalid('poster') ?>" type="file" id="poster" name="poster" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"<?= $current_poster ? '' : ' required' ?> aria-describedby="poster-help">
        <div class="form-text" id="poster-help"><?= e($poster_help) ?></div>
        <?= $feedback('poster') ?>
      </div>
      <div class="col-md-4">
        <div class="poster-preview-box">
<?php if ($current_poster): ?>
          <img class="poster-preview" id="poster-preview" src="<?= e(poster_url($current_poster)) ?>" alt="Current poster">
          <div class="small text-secondary text-center mt-1" id="poster-preview-label">Current poster</div>
<?php else: ?>
          <img class="poster-preview d-none" id="poster-preview" alt="Selected poster preview">
          <div class="small text-secondary text-center mt-1" id="poster-preview-label">No poster selected</div>
<?php endif; ?>
        </div>
      </div>
    </div>
    <div class="d-flex gap-2 mt-4">
      <button type="submit" class="btn btn-primary"><?= e($button) ?></button>
      <a class="btn btn-outline-secondary" href="index.php">Cancel</a>
    </div>
  </div>
</form>
<?php
}
