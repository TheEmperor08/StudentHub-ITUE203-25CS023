<?php
// StudentHub – Practical 12: administrator login. GET shows the form; POST checks the CSRF token, looks the email up
// in the admins table with a prepared statement and verifies the password with password_verify(). After a
// successful login the session ID is regenerated (protection against session fixation).
declare(strict_types=1);
require_once __DIR__ . '/includes/functions.php';

start_app();
if (current_admin() !== null) {
    redirect('index.php');
}

const LOGIN_MESSAGES = [
    'invalid'    => ['danger', 'Invalid email or password.'],
    'csrf'       => ['danger', 'The login form expired. Please try again.'],
    'logged_out' => ['success', 'You have been logged out successfully.'],
    'timeout'    => ['warning', 'Your session expired after 30 minutes of inactivity. Please log in again.'],
];
$status = is_string($_GET['status'] ?? null) ? $_GET['status'] : '';
$email = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $email = strtolower(trim((string) (is_string($_POST['email'] ?? null) ? $_POST['email'] : '')));
    $password = is_string($_POST['password'] ?? null) ? $_POST['password'] : '';
    if (!csrf_is_valid($_POST['csrf_token'] ?? null)) {
        $status = 'csrf';
    } else {
        $stmt = get_db()->prepare('SELECT admin_id, full_name, email, password_hash FROM admins WHERE email = ?');
        $stmt->bind_param('s', $email);
        $stmt->execute();
        $row = $stmt->get_result()->fetch_assoc();
        // An unknown email is checked against a dummy hash, so both failures take about the same time
        $hash = $row['password_hash'] ?? '$2y$10$qAzAl/cRo1Zi1CMFWjkd6uXqfnlXMCb8ADDDWVXGEfMWXNVeKN7Pa';
        $verified = password_verify($password, $hash);          // always runs, also for an unknown email
        if ($verified && $row !== null && $email !== '' && $password !== '') {
            session_regenerate_id(true);
            $_SESSION = [
                'admin'         => ['id' => (int) $row['admin_id'], 'name' => $row['full_name'], 'email' => $row['email']],
                'last_activity' => time(),
                'csrf_token'    => bin2hex(random_bytes(32)),       // new token for the new session
            ];
            $update = get_db()->prepare('UPDATE admins SET last_login_at = NOW() WHERE admin_id = ?');
            $update->bind_param('i', $_SESSION['admin']['id']);
            $update->execute();
            flash('success', 'Welcome, ' . $row['full_name'] . '. You are logged in as administrator.');
            redirect('index.php');
        }
        $status = 'invalid';
    }
    http_response_code(401);
}

page_start('Administrator login');
?>
<div class="card shadow-sm mx-auto login-card">
  <div class="card-body p-4">
    <p class="text-secondary">Sign in with an administrator account to manage events.</p>
<?php if (isset(LOGIN_MESSAGES[$status])): [$kind, $text] = LOGIN_MESSAGES[$status]; ?>
    <div class="alert alert-<?= $kind ?>" role="<?= $kind === 'success' ? 'status' : 'alert' ?>"><?= e($text) ?></div>
<?php endif; ?>
    <form method="post" action="login.php">
      <?= csrf_field() ?>
      <div class="mb-3">
        <label class="form-label fw-semibold" for="email">Email</label>
        <input class="form-control" type="email" id="email" name="email" required maxlength="254" autocomplete="username" value="<?= e($email) ?>">
      </div>
      <div class="mb-3">
        <label class="form-label fw-semibold" for="password">Password</label>
        <input class="form-control" type="password" id="password" name="password" required maxlength="72" autocomplete="current-password">
      </div>
      <button type="submit" class="btn btn-primary w-100">Log in</button>
    </form>
    <p class="small text-secondary mt-3 mb-0">Demo account: <code>admin.demo@example.com</code> – set its password with <code>tools\set_admin_password.php</code> (see README).</p>
  </div>
</div>
<?php page_end(); ?>
