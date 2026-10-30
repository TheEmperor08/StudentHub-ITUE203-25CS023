<?php
require_once "db.php";
require_once __DIR__ . "/includes/auth.php";
require_once "student_profile.php";
$current_user = require_permission("portal.view");

$profile = get_student_profile($conn);
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Academic Results – <?= htmlspecialchars($profile['name']) ?> (CSPIT)</title>
    <link rel="stylesheet" href="assets/css/global.css?v=9">
    <script src="assets/js/theme.js"></script>
</head>
<body>

<div class="grid-container">
    <header>
        <div class="page-header__icon" aria-hidden="true"><i class="bi bi-bar-chart-line"></i></div>
        <div class="page-header__text">
            <p class="eyebrow">Academics</p>
            <h1>Academic Examination Results</h1>
            <p><?= htmlspecialchars($profile['name']) ?> | Enrollment: <mark><?= htmlspecialchars($profile['enrollment_no']) ?></mark> | B.Tech CSE (CSPIT, CHARUSAT)</p>
        </div>
    </header>

    <?php include "sidebar.php"; ?>

    <main id="main-content">
        <section>
            <h2><i class="bi bi-graph-up" aria-hidden="true"></i> Cumulative Academic Performance</h2>
            <p><span class="badge badge-sample"><i class="bi bi-info-circle" aria-hidden="true"></i> Sample / demo data</span> all CGPA, SGPA and grade figures on this page are placeholders, not actual academic results.</p>
            <div class="stat-grid">
                <article class="stat-card">
                    <div class="stat-top"><span class="stat-label">Overall CGPA</span><span class="stat-icon violet"><i class="bi bi-award" aria-hidden="true"></i></span></div>
                    <span class="stat-value">8.05 <mark>Sample</mark></span>
                    <meter value="8.05" min="0" max="10" aria-label="CGPA 8.05 out of 10 (sample)">8.05</meter>
                    <p class="stat-note">First Class with Distinction</p>
                </article>
                <article class="stat-card">
                    <div class="stat-top"><span class="stat-label">Semester 1 SGPA</span><span class="stat-icon"><i class="bi bi-1-circle" aria-hidden="true"></i></span></div>
                    <span class="stat-value">8.32 <mark>Sample</mark></span>
                    <meter value="8.32" min="0" max="10" aria-label="Semester 1 SGPA 8.32 (sample)">8.32</meter>
                </article>
                <article class="stat-card">
                    <div class="stat-top"><span class="stat-label">Semester 2 SGPA</span><span class="stat-icon emerald"><i class="bi bi-2-circle" aria-hidden="true"></i></span></div>
                    <span class="stat-value">7.77 <mark>Sample</mark></span>
                    <meter value="7.77" min="0" max="10" aria-label="Semester 2 SGPA 7.77 (sample)">7.77</meter>
                </article>
            </div>
            
            <div class="table-wrap"><table>
                <thead>
                    <tr>
                        <th>Semester</th>
                        <th>Institute</th>
                        <th>Semester SGPA</th>
                        <th>Cumulative CGPA</th>
                        <th>Result Status</th>
                        <th>Marksheet</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>Semester 1</strong></td>
                        <td>CSPIT – CHARUSAT</td>
                        <td><strong>8.32</strong></td>
                        <td>8.32</td>
                        <td><span class="badge badge-success">PASSED</span></td>
                        <td><a href="#grade-summary">View Grade Card &rarr;</a></td>
                    </tr>
                    <tr>
                        <td><strong>Semester 2</strong></td>
                        <td>CSPIT – CHARUSAT</td>
                        <td><strong>7.77</strong></td>
                        <td><strong>8.05</strong></td>
                        <td><span class="badge badge-success">PASSED</span></td>
                        <td><a href="#grade-summary">View Grade Card &rarr;</a></td>
                    </tr>
                    <tr>
                        <td><strong>Semester 3 (Current)</strong></td>
                        <td>CSPIT – CHARUSAT (A7 Building)</td>
                        <td><em>Ongoing</em></td>
                        <td><em>Ongoing</em></td>
                        <td><strong>21 Credits Registered</strong></td>
                        <td><em>In Progress</em></td>
                    </tr>
                </tbody>
            </table></div>
        </section>

        <section id="grade-summary">
            <h2><i class="bi bi-card-checklist" aria-hidden="true"></i> Semester 2 Grade Summary (Last Completed Semester)</h2>
            <p>Semester 2 SGPA: <strong>7.77 / 10.0</strong> | Status: Regular Passed</p>

            <div class="table-wrap"><table>
                <thead>
                    <tr>
                        <th>Subject Category</th>
                        <th>Evaluation Type</th>
                        <th>Result Grade</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>Core Engineering Subjects</strong></td>
                        <td>Theory & Practical Exams</td>
                        <td>AA / AB</td>
                    </tr>
                    <tr>
                        <td><strong>Mathematics & Foundation</strong></td>
                        <td>End Semester Theory</td>
                        <td>AB / BB</td>
                    </tr>
                    <tr>
                        <td><strong>Laboratory & Workshops</strong></td>
                        <td>Practical Evaluation</td>
                        <td>AA</td>
                    </tr>
                </tbody>
            </table></div>
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
