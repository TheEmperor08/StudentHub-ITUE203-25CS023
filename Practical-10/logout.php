<?php
// StudentHub – Practical 10: secure logout. Only a POST with the session's CSRF token logs out (so another
// website cannot log the user out). The session data is cleared, the session cookie is expired and the
// session is destroyed on the server; the browser is then sent to the login page.
declare(strict_types=1);

require __DIR__ . '/includes/auth.php';

start_secure_session();
send_security_headers();

if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'POST' || !csrf_is_valid($_POST['csrf_token'] ?? null)) {
    redirect(current_user() !== null ? 'dashboard.php' : 'login.php');
}
end_session();
redirect('login.php?status=logged_out');
