<?php
// StudentHub – the one authentication and authorisation system of the portal (Practicals 9 and 10 integrated).
//
//   start_secure_session()   session cookie STUDENTHUBSESSID: HttpOnly, SameSite=Strict, Secure on HTTPS, strict mode
//   require_login()          logged in, not idle longer than the timeout, account still exists (re-read every request)
//   require_permission($p)   require_login() + role check; otherwise HTTP 403 page and an audit-log entry
//   optional_user()          for public pages: the user if a valid session exists, else null (never redirects)
//   csrf_field() / require_valid_csrf()   token for every state-changing POST form
//   login_user() / end_session()           session ID regeneration at login, complete removal at logout
//
// Session keys (unchanged from the existing portal): user_id, username, email, role, plus last_activity and csrf_token.
// Roles stay exactly admin, editor and student; permissions are listed explicitly below.

require_once dirname(__DIR__) . '/db.php';
require_once dirname(__DIR__) . '/audit_logger.php';

const STUDENTHUB_ROLES = ['admin', 'editor', 'student'];

// Every permission and the roles that hold it. An editor has only what is listed here (no admin rights).
const STUDENTHUB_PERMISSIONS = [
    'portal.view'     => ['admin', 'editor', 'student'],   // dashboard, profile, academic and campus pages
    'admin.console'   => ['admin'],                        // Admin Console (admin_dashboard.php)
    'students.manage' => ['admin'],
    'events.manage'   => ['admin'],
    'users.manage'    => ['admin'],
    'audit.view'      => ['admin'],
];

function e($value): string
{
    return htmlspecialchars((string) $value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function role_can(?string $role, string $permission): bool
{
    return $role !== null && in_array($role, STUDENTHUB_PERMISSIONS[$permission] ?? [], true);
}

// Inactivity timeout in seconds (default 30 minutes; STUDENTHUB_SESSION_TIMEOUT overrides it, e.g. for tests)
function session_timeout_seconds(): int
{
    $value = (int) (getenv('STUDENTHUB_SESSION_TIMEOUT') ?: 1800);
    return max(1, $value);
}

function start_secure_session(): void
{
    if (session_status() === PHP_SESSION_ACTIVE) {
        return;
    }
    ini_set('session.use_strict_mode', '1');      // IDs not created by this server are refused
    ini_set('session.use_only_cookies', '1');     // never accept a session ID from the URL
    ini_set('session.use_trans_sid', '0');
    session_name('STUDENTHUBSESSID');
    session_set_cookie_params([
        'lifetime' => 0,
        'path'     => '/',
        'secure'   => !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off',
        'httponly' => true,
        'samesite' => 'Strict',
    ]);
    session_start();
}

// Security headers. Private pages are also kept out of the browser cache, so the Back button cannot show them after logout.
function send_security_headers(bool $private): void
{
    if (headers_sent()) {
        return;
    }
    header('X-Frame-Options: DENY');
    header('X-Content-Type-Options: nosniff');
    header('Referrer-Policy: same-origin');
    if ($private) {
        header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0, private');
        header('Pragma: no-cache');
    }
}

// ---------------------------------------------------------------- CSRF
function csrf_token(): string
{
    if (!isset($_SESSION['csrf_token']) || !is_string($_SESSION['csrf_token'])) {
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['csrf_token'];
}

function csrf_field(): string
{
    return '<input type="hidden" name="csrf_token" value="' . e(csrf_token()) . '">';
}

function csrf_is_valid($submitted): bool
{
    $expected = $_SESSION['csrf_token'] ?? null;
    return is_string($expected) && is_string($submitted) && $submitted !== '' && hash_equals($expected, $submitted);
}

// For POST handlers: a missing or wrong token stops the request (HTTP 403) and is written to the audit log
function require_valid_csrf(): void
{
    if (csrf_is_valid($_POST['csrf_token'] ?? null)) {
        return;
    }
    global $conn;
    log_audit($conn, isset($_SESSION['user_id']) ? (int) $_SESSION['user_id'] : null, $_SESSION['username'] ?? 'guest',
        'CSRF_REJECTED', 'POST to ' . basename($_SERVER['SCRIPT_NAME'] ?? '') . ' without a valid token', 'SECURITY_BLOCK');
    studenthub_fail(403, 'Security check failed', 'This form has expired or was not sent from StudentHub. Go back, reload the page and try again. Nothing was changed.');
    exit;
}

// ---------------------------------------------------------------- messages and redirects
function flash(string $type, string $message): void
{
    $_SESSION['flash'] = ['type' => $type === 'success' ? 'success' : 'error', 'message' => $message];
}

function take_flash(): ?array
{
    $flash = $_SESSION['flash'] ?? null;
    unset($_SESSION['flash']);
    return is_array($flash) ? $flash : null;
}

// Redirects only to a page of this portal (a relative path such as "dashboard.php?tab=x"); anything else goes home
function redirect(string $location): void
{
    if (!preg_match('#^[A-Za-z0-9_\-]+\.php(\?[A-Za-z0-9_\-=&%.]*)?$#', $location)) {
        $location = 'index.php';
    }
    header('Location: ' . $location, true, 303);
    exit;
}

// ---------------------------------------------------------------- session lifecycle
function current_user(): ?array
{
    if (!isset($_SESSION['user_id'], $_SESSION['username'], $_SESSION['role']) || !in_array($_SESSION['role'], STUDENTHUB_ROLES, true)) {
        return null;
    }
    return ['id' => (int) $_SESSION['user_id'], 'username' => (string) $_SESSION['username'],
            'email' => (string) ($_SESSION['email'] ?? ''), 'role' => (string) $_SESSION['role']];
}

function session_has_expired(): bool
{
    $last = $_SESSION['last_activity'] ?? null;
    return !is_int($last) || time() - $last > session_timeout_seconds();
}

// Empties the session and gives it a new ID (used when a session is no longer valid)
function reset_session(): void
{
    $_SESSION = [];
    session_regenerate_id(true);
}

// Logout: clears the data, expires the cookie in the browser and deletes the session on the server
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

// Successful login or registration: new session ID (session fixation), new CSRF token, details from the database
function login_user(array $account): void
{
    $_SESSION = [];
    session_regenerate_id(true);
    $_SESSION['user_id']       = (int) $account['id'];
    $_SESSION['username']      = (string) $account['username'];
    $_SESSION['email']         = (string) $account['email'];
    $_SESSION['role']          = (string) $account['role'];
    $_SESSION['last_activity'] = time();
    $_SESSION['csrf_token']    = bin2hex(random_bytes(32));
}

// A student account whose linked student record (students.user_id) was deactivated in the Admin Console (Practical 11
// soft delete) may neither sign in nor keep a session. Admin and editor accounts and student accounts without a linked
// record are not affected. "Inactive" is matched like everywhere else in the portal (trimmed, any letter case).
function account_is_deactivated(string $role, ?string $student_status): bool
{
    return $role === 'student' && $student_status !== null && strcasecmp(trim($student_status), 'Inactive') === 0;
}

// Why an account may not sign in or keep a session (null = allowed): an account disabled by an administrator (users.status,
// Practical 14, any role) or a student account whose linked student record is inactive (Practical 11)
function account_block_reason(array $row): ?string
{
    if (($row['account_status'] ?? 'active') === 'disabled') {
        return 'the account is disabled';
    }
    return account_is_deactivated((string) $row['role'], $row['student_status'] ?? null) ? 'the linked student record is inactive' : null;
}

// Re-reads the account on every request: a deleted account loses access at once, a role change applies immediately and a
// disabled account or deactivated student is signed out. Returns [user or null, reason ('account_unavailable' or
// 'access_disabled'), detail for the audit log].
function refresh_user_from_database(array $user): array
{
    global $conn;
    $stmt = $conn->prepare('SELECT u.id, u.username, u.email, u.role, u.status AS account_status, s.status AS student_status
                            FROM users u LEFT JOIN students s ON s.user_id = u.id WHERE u.id = ?');
    $stmt->bind_param('i', $user['id']);
    $stmt->execute();
    $row = $stmt->get_result()->fetch_assoc();
    $stmt->close();
    if (!$row || !in_array($row['role'], STUDENTHUB_ROLES, true)) {
        return [null, 'account_unavailable', ''];
    }
    if (($block = account_block_reason($row)) !== null) {
        return [null, 'access_disabled', $block];
    }
    $_SESSION['username'] = $row['username'];
    $_SESSION['email']    = $row['email'];
    $_SESSION['role']     = $row['role'];
    return [['id' => (int) $row['id'], 'username' => $row['username'], 'email' => $row['email'], 'role' => $row['role']], '', ''];
}

// Returns [user or null, reason]: reason is '' (valid or no session), 'timeout', 'account_unavailable' or 'access_disabled'
function validate_session(): array
{
    $user = current_user();
    if ($user === null) {
        return [null, ''];
    }
    if (session_has_expired()) {
        global $conn;
        log_audit($conn, $user['id'], $user['username'], 'SESSION_TIMEOUT', 'Session ended after ' . session_timeout_seconds() . ' s of inactivity.', 'INFO');
        reset_session();
        return [null, 'timeout'];
    }
    [$fresh, $reason, $detail] = refresh_user_from_database($user);
    if ($fresh === null) {
        if ($reason === 'access_disabled') {
            global $conn;
            log_audit($conn, $user['id'], $user['username'], 'SESSION_REVOKED', "Session ended: $detail.", 'SECURITY_BLOCK');
        }
        reset_session();                                 // session data deleted on the server, new empty session ID
        return [null, $reason];
    }
    $_SESSION['last_activity'] = time();
    return [$fresh, ''];
}

// Public pages (home, login, register, contact): the user if a valid session exists, otherwise null
function optional_user(): ?array
{
    start_secure_session();
    send_security_headers(false);
    return validate_session()[0];
}

function require_login(): array
{
    start_secure_session();
    send_security_headers(true);
    [$user, $reason] = validate_session();
    if ($user === null) {
        redirect('login.php?status=' . ($reason !== '' ? $reason : 'login_required'));
    }
    return $user;
}

function require_permission(string $permission): array
{
    $user = require_login();
    if (!role_can($user['role'], $permission)) {
        global $conn;
        log_audit($conn, $user['id'], $user['username'], 'ACCESS_DENIED',
            "Role '{$user['role']}' lacks permission '$permission' for " . basename($_SERVER['SCRIPT_NAME'] ?? ''), 'SECURITY_BLOCK');
        include dirname(__DIR__) . '/403.php';
        exit;
    }
    return $user;
}

// Logout is a POST form with the CSRF token (a link or image on another site cannot log the user out)
function logout_button(string $button_class = '', string $label = 'Logout', string $icon = 'bi-box-arrow-right'): string
{
    return '<form method="post" action="logout.php" class="logout-form">' . csrf_field()
        . '<button type="submit" class="' . e($button_class) . '"><i class="bi ' . e($icon) . '" aria-hidden="true"></i> <span>' . e($label) . '</span></button></form>';
}

// ---------------------------------------------------------------- password policy (Practical 9)
function password_problems(string $password): array
{
    $problems = [];
    if (mb_strlen($password, 'UTF-8') < 8) {
        $problems[] = 'at least 8 characters';
    }
    if (strlen($password) > 72) {                       // bcrypt uses only the first 72 bytes
        $problems[] = 'at most 72 characters';
    }
    if (!preg_match('/[A-Z]/', $password)) {
        $problems[] = 'an uppercase letter';
    }
    if (!preg_match('/[a-z]/', $password)) {
        $problems[] = 'a lowercase letter';
    }
    if (!preg_match('/[0-9]/', $password)) {
        $problems[] = 'a number';
    }
    if (!preg_match('/[^A-Za-z0-9]/', $password)) {
        $problems[] = 'a special character such as ! @ # ?';
    }
    return $problems;
}

const PASSWORD_POLICY_TEXT = 'At least 8 characters (max. 72) with an uppercase letter, a lowercase letter, a number and a special character.';
