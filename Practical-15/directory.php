<?php
require_once "db.php";
require_once __DIR__ . "/includes/auth.php";
$current_user = require_permission("portal.view");

$students = [];
// Deactivated (soft-deleted) records stay in the database but are not listed in the directory
$res = $conn->query("SELECT enrollment_no, name, email, course, semester, gender FROM students WHERE COALESCE(TRIM(status), '') <> 'Inactive' ORDER BY id ASC");
if ($res) {
    while ($r = $res->fetch_assoc()) {
        $students[] = $r;
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Campus Data Directory – StudentHub</title>
    <link rel="stylesheet" href="assets/css/global.css?v=11">
    <script src="assets/js/theme.js"></script>
</head>
<body>

<div class="grid-container">
    <header>
        <div class="page-header__icon" aria-hidden="true"><i class="bi bi-people"></i></div>
        <div class="page-header__text">
            <p class="eyebrow">Campus</p>
            <h1>Campus Data Directory</h1>
            <p>Dynamic Student & Academic Directory – CSPIT, CHARUSAT</p>
        </div>
    </header>

    <?php include "sidebar.php"; ?>

    <main id="main-content">
        <section>
            <h2><i class="bi bi-people" aria-hidden="true"></i> Enrolled Students Directory (Live MySQL)</h2>
            <p>Search across names, enrollment numbers and departments.</p>
            <div class="search-field">
                <i class="bi bi-search" aria-hidden="true"></i>
                <label for="liveSearch" class="sr-only">Search the directory</label>
                <input type="text" id="liveSearch" placeholder="Search student name, enrollment, or department..." onkeyup="filterTable()">
            </div>
            <?php if (empty($students)): ?>
                <div class="empty-state"><i class="bi bi-person-x" aria-hidden="true"></i><p>No student records are available yet.</p></div>
            <?php endif; ?>

            <div class="table-wrap"><table id="studentDirTable">
                <thead>
                    <tr>
                        <th>Enrollment No</th>
                        <th>Student Name</th>
                        <th>Email Address</th>
                        <th>Department</th>
                        <th>Semester</th>
                        <th>Gender</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($students as $st): ?>
                        <tr>
                            <td><mark><?= htmlspecialchars($st['enrollment_no'] ?: '—') ?></mark></td>
                            <td><strong><?= htmlspecialchars($st['name']) ?></strong></td>
                            <td><a href="mailto:<?= htmlspecialchars($st['email']) ?>"><?= htmlspecialchars($st['email']) ?></a></td>
                            <td><?= htmlspecialchars($st['course']) ?></td>
                            <td>Sem <?= htmlspecialchars($st['semester'] ?: 3) ?></td>
                            <td><?= htmlspecialchars($st['gender']) ?></td>
                        </tr>
                    <?php endforeach; ?>
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

<script>
function filterTable() {
    let input = document.getElementById("liveSearch").value.toUpperCase();
    let rows = document.getElementById("studentDirTable").getElementsByTagName("tr");
    for (let i = 1; i < rows.length; i++) {
        let text = rows[i].textContent || rows[i].innerText;
        rows[i].style.display = (text.toUpperCase().indexOf(input) > -1) ? "" : "none";
    }
}
</script>
</body>
</html>
