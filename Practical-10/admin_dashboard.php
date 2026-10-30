<?php
// StudentHub – Practical 10: Admin dashboard. require_role('admin') lets only logged-in Admin users in;
// a Student receives HTTP 403 "Unauthorized Access" and a visitor who is not logged in goes to the login page.
declare(strict_types=1);

require __DIR__ . '/includes/auth.php';

$user = require_role('admin');

$accounts = null;
try {
    $stmt = get_db()->prepare('SELECT user_id, name, email, role, created_at FROM users ORDER BY role, user_id');
    $stmt->execute();
    $accounts = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
    $stmt->close();
} catch (RuntimeException $exception) {
    if ($exception instanceof mysqli_sql_exception) {
        error_log('Practical 10 admin dashboard query failed: [' . $exception->getCode() . '] ' . $exception->getMessage());
    }
}
$counts = ['admin' => 0, 'student' => 0];
foreach ($accounts ?? [] as $account) {
    $counts[$account['role']]++;
}

page_start('Admin Dashboard', $user);
?>
<section class="card">
    <h2>Admin area</h2>
    <p>Welcome, <?= e($user['name']) ?>. Only accounts with the role <strong>Admin</strong> can open this page.</p>
    <div class="stats">
        <div class="stat"><span class="stat-value"><?= $accounts === null ? '–' : count($accounts) ?></span><span class="stat-label">Accounts</span></div>
        <div class="stat"><span class="stat-value"><?= $accounts === null ? '–' : $counts['admin'] ?></span><span class="stat-label">Admins</span></div>
        <div class="stat"><span class="stat-value"><?= $accounts === null ? '–' : $counts['student'] ?></span><span class="stat-label">Students</span></div>
    </div>
</section>

<section class="card">
    <h2>Registered users and roles</h2>
<?php if ($accounts === null): ?>
    <div class="alert alert-error" role="alert">The user list could not be loaded right now.</div>
<?php else: ?>
    <div class="table-wrap">
        <table>
            <thead><tr><th scope="col">ID</th><th scope="col">Name</th><th scope="col">Email</th><th scope="col">Role</th><th scope="col">Created</th></tr></thead>
            <tbody>
<?php foreach ($accounts as $account): ?>
                <tr><td><?= e($account['user_id']) ?></td><td><?= e($account['name']) ?></td><td><?= e($account['email']) ?></td><td><span class="badge badge-<?= e($account['role']) ?>"><?= e(ROLES[$account['role']]) ?></span></td><td><?= e($account['created_at']) ?></td></tr>
<?php endforeach; ?>
            </tbody>
        </table>
    </div>
<?php endif; ?>
</section>
<?php
page_end();
