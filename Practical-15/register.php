<?php
session_start();
require_once "db.php";
require_once "audit_logger.php";

$error   = "";
$success = "";

if ($_SERVER["REQUEST_METHOD"] === "POST") {
    $name         = trim($_POST["name"] ?? "");
    $email        = trim($_POST["email"] ?? "");
    $mobile       = trim($_POST["mobile"] ?? "");
    $gender       = trim($_POST["gender"] ?? "Male");
    $course       = trim($_POST["course"] ?? "Computer Science Engineering");
    $adm_year     = trim($_POST["adm_year"] ?? "2026");
    $password     = $_POST["password"] ?? "";
    $confirm_pass = $_POST["confirm_password"] ?? "";
    $agree        = isset($_POST["agree"]);

    if (empty($name) || empty($email) || empty($password)) {
        $error = "Please fill in all required fields.";
    } elseif ($password !== $confirm_pass) {
        $error = "Passwords do not match.";
    } elseif (strlen($password) < 6) {
        $error = "Password must be at least 6 characters long.";
    } elseif (!$agree) {
        $error = "Please agree to the Terms & Conditions.";
    } else {
        // Check if user already exists
        $check = $conn->prepare("SELECT id FROM users WHERE email = ?");
        $check->bind_param("s", $email);
        $check->execute();
        $check->store_result();

        if ($check->num_rows > 0) {
            $error = "An account with that email address already exists. Please log in.";
            $check->close();
        } else {
            $check->close();
            // Generate username from email or name
            $username = strtolower(explode("@", $email)[0]);
            
            // Generate Enrollment No based on Year and Course
            $yr_prefix = substr($adm_year, 2, 2);
            $dept_code = "CS";
            if (stripos($course, "Information") !== false || stripos($course, "IT") !== false) {
                $dept_code = "IT";
            } elseif (stripos($course, "Data") !== false) {
                $dept_code = "DS";
            } elseif (stripos($course, "Web") !== false) {
                $dept_code = "WD";
            }
            $enrollment_no = $yr_prefix . $dept_code . sprintf("%03d", rand(101, 899));
            $hashed = password_hash($password, PASSWORD_BCRYPT);

            // Insert into users table
            $u_stmt = $conn->prepare("INSERT INTO users (username, email, password, role, created_at) VALUES (?, ?, ?, 'student', NOW())");
            $u_stmt->bind_param("sss", $username, $email, $hashed);

            if ($u_stmt->execute()) {
                $new_user_id = $u_stmt->insert_id;
                $u_stmt->close();

                // Insert into students table
                $sem = 3;
                $s_stmt = $conn->prepare("INSERT INTO students (enrollment_no, name, email, course, semester, gender, status, created_at) VALUES (?, ?, ?, ?, ?, ?, 'Active', NOW())");
                $s_stmt->bind_param("ssssis", $enrollment_no, $name, $email, $course, $sem, $gender);
                $s_stmt->execute();
                $s_stmt->close();

                // Clear old session & auto-login new student immediately!
                session_unset();
                session_regenerate_id(true);
                $_SESSION["user_id"]  = $new_user_id;
                $_SESSION["username"] = $username;
                $_SESSION["email"]    = $email;
                $_SESSION["role"]     = "student";

                // Log audit
                log_audit($conn, $new_user_id, $username, "USER_REGISTER", "New student registered and auto-logged in: $name ($email)", "SUCCESS");

                // Redirect directly into student dashboard
                header("Location: dashboard.php");
                exit();
            } else {
                $error = "Registration failed: " . htmlspecialchars($conn->error);
            }
        }
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Student Registration - StudentHub</title>
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
        <p class="eyebrow">New student registration</p>
        <h2>Create your StudentHub account.</h2>
        <p>Register once to access your dashboard, timetable, attendance and campus notices.</p>
        <ul class="auth-features">
            <li><i class="bi bi-person-check" aria-hidden="true"></i> Your profile is created automatically</li>
            <li><i class="bi bi-key" aria-hidden="true"></i> Passwords are stored as bcrypt hashes</li>
            <li><i class="bi bi-box-arrow-in-right" aria-hidden="true"></i> Signed in straight after registering</li>
        </ul>
    </div>
    <p class="auth-foot">CSPIT · CHARUSAT · Academic Year 2026-27</p>
</aside>

<main class="auth-main">
    <button type="button" class="theme-toggle-nav theme-toggle-icon auth-theme-toggle" onclick="window.toggleTheme()" aria-pressed="false" aria-label="Switch to dark mode">
        <i class="bi bi-moon-stars" aria-hidden="true"></i>
    </button>

    <div class="auth-card wide">
        <h1>Student Registration</h1>
        <p class="auth-sub">Fields marked * are required.</p>

        <?php if (!empty($error)): ?>
            <div class="alert-error" role="alert">
                <i class="bi bi-exclamation-triangle-fill" aria-hidden="true"></i>
                <p><?= htmlspecialchars($error) ?></p>
            </div>
        <?php endif; ?>

            <form method="POST" action="register.php">
                <div class="form-row">
                    <div class="form-group">
                        <label for="name">Full Name *</label>
                        <input type="text" id="name" name="name" placeholder="John Doe" required autofocus>
                    </div>
                    <div class="form-group">
                        <label for="email">Email Address *</label>
                        <input type="email" id="email" name="email" placeholder="john@studenthub.edu" required>
                    </div>
                </div>
        
                <div class="form-row">
                    <div class="form-group">
                        <label for="mobile">Mobile Number *</label>
                        <input type="tel" id="mobile" name="mobile" placeholder="9876543210" required>
                    </div>
                    <div class="form-group">
                        <label>Gender *</label>
                        <div class="gender-options">
                            <label><input type="radio" name="gender" value="Male" checked> Male</label>
                            <label><input type="radio" name="gender" value="Female"> Female</label>
                            <label><input type="radio" name="gender" value="Other"> Other</label>
                        </div>
                    </div>
                </div>
        
                <div class="form-row">
                    <div class="form-group">
                        <label for="course">Course *</label>
                        <select id="course" name="course" required>
                            <option value="">-- Select Course --</option>
                            <option value="Information Technology">Information Technology</option>
                            <option value="Computer Science Engineering">Computer Science Engineering</option>
                            <option value="Data Science">Data Science</option>
                            <option value="Web Development">Web Development</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="adm_year">Admission Year *</label>
                        <select id="adm_year" name="adm_year" required>
                            <option value="">-- Select Year --</option>
                            <option value="2026" selected>2026</option>
                            <option value="2025">2025</option>
                            <option value="2024">2024</option>
                        </select>
                    </div>
                </div>
        
                <div class="form-row">
                    <div class="form-group">
                        <label for="password">Password *</label>
                        <input type="password" id="password" name="password" placeholder="Create a strong password" required>
                    </div>
                    <div class="form-group">
                        <label for="confirm_password">Confirm Password *</label>
                        <input type="password" id="confirm_password" name="confirm_password" placeholder="Re-enter password" required>
                    </div>
                </div>
        
                <div class="terms-group">
                    <input type="checkbox" id="agree" name="agree" required checked>
                    <label for="agree">I agree to the Terms & Conditions and Privacy Policy.</label>
                </div>
        
                <button type="submit" class="btn-submit btn-block"><i class="bi bi-person-plus" aria-hidden="true"></i> Register Account</button>
            </form>

        <p class="auth-links">Already registered? <a href="login.php">Back to Login</a></p>
    </div>
</main>

</body>
</html>
