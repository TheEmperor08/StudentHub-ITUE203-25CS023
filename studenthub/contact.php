<?php
session_start();
require_once "db.php";
require_once "audit_logger.php";
require_once "student_profile.php";

$profile = get_student_profile($conn);

$msg = "";
if ($_SERVER["REQUEST_METHOD"] === "POST") {
    $name  = trim($_POST["name"] ?? "");
    $email = trim($_POST["mail"] ?? "");
    $enr   = trim($_POST["id"] ?? "");
    $query = trim($_POST["msg"] ?? "");

    $msg = "Thank you $name! Your inquiry has been submitted to the A7 CSE helpdesk.";
    if (isset($_SESSION["user_id"])) {
        log_audit($conn, $_SESSION["user_id"], $_SESSION["username"], "SUBMIT_INQUIRY", "Student inquiry: $query", "SUCCESS");
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Contact Support – CSPIT Charusat</title>
    <link rel="stylesheet" href="assets/css/global.css?v=7">
    <script src="assets/js/theme.js"></script>
</head>
<body>

<div class="grid-container">
    <header>
        <div class="page-header__icon" aria-hidden="true"><i class="bi bi-life-preserver"></i></div>
        <div class="page-header__text">
            <p class="eyebrow">Campus</p>
            <h1>Contact Support & Helpdesk</h1>
            <p>Department of Computer Science & Engineering (CSPIT, CHARUSAT)</p>
        </div>
    </header>

    <?php include "sidebar.php"; ?>

    <main id="main-content">
        <?php if (!empty($msg)): ?>
            <div class="alert-success" role="status">
                <i class="bi bi-check-circle-fill" aria-hidden="true"></i> <p><?= htmlspecialchars($msg) ?></p>
            </div>
        <?php endif; ?>

        <div class="split">
        <section>
            <h2><i class="bi bi-building" aria-hidden="true"></i> Department & Campus Directory</h2>
            <p>Reach out to the student section or department coordinators during university hours.</p>

            <ul class="info-list">
                <li><span class="notice-icon" aria-hidden="true"><i class="bi bi-cpu"></i></span><div><strong>Department</strong><span>Computer Science & Engineering (CSE)</span></div></li>
                <li><span class="notice-icon" aria-hidden="true"><i class="bi bi-bank"></i></span><div><strong>Institute</strong><span>Chandubhai S. Patel Institute of Technology (CSPIT)</span></div></li>
                <li><span class="notice-icon" aria-hidden="true"><i class="bi bi-geo-alt"></i></span><div><strong>Location</strong><span>A7 Building, CHARUSAT University Campus, Changa, Gujarat</span></div></li>
                <li><span class="notice-icon" aria-hidden="true"><i class="bi bi-envelope"></i></span><div><strong>Official Support Email</strong><a href="mailto:support@charusat.edu.in">support@charusat.edu.in</a></div></li>
                <li><span class="notice-icon" aria-hidden="true"><i class="bi bi-telephone"></i></span><div><strong>Helpline</strong><a href="tel:+91-2697-265011">+91-2697-265011</a></div></li>
            </ul>
        </section>

        <section>
            <h2><i class="bi bi-chat-left-text" aria-hidden="true"></i> Submit Student Inquiry</h2>
            <p>Send us your technical query regarding portal access or academic schedules.</p>

            <form action="contact.php" method="POST">
                <fieldset>
                    <legend class="sr-only">Inquiry Form</legend>
                    <p>
                        <label for="name">Student Name:</label>
                        <input type="text" id="name" name="name" value="<?= htmlspecialchars($profile['name']) ?>" required>
                    </p>
                    <p>
                        <label for="id">Enrollment Number:</label>
                        <input type="text" id="id" name="id" value="<?= htmlspecialchars($profile['enrollment_no']) ?>" required>
                    </p>
                    <p>
                        <label for="mail">Student Email:</label>
                        <input type="email" id="mail" name="mail" value="<?= htmlspecialchars($profile['email']) ?>" required>
                    </p>
                    <p>
                        <label for="msg">Message or Question:</label>
                        <textarea id="msg" name="msg" rows="4" required placeholder="Type your query here..."></textarea>
                    </p>
                    <p>
                        <button type="submit"><i class="bi bi-send" aria-hidden="true"></i> Send Inquiry</button>
                        <button type="reset">Clear</button>
                    </p>
                </fieldset>
            </form>
        </section>
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
