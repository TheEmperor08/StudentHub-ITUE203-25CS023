<?php
require_once "db.php";
require_once __DIR__ . "/includes/auth.php";
$current_user = require_permission("portal.view");

$events = [];
$e_res = $conn->query("SELECT id, title, category, event_date, location, description FROM events ORDER BY event_date ASC");
if ($e_res) {
    while ($r = $e_res->fetch_assoc()) {
        $events[] = $r;
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Campus Notifications – CSPIT Charusat</title>
    <link rel="stylesheet" href="assets/css/global.css?v=8">
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
        <section>
            <h2><i class="bi bi-megaphone" aria-hidden="true"></i> Latest Campus Notices & Events</h2>
            <p>Announcements from CSPIT administration and the CSE department.</p>

            <div class="notice-list">
            <?php if (!empty($events)): ?>
                <?php foreach ($events as $ev): ?>
                    <?php $ts = strtotime($ev['event_date']); ?>
                    <article class="notice">
                        <div class="date-badge" aria-hidden="true"><span class="month"><?= date("M", $ts) ?></span><span class="day"><?= date("d", $ts) ?></span></div>
                        <div class="notice-body">
                            <h3><?= htmlspecialchars($ev['title']) ?></h3>
                            <p><?= htmlspecialchars($ev['description'] ?: 'Official announcement from CSPIT administration.') ?></p>
                            <div class="notice-meta">
                                <span><i class="bi bi-calendar3" aria-hidden="true"></i> <time datetime="<?= htmlspecialchars($ev['event_date']) ?>"><?= date("M d, Y", $ts) ?></time></span>
                                <span><i class="bi bi-geo-alt" aria-hidden="true"></i> <?= htmlspecialchars($ev['location']) ?></span>
                                <mark><?= htmlspecialchars($ev['category']) ?></mark>
                            </div>
                        </div>
                    </article>
                <?php endforeach; ?>
            <?php endif; ?>

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
