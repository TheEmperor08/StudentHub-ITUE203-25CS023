<?php
// StudentHub – Help & Contact (Practical 7 integrated): the inquiry form is sent with POST and a CSRF token, every field is
// validated and sanitised on the server, and a valid inquiry is stored in the inquiries table (includes/inquiries.php).
// Errors are shown under the fields with the entered values kept; a stored inquiry gets a reference number (PRG redirect).
require_once "db.php";
require_once __DIR__ . "/includes/auth.php";
require_once __DIR__ . "/includes/inquiries.php";
$current_user = optional_user();
require_once "audit_logger.php";
require_once "student_profile.php";

$profile = get_student_profile($conn);
$values  = ["name" => $current_user ? $profile["name"] : "", "mail" => $current_user ? $profile["email"] : "",
            "id" => $current_user && $profile["enrollment_no"] !== "—" ? $profile["enrollment_no"] : "", "topic" => "General", "msg" => ""];
$errors  = [];
if ($_SERVER["REQUEST_METHOD"] === "POST") {
    require_valid_csrf();
    [$clean, $errors] = validate_inquiry($_POST);
    foreach (INQUIRY_FIELDS as $field) {
        $values[$field] = is_string($_POST[$field] ?? null) ? $_POST[$field] : "";
    }
    if (!$errors) {
        $inquiry_id = save_inquiry($conn, $clean, $current_user["id"] ?? null);
        log_audit($conn, $current_user["id"] ?? null, $current_user["username"] ?? "guest", "SUBMIT_INQUIRY", "Inquiry #$inquiry_id stored (topic: {$clean["topic"]})", "SUCCESS");
        flash("success", "Thank you, {$clean["name"]}. Your inquiry has been received by the A7 CSE helpdesk (reference #$inquiry_id).");
        redirect("contact.php");
    }
    http_response_code(422);
}
$flash = take_flash();
function inquiry_error(array $errors, string $field): string
{
    return isset($errors[$field]) ? '<span class="field-error" id="' . $field . '-error">' . e($errors[$field]) . '</span>' : '';
}
function inquiry_attrs(array $errors, string $field): string
{
    return isset($errors[$field]) ? ' aria-invalid="true" aria-describedby="' . $field . '-error"' : '';
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Contact Support – CSPIT Charusat</title>
    <link rel="stylesheet" href="assets/css/global.css?v=11">
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

            <?php if ($flash): ?>
                <div class="alert-<?= $flash["type"] === "success" ? "success" : "error" ?> flash-message" role="status">
                    <i class="bi bi-<?= $flash["type"] === "success" ? "check-circle-fill" : "exclamation-triangle-fill" ?>" aria-hidden="true"></i>
                    <p><?= e($flash["message"]) ?></p>
                </div>
            <?php endif; ?>
            <?php if ($errors): ?>
                <div class="alert-error flash-message" role="alert"><i class="bi bi-exclamation-triangle-fill" aria-hidden="true"></i><p>Please correct the highlighted fields. Your inquiry was not sent.</p></div>
            <?php endif; ?>
            <form action="contact.php" method="POST" novalidate>
                <?= csrf_field() ?>
                <fieldset>
                    <legend class="sr-only">Inquiry Form</legend>
                    <p>
                        <label for="name">Your Name:</label>
                        <input type="text" id="name" name="name" maxlength="100" autocomplete="name" value="<?= e($values["name"]) ?>" required<?= inquiry_attrs($errors, "name") ?>>
                        <?= inquiry_error($errors, "name") ?>
                    </p>
                    <p>
                        <label for="id">Enrollment Number (optional):</label>
                        <input type="text" id="id" name="id" maxlength="20" placeholder="e.g. 25CS023" value="<?= e($values["id"]) ?>"<?= inquiry_attrs($errors, "id") ?>>
                        <?= inquiry_error($errors, "id") ?>
                    </p>
                    <p>
                        <label for="mail">Email:</label>
                        <input type="email" id="mail" name="mail" maxlength="100" autocomplete="email" value="<?= e($values["mail"]) ?>" required<?= inquiry_attrs($errors, "mail") ?>>
                        <?= inquiry_error($errors, "mail") ?>
                    </p>
                    <p>
                        <label for="topic">Topic:</label>
                        <select id="topic" name="topic"<?= inquiry_attrs($errors, "topic") ?>>
                            <?php foreach (INQUIRY_TOPICS as $topic): ?>
                                <option value="<?= e($topic) ?>"<?= $values["topic"] === $topic ? " selected" : "" ?>><?= e($topic) ?></option>
                            <?php endforeach; ?>
                        </select>
                        <?= inquiry_error($errors, "topic") ?>
                    </p>
                    <p>
                        <label for="msg">Message or Question (10–2000 characters):</label>
                        <textarea id="msg" name="msg" rows="4" maxlength="2000" required placeholder="Type your query here..."<?= inquiry_attrs($errors, "msg") ?>><?= e($values["msg"]) ?></textarea>
                        <?= inquiry_error($errors, "msg") ?>
                    </p>
                    <p class="hp-field" aria-hidden="true"><label for="website">Leave this field empty</label><input type="text" id="website" name="website" tabindex="-1" autocomplete="off"></p>
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
