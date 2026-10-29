<?php
session_start();
require_once "db.php";
require_once "audit_logger.php";
require_once "student_profile.php";

if (!isset($_SESSION["user_id"])) {
    header("Location: login.php?error=Please login to access your student dashboard.");
    exit();
}

$user_id  = $_SESSION["user_id"];
$username = $_SESSION["username"];
$email    = $_SESSION["email"] ?? "";
$role     = $_SESSION["role"] ?? "student";

// Log student dashboard view
log_audit($conn, $user_id, $username, "VIEW_DASHBOARD", "Student viewed academic dashboard.", "SUCCESS");

// Fetch student profile details from students table
$profile        = get_student_profile($conn);
$student_name   = $profile["name"];
$enrollment_no  = $profile["enrollment_no"];
$course         = "B.Tech CSE";
if ($profile["course"] !== "") {
    $course = "B.Tech " . (strpos($profile["course"], "Computer") !== false ? "CSE" : $profile["course"]);
}
$semester       = ordinal_suffix($profile["semester"]) . " Semester";

// Fetch upcoming campus events from events table
$events = [];
$e_res = $conn->query("SELECT id, title, event_date, location, description FROM events ORDER BY event_date ASC LIMIT 2");
if ($e_res) {
    while ($ev = $e_res->fetch_assoc()) {
        $events[] = $ev;
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - <?= htmlspecialchars($student_name) ?> (CSPIT)</title>
    <link rel="stylesheet" href="assets/css/global.css?v=7">
    <script src="assets/js/theme.js"></script>
</head>
<body>

<div class="grid-container">
    <header class="hero">
        <div class="page-header__text">
            <p class="eyebrow">Student Dashboard</p>
            <h1>Welcome back, <?= htmlspecialchars($student_name) ?></h1>
            <p>Here is your semester at a glance – CSPIT, CHARUSAT.</p>
            <div class="header-meta">
                <span class="chip"><i class="bi bi-person-badge" aria-hidden="true"></i> Enrollment <mark><?= htmlspecialchars($enrollment_no) ?></mark></span>
                <span class="chip"><i class="bi bi-mortarboard" aria-hidden="true"></i> <?= htmlspecialchars($course) ?> (<?= htmlspecialchars($semester) ?>)</span>
                <span class="chip"><i class="bi bi-geo-alt" aria-hidden="true"></i> A7 Building, Room 506</span>
            </div>
        </div>
        <div class="hero-actions">
            <a class="btn" href="#timetable"><i class="bi bi-clock" aria-hidden="true"></i> Timetable</a>
            <a class="btn btn-secondary" href="results.php"><i class="bi bi-bar-chart-line" aria-hidden="true"></i> Results</a>
        </div>
    </header>

    <?php include "sidebar.php"; ?>

    <main id="main-content">
        <p class="section-note"><span class="badge badge-sample"><i class="bi bi-info-circle" aria-hidden="true"></i> Sample / demo data</span> The attendance and CGPA figures below are placeholders, not actual academic results.</p>

        <div class="stat-grid">
            <article class="stat-card">
                <div class="stat-top">
                    <span class="stat-label">Overall Attendance</span>
                    <span class="stat-icon emerald"><i class="bi bi-calendar-check" aria-hidden="true"></i></span>
                </div>
                <span class="stat-value">94.0% <mark>Sample</mark></span>
                <meter value="94" min="0" max="100" aria-label="Attendance 94 percent (sample)">94%</meter>
                <a href="attendance.php">View subjects &rarr;</a>
            </article>
            <article class="stat-card">
                <div class="stat-top">
                    <span class="stat-label">Overall CGPA</span>
                    <span class="stat-icon violet"><i class="bi bi-bar-chart-line" aria-hidden="true"></i></span>
                </div>
                <span class="stat-value">8.05 <mark>Sample</mark></span>
                <meter value="8.05" min="0" max="10" aria-label="CGPA 8.05 out of 10 (sample)">8.05</meter>
                <a href="results.php">Grade cards &rarr;</a>
            </article>
            <article class="stat-card">
                <div class="stat-top">
                    <span class="stat-label">Enrolled Credits</span>
                    <span class="stat-icon"><i class="bi bi-journal-bookmark" aria-hidden="true"></i></span>
                </div>
                <span class="stat-value">21</span>
                <progress value="21" max="21" aria-label="21 of 21 credits enrolled">100%</progress>
                <p class="stat-note">6 subjects · <a href="courses.php">View syllabus &rarr;</a></p>
            </article>
            <article class="stat-card">
                <div class="stat-top">
                    <span class="stat-label">Assignments</span>
                    <span class="stat-icon amber"><i class="bi bi-pencil-square" aria-hidden="true"></i></span>
                </div>
                <span class="stat-value">Coming soon</span>
                <progress value="0" max="100" aria-label="Assignments progress 0 percent">0%</progress>
                <a href="assignments.php">Check updates &rarr;</a>
            </article>
        </div>

        <section id="timetable">
            <h2><i class="bi bi-clock" aria-hidden="true"></i> Semester 3 Timetable</h2>
            <p>Division I · Room 506 · Department of Computer Science & Engineering (CSPIT, A7 Building)</p>
            <div class="table-wrap"><table>
                <thead>
                    <tr>
                        <th>Day / Time</th>
                        <th>09:10 AM - 10:10 AM</th>
                        <th>10:10 AM - 11:10 AM</th>
                        <th>11:10 AM - 12:10 PM</th>
                        <th>12:10 PM - 02:10 PM (After Lunch)</th>
                        <th>02:20 PM - 04:20 PM</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>Monday</strong></td>
                        <td>FDSA - Room 506 (VMP)</td>
                        <td>FCN - Room 506 (HYY)</td>
                        <td>Lunch Break</td>
                        <td>HS - Room 506 (ADK)</td>
                        <td>Labs: A1-FDSA / B1-FCN / C1-WDF</td>
                    </tr>
                    <tr>
                        <td><strong>Tuesday</strong></td>
                        <td>MATHS - Room 506 (PM)</td>
                        <td>FDSA - Room 506 (ART)</td>
                        <td>Lunch Break</td>
                        <td>Labs: A1-FCN / B1-WDF / C1-FCN</td>
                        <td>FCN (HYY) & WDF (SRG) - Room 506</td>
                    </tr>
                    <tr>
                        <td><strong>Wednesday</strong></td>
                        <td>MATHS - Room 506 (PM)</td>
                        <td>OOP - Room 506 (SSS)</td>
                        <td>Lunch Break</td>
                        <td>Labs: A1-WDF / B1-WDF / C1-FDSA</td>
                        <td>WDF (SRG) & FDSA (VMP) - Room 506</td>
                    </tr>
                    <tr>
                        <td><strong>Thursday</strong></td>
                        <td>WDF - Room 506 (VYP)</td>
                        <td>FCN - Room 506 (HYY)</td>
                        <td>Lunch Break</td>
                        <td>Labs: A1-WDF / B1-FDSA / C1-WDF</td>
                        <td>Labs: A1-OOP / B1-WDF / C1-OOP</td>
                    </tr>
                    <tr>
                        <td><strong>Friday</strong></td>
                        <td>MATHS - Room 506 (PM)</td>
                        <td>FDSA - Room 506 (ART)</td>
                        <td>Lunch Break</td>
                        <td>Counselling Sessions (Rooms 631-633)</td>
                        <td>FCN (HYY) & OOP (SSS) - Room 506</td>
                    </tr>
                </tbody>
            </table></div>
        </section>
    </main>

    <aside>
        <h2><i class="bi bi-calendar-event" aria-hidden="true"></i> Upcoming Events</h2>
        <div class="event-list">
        <?php if (!empty($events)): ?>
            <?php foreach ($events as $ev): ?>
                <?php $ts = strtotime($ev['event_date']); ?>
                <article class="notice">
                    <div class="date-badge" aria-hidden="true"><span class="month"><?= date("M", $ts) ?></span><span class="day"><?= date("d", $ts) ?></span></div>
                    <div class="notice-body">
                        <h3><?= htmlspecialchars($ev['title']) ?></h3>
                        <p><?= htmlspecialchars($ev['description'] ?: 'Join campus hackathons and activities.') ?></p>
                        <div class="notice-meta">
                            <span><i class="bi bi-calendar3" aria-hidden="true"></i> <time datetime="<?= htmlspecialchars($ev['event_date']) ?>"><?= date("M d, Y", $ts) ?></time></span>
                            <span><i class="bi bi-geo-alt" aria-hidden="true"></i> <?= htmlspecialchars($ev['location']) ?></span>
                        </div>
                    </div>
                </article>
            <?php endforeach; ?>
        <?php else: ?>
            <div class="empty-state">
                <i class="bi bi-calendar-x" aria-hidden="true"></i>
                <p>No upcoming events have been published yet.</p>
            </div>
        <?php endif; ?>
        </div>
        <p><a href="notifications.php">See all notices &rarr;</a></p>
    </aside>

    <footer>
        <p>&copy; <time datetime="2026">2026</time> StudentHub – CSPIT, CHARUSAT. All rights reserved.</p>
        <address>
            A7 Building, CSPIT | Email: <a href="mailto:support@charusat.edu.in">support@charusat.edu.in</a> | Phone: <a href="tel:+91-2697-265011">+91-2697-265011</a>
        </address>
    </footer>
</div>

</body>
</html>
