<?php
// StudentHub – Practical 11: edit a student (UPDATE). GET edit.php?id=N shows the form filled from MySQL;
// POST validates and updates the record with a prepared statement. The status is changed only by delete.php.
declare(strict_types=1);
require_once __DIR__ . '/includes/functions.php';

start_app();
$db = get_db();
$id = positive_id($_SERVER['REQUEST_METHOD'] === 'POST' ? ($_POST['student_id'] ?? '') : ($_GET['id'] ?? ''));
$student = $id > 0 ? find_student($db, $id) : null;
if ($student === null) {
    flash('error', 'That student record was not found.');
    redirect('index.php');
}
$values = $student;
$errors = [];

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!use_form_token($_POST['form_token'] ?? null)) {
        reject_invalid_token();
    }
    [$values, $errors] = validate_student($_POST);
    if (!$errors && email_taken($db, $values['email'], $id)) {
        $errors['email'] = 'This email is already registered to another student.';
    }
    if (!$errors) {
        try {
            $stmt = $db->prepare('UPDATE students SET full_name = ?, email = ?, course = ?, semester = ? WHERE student_id = ?');
            $stmt->bind_param('sssii', $values['full_name'], $values['email'], $values['course'], $values['semester'], $id);
            $stmt->execute();
            $message = $stmt->affected_rows > 0
                ? 'Student “' . $values['full_name'] . '” was updated successfully.'
                : 'No changes were made to “' . $values['full_name'] . '”.';
            flash('success', $message, $id);
            redirect('index.php');
        } catch (mysqli_sql_exception $exception) {
            if ($exception->getCode() !== 1062) {
                throw $exception;
            }
            $errors['email'] = 'This email is already registered to another student.';
        }
    }
    http_response_code(422);
}

page_start('Edit student');
if ($errors) {
    echo '<div class="alert alert-error" role="alert">The changes were not saved. Please correct the highlighted fields.</div>', "\n";
}
echo '<p class="muted">Editing student <strong>ID ', $id, '</strong> · status ', status_badge($student['status']),
     ' · added ', e(date('d M Y, H:i', strtotime($student['created_at']))), '</p>', "\n";
student_form('edit.php', 'Save changes', $values, $errors, ['student_id' => $id]);
page_end();
