<?php
require_once "db.php";
require_once __DIR__ . "/includes/auth.php";
require_once "audit_logger.php";
require_once "student_profile.php";

$current_user = require_permission("portal.view");

$profile = get_student_profile($conn);

$subjects = ["CSUC201 - FDSA", "ITUE204 - WDF", "CEUE203 - OOP", "ITUC201 - FCN"];

$msg   = "";
$error = "";
if ($_SERVER["REQUEST_METHOD"] === "POST") {
    require_valid_csrf();
    $subj = $_POST["subject"] ?? "";
    // Assignment uploads are not implemented: any attached file is ignored and never written to disk
    $file_sent = ($_FILES["workfile"]["error"] ?? UPLOAD_ERR_NO_FILE) !== UPLOAD_ERR_NO_FILE;

    if (!in_array($subj, $subjects, true)) {
        $error = "Please choose a subject from the list. Nothing was recorded.";
    } else {
        $msg = "Your submission notice for $subj was noted in the activity log only. "
             . ($file_sent ? "File uploads are not available yet, so the attached file was NOT received or stored."
                           : "File uploads are not available yet; please submit your work to the course faculty.");
        log_audit($conn, $_SESSION["user_id"], $_SESSION["username"], "SUBMIT_ASSIGNMENT", "Submission notice (no file stored) for: $subj", "SUCCESS");
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Assignments – Semester 3 (CSPIT)</title>
    <link rel="stylesheet" href="assets/css/global.css?v=10">
    <script src="assets/js/theme.js"></script>
</head>
<body>

<div class="grid-container">
    <header>
        <div class="page-header__icon" aria-hidden="true"><i class="bi bi-pencil-square"></i></div>
        <div class="page-header__text">
            <p class="eyebrow">Academics</p>
            <h1>Semester 3 Academic Assignments</h1>
            <p><?= htmlspecialchars($profile['name']) ?> | B.Tech CSE (3rd Semester) – A7 Building, CSPIT</p>
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
            <h2><i class="bi bi-list-check" aria-hidden="true"></i> Semester 3 Assignments Status</h2>
            <p><strong>Notice:</strong> All theory problem sets and laboratory manuals for Semester 3 are organized by course faculty.</p>
            <h3><i class="bi bi-hourglass-split" aria-hidden="true"></i> Assignments Submission Portal</h3>

            <div class="table-wrap"><table>
                <thead>
                    <tr>
                        <th>Course Code & Subject Name</th>
                        <th>Faculty Coordinator</th>
                        <th>Assignment Status</th>
                        <th>Submission Action</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>CSUC201 – Data Structure and Algorithm (FDSA)</strong></td>
                        <td>Prof. Avani Khokhariya / Dr. Amit Thakkar</td>
                        <td><span class="badge badge-success">Open for Submission</span></td>
                        <td><a href="#upload-section">Submit Solution &rarr;</a></td>
                    </tr>
                    <tr>
                        <td><strong>ITUE204 – Web Development Frameworks (WDF)</strong></td>
                        <td>Prof. Srushti Gajjar / Prof. Vaibhavi Patel</td>
                        <td><span class="badge badge-success">Open for Submission</span></td>
                        <td><a href="#upload-section">Submit Solution &rarr;</a></td>
                    </tr>
                    <tr>
                        <td><strong>CEUE203 – Object Oriented Programming (OOP)</strong></td>
                        <td>Prof. Siddharth Shah / Prof. Akshita Kadam</td>
                        <td><span class="badge badge-neutral">Coming Soon</span></td>
                        <td><em>Scheduled next week</em></td>
                    </tr>
                    <tr>
                        <td><strong>ITUC201 – Computer Networks (FCN)</strong></td>
                        <td>Prof. Harshul Yagnik / Prof. Brinda Patel</td>
                        <td><span class="badge badge-neutral">Coming Soon</span></td>
                        <td><em>Scheduled next week</em></td>
                    </tr>
                </tbody>
            </table></div>
        </section>

        <section id="upload-section">
            <h2><i class="bi bi-upload" aria-hidden="true"></i> Advance Submission Form</h2>
            <p><mark>Uploads unavailable:</mark> file uploads are not available yet. You can record a submission notice for a subject (kept in the activity log), but no file is received or stored. Submit your work to the course faculty.</p>

            <form action="assignments.php" method="POST" enctype="multipart/form-data">
                <?= csrf_field() ?>
                <fieldset>
                    <legend>Submit Assignment Solution</legend>
                    <p>
                        <label for="sub-select">Select Subject:</label>
                        <select id="sub-select" name="subject" required>
                            <option value="">-- Choose Subject --</option>
                            <option value="CSUC201 - FDSA">CSUC201 – Data Structure and Algorithm (FDSA)</option>
                            <option value="ITUE204 - WDF">ITUE204 – Web Development Frameworks (WDF)</option>
                            <option value="CEUE203 - OOP">CEUE203 – Object Oriented Programming (OOP)</option>
                            <option value="ITUC201 - FCN">ITUC201 – Fundamentals of Computer Networks (FCN)</option>
                        </select>
                    </p>
                    <p>
                        <label for="workfile">Select Solution File (PDF/ZIP):</label>
                        <input type="file" id="workfile" name="workfile" disabled aria-describedby="workfile-note">
                        <small id="workfile-note">File uploads are not available yet; no file can be stored.</small>
                    </p>
                    <p>
                        <button type="submit"><i class="bi bi-send-check" aria-hidden="true"></i> Record Submission Notice</button>
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
