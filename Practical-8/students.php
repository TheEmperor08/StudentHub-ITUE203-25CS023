<?php
// Practical 8: Display Student Data from MySQL using PDO
require_once "db.php";

$stmt = $pdo->prepare("SELECT student_id, enrollment_no, full_name, branch, semester, email FROM students ORDER BY student_id ASC");
$stmt->execute();
$students = $stmt->fetchAll();
?>

<h2>Student List (<?php echo count($students); ?> records from MySQL)</h2>
<table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse; font-family:Arial, sans-serif;">
    <tr style="background-color:#f2f2f2;"><th>ID</th><th>Enrollment</th><th>Name</th><th>Branch</th><th>Semester</th><th>Email</th></tr>
    <?php foreach ($students as $student): ?>
        <tr>
            <td><?php echo (int)$student["student_id"]; ?></td>
            <td><?php echo htmlspecialchars($student["enrollment_no"]); ?></td>
            <td><?php echo htmlspecialchars($student["full_name"]); ?></td>
            <td><?php echo htmlspecialchars($student["branch"]); ?></td>
            <td><?php echo (int)$student["semester"]; ?></td>
            <td><?php echo htmlspecialchars($student["email"]); ?></td>
        </tr>
    <?php endforeach; ?>
</table>
<p><a href="insert.php">Add a student</a> | <a href="test_connection.php">Event registrations (JOIN)</a></p>
