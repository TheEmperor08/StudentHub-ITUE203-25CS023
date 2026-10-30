<?php
// StudentHub – Practical 12: secure logout. Only a POST with the CSRF token logs out (another site cannot log the
// administrator out); the session data, the cookie and the server-side session are all removed.
declare(strict_types=1);
require_once __DIR__ . '/includes/functions.php';

start_app();
if ($_SERVER['REQUEST_METHOD'] !== 'POST' || !csrf_is_valid($_POST['csrf_token'] ?? null)) {
    redirect(current_admin() ? 'index.php' : 'login.php');
}
end_session();
redirect('login.php?status=logged_out');
