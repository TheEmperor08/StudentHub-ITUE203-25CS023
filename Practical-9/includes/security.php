<?php
// StudentHub – Practical 9: session, CSRF token, security headers and output escaping.
declare(strict_types=1);

// Escapes a value for HTML output (text and attribute values)
function e(mixed $value): string
{
    return htmlspecialchars((string) $value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

// Starts the session with safe cookie settings: not readable by JavaScript, not sent with requests from
// other sites, sent only over HTTPS when the page uses HTTPS, and only session IDs created by the server.
function start_secure_session(): void
{
    if (session_status() === PHP_SESSION_ACTIVE) {
        return;
    }
    ini_set('session.use_strict_mode', '1');
    ini_set('session.use_only_cookies', '1');
    ini_set('session.use_trans_sid', '0');
    $https = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off');
    session_name('P9SESSID');
    session_set_cookie_params([
        'lifetime' => 0,
        'path'     => '/',
        'secure'   => $https,
        'httponly' => true,
        'samesite' => 'Strict',
    ]);
    session_start();
}

// Headers sent with every page: no framing (clickjacking), no MIME sniffing, scripts and styles only
// from this site, and no referrer sent to other sites.
function send_security_headers(): void
{
    header("Content-Security-Policy: default-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'; object-src 'none'");
    header('X-Frame-Options: DENY');
    header('X-Content-Type-Options: nosniff');
    header('Referrer-Policy: same-origin');
    header('Cache-Control: no-store');
}

// One random token per session (32 bytes from random_bytes, written as 64 hex characters)
function csrf_token(): string
{
    if (!isset($_SESSION['csrf_token']) || !is_string($_SESSION['csrf_token'])) {
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['csrf_token'];
}

// A request is accepted only if it sends exactly the token stored in this session.
// hash_equals() compares in constant time, so the comparison does not reveal how many characters matched.
function csrf_is_valid(mixed $submitted): bool
{
    $expected = $_SESSION['csrf_token'] ?? null;
    return is_string($expected) && is_string($submitted) && $submitted !== ''
        && hash_equals($expected, $submitted);
}

// New token after a successful registration, so an old copy of the form cannot be submitted again
function csrf_rotate(): void
{
    $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
}
