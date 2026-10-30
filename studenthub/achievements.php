<?php
require_once "db.php";
require_once __DIR__ . "/includes/auth.php";
require_once "audit_logger.php";
require_once "student_profile.php";

$current_user = require_permission("portal.view");

$profile = get_student_profile($conn);

$msg   = "";
$error = "";
if ($_SERVER["REQUEST_METHOD"] === "POST") {
    require_valid_csrf();
    $event = trim($_POST["event"] ?? "");
    $date  = trim($_POST["date"] ?? "");
    $parsed_date = DateTime::createFromFormat("!Y-m-d", $date);
    // Certificate uploads are not implemented: any attached file is ignored and never written to disk
    $file_sent = ($_FILES["cert"]["error"] ?? UPLOAD_ERR_NO_FILE) !== UPLOAD_ERR_NO_FILE;

    if ($event === "" || mb_strlen($event) > 150) {
        $error = "Please enter an event name (up to 150 characters). Nothing was recorded.";
    } elseif (!$parsed_date || $parsed_date->format("Y-m-d") !== $date) {
        $error = "Please enter a valid event date. Nothing was recorded.";
    } else {
        $msg = "Achievement details for '$event' ($date) were noted in the activity log only. "
             . ($file_sent ? "Certificate uploads are not available yet, so the attached file was NOT saved."
                           : "Certificate uploads are not available yet.");
        log_audit($conn, $_SESSION["user_id"], $_SESSION["username"], "ADD_ACHIEVEMENT", "Achievement noted (no certificate stored): $event ($date)", "SUCCESS");
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Achievements – <?= htmlspecialchars($profile['name']) ?> (CSPIT)</title>
    <link rel="stylesheet" href="assets/css/global.css?v=11">
    <script src="assets/js/theme.js"></script>
</head>
<body>

<div class="grid-container">
    <header>
        <div class="page-header__icon" aria-hidden="true"><i class="bi bi-award"></i></div>
        <div class="page-header__text">
            <p class="eyebrow">Academics</p>
            <h1>Student Achievements & Hackathons</h1>
            <p><?= htmlspecialchars($profile['name']) ?> | Computer Science & Engineering – CSPIT, CHARUSAT</p>
        </div>
    </header>

    <?php include "sidebar.php"; ?>

    <main id="main-content">
        <?php if (!empty($msg)): ?>
            <div class="alert-info" role="status">
                <i class="bi bi-info-circle-fill" aria-hidden="true"></i> <p><?= htmlspecialchars($msg) ?></p>
            </div>
        <?php endif; ?>

        <?php if (!empty($error)): ?>
            <div class="alert-error" role="alert">
                <i class="bi bi-x-circle-fill" aria-hidden="true"></i> <p><?= htmlspecialchars($error) ?></p>
            </div>
        <?php endif; ?>

        <section>
            <h2><i class="bi bi-rocket-takeoff" aria-hidden="true"></i> Upcoming Hackathon Participation</h2>
            <p>Competitions you are preparing for.</p>
            <article class="notice">
                <div class="date-badge" aria-hidden="true"><span class="month">Aug</span><span class="day">22</span></div>
                <div class="notice-body">
                    <h3>Odoo Hackathon at LDCE</h3>
                    <p>Preparing to represent Computer Science & Engineering (CSPIT, CHARUSAT) at the prestigious Odoo Hackathon!</p>
                    <div class="notice-meta">
                        <span><i class="bi bi-calendar3" aria-hidden="true"></i> <time datetime="2026-08-22">August 22, 2026</time></span>
                        <span><i class="bi bi-geo-alt" aria-hidden="true"></i> L.D. College of Engineering (LDCE)</span>
                        <mark>Registered & Active Preparation</mark>
                    </div>
                </div>
            </article>
        </section>

        <section>
            <h2><i class="bi bi-patch-check" aria-hidden="true"></i> Academic Badges & Honors</h2>
            <p>Recognition earned across the programme.</p>
            <div class="feature-grid">
                <article class="feature-card">
                    <div class="notice-icon" aria-hidden="true"><i class="bi bi-code-slash"></i></div>
                    <h3>Web Development Frameworks Specialist</h3>
                    <p>Demonstrated strong skills in building pure HTML5 semantic web structures, PHP server-side apps, and MySQL database platforms.</p>
                    <span class="badge badge-success"><i class="bi bi-check2-circle" aria-hidden="true"></i> Verified Badge</span>
                </article>
                <article class="feature-card">
                    <div class="notice-icon" aria-hidden="true"><i class="bi bi-trophy"></i></div>
                    <h3>Consistent Academic Honors</h3>
                    <p>Achieved impressive results across previous semesters (8.32 SGPA in Sem 1 and overall 8.05 CGPA).</p>
                    <p><span class="badge badge-sample"><i class="bi bi-info-circle" aria-hidden="true"></i> Sample / demo data</span> these grade figures are placeholders, not actual academic results.</p>
                </article>
            </div>
        </section>

        <section>
            <h2><i class="bi bi-plus-circle" aria-hidden="true"></i> Submit New Hackathon or Competition Record</h2>
            <p>Details are noted in the activity log; certificate uploads are not available yet.</p>
            <form action="achievements.php" method="POST" enctype="multipart/form-data">
                <?= csrf_field() ?>
                <fieldset>
                    <legend>Add Achievement Details</legend>
                    <p>
                        <label for="event">Event Name:</label>
                        <input type="text" id="event" name="event" value="Odoo Hackathon 2026" required>
                    </p>
                    <p>
                        <label for="date">Event Date:</label>
                        <input type="date" id="date" name="date" value="2026-08-22" required>
                    </p>
                    <p>
                        <label for="cert">Upload Certificate / Proof:</label>
                        <input type="file" id="cert" name="cert" disabled aria-describedby="cert-note">
                        <small id="cert-note">Certificate uploads are not available yet. Details are noted in the activity log only; no file is stored.</small>
                    </p>
                    <p>
                        <button type="submit"><i class="bi bi-journal-plus" aria-hidden="true"></i> Submit Details</button>
                    </p>
                </fieldset>
            </form>
        </section>
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
