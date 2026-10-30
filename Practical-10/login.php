<?php
// StudentHub – Practical 10: login form (email and password). The form is sent to authenticate.php.
declare(strict_types=1);

require __DIR__ . '/includes/auth.php';

start_secure_session();
send_security_headers();

// Already logged in (and not timed out): go straight to the dashboard
if (current_user() !== null && !session_has_expired()) {
    redirect('dashboard.php');
}

// Fixed messages selected by a code, so no text from the address is ever shown in the page
$timeout = session_timeout_seconds();
$timeoutText = $timeout % 60 === 0 ? ($timeout / 60) . ' minute' . ($timeout === 60 ? '' : 's') : $timeout . ' seconds';
$messages = [
    'invalid'        => ['error', 'Invalid email or password.'],
    'login_required' => ['info', 'Please log in to continue.'],
    'logged_out'     => ['success', 'You have been logged out successfully.'],
    'timeout'        => ['warning', "Your session expired after $timeoutText of inactivity. Please log in again."],
    'expired'        => ['warning', 'The login form expired. Please try again.'],
    'unavailable'    => ['error', 'Login is not available right now. Please try again later.'],
];
$status = is_string($_GET['status'] ?? null) ? $_GET['status'] : '';
$message = $messages[$status] ?? null;

page_start('Log in');
?>
<section class="card login-card" aria-labelledby="login-title">
    <h2 id="login-title">Log in to StudentHub</h2>
    <p class="hint">Use the email address and password of your account.</p>
<?php if ($message): ?>
    <div class="alert alert-<?= e($message[0]) ?>" role="<?= $message[0] === 'error' ? 'alert' : 'status' ?>"><?= e($message[1]) ?></div>
<?php endif; ?>
    <form action="authenticate.php" method="post" class="login-form">
        <input type="hidden" name="csrf_token" value="<?= e(csrf_token()) ?>">
        <label for="email">Email address</label>
        <input type="email" id="email" name="email" required maxlength="254" autocomplete="username" autofocus>
        <label for="password">Password</label>
        <input type="password" id="password" name="password" required maxlength="72" autocomplete="current-password">
        <button type="submit">Log in</button>
    </form>
</section>
<?php
page_end();
