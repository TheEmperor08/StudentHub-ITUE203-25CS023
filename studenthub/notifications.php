<?php
// StudentHub – Campus Events & Notices. Students register for events and cancel their registration here (Practicals 8 and
// 12): register_student_for_event() runs in one transaction and refuses duplicates, full, closed and past events and
// inactive students. Only a student account with a linked student record (students.user_id) can register.
require_once "db.php";
require_once __DIR__ . "/includes/auth.php";
require_once __DIR__ . "/includes/event_management.php";
require_once __DIR__ . "/includes/event_registration.php";
require_once "audit_logger.php";
$current_user = require_permission("portal.view");
$student = $current_user["role"] === "student" ? linked_student($conn, $current_user["id"]) : null;

if ($_SERVER["REQUEST_METHOD"] === "POST") {
    require_valid_csrf();
    $action   = is_string($_POST["action"] ?? null) ? $_POST["action"] : "";
    $event_id = event_id_from($_POST["event_id"] ?? "");
    $event    = $event_id > 0 ? find_event($conn, $event_id) : null;
    if (!in_array($action, ["register", "cancel"], true) || $event === null) {
        flash("error", "That event was not found.");
    } elseif ($student === null) {
        flash("error", "Event registration is available to students with a linked student record.");
    } else {
        try {
            if ($action === "register") {
                $registration = register_student_for_event($conn, (int) $student["id"], $event_id);
                log_audit($conn, $current_user["id"], $current_user["username"], "EVENT_REGISTER", "Registered for event ID $event_id (registration ID $registration)", "SUCCESS");
                flash("success", "You are registered for “{$event["title"]}”.");
            } else {
                $registration = cancel_event_registration($conn, (int) $student["id"], $event_id);
                log_audit($conn, $current_user["id"], $current_user["username"], "EVENT_REGISTRATION_CANCEL", "Cancelled registration ID $registration for event ID $event_id", "SUCCESS");
                flash("success", "Your registration for “{$event["title"]}” was cancelled.");
            }
        } catch (EventRegistrationException $e) {
            flash("error", $e->getMessage());
        }
    }
    redirect("notifications.php");
}

$events = event_list($conn, array_fill_keys(["q", "category", "status"], "") + ["when" => "upcoming", "page" => 1]);
$past   = event_list($conn, array_fill_keys(["q", "category", "status"], "") + ["when" => "past", "page" => 1]);
$mine   = $student !== null ? student_registration_map($conn, (int) $student["id"]) : [];
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Campus Notifications – CSPIT Charusat</title>
    <link rel="stylesheet" href="assets/css/global.css?v=11">
    <script src="assets/js/theme.js"></script>
</head>
<body>

<div class="grid-container">
    <header>
        <div class="page-header__icon" aria-hidden="true"><i class="bi bi-megaphone"></i></div>
        <div class="page-header__text">
            <p class="eyebrow">Campus</p>
            <h1>Campus Announcements & Bulletins</h1>
            <p>A7 Building, CSPIT – CHARUSAT University Campus</p>
        </div>
    </header>

    <?php include "sidebar.php"; ?>

    <main id="main-content">
        <?php if ($flash = take_flash()): ?>
            <div class="alert-<?= $flash["type"] === "success" ? "success" : "error" ?> flash-message" role="status">
                <i class="bi bi-<?= $flash["type"] === "success" ? "check-circle-fill" : "exclamation-triangle-fill" ?>" aria-hidden="true"></i>
                <p><?= e($flash["message"]) ?></p>
            </div>
        <?php endif; ?>
        <section id="events" aria-labelledby="events-title">
            <h2 id="events-title"><i class="bi bi-calendar-event" aria-hidden="true"></i> Upcoming Campus Events</h2>
            <p>
                <?php if ($student !== null): ?>
                    Register for an event or cancel your registration. Seats are limited where a capacity is shown.
                <?php else: ?>
                    Event registration is available to students with a linked student record.
                <?php endif; ?>
            </p>
            <div class="notice-list event-list-page">
                <?php if (!$events): ?>
                    <p class="section-note">No upcoming events have been published yet.</p>
                <?php endif; ?>
                <?php foreach ($events as $ev): $ts = strtotime($ev["event_date"]); $state = $mine[(int) $ev["id"]] ?? null;
                    $full = $ev["capacity"] !== null && (int) $ev["seats_taken"] >= (int) $ev["capacity"]; ?>
                    <article class="notice event-card" id="event-<?= (int) $ev["id"] ?>">
                        <div class="date-badge" aria-hidden="true"><span class="month"><?= date("M", $ts) ?></span><span class="day"><?= date("d", $ts) ?></span></div>
                        <?php if (event_poster_state($ev) === "ok"): ?>
                            <img class="event-poster" src="poster.php?event=<?= (int) $ev["id"] ?>" alt="Poster: <?= e($ev["title"]) ?>" width="120" height="120">
                        <?php endif; ?>
                        <div class="notice-body">
                            <h3><?= e($ev["title"]) ?></h3>
                            <p><?= e($ev["description"] ?: "Campus event organised at CSPIT, CHARUSAT.") ?></p>
                            <div class="notice-meta">
                                <span><i class="bi bi-calendar3" aria-hidden="true"></i> <time datetime="<?= e($ev["event_date"]) ?>"><?= e(event_when_label($ev)) ?></time></span>
                                <span><i class="bi bi-geo-alt" aria-hidden="true"></i> <?= e($ev["location"]) ?></span>
                                <span><i class="bi bi-people" aria-hidden="true"></i> <?= $ev["capacity"] !== null ? (int) $ev["seats_taken"] . " of " . (int) $ev["capacity"] . " seats taken" : (int) $ev["seats_taken"] . " registered · no seat limit" ?></span>
                                <mark><?= e($ev["category"]) ?></mark>
                                <span class="badge <?= $ev["status"] === "open" ? "badge-success" : "badge-neutral" ?>"><?= e(EVENT_STATUSES[$ev["status"]]) ?></span>
                            </div>
                            <?php if ($student !== null): ?>
                                <div class="event-actions">
                                    <?php if ($state === "registered"): ?>
                                        <span class="badge badge-success"><i class="bi bi-check2-circle" aria-hidden="true"></i> You are registered</span>
                                        <form method="post" action="notifications.php"><?= csrf_field() ?><input type="hidden" name="action" value="cancel"><input type="hidden" name="event_id" value="<?= (int) $ev["id"] ?>"><button type="submit" class="btn-secondary btn-sm">Cancel registration</button></form>
                                    <?php elseif ($state === "attended"): ?>
                                        <span class="badge badge-success">Attended</span>
                                    <?php elseif ($ev["status"] !== "open"): ?>
                                        <span class="badge badge-neutral">Registration closed</span>
                                    <?php elseif ($full): ?>
                                        <span class="badge badge-warning">Event full</span>
                                    <?php else: ?>
                                        <?php if ($state === "cancelled"): ?><span class="badge badge-neutral">Registration cancelled</span><?php endif; ?>
                                        <form method="post" action="notifications.php"><?= csrf_field() ?><input type="hidden" name="action" value="register"><input type="hidden" name="event_id" value="<?= (int) $ev["id"] ?>"><button type="submit" class="btn-sm"><i class="bi bi-person-plus" aria-hidden="true"></i> Register</button></form>
                                    <?php endif; ?>
                                </div>
                            <?php endif; ?>
                        </div>
                    </article>
                <?php endforeach; ?>
            </div>
        </section>

        <?php if ($past): ?>
        <section aria-labelledby="past-title">
            <h2 id="past-title"><i class="bi bi-clock-history" aria-hidden="true"></i> Past Events</h2>
            <div class="notice-list">
                <?php foreach ($past as $ev): $ts = strtotime($ev["event_date"]); $state = $mine[(int) $ev["id"]] ?? null; ?>
                    <article class="notice">
                        <div class="date-badge" aria-hidden="true"><span class="month"><?= date("M", $ts) ?></span><span class="day"><?= date("d", $ts) ?></span></div>
                        <div class="notice-body">
                            <h3><?= e($ev["title"]) ?></h3>
                            <div class="notice-meta">
                                <span><i class="bi bi-calendar3" aria-hidden="true"></i> <time datetime="<?= e($ev["event_date"]) ?>"><?= e(event_when_label($ev)) ?></time></span>
                                <span><i class="bi bi-geo-alt" aria-hidden="true"></i> <?= e($ev["location"]) ?></span>
                                <mark><?= e($ev["category"]) ?></mark>
                                <?php if ($state !== null): ?><span class="badge badge-neutral">Your registration: <?= e($state) ?></span><?php endif; ?>
                            </div>
                        </div>
                    </article>
                <?php endforeach; ?>
            </div>
        </section>
        <?php endif; ?>

        <section aria-labelledby="notices-title">
            <h2 id="notices-title"><i class="bi bi-megaphone" aria-hidden="true"></i> Campus Notices</h2>
            <p>Announcements from CSPIT administration and the CSE department.</p>

            <div class="notice-list">

                <article class="notice">
                    <div class="date-badge" aria-hidden="true"><span class="month">Aug</span><span class="day">22</span></div>
                    <div class="notice-body">
                        <h3>Odoo Hackathon at LDCE on 22nd August!</h3>
                        <p>The upcoming Odoo Hackathon is scheduled at L.D. College of Engineering on <time datetime="2026-08-22">August 22, 2026</time>. CSE students interested in open-source software development and competitive programming are strongly encouraged to participate and form teams!</p>
                        <div class="notice-meta">
                            <span><i class="bi bi-clock-history" aria-hidden="true"></i> Posted <time datetime="2026-08-05">Aug 5, 2026</time></span>
                            <mark>Hackathon Alert</mark>
                        </div>
                    </div>
                </article>

                <article class="notice">
                    <div class="notice-icon" aria-hidden="true"><i class="bi bi-calendar-week"></i></div>
                    <div class="notice-body">
                        <h3>Semester 3 Academic Timetable (With Effect From July 6)</h3>
                        <p>The revised timetable for B.Tech Semester 3 CSE (Division I) has been released. Most regular theory lectures will be conducted in Room 506 (A7 Building). Practical batches A1, B1, and C1 must attend sessions in computer laboratories 631, 632, and 633.</p>
                        <div class="notice-meta">
                            <span><i class="bi bi-clock-history" aria-hidden="true"></i> Posted <time datetime="2026-07-06">July 6, 2026</time></span>
                            <span class="badge badge-neutral">Academic Notice</span>
                        </div>
                    </div>
                </article>

                <article class="notice">
                    <div class="date-badge" aria-hidden="true"><span class="month">Aug</span><span class="day">15</span></div>
                    <div class="notice-body">
                        <h3>Independence Day Celebration & Flag Hoisting</h3>
                        <p>All faculty members and students are invited to celebrate Independence Day on <time datetime="2026-08-15">August 15</time> at the central university grounds.</p>
                        <div class="notice-meta">
                            <span class="badge badge-neutral">Campus Event</span>
                        </div>
                    </div>
                </article>
            </div>
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
