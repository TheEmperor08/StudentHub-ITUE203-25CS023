<?php
if (session_status() === PHP_SESSION_NONE) {
    session_start();
}
http_response_code(403);

$username = $_SESSION["username"] ?? "Guest";
$role     = $_SESSION["role"] ?? "unauthenticated";
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>403 Forbidden - Access Restricted | StudentHub</title>
    <link rel="stylesheet" href="assets/css/auth.css?v=1">
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
        <h1>Access Denied: Admins Only</h1>
        <p class="auth-sub">You do not have administrative privileges to access the Administrator Management Console.</p>

        <div class="info-box">
            <p>Logged in as: <strong><?php echo htmlspecialchars($username); ?></strong></p>
            <p>Current Role: <span class="badge"><?php echo htmlspecialchars($role); ?></span> <span class="badge badge-danger">Unauthorized for Admin Areas</span></p>
            <p><small>Security Notice: This unauthorized access attempt has been logged in the <code>audit_logs</code> database.</small></p>
        </div>

        <div class="action-row">
            <a href="student_dashboard.php" class="btn"><i class="bi bi-grid-1x2" aria-hidden="true"></i> Student Dashboard</a>
            <a href="logout.php" class="btn btn-danger-outline"><i class="bi bi-box-arrow-right" aria-hidden="true"></i> Logout & Switch Account</a>
        </div>
    </div>
</main>

</body>
</html>
