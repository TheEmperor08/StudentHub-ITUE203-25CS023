<?php
// StudentHub – Practical 10: secure session, CSRF token, inactivity timeout, role checks and page layout.
// Every protected page calls require_login() or require_role() before it outputs anything.
declare(strict_types=1);

require_once dirname(__DIR__) . '/db.php';

const ROLES = ['admin' => 'Admin', 'student' => 'Student'];
const ROLE_DASHBOARDS = ['admin' => 'admin_dashboard.php', 'student' => 'student_dashboard.php'];

function e(mixed $value): string
{
    return htmlspecialchars((string) $value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

// Session cookie: not readable by JavaScript, not sent with requests from other sites, HTTPS-only when the
// page uses HTTPS; only session IDs created by the server are accepted (strict mode).
function start_secure_session(): void
{
    if (session_status() === PHP_SESSION_ACTIVE) {
        return;
    }
    ini_set('session.use_strict_mode', '1');
    ini_set('session.use_only_cookies', '1');
    ini_set('session.use_trans_sid', '0');
    session_name('P10SESSID');
    session_set_cookie_params([
        'lifetime' => 0,
        'path'     => '/',
        'secure'   => !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off',
        'httponly' => true,
        'samesite' => 'Strict',
    ]);
    session_start();
}

// Security headers for every page. no-store also stops the browser from showing a protected page from its
// cache (for example with the Back button) after logout: it must ask the server again, which refuses.
function send_security_headers(): void
{
    header("Content-Security-Policy: default-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'; object-src 'none'");
    header('X-Frame-Options: DENY');
    header('X-Content-Type-Options: nosniff');
    header('Referrer-Policy: same-origin');
    header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0, private');
    header('Pragma: no-cache');
    header('Expires: 0');
}

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

function redirect(string $location): never
{
    header('Location: ' . $location, true, 303);
    exit;
}

function session_timeout_seconds(): int
{
    return max(1, (int) app_config()['session_timeout']);
}

function current_user(): ?array
{
    $user = $_SESSION['user'] ?? null;
    return is_array($user) && isset($user['id'], $user['name'], $user['role'], ROLES[$user['role']]) ? $user : null;
}

function session_has_expired(): bool
{
    $last = $_SESSION['last_activity'] ?? null;
    return !is_int($last) || time() - $last > session_timeout_seconds();
}

// Clears the session data, expires the session cookie in the browser and deletes the session on the server
function end_session(): void
{
    $_SESSION = [];
    $params = session_get_cookie_params();
    setcookie(session_name(), '', [
        'expires' => time() - 42000, 'path' => $params['path'], 'domain' => $params['domain'],
        'secure' => $params['secure'], 'httponly' => $params['httponly'], 'samesite' => $params['samesite'],
    ]);
    session_destroy();
}

// Protected pages: not logged in → login page; inactive too long → timeout.php; otherwise the activity
// time is renewed. Returns the logged-in user (id, name, email, role) taken from the session, never from the browser.
function require_login(): array
{
    start_secure_session();
    send_security_headers();
    $user = current_user();
    if ($user === null) {
        redirect('login.php?status=login_required');
    }
    if (session_has_expired()) {
        redirect('timeout.php');
    }
    $_SESSION['last_activity'] = time();
    return $user;
}

// Like require_login(), but a logged-in user with another role receives HTTP 403 "Unauthorized Access"
function require_role(string $role): array
{
    $user = require_login();
    if ($user['role'] !== $role) {
        http_response_code(403);
        page_start('Unauthorized Access', $user);
        echo '<section class="card alert-card" role="alert">', "\n",
             '    <h2 class="denied-title">Unauthorized Access</h2>', "\n",
             '    <p>Your account (role: <strong>', e(ROLES[$user['role']]), '</strong>) is not allowed to open the ',
             e(ROLES[$role]), ' dashboard. The request was refused by the server (HTTP 403).</p>', "\n",
             '    <p><a class="button" href="', e(ROLE_DASHBOARDS[$user['role']]), '">Go to your ',
             e(ROLES[$user['role']]), ' dashboard</a></p>', "\n",
             '</section>', "\n";
        page_end();
        exit;
    }
    return $user;
}

// Shared page layout. On protected pages a meta refresh opens timeout.php one second after the inactivity
// limit, so an idle page returns to the login page by itself.
function page_start(string $title, ?array $user = null): void
{
    $refresh = $user ? '    <meta http-equiv="refresh" content="' . (session_timeout_seconds() + 1) . ';url=timeout.php">' . "\n" : '';
    echo '<!DOCTYPE html>', "\n", '<html lang="en">', "\n", '<head>', "\n",
         '    <meta charset="UTF-8">', "\n",
         '    <meta name="viewport" content="width=device-width, initial-scale=1.0">', "\n",
         $refresh,
         '    <title>', e($title), ' - StudentHub Practical 10</title>', "\n",
         '    <link rel="icon" href="favicon.svg" type="image/svg+xml">', "\n",
         '    <link rel="stylesheet" href="style.css">', "\n",
         '</head>', "\n", '<body>', "\n",
         '<header class="site-header">', "\n", '    <div class="container header-row">', "\n",
         '        <div>', "\n",
         '            <p class="brand">StudentHub · Practical 10</p>', "\n",
         '            <h1>', e($title), '</h1>', "\n",
         '        </div>', "\n";
    if ($user) {
        echo '        <div class="user-box">', "\n",
             '            <span>', e($user['name']), ' <span class="badge badge-', e($user['role']), '">', e(ROLES[$user['role']]), '</span></span>', "\n",
             '            <nav aria-label="Account"><a href="dashboard.php">Dashboard</a> <a href="', e(ROLE_DASHBOARDS[$user['role']]), '">', e(ROLES[$user['role']]), ' area</a></nav>', "\n",
             '            <form action="logout.php" method="post"><input type="hidden" name="csrf_token" value="', e(csrf_token()), '"><button type="submit" class="button-small">Log out</button></form>', "\n",
             '        </div>', "\n";
    }
    echo '    </div>', "\n", '</header>', "\n", '<main class="container" id="main">', "\n";
}

function page_end(): void
{
    echo '</main>', "\n",
         '<footer class="site-footer"><div class="container"><p>&copy; <time datetime="2026">2026</time> StudentHub – ITUE203 Practical 10 by Shreyas (25CS023). Demo accounts are fictional.</p></div></footer>', "\n",
         '</body>', "\n", '</html>', "\n";
}
