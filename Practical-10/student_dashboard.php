<?php
// StudentHub – Practical 10: Student dashboard. require_role('student') lets only logged-in Student users in;
// an Admin receives HTTP 403 "Unauthorized Access" and a visitor who is not logged in goes to the login page.
declare(strict_types=1);

require __DIR__ . '/includes/auth.php';

$user = require_role('student');

page_start('Student Dashboard', $user);
?>
<section class="card">
    <h2>Student area</h2>
    <p>Welcome, <?= e($user['name']) ?>. Only accounts with the role <strong>Student</strong> can open this page.</p>
    <dl class="details">
        <dt>Name</dt><dd><?= e($user['name']) ?></dd>
        <dt>Email</dt><dd><?= e($user['email']) ?></dd>
        <dt>Role</dt><dd><span class="badge badge-student">Student</span></dd>
    </dl>
</section>

<section class="card">
    <h2>Notices <span class="hint">(sample content)</span></h2>
    <ul class="notices">
        <li><strong>Library:</strong> extended opening hours during the examination weeks.</li>
        <li><strong>Events:</strong> registrations for the coding club workshop are open.</li>
        <li><strong>Reminder:</strong> log out when you use a shared computer.</li>
    </ul>
</section>
<?php
page_end();
