<?php
session_start();
require_once "db.php";

$is_logged_in = isset($_SESSION["user_id"]);
$user_role    = $_SESSION["role"] ?? "guest";
$username     = $_SESSION["username"] ?? "";

// Fetch upcoming campus alerts from events table
$events = [];
$e_res = $conn->query("SELECT id, title, event_date, location, category FROM events ORDER BY event_date ASC LIMIT 3");
if ($e_res) {
    while ($row = $e_res->fetch_assoc()) {
        $events[] = $row;
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StudentHub - CSPIT Charusat Portal</title>
    <link rel="stylesheet" href="assets/css/home.css?v=1">
    <script src="assets/js/theme.js"></script>
</head>
<body>

    <!-- Notification Banner (Practical 4) -->
    <div class="notification-banner" id="notification-banner" role="status">
        <i class="bi bi-stars" aria-hidden="true"></i>
        <span>Welcome to the redesigned StudentHub portal – now with light and dark themes.</span>
        <button class="close-banner" id="close-banner" aria-label="Close notification">&times;</button>
    </div>

    <header class="site-header">
        <div class="topnav">
            <a class="site-brand" href="index.php">
                <span class="brand-mark" aria-hidden="true"><i class="bi bi-mortarboard-fill"></i></span>
                <span><strong>StudentHub</strong><small>CSPIT · CHARUSAT</small></span>
            </a>
            <button class="theme-toggle" id="theme-toggle-btn" type="button"><i class="bi bi-moon-stars" aria-hidden="true"></i> Dark</button>
            <button class="hamburger" id="hamburger-menu" type="button" aria-label="Toggle navigation menu"><i class="bi bi-list" aria-hidden="true"></i></button>

            <!-- Navigation (collapses behind the hamburger on phones – Practical 4) -->
            <nav class="hero-nav" aria-label="Main navigation">
                <ul id="nav-links">
                    <li><a href="index.php" class="active" aria-current="page">Home</a></li>
                    <?php if ($is_logged_in): ?>
                        <li><a href="dashboard.php">Dashboard</a></li>
                        <li><a href="profile.php">My Profile</a></li>
                        <li><a href="courses.php">Courses</a></li>
                        <li><a href="attendance.php">Attendance</a></li>
                        <?php if ($user_role === "admin"): ?>
                            <li><a href="admin_dashboard.php" class="nav-admin"><i class="bi bi-shield-lock" aria-hidden="true"></i> Admin Console</a></li>
                        <?php endif; ?>
                        <li><a href="logout.php">Logout</a></li>
                    <?php else: ?>
                        <li><a href="login.php">Login</a></li>
                        <li><a href="register.php">Register</a></li>
                        <li><a href="dashboard.php">Dashboard</a></li>
                        <li><a href="contact.php">Contact Us</a></li>
                    <?php endif; ?>
                </ul>
            </nav>
        </div>

        <div class="hero">
            <div>
                <p class="eyebrow">Chandubhai S. Patel Institute of Technology</p>
                <h1>StudentHub – CSPIT</h1>
                <p>Your portal for Computer Science &amp; Engineering at CHARUSAT: timetable, subjects, attendance, results and campus notices in one place.</p>
                <div class="hero-cta">
                    <?php if ($is_logged_in): ?>
                        <a class="btn" href="dashboard.php"><i class="bi bi-grid-1x2" aria-hidden="true"></i> Go to Dashboard</a>
                    <?php else: ?>
                        <a class="btn" href="login.php"><i class="bi bi-box-arrow-in-right" aria-hidden="true"></i> Sign In</a>
                        <a class="btn btn-secondary" href="register.php"><i class="bi bi-person-plus" aria-hidden="true"></i> Create Account</a>
                    <?php endif; ?>
                </div>
            </div>
            <div class="hero-panel">
                <h2><i class="bi bi-lightning-charge" aria-hidden="true"></i> At a glance</h2>
                <ul>
                    <li><i class="bi bi-geo-alt" aria-hidden="true"></i> A7 Building, Room 506 – Division I</li>
                    <li><i class="bi bi-journal-bookmark" aria-hidden="true"></i> 6 subjects · 21 credits in Semester 3</li>
                    <li><i class="bi bi-shield-check" aria-hidden="true"></i> Minimum 75% attendance for exams</li>
                </ul>
            </div>
        </div>
    </header>

    <div class="main-container">
        <main>
            <section>
                <h2><i class="bi bi-house-heart" aria-hidden="true"></i> Welcome to Student Portal</h2>
                <p>Your personalized portal for Computer Science &amp; Engineering (CSE) at CSPIT, A7 Building, CHARUSAT. Access your timetable, 3rd semester subjects, attendance records, and campus announcements.</p>
                <button class="btn-action" id="open-modal-btn" type="button"><i class="bi bi-book" aria-hidden="true"></i> View Portal Guidelines</button>
            </section>

            <!-- Campus Image Slider (Practical 4) -->
            <div class="slider-container">
                <button class="slider-btn slider-prev" id="slider-prev" aria-label="Previous slide"><i class="bi bi-chevron-left" aria-hidden="true"></i></button>
                <div class="slide">
                    <img src="https://images.unsplash.com/photo-1541339907198-e08756dedf3f?ixlib=rb-4.0.3&auto=format&fit=crop&w=1200&q=80" alt="University Campus">
                    <div class="slide-text">
                        <h3><i class="bi bi-mortarboard" aria-hidden="true"></i> Welcome to Semester 3 CSE!</h3>
                        <p>Experience the best learning environment at CSPIT, CHARUSAT.</p>
                    </div>
                </div>
                <div class="slide">
                    <img src="https://images.unsplash.com/photo-1531482615713-2afd69097998?ixlib=rb-4.0.3&auto=format&fit=crop&w=1200&q=80" alt="Hackathon Team">
                    <div class="slide-text">
                        <h3><i class="bi bi-rocket-takeoff" aria-hidden="true"></i> Upcoming Odoo Hackathon</h3>
                        <p>Join the university coding team at LDCE this semester!</p>
                    </div>
                </div>
                <div class="slide">
                    <img src="https://images.unsplash.com/photo-1517694712202-14dd9538aa97?ixlib=rb-4.0.3&auto=format&fit=crop&w=1200&q=80" alt="Coding Labs">
                    <div class="slide-text">
                        <h3><i class="bi bi-calendar-week" aria-hidden="true"></i> Academic Timetable &amp; Lab Sessions</h3>
                        <p>Access Room 506 division schedule and subject outlines.</p>
                    </div>
                </div>
                <button class="slider-btn slider-next" id="slider-next" aria-label="Next slide"><i class="bi bi-chevron-right" aria-hidden="true"></i></button>
            </div>

            <section>
                <h2><i class="bi bi-compass" aria-hidden="true"></i> Portal Navigation</h2>
                <div class="articles-flex">
                    <article>
                        <span class="card-icon" aria-hidden="true"><i class="bi bi-journal-bookmark"></i></span>
                        <h3>Semester 3 Subjects &amp; Timetable</h3>
                        <p>Check your enrolled CSE subjects including FDSA, WDF, OOP, FCN, and Discrete Maths.</p>
                        <p><a href="courses.php">View Courses &rarr;</a></p>
                    </article>

                    <article>
                        <span class="card-icon" aria-hidden="true"><i class="bi bi-bar-chart-line"></i></span>
                        <h3>Attendance &amp; CGPA</h3>
                        <p>Monitor your average attendance (94%) and past semester marksheets (CGPA 8.05). <span class="badge badge-sample">Sample data</span></p>
                        <p><a href="attendance.php">Check Attendance</a> · <a href="results.php">View Results &rarr;</a></p>
                    </article>

                    <article>
                        <span class="card-icon" aria-hidden="true"><i class="bi bi-trophy"></i></span>
                        <h3>Assignments &amp; Competitions</h3>
                        <p>Semester 3 assignments and problem sets. Stay updated with campus hackathons and activities.</p>
                        <p><a href="assignments.php">View Assignments</a> · <a href="achievements.php">Achievements &rarr;</a></p>
                    </article>
                </div>
            </section>

            <!-- Quick FAQ (Practical 4) -->
            <section>
                <h2><i class="bi bi-question-circle" aria-hidden="true"></i> Quick FAQ</h2>
                <div class="faq-item">
                    <button class="faq-question" type="button">Where is the CSE Department located? <i class="bi bi-chevron-down" aria-hidden="true"></i></button>
                    <div class="faq-answer">The Department of Computer Science &amp; Engineering is located in A7 Building, CSPIT, CHARUSAT Campus.</div>
                </div>
                <div class="faq-item">
                    <button class="faq-question" type="button">How do I check my 3rd semester schedule? <i class="bi bi-chevron-down" aria-hidden="true"></i></button>
                    <div class="faq-answer">Log into your <a href="dashboard.php">Dashboard</a> to check lecture rooms (Room 506) and practical batch schedules.</div>
                </div>
                <div class="faq-item">
                    <button class="faq-question" type="button">Who do I contact for portal queries? <i class="bi bi-chevron-down" aria-hidden="true"></i></button>
                    <div class="faq-answer">You can reach out via our <a href="contact.php">Contact Us page</a> or email support@charusat.edu.in.</div>
                </div>
            </section>
        </main>

        <aside>
            <div class="card-alert">
                <h2><i class="bi bi-megaphone" aria-hidden="true"></i> Latest Campus Alerts</h2>
                <ul>
                    <?php if (!empty($events)): ?>
                        <?php foreach ($events as $ev): ?>
                            <li>
                                <time datetime="<?= htmlspecialchars($ev['event_date']) ?>"><?= date("M d, Y", strtotime($ev['event_date'])) ?></time>
                                <strong><?= htmlspecialchars($ev['title']) ?></strong> · <?= htmlspecialchars($ev['location']) ?>
                            </li>
                        <?php endforeach; ?>
                    <?php else: ?>
                        <li><time datetime="2026-08-22">August 22, 2026</time> <strong>Odoo Hackathon at LDCE!</strong> Get your team ready and register before the deadline.</li>
                        <li><time datetime="2026-08-15">August 15, 2026</time> Independence Day Celebration at CHARUSAT Campus.</li>
                    <?php endif; ?>
                </ul>
                <p><a href="notifications.php">See all announcements &rarr;</a></p>
            </div>
        </aside>
    </div>

    <footer class="site-footer">
        <p>&copy; <time datetime="2026">2026</time> StudentHub – CSPIT, CHARUSAT. All rights reserved.</p>
        <address>
            A7 Building, CSPIT, CHARUSAT University Campus, Changa, Gujarat.<br>
            Email: <a href="mailto:support@charusat.edu.in">support@charusat.edu.in</a> | Phone: <a href="tel:+91-2697-265011">+91-2697-265011</a>
        </address>
    </footer>

    <!-- Portal Guidelines Modal (Practical 4) -->
    <div class="modal-overlay" id="custom-modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">
        <div class="modal-content">
            <button class="close-modal" id="close-modal-btn" type="button" aria-label="Close guidelines">&times;</button>
            <h2 id="modal-title" style="margin-top:0;">Portal Guidelines</h2>
            <p>Welcome to StudentHub! Please review the university academic standards:</p>
            <ul>
                <li>Maintain a minimum of <strong>75% attendance</strong> across all enrolled subjects.</li>
                <li>Submit laboratory assignments before designated cutoff dates.</li>
                <li>Report administrative discrepancies directly to the A7 CSE helpdesk.</li>
            </ul>
            <button class="btn-action" type="button" style="width:100%;" onclick="document.getElementById('custom-modal').classList.remove('show-modal')">I Understand</button>
        </div>
    </div>

    <script src="assets/js/script.js"></script>
</body>
</html>
