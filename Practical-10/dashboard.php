<?php
// StudentHub – Practical 10: main dashboard for every logged-in user. require_login() checks the session and
// the inactivity timeout on the server before anything is shown.
declare(strict_types=1);

require __DIR__ . '/includes/auth.php';

$user = require_login();
$idCheck = $_SESSION['id_check'] ?? null;
$timeout = session_timeout_seconds();

page_start('Dashboard', $user);
?>
<section class="card">
    <h2>Welcome, <?= e($user['name']) ?></h2>
    <p>You are logged in as <strong><?= e($user['email']) ?></strong> with the role <span class="badge badge-<?= e($user['role']) ?>"><?= e(ROLES[$user['role']]) ?></span>.</p>
    <p><a class="button" href="<?= e(ROLE_DASHBOARDS[$user['role']]) ?>">Open the <?= e(ROLES[$user['role']]) ?> dashboard</a></p>
</section>

<section class="card">
    <h2>Session security</h2>
    <dl class="details">
        <dt>Logged in at</dt><dd><?= e(date('Y-m-d H:i:s', (int) ($_SESSION['login_time'] ?? time()))) ?></dd>
        <dt>Inactivity timeout</dt><dd><?= e($timeout) ?> seconds – after that the next request (or this page, automatically) goes to timeout.php and the session ends</dd>
<?php if (is_array($idCheck)): ?>
        <dt>Session ID regenerated</dt>
        <dd><?= $idCheck['before'] !== $idCheck['after'] ? '<strong class="ok">Yes</strong> – the ID used before login was replaced and deleted' : '<strong class="bad">No</strong>' ?><br>
            <span class="hint">SHA-256 fingerprint before login <code><?= e($idCheck['before']) ?>…</code> → after login <code><?= e($idCheck['after']) ?>…</code> (the IDs themselves are never shown)</span></dd>
<?php endif; ?>
        <dt>Role source</dt><dd>users table (checked on the server for every protected page)</dd>
    </dl>
</section>
<?php
page_end();
