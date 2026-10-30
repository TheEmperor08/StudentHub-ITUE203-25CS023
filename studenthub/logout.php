<?php
// StudentHub – secure logout (Practical 10 integrated). Only a POST with the CSRF token logs out, so a link or image on
// another site cannot sign the user out. The session data, the cookie and the server-side session are all removed.
// Opening logout.php directly (GET) shows a confirmation button instead of logging out.
require_once __DIR__ . "/includes/auth.php";

start_secure_session();
send_security_headers(true);
$user = current_user();

if ($_SERVER["REQUEST_METHOD"] === "POST") {
    if (!$user) {
        redirect("login.php");
    }
    if (!csrf_is_valid($_POST["csrf_token"] ?? null)) {
        log_audit($conn, $user["id"], $user["username"], "CSRF_REJECTED", "Logout request without a valid token (ignored).", "SECURITY_BLOCK");
        redirect($user["role"] === "admin" ? "admin_dashboard.php" : "dashboard.php");
    }
    log_audit($conn, $user["id"], $user["username"], "USER_LOGOUT", "User logged out successfully.", "SUCCESS");
    end_session();
    redirect("login.php?status=logged_out");
}

if (!$user) {
    redirect("login.php");
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sign out – StudentHub</title>
    <link rel="stylesheet" href="assets/css/auth.css?v=2">
    <script src="assets/js/theme.js"></script>
</head>
<body class="auth">
<main class="auth-main">
    <div class="auth-card">
        <h1>Sign out?</h1>
        <p class="auth-sub">You are signed in as <strong><?= e($user["username"]) ?></strong>.</p>
        <?= logout_button("btn-block", "Sign out") ?>
        <p class="auth-links"><a href="<?= $user["role"] === "admin" ? "admin_dashboard.php" : "dashboard.php" ?>">&larr; Stay signed in</a></p>
    </div>
</main>
</body>
</html>
