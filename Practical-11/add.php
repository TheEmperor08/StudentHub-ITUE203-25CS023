<?php
// StudentHub – Practical 11: add a student (CREATE). GET shows the form; POST validates and inserts with a
// MySQLi prepared statement, then redirects to the list (Post/Redirect/Get, so a refresh cannot add it again).
declare(strict_types=1);
require_once __DIR__ . '/includes/functions.php';

start_app();
$values = [];
$errors = [];

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!use_form_token($_POST['form_token'] ?? null)) {
        reject_invalid_token();
    }
    [$values, $errors] = validate_student($_POST);
    $db = get_db();
    if (!$errors && email_taken($db, $values['email'])) {
        $errors['email'] = 'This email is already registered to another student.';
    }
    if (!$errors) {
        try {
            $stmt = $db->prepare('INSERT INTO students (full_name, email, course, semester) VALUES (?, ?, ?, ?)');
            $stmt->bind_param('sssi', $values['full_name'], $values['email'], $values['course'], $values['semester']);
            $stmt->execute();
            flash('success', 'Student “' . $values['full_name'] . '” was added successfully (ID ' . $stmt->insert_id . ').', $stmt->insert_id);
            redirect('index.php');
        } catch (mysqli_sql_exception $exception) {
            if ($exception->getCode() !== 1062) {               // 1062 = duplicate key (email added at the same moment)
                throw $exception;
            }
            $errors['email'] = 'This email is already registered to another student.';
        }
    }
    http_response_code(422);
}

page_start('Add student', 'add.php');
if ($errors) {
    echo '<div class="alert alert-error" role="alert">The student was not added. Please correct the highlighted fields.</div>', "\n";
}
echo '<p class="muted">All fields are required. New students are saved with status <strong>Active</strong>.</p>', "\n";
student_form('add.php', 'Add student', $values, $errors);
page_end();
