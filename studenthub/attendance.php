<?php
require_once "db.php";
require_once __DIR__ . "/includes/auth.php";
require_once "audit_logger.php";
require_once "student_profile.php";

$current_user = require_permission("portal.view");

$profile = get_student_profile($conn);

$msg = "";
if ($_SERVER["REQUEST_METHOD"] === "POST") {
    require_valid_csrf();
    $ldate   = $_POST["ldate"] ?? "";
    $ltype   = $_POST["ltype"] ?? "";
    $lreason = trim($_POST["lreason"] ?? "");
    $msg = "Leave application submitted successfully for date: " . htmlspecialchars($ldate);
    log_audit($conn, $_SESSION["user_id"], $_SESSION["username"], "APPLY_LEAVE", "Leave requested: $ltype on $ldate", "SUCCESS");
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Attendance Record – CSPIT Charusat</title>
    <link rel="stylesheet" href="assets/css/global.css?v=10">
    <script src="assets/js/theme.js"></script>
</head>
<body>

<div class="grid-container">
    <header>
        <div class="page-header__icon" aria-hidden="true"><i class="bi bi-calendar-check"></i></div>
        <div class="page-header__text">
            <p class="eyebrow">Academics</p>
            <h1>Semester 3 Attendance Record</h1>
            <p><?= htmlspecialchars($profile['name']) ?> (<?= htmlspecialchars($profile['enrollment_no']) ?>) | Computer Science & Engineering – CSPIT, CHARUSAT</p>
        </div>
    </header>

    <?php include "sidebar.php"; ?>

    <main id="main-content">
        <?php if (!empty($msg)): ?>
            <div class="alert-success" role="status">
                <i class="bi bi-check-circle-fill" aria-hidden="true"></i> <p><?= $msg ?></p>
            </div>
        <?php endif; ?>

        <section>
            <h2><i class="bi bi-calendar-check" aria-hidden="true"></i> Subject-wise Attendance (Average: 94.0%)</h2>
            <p><span class="badge badge-sample"><i class="bi bi-info-circle" aria-hidden="true"></i> Sample / demo data</span> the lecture counts and percentages below are placeholders, not actual attendance records.</p>
            <p>University mandate: Minimum 75% attendance is required to appear for end-semester examinations.</p>
            
            <div class="table-wrap"><table>
                <thead>
                    <tr>
                        <th>Course Code & Subject</th>
                        <th>Lectures Held</th>
                        <th>Lectures Attended</th>
                        <th>Percentage</th>
                        <th>Meter Indicator</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>CSUC201 – Data Structure & Algorithm (FDSA)</strong></td>
                        <td>20</td>
                        <td>19</td>
                        <td>95%</td>
                        <td><meter value="95" min="0" max="100">95%</meter></td>
                    </tr>
                    <tr>
                        <td><strong>ITUE204 – Web Development Frameworks (WDF)</strong></td>
                        <td>25</td>
                        <td>24</td>
                        <td>96%</td>
                        <td><meter value="96" min="0" max="100">96%</meter></td>
                    </tr>
                    <tr>
                        <td><strong>CEUE203 – Object Oriented Programming (OOP)</strong></td>
                        <td>15</td>
                        <td>14</td>
                        <td>93.3%</td>
                        <td><meter value="93.3" min="0" max="100">93%</meter></td>
                    </tr>
                    <tr>
                        <td><strong>ITUC201 – Computer Networks (FCN)</strong></td>
                        <td>25</td>
                        <td>23</td>
                        <td>92%</td>
                        <td><meter value="92" min="0" max="100">92%</meter></td>
                    </tr>
                    <tr>
                        <td><strong>MSUD203 – Discrete Mathematics (MATHS)</strong></td>
                        <td>17</td>
                        <td>16</td>
                        <td>94.1%</td>
                        <td><meter value="94.1" min="0" max="100">94%</meter></td>
                    </tr>
                    <tr>
                        <td><strong>HSUV201 – Creativity, Problem Solving (HS)</strong></td>
                        <td>16</td>
                        <td>15</td>
                        <td>93.7%</td>
                        <td><meter value="93.7" min="0" max="100">94%</meter></td>
                    </tr>
                </tbody>
                <tfoot>
                    <tr>
                        <th>Total Average:</th>
                        <th>118</th>
                        <th>111</th>
                        <th>94.0%</th>
                        <th><meter value="94" min="0" max="100">94%</meter> Excellent</th>
                    </tr>
                </tfoot>
            </table></div>
        </section>

        <section>
            <h2><i class="bi bi-envelope-paper" aria-hidden="true"></i> Apply for Student Leave</h2>
            <form action="attendance.php" method="POST">
                <?= csrf_field() ?>
                <fieldset>
                    <legend>Leave Application Form</legend>
                    <p>
                        <label for="ldate">Date of Absence:</label>
                        <input type="date" id="ldate" name="ldate" value="<?= date('Y-m-d') ?>" required>
                    </p>
                    <p>
                        <label for="ltype">Leave Reason / Type:</label>
                        <select id="ltype" name="ltype" required>
                            <option value="Hackathon / Technical Competition (On Duty)">Hackathon / Technical Competition (On Duty)</option>
                            <option value="Medical / Sick Leave">Medical / Sick Leave</option>
                            <option value="Personal Emergency">Personal Emergency</option>
                        </select>
                    </p>
                    <p>
                        <label for="lreason">Details & Remarks:</label>
                        <textarea id="lreason" name="lreason" rows="3" required placeholder="e.g., Attending Odoo Hackathon at LDCE on Aug 22"></textarea>
                    </p>
                    <p>
                        <button type="submit"><i class="bi bi-send" aria-hidden="true"></i> Submit Leave Request</button>
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
