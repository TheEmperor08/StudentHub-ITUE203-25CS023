<?php
// StudentHub – sign in (Practical 10 integrated): CSRF-protected form, password_verify(), one generic message for every
// failure, session ID regeneration on success, and fixed status messages chosen by a code (no text from the URL is shown).
require_once __DIR__ . "/includes/auth.php";

$already_logged = optional_user();

const LOGIN_STATUS = [
    "login_required"      => ["info", "Please sign in to continue."],
    "timeout"             => ["info", "Your session ended because you were inactive for too long. Please sign in again."],
    "logged_out"          => ["success", "You have been signed out."],
    "account_unavailable" => ["error", "Your account is no longer available. Please contact the administrator."],
    "access_disabled"     => ["error", "Your access to StudentHub is currently disabled. Please contact the administrator."],
];
$status  = is_string($_GET["status"] ?? null) && isset(LOGIN_STATUS[$_GET["status"]]) ? LOGIN_STATUS[$_GET["status"]] : null;
$error   = "";
$entered = "";
$denied  = false;          // correct password, but the student account is deactivated

if ($_SERVER["REQUEST_METHOD"] === "POST") {
    $entered  = trim((string) (is_string($_POST["login_input"] ?? null) ? $_POST["login_input"] : ""));
    $password = is_string($_POST["password"] ?? null) ? $_POST["password"] : "";

    if (!csrf_is_valid($_POST["csrf_token"] ?? null)) {
        $error = "The sign-in form expired. Please try again.";
    } elseif ($entered === "" || $password === "") {
        $error = "Please enter both your username or email and your password.";
    } else {
        // An e-mail address contains "@", a username never does
        $column = str_contains($entered, "@") ? "email" : "username";
        $stmt = $conn->prepare("SELECT u.id, u.username, u.email, u.password, u.role, u.status AS account_status, s.status AS student_status
                                FROM users u LEFT JOIN students s ON s.user_id = u.id WHERE u.$column = ? LIMIT 1");
        $stmt->bind_param("s", $entered);
        $stmt->execute();
        $account = $stmt->get_result()->fetch_assoc();
        $stmt->close();

        // An unknown account is checked against a dummy hash, so both failures take about the same time
        $hash = $account["password"] ?? '$2y$10$cL5pLAsT9eF311SYAHI/9OCtAW62Xl1zkDZ3VA2wDn4DbvPI3.YlC';
        $verified = password_verify($password, $hash);
        // Correct password, but the account is disabled or its linked student record is deactivated: no session is started
        // (generic message; the status is only revealed to someone who knows the password)
        $block  = $account !== null && $verified ? account_block_reason($account) : null;
        $denied = $block !== null;
        if ($denied) {
            log_audit($conn, (int) $account["id"], $account["username"], "LOGIN_DENIED", "Sign-in refused: $block.", "SECURITY_BLOCK");
        } elseif ($account !== null && $verified && in_array($account["role"], STUDENTHUB_ROLES, true)) {
            login_user($account);
            $up = $conn->prepare("UPDATE users SET last_login = NOW() WHERE id = ?");
            $up->bind_param("i", $account["id"]);
            $up->execute();
            $up->close();
            log_audit($conn, (int) $account["id"], $account["username"], "USER_LOGIN", "User logged in with role=" . $account["role"], "SUCCESS");
            if ($account["role"] === "admin") {
                flash("success", "Welcome, " . $account["username"] . ". You are signed in as administrator.");
                redirect("admin_dashboard.php");
            }
            flash("success", "Welcome back, " . $account["username"] . ".");
            redirect("dashboard.php");
        }
        if ($denied) {
            $error = LOGIN_STATUS["access_disabled"][1];
        } else {
            $error = "Invalid username/email or password.";
            log_audit($conn, null, mb_substr($entered, 0, 100), "LOGIN_FAILED",
                $account === null ? "Sign-in attempt for an unknown account." : "Wrong password.", "FAILED");
        }
    }
    http_response_code($denied ? 403 : 401);
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StudentHub Portal - Unified Login</title>
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
        <p class="eyebrow">CSPIT · CHARUSAT</p>
        <h2>Your campus, in one place.</h2>
        <p>Timetables, attendance, results and campus notices for B.Tech students – with secure, role-based access.</p>
        <ul class="auth-features">
            <li><i class="bi bi-calendar-check" aria-hidden="true"></i> Attendance & weekly timetable</li>
            <li><i class="bi bi-bar-chart-line" aria-hidden="true"></i> Results and academic progress</li>
            <li><i class="bi bi-shield-lock" aria-hidden="true"></i> Separate student and admin consoles</li>
        </ul>
    </div>
    <p class="auth-foot">Academic Year 2026-27 · Practical 15</p>
</aside>

<main class="auth-main">
    <button type="button" class="theme-toggle-nav theme-toggle-icon auth-theme-toggle" onclick="window.toggleTheme()" aria-pressed="false" aria-label="Switch to dark mode">
        <i class="bi bi-moon-stars" aria-hidden="true"></i>
    </button>

    <div class="auth-card">
        <h1>Sign in</h1>
        <p class="auth-sub">Unified Portal Login · CSPIT Campus Portal</p>

        <?php if ($already_logged): ?>
            <div class="alert-info" role="status">
                <i class="bi bi-info-circle-fill" aria-hidden="true"></i>
                <p>Signed in as <strong><?= e($already_logged["username"]) ?></strong> · <a href="<?= $already_logged["role"] === "admin" ? "admin_dashboard.php" : "dashboard.php" ?>">Continue &rarr;</a></p>
                <?= logout_button("link-button", "Sign out") ?>
            </div>
        <?php endif; ?>

        <?php if ($status && !$error): ?>
            <div class="alert-<?= $status[0] === "error" ? "error" : ($status[0] === "success" ? "success" : "info") ?>" role="status">
                <i class="bi bi-info-circle-fill" aria-hidden="true"></i>
                <p><?= e($status[1]) ?></p>
            </div>
        <?php endif; ?>

        <?php if ($error): ?>
            <div class="alert-error" role="alert">
                <i class="bi bi-exclamation-triangle-fill" aria-hidden="true"></i>
                <p><?= e($error) ?></p>
            </div>
        <?php endif; ?>

        <form method="POST" action="login.php">
            <?= csrf_field() ?>
            <div class="field">
                <label for="login_input">Username or Email Address</label>
                <div class="input-icon">
                    <i class="bi bi-person" aria-hidden="true"></i>
                    <input type="text" id="login_input" name="login_input" placeholder="Enter your username or email" required autofocus autocomplete="username" maxlength="100" value="<?= e($entered) ?>">
                </div>
            </div>

            <div class="field">
                <label for="password">Password</label>
                <div class="input-icon">
                    <i class="bi bi-lock" aria-hidden="true"></i>
                    <input type="password" id="password" name="password" placeholder="Enter your password" required autocomplete="current-password">
                </div>
            </div>

            <button type="submit" class="btn-block">Sign In to StudentHub <i class="bi bi-arrow-right" aria-hidden="true"></i></button>

            <p class="auth-links">New student? <a href="register.php">Create an account</a></p>
            <p class="auth-links"><a class="muted" href="index.php">&larr; Back to Home</a></p>
        </form>
    </div>
</main>

</body>
</html>
