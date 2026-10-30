<?php
// StudentHub – Practical 11: soft delete. GET delete.php?id=N only shows a confirmation page; the change happens
// after the user confirms with a POST (form token required). The record is never removed: its status becomes
// 'inactive' and deleted_at stores the time. There is no permanent DELETE anywhere in the application.
declare(strict_types=1);
require_once __DIR__ . '/includes/functions.php';

start_app();
$db = get_db();

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!use_form_token($_POST['form_token'] ?? null)) {
        reject_invalid_token();
    }
    $id = positive_id($_POST['student_id'] ?? '');
    $student = $id > 0 ? find_student($db, $id) : null;
    $stmt = $db->prepare("UPDATE students SET status = 'inactive', deleted_at = NOW() WHERE student_id = ? AND status = 'active'");
    $stmt->bind_param('i', $id);
    $stmt->execute();
    if ($stmt->affected_rows === 1) {
        flash('success', 'Student “' . $student['full_name'] . '” was deactivated. The record is kept in the database with status Inactive.', $id);
    } else {
        flash('error', $student ? 'Student “' . $student['full_name'] . '” is already inactive.' : 'That student record was not found.');
    }
    redirect('index.php');
}

$id = positive_id($_GET['id'] ?? '');
$student = $id > 0 ? find_student($db, $id) : null;
if ($student === null) {
    flash('error', 'That student record was not found.');
    redirect('index.php');
}
if ($student['status'] !== 'active') {
    flash('error', 'Student “' . $student['full_name'] . '” is already inactive.', $id);
    redirect('index.php');
}

page_start('Confirm deactivation');
?>
<section class="card confirm-card" aria-labelledby="confirm-title">
    <h2 id="confirm-title">Deactivate this student?</h2>
    <div class="alert alert-warning" role="alert">Are you sure you want to deactivate <strong><?= e($student['full_name']) ?></strong>? Their status will change from <strong>Active</strong> to <strong>Inactive</strong>. This is a soft delete: the record stays in the database and still appears in the list and the CSV export.</div>
    <dl class="details">
        <dt>Student ID</dt><dd><?= $id ?></dd>
        <dt>Full name</dt><dd><?= e($student['full_name']) ?></dd>
        <dt>Email</dt><dd><?= e($student['email']) ?></dd>
        <dt>Course</dt><dd><?= e($student['course']) ?></dd>
        <dt>Semester</dt><dd><?= (int) $student['semester'] ?></dd>
        <dt>Status</dt><dd><?= status_badge($student['status']) ?></dd>
    </dl>
    <form method="post" action="delete.php" class="form-actions">
        <input type="hidden" name="form_token" value="<?= e(form_token()) ?>">
        <input type="hidden" name="student_id" value="<?= $id ?>">
        <button type="submit" class="btn btn-danger">Yes, deactivate student</button>
        <a class="btn btn-secondary" href="index.php">Cancel</a>
    </form>
</section>
<?php page_end(); ?>
