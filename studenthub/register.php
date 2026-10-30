<?php
// StudentHub – student self-registration (Practical 9 integrated). Server-side validation, CSRF token, duplicate
// checks and one transaction that creates the account (role 'student') together with its linked student record.
require_once __DIR__ . "/includes/auth.php";
require_once __DIR__ . "/includes/registration.php";

if ($current = optional_user()) {
    redirect($current["role"] === "admin" ? "admin_dashboard.php" : "dashboard.php");
}

$values = ["name" => "", "username" => "", "email" => "", "gender" => "Male", "course" => "", "adm_year" => registration_admission_years()[0]];
$errors = [];
$error  = "";

if ($_SERVER["REQUEST_METHOD"] === "POST") {
    if (!csrf_is_valid($_POST["csrf_token"] ?? null)) {
        $error = "The registration form expired. Please check your details and submit again.";
    } else {
        [$clean, $errors] = validate_registration($_POST);
        foreach (array_keys($values) as $key) {
            $values[$key] = $clean[$key] ?? $values[$key];
        }
        if (!$errors) {
            try {
                $result = register_student_account($conn, $clean);
                if (isset($result["errors"])) {
                    $errors = $result["errors"];
                } else {
                    login_user(["id" => $result["user_id"], "username" => $clean["username"], "email" => $clean["email"], "role" => "student"]);
                    log_audit($conn, $result["user_id"], $clean["username"], "USER_REGISTER",
                        "New student account and linked student record created (enrollment " . $result["enrollment_no"] . ").", "SUCCESS");
                    flash("success", "Welcome to StudentHub, " . $clean["name"] . "! Your enrollment number is " . $result["enrollment_no"] . ".");
                    redirect("dashboard.php");
                }
            } catch (RuntimeException $e) {
                $error = "Your account could not be created because of a server problem. Nothing was saved. Please try again later.";
            }
        }
    }
    if ($error === "" && $errors) {
        $error = "Please correct the highlighted fields.";
    }
    http_response_code(422);
}

function field_error(array $errors, string $field): string
{
    return isset($errors[$field]) ? '<p class="field-error" id="' . $field . '-error">' . e($errors[$field]) . '</p>' : '';
}

function field_attrs(array $errors, string $field): string
{
    return isset($errors[$field]) ? ' aria-invalid="true" aria-describedby="' . $field . '-error"' : '';
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Student Registration - StudentHub</title>
    <link rel="stylesheet" href="assets/css/auth.css?v=2">
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
            <li><i class="bi bi-person-check" aria-hidden="true"></i> Your student record and enrollment number are created automatically</li>
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

            <form method="POST" action="register.php" novalidate>
                <?= csrf_field() ?>
                <div class="form-row">
                    <div class="form-group">
                        <label for="name">Full Name *</label>
                        <input type="text" id="name" name="name" placeholder="e.g. Asha Patel" required minlength="2" maxlength="100" autocomplete="name" value="<?= e($values["name"]) ?>"<?= field_attrs($errors, "name") ?>>
                        <?= field_error($errors, "name") ?>
                    </div>
                    <div class="form-group">
                        <label for="username">Username *</label>
                        <input type="text" id="username" name="username" placeholder="e.g. asha_patel" required minlength="3" maxlength="30" pattern="[A-Za-z][A-Za-z0-9_]*" autocomplete="username" value="<?= e($values["username"]) ?>"<?= field_attrs($errors, "username") ?>>
                        <?= field_error($errors, "username") ?>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label for="email">Email Address *</label>
                        <input type="email" id="email" name="email" placeholder="name@example.com" required maxlength="100" autocomplete="email" spellcheck="false" value="<?= e($values["email"]) ?>"<?= field_attrs($errors, "email") ?>>
                        <?= field_error($errors, "email") ?>
                    </div>
                    <div class="form-group">
                        <span class="label-text">Gender *</span>
                        <div class="gender-options" role="radiogroup" aria-label="Gender">
                            <?php foreach (REGISTRATION_GENDERS as $g): ?>
                                <label><input type="radio" name="gender" value="<?= e($g) ?>"<?= $values["gender"] === $g ? " checked" : "" ?>> <?= e($g) ?></label>
                            <?php endforeach; ?>
                        </div>
                        <?= field_error($errors, "gender") ?>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label for="course">Course *</label>
                        <select id="course" name="course" required<?= field_attrs($errors, "course") ?>>
                            <option value="">-- Select Course --</option>
                            <?php foreach (array_keys(REGISTRATION_COURSES) as $c): ?>
                                <option value="<?= e($c) ?>"<?= $values["course"] === $c ? " selected" : "" ?>><?= e($c) ?></option>
                            <?php endforeach; ?>
                        </select>
                        <?= field_error($errors, "course") ?>
                    </div>
                    <div class="form-group">
                        <label for="adm_year">Admission Year *</label>
                        <select id="adm_year" name="adm_year" required<?= field_attrs($errors, "adm_year") ?>>
                            <?php foreach (registration_admission_years() as $y): ?>
                                <option value="<?= e($y) ?>"<?= $values["adm_year"] === $y ? " selected" : "" ?>><?= e($y) ?></option>
                            <?php endforeach; ?>
                        </select>
                        <?= field_error($errors, "adm_year") ?>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label for="password">Password *</label>
                        <input type="password" id="password" name="password" placeholder="Create a strong password" required minlength="8" maxlength="72" autocomplete="new-password" aria-describedby="password-help<?= isset($errors["password"]) ? " password-error" : "" ?>"<?= isset($errors["password"]) ? ' aria-invalid="true"' : "" ?>>
                        <p class="field-help" id="password-help"><?= e(PASSWORD_POLICY_TEXT) ?></p>
                        <?= field_error($errors, "password") ?>
                    </div>
                    <div class="form-group">
                        <label for="confirm_password">Confirm Password *</label>
                        <input type="password" id="confirm_password" name="confirm_password" placeholder="Re-enter password" required minlength="8" maxlength="72" autocomplete="new-password"<?= field_attrs($errors, "confirm_password") ?>>
                        <?= field_error($errors, "confirm_password") ?>
                    </div>
                </div>
                <div class="terms-group">
                    <input type="checkbox" id="agree" name="agree" value="1" required<?= isset($errors["agree"]) ? ' aria-invalid="true" aria-describedby="agree-error"' : "" ?>>
                    <label for="agree">I agree to the Terms &amp; Conditions and Privacy Policy.</label>
                </div>
                <?= field_error($errors, "agree") ?>
        
                <button type="submit" class="btn-submit btn-block"><i class="bi bi-person-plus" aria-hidden="true"></i> Register Account</button>
            </form>

        <p class="auth-links">Already registered? <a href="login.php">Back to Login</a></p>
    </div>
</main>

</body>
</html>
