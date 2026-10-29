<?php
// Creates a local demo account with a bcrypt-hashed password.
// Usage: php tools/create_demo_user.php --db=<database> --username=<name> --email=<email> [--role=student|editor|admin]
// The password is read from STDIN, so it never appears in the repository or shell history.

if (PHP_SAPI !== "cli") {
    http_response_code(403);
    exit("This tool can only be run from the command line.\n");
}

$opts = getopt("", ["db:", "username:", "email:", "role::"]);
$db       = $opts["db"] ?? "";
$username = trim($opts["username"] ?? "");
$email    = trim($opts["email"] ?? "");
$role     = $opts["role"] ?? "student";

if ($db === "" || $username === "" || $email === "") {
    fwrite(STDERR, "Usage: php tools/create_demo_user.php --db=<database> --username=<name> --email=<email> [--role=student|editor|admin]\n");
    exit(1);
}
if (!preg_match('/^[A-Za-z0-9_]{1,64}$/', $db)) {
    fwrite(STDERR, "Invalid database name.\n");
    exit(1);
}
if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
    fwrite(STDERR, "Invalid email address.\n");
    exit(1);
}
if (!in_array($role, ["student", "editor", "admin"], true)) {
    fwrite(STDERR, "Role must be student, editor or admin.\n");
    exit(1);
}

fwrite(STDOUT, "Password for '$username' (min 6 chars): ");
$password = rtrim((string)fgets(STDIN), "\r\n");
if (strlen($password) < 6) {
    fwrite(STDERR, "\nPassword must be at least 6 characters.\n");
    exit(1);
}

mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);
try {
    $conn = new mysqli(getenv("DB_HOST") ?: "localhost", getenv("DB_USER") ?: "root", getenv("DB_PASS") ?: "", $db);
    $conn->set_charset("utf8mb4");

    // Never overwrite an existing account
    $check = $conn->prepare("SELECT id FROM users WHERE username = ? OR email = ?");
    $check->bind_param("ss", $username, $email);
    $check->execute();
    if ($check->get_result()->fetch_assoc()) {
        fwrite(STDERR, "\nA user with that username or email already exists in '$db'. Nothing was changed.\n");
        exit(1);
    }

    $has_role = $conn->query("SHOW COLUMNS FROM users LIKE 'role'")->num_rows > 0;
    $hash = password_hash($password, PASSWORD_BCRYPT);

    if ($has_role) {
        $stmt = $conn->prepare("INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)");
        $stmt->bind_param("ssss", $username, $email, $hash, $role);
    } else {
        $stmt = $conn->prepare("INSERT INTO users (username, email, password) VALUES (?, ?, ?)");
        $stmt->bind_param("sss", $username, $email, $hash);
    }
    $stmt->execute();
    fwrite(STDOUT, "\nCreated '$username' in '$db'" . ($has_role ? " with role '$role'" : "") . ".\n");
} catch (mysqli_sql_exception $e) {
    fwrite(STDERR, "\nDatabase error: " . $e->getMessage() . "\n");
    exit(1);
}
