<?php
// Practical 8: Data Retrieval Test using PDO Prepared Statements and a 3-table JOIN
require_once "db.php";

$branch = trim($_GET["branch"] ?? "");

echo "<h3>Testing Data Retrieval using PDO:</h3>";

// 1. Student Records (optionally filtered by branch through a bound parameter)
$sql = "SELECT student_id, full_name, email, branch FROM students";
$params = [];
if ($branch !== "") {
    $sql .= " WHERE branch = ?";
    $params[] = $branch;
}
$sql .= " ORDER BY student_id ASC";
$stmt = $pdo->prepare($sql);
$stmt->execute($params);
$students = $stmt->fetchAll();

echo "<form method='GET'><label>Filter by branch: <input name='branch' value='" . htmlspecialchars($branch) . "' placeholder='CSE'></label> <button type='submit'>Filter</button></form>";
echo "<h4>Student Records (Count: " . count($students) . "):</h4>";
echo "<table border='1' cellpadding='8' cellspacing='0' style='border-collapse:collapse; width:80%; font-family:Arial, sans-serif;'>";
echo "<tr style='background-color:#f2f2f2;'><th>Student ID</th><th>Name</th><th>Email</th><th>Branch</th></tr>";
foreach ($students as $student) {
    echo "<tr>";
    echo "<td>" . (int)$student["student_id"] . "</td>";
    echo "<td>" . htmlspecialchars($student["full_name"]) . "</td>";
    echo "<td>" . htmlspecialchars($student["email"]) . "</td>";
    echo "<td>" . htmlspecialchars($student["branch"]) . "</td>";
    echo "</tr>";
}
echo "</table>";

// 2. Event Registrations (JOIN across students, registrations and events)
$reg_stmt = $pdo->prepare(
    "SELECT r.registration_id, s.full_name, e.event_name, e.location
     FROM registrations r
     JOIN students s ON s.student_id = r.student_id
     JOIN events e   ON e.event_id   = r.event_id
     ORDER BY r.registration_id ASC"
);
$reg_stmt->execute();
$registrations = $reg_stmt->fetchAll();

echo "<br><h4>Event Registrations (Count: " . count($registrations) . "):</h4>";
echo "<table border='1' cellpadding='8' cellspacing='0' style='border-collapse:collapse; width:80%; font-family:Arial, sans-serif;'>";
echo "<tr style='background-color:#f2f2f2;'><th>Reg ID</th><th>Student Name</th><th>Event Name</th><th>Venue</th></tr>";
foreach ($registrations as $reg) {
    echo "<tr>";
    echo "<td>" . (int)$reg["registration_id"] . "</td>";
    echo "<td>" . htmlspecialchars($reg["full_name"]) . "</td>";
    echo "<td>" . htmlspecialchars($reg["event_name"]) . "</td>";
    echo "<td>" . htmlspecialchars($reg["location"]) . "</td>";
    echo "</tr>";
}
echo "</table>";
?>
