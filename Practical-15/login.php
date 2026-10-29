<?php
session_start();
require_once "db.php";
require_once "audit_logger.php";

$error   = $_GET["error"] ?? "";
$message = $_GET["message"] ?? "";
$already_logged_user = $_SESSION["username"] ?? null;

if ($_SERVER["REQUEST_METHOD"] === "POST") {
    $login_input = trim($_POST["login_input"] ?? ($_POST["email"] ?? ($_POST["username"] ?? "")));
    $password    = $_POST["password"] ?? "";

    if ($login_input === "" || $password === "") {
        $error = "Please enter both username/email and password.";
    } else {
        $stmt = $conn->prepare("SELECT id, username, email, password, role FROM users WHERE email = ? OR username = ?");
        $stmt->bind_param("ss", $login_input, $login_input);
        $stmt->execute();
        $result = $stmt->get_result();

        if ($user = $result->fetch_assoc()) {
            if (password_verify($password, $user["password"])) {
                // Wipe prior session & regenerate ID
                session_unset();
                session_regenerate_id(true);
                $_SESSION["user_id"]  = $user["id"];
                $_SESSION["username"] = $user["username"];
                $_SESSION["email"]    = $user["email"];
                $_SESSION["role"]     = $user["role"];

                // Update last_login
                $up = $conn->prepare("UPDATE users SET last_login = NOW() WHERE id = ?");
                $up->bind_param("i", $user["id"]);
                $up->execute();
                $up->close();

                // Audit log
                log_audit($conn, $user["id"], $user["username"], "USER_LOGIN", "User logged in with role=" . $user["role"], "SUCCESS");

                if ($user["role"] === "admin") {
                    header("Location: admin_dashboard.php?success=Welcome Administrator! Master console loaded successfully.");
                    exit();
                } else {
                    header("Location: dashboard.php");
                    exit();
                }
            } else {
                $error = "Invalid credentials. Please verify your password.";
                log_audit($conn, null, $login_input, "LOGIN_FAILED", "Invalid password attempt for: $login_input", "FAILED");
            }
        } else {
            $error = "Account not found for: " . htmlspecialchars($login_input);
            log_audit($conn, null, $login_input, "LOGIN_FAILED", "Non-existent account attempted: $login_input", "FAILED");
        }
        $stmt->close();
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StudentHub Portal - Unified Login</title>
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

        <?php if ($already_logged_user): ?>
            <div class="alert-info" role="status">
                <i class="bi bi-info-circle-fill" aria-hidden="true"></i>
                <p>Active: <strong><?= htmlspecialchars($already_logged_user) ?></strong> · <a href="dashboard.php">Dashboard &rarr;</a> · <a href="logout.php">Logout</a></p>
            </div>
        <?php endif; ?>

        <?php if ($error): ?>
            <div class="alert-error" role="alert">
                <i class="bi bi-exclamation-triangle-fill" aria-hidden="true"></i>
                <p><?php echo htmlspecialchars($error); ?></p>
            </div>
        <?php endif; ?>

        <?php if ($message): ?>
            <div class="alert-success" role="status">
                <i class="bi bi-check-circle-fill" aria-hidden="true"></i>
                <p><?php echo htmlspecialchars($message); ?></p>
            </div>
        <?php endif; ?>

        <form method="POST" action="login.php">
            <div class="field">
                <label for="login_input">Username or Email Address</label>
                <div class="input-icon">
                    <i class="bi bi-person" aria-hidden="true"></i>
                    <input type="text" id="login_input" name="login_input" placeholder="Enter your username or email" required autofocus autocomplete="username">
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
