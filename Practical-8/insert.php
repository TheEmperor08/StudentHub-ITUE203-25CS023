<?php
// Practical 8: Insert Student Data using PDO Prepared Statements
require_once "db.php";

$errors  = [];
$success = "";
$values  = ["enrollment_no" => "", "full_name" => "", "branch" => "CSE", "semester" => "3", "email" => ""];
$branches = ["CSE", "CE", "IT"];

if ($_SERVER["REQUEST_METHOD"] === "POST") {
    foreach ($values as $key => $default) {
        $values[$key] = trim($_POST[$key] ?? "");
    }
    $values["enrollment_no"] = strtoupper($values["enrollment_no"]);

    if (!preg_match('/^\d{2}[A-Z]{2}\d{3}$/', $values["enrollment_no"])) {
        $errors[] = "Enrollment number must look like 25CS023.";
    }
    if ($values["full_name"] === "" || mb_strlen($values["full_name"]) > 100) {
        $errors[] = "Name is required (max 100 characters).";
    }
    if (!in_array($values["branch"], $branches, true)) {
        $errors[] = "Please choose a valid branch.";
    }
    $semester = filter_var($values["semester"], FILTER_VALIDATE_INT, ["options" => ["min_range" => 1, "max_range" => 8]]);
    if ($semester === false) {
        $errors[] = "Semester must be between 1 and 8.";
    }
    if (!filter_var($values["email"], FILTER_VALIDATE_EMAIL)) {
        $errors[] = "Please enter a valid email address.";
    }

    if (!$errors) {
        try {
            $stmt = $pdo->prepare("INSERT INTO students (enrollment_no, full_name, branch, semester, email) VALUES (?, ?, ?, ?, ?)");
            $stmt->execute([$values["enrollment_no"], $values["full_name"], $values["branch"], $semester, $values["email"]]);
            $success = "Student Added Successfully (ID " . (int)$pdo->lastInsertId() . ")";
            $values = ["enrollment_no" => "", "full_name" => "", "branch" => "CSE", "semester" => "3", "email" => ""];
        } catch (PDOException $e) {
            // 23000 = integrity constraint violation (duplicate enrollment number or email)
            $errors[] = ($e->getCode() === "23000") ? "That enrollment number or email already exists." : "Could not add the student.";
        }
    }
}
?>
<h2>Add Student (PDO Prepared Statement)</h2>
<?php if ($success): ?><p style="color:green;"><?php echo htmlspecialchars($success); ?></p><?php endif; ?>
<?php foreach ($errors as $error): ?><p style="color:#b91c1c;"><?php echo htmlspecialchars($error); ?></p><?php endforeach; ?>
<form method="POST" action="insert.php">
    <p><label>Enrollment No: <input name="enrollment_no" value="<?php echo htmlspecialchars($values["enrollment_no"]); ?>" placeholder="25CS023" required></label></p>
    <p><label>Full Name: <input name="full_name" value="<?php echo htmlspecialchars($values["full_name"]); ?>" required></label></p>
    <p><label>Branch:
        <select name="branch">
            <?php foreach ($branches as $b): ?>
                <option value="<?php echo $b; ?>" <?php echo $values["branch"] === $b ? "selected" : ""; ?>><?php echo $b; ?></option>
            <?php endforeach; ?>
        </select></label></p>
    <p><label>Semester: <input type="number" name="semester" min="1" max="8" value="<?php echo htmlspecialchars($values["semester"]); ?>" required></label></p>
    <p><label>Email: <input type="email" name="email" value="<?php echo htmlspecialchars($values["email"]); ?>" required></label></p>
    <p><button type="submit">Insert Student</button></p>
</form>
<p><a href="students.php">View student list</a></p>
