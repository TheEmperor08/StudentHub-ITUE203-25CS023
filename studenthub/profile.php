<?php
require_once "db.php";
require_once __DIR__ . "/includes/auth.php";
require_once "audit_logger.php";
require_once "student_profile.php";

$current_user = require_permission("portal.view");

$user_id  = $_SESSION["user_id"];
$username = $_SESSION["username"];
$email    = $_SESSION["email"] ?? "";

$profile       = get_student_profile($conn);
$student_name  = $profile["name"];
$enrollment_no = $profile["enrollment_no"];
$course        = $profile["course"] ?: "Computer Science & Engineering (CSE)";
$sem           = "Semester " . $profile["semester"] . " (Division I)";

$msg   = "";
$error = "";
if ($_SERVER["REQUEST_METHOD"] === "POST") {
    require_valid_csrf();
    $form_action = $_POST["form_action"] ?? "update_contact";

    if ($form_action === "change_password") {
        $old_pass     = $_POST["oldpass"] ?? "";
        $new_pass     = $_POST["newpass"] ?? "";
        $confirm_pass = $_POST["confirm_newpass"] ?? "";

        if ($old_pass === "" || $new_pass === "") {
            $error = "Please enter both your current and new password.";
        } elseif ($problems = password_problems($new_pass)) {
            $error = "The new password needs " . implode(", ", $problems) . ".";
        } elseif ($new_pass !== $confirm_pass) {
            $error = "New passwords do not match.";
        } else {
            // Verify current password against the stored hash before changing anything
            $stored_hash = null;
            $pw_stmt = $conn->prepare("SELECT password FROM users WHERE id = ?");
            if ($pw_stmt) {
                $pw_stmt->bind_param("i", $user_id);
                $pw_stmt->execute();
                $pw_row = $pw_stmt->get_result()->fetch_assoc();
                $stored_hash = $pw_row["password"] ?? null;
                $pw_stmt->close();
            }

            if ($stored_hash === null || !password_verify($old_pass, $stored_hash)) {
                $error = "Current password is incorrect. Your password was not changed.";
                log_audit($conn, $user_id, $username, "CHANGE_PASSWORD", "Password change rejected: incorrect current password.", "FAILED");
            } else {
                $hashed = password_hash($new_pass, PASSWORD_BCRYPT);
                $up = $conn->prepare("UPDATE users SET password = ? WHERE id = ?");
                if ($up) {
                    $up->bind_param("si", $hashed, $user_id);
                    if ($up->execute() && $up->affected_rows === 1) {
                        session_regenerate_id(true);
                        $msg = "Password changed successfully.";
                        log_audit($conn, $user_id, $username, "CHANGE_PASSWORD", "User changed account password.", "SUCCESS");
                    }
                    $up->close();
                }
                if ($msg === "") {
                    $error = "Password could not be updated due to a server error. Your password was not changed.";
                }
            }
        }
    } else {
        // The students table has no phone/address columns yet, so nothing can be saved
        $error = "Saving phone and address is not available yet. No changes were stored.";
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Profile – <?= htmlspecialchars($student_name) ?></title>
    <link rel="stylesheet" href="assets/css/global.css?v=10">
    <script src="assets/js/theme.js"></script>
</head>
<body>

<div class="grid-container">
    <header>
        <div class="page-header__icon" aria-hidden="true"><i class="bi bi-person-circle"></i></div>
        <div class="page-header__text">
            <p class="eyebrow">Overview</p>
            <h1>Student Profile</h1>
            <p>Personal and Academic Profile Record – CSPIT, CHARUSAT</p>
        </div>
    </header>

    <?php include "sidebar.php"; ?>

    <main id="main-content">
        <?php if (!empty($msg)): ?>
            <div class="alert-success" role="status">
                <i class="bi bi-check-circle-fill" aria-hidden="true"></i> <p><?= htmlspecialchars($msg) ?></p>
            </div>
        <?php endif; ?>

        <?php if (!empty($error)): ?>
            <div class="alert-error" role="alert">
                <i class="bi bi-x-circle-fill" aria-hidden="true"></i> <p><?= htmlspecialchars($error) ?></p>
            </div>
        <?php endif; ?>

        <div class="profile-layout">
        <section class="profile-card">
            <div class="profile-avatar" aria-hidden="true"><?= htmlspecialchars(mb_strtoupper(mb_substr($student_name, 0, 1))) ?></div>
            <h2><?= htmlspecialchars($student_name) ?></h2>
            <p class="section-note">B.Tech Student · CSPIT, CHARUSAT</p>
            <span class="chip"><i class="bi bi-person-badge" aria-hidden="true"></i> <?= htmlspecialchars($enrollment_no) ?></span>
            <span class="chip"><i class="bi bi-mortarboard" aria-hidden="true"></i> <?= htmlspecialchars($sem) ?></span>
        </section>

        <div>
        <section>
            <h2><i class="bi bi-person-vcard" aria-hidden="true"></i> Personal Information</h2>
            <p>Details from your student record.</p>
            <dl>
                <dt><strong>Student Name:</strong></dt>
                <dd><?= htmlspecialchars($student_name) ?></dd>
                
                <dt><strong>Enrollment Number:</strong></dt>
                <dd><mark><?= htmlspecialchars($enrollment_no) ?></mark></dd>
                
                <dt><strong>Institute & Department:</strong></dt>
                <dd>Chandubhai S. Patel Institute of Technology (CSPIT) – <?= htmlspecialchars($course) ?></dd>
                
                <dt><strong>Campus Building:</strong></dt>
                <dd>A7 Building, CHARUSAT University Campus, Changa</dd>
                
                <dt><strong>Current Semester:</strong></dt>
                <dd><?= htmlspecialchars($sem) ?></dd>

                <dt><strong>Student Official Email:</strong></dt>
                <dd><a href="mailto:<?= htmlspecialchars($email) ?>"><?= htmlspecialchars($email) ?></a></dd>
            </dl>
        </section>

        <section>
            <h2><i class="bi bi-telephone" aria-hidden="true"></i> Contact & Address</h2>
            <p>Saving phone and address details is not available yet.</p>
            <form action="profile.php" method="POST">
                <?= csrf_field() ?>
                <fieldset>
                    <legend class="sr-only">Edit Student Records</legend>
                    <p>
                        <label for="phone">Phone Number:</label>
                        <input type="tel" id="phone" name="phone" value="" placeholder="e.g. +91 98765 43210" autocomplete="tel">
                    </p>
                    <p>
                        <label for="address">Hostel / Residential Address:</label>
                        <textarea id="address" name="address" rows="3" placeholder="Hostel / residential address"></textarea>
                    </p>
                    <p>
                        <button type="submit"><i class="bi bi-check2" aria-hidden="true"></i> Save Details</button>
                    </p>
                </fieldset>
            </form>
        </section>

        <section>
            <h2><i class="bi bi-shield-lock" aria-hidden="true"></i> Account Security</h2>
            <p>Your password is stored as a secure bcrypt hash.</p>
            <details>
                <summary><i class="bi bi-key" aria-hidden="true"></i> Change Login Password</summary>
                <form action="profile.php" method="POST">
                <?= csrf_field() ?>
                    <input type="hidden" name="form_action" value="change_password">
                    <fieldset>
                        <legend class="sr-only">Change password</legend>
                        <p>
                            <label for="oldpass">Current Password:</label>
                            <input type="password" id="oldpass" name="oldpass" required autocomplete="current-password">
                        </p>
                        <p>
                            <label for="newpass">New Password:</label>
                            <input type="password" id="newpass" name="newpass" required minlength="6" autocomplete="new-password">
                        </p>
                        <p>
                            <label for="confirm_newpass">Confirm New Password:</label>
                            <input type="password" id="confirm_newpass" name="confirm_newpass" required minlength="6" autocomplete="new-password">
                        </p>
                        <p>
                            <button type="submit"><i class="bi bi-shield-check" aria-hidden="true"></i> Update Password</button>
                        </p>
                    </fieldset>
                </form>
            </details>
        </section>
        </div>
        </div>
    </main>

    <footer>
        <p>&copy; <time datetime="2026">2026</time> StudentHub – CSPIT, CHARUSAT. All rights reserved.</p>
        <address>
            Email: <a href="mailto:support@charusat.edu.in">support@charusat.edu.in</a> | Phone: <a href="tel:+91-2697-265011">+91-2697-265011</a>
        </address>
    </footer>
</div>

</body>
</html>
