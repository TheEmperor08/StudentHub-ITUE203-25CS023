<?php
// StudentHub – Practical 10: checks the login form. The user is looked up by email with a MySQLi prepared
// statement and the password is checked with password_verify(). On success the session ID is regenerated and
// the user's ID, name and role (taken from the database, never from the browser) are stored in the session.
declare(strict_types=1);

require __DIR__ . '/includes/auth.php';

start_secure_session();
send_security_headers();

if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'POST') {
    redirect('login.php');
}
if (!csrf_is_valid($_POST['csrf_token'] ?? null)) {
    redirect('login.php?status=expired');
}

$email = is_string($_POST['email'] ?? null) ? trim($_POST['email']) : '';
$password = is_string($_POST['password'] ?? null) ? $_POST['password'] : '';
// Same generic message for every failure, so the page never reveals whether an email address is registered
if ($email === '' || $password === '' || strlen($email) > 254 || strlen($password) > 72) {
    redirect('login.php?status=invalid');
}

try {
    $stmt = get_db()->prepare('SELECT user_id, name, email, password_hash, role FROM users WHERE email = ? LIMIT 1');
    $stmt->bind_param('s', $email);
    $stmt->execute();
    $row = $stmt->get_result()->fetch_assoc();
    $stmt->close();
} catch (RuntimeException $exception) {          // includes mysqli_sql_exception; connection errors are logged in db.php
    if ($exception instanceof mysqli_sql_exception) {
        error_log('Practical 10 login query failed: [' . $exception->getCode() . '] ' . $exception->getMessage());
    }
    redirect('login.php?status=unavailable');
}

// For an unknown email a dummy hash is checked, so both failures take about the same time
$hash = $row['password_hash'] ?? '$2y$10$0000000000000000000000.000000000000000000000000000000';
if (!password_verify($password, $hash) || $row === null) {
    redirect('login.php?status=invalid');
}

// Successful login: new session ID (the old one is deleted), so an ID known before login is useless
$oldId = session_id();
session_regenerate_id(true);
$_SESSION['user'] = ['id' => (int) $row['user_id'], 'name' => $row['name'], 'email' => $row['email'], 'role' => $row['role']];
$_SESSION['last_activity'] = time();
$_SESSION['login_time'] = time();
// Evidence for the dashboard: short SHA-256 fingerprints of the old and new ID (not the IDs themselves)
$_SESSION['id_check'] = ['before' => substr(hash('sha256', $oldId), 0, 12), 'after' => substr(hash('sha256', session_id()), 0, 12)];
$_SESSION['csrf_token'] = bin2hex(random_bytes(32));

redirect(ROLE_DASHBOARDS[$row['role']]);
