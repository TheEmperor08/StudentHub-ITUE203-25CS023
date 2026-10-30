<?php
// Shared "403 Forbidden" page. require_permission() (includes/auth.php) shows it after logging the denied attempt.
require_once __DIR__ . "/includes/auth.php";
start_secure_session();
send_security_headers(true);
http_response_code(403);

$username     = $_SESSION["username"] ?? "Guest";
$role         = $_SESSION["role"] ?? "unauthenticated";
$is_signed_in = isset($_SESSION["user_id"]);
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>403 Forbidden - Access Restricted | StudentHub</title>
    <link rel="stylesheet" href="assets/css/auth.css?v=3">
    <script src="assets/js/theme.js"></script>
</head>
<body class="auth">

<aside class="auth-brand">
    <a class="auth-logo" href="index.php">
        <span class="brand-mark" aria-hidden="true"><i class="bi bi-mortarboard-fill"></i></span>
        <span>StudentHub</span>
    </a>
    <div class="auth-pitch">
        <p class="eyebrow">Role-based access control</p>
        <h2>This area is for administrators only.</h2>
        <p>Every request is checked against your account role on the server.</p>
    </div>
    <p class="auth-foot">CSPIT · CHARUSAT</p>
</aside>

<main class="auth-main">
    <div class="auth-card">
        <div class="denied-icon" aria-hidden="true"><i class="bi bi-shield-slash"></i></div>
        <span class="badge badge-danger status-pill">HTTP 403 Forbidden</span>
        <h1>Access Denied</h1>
        <p class="auth-sub">Your account does not have permission to open this page. The server refused the request.</p>

        <div class="info-box">
            <p>Logged in as: <strong><?php echo htmlspecialchars($username); ?></strong></p>
            <p>Current Role: <span class="badge"><?php echo htmlspecialchars($role); ?></span> <span class="badge badge-danger">Not permitted here</span></p>
            <p><small>Security notice: this attempt has been recorded in the audit log.</small></p>
        </div>

        <div class="action-row">
            <?php if ($is_signed_in): ?>
                <a href="dashboard.php" class="btn"><i class="bi bi-grid-1x2" aria-hidden="true"></i> My Dashboard</a>
                <?= logout_button("btn btn-danger-outline", "Sign out & switch account") ?>
            <?php else: ?>
                <a href="login.php" class="btn"><i class="bi bi-box-arrow-in-right" aria-hidden="true"></i> Sign in</a>
            <?php endif; ?>
        </div>
    </div>
</main>

</body>
</html>
