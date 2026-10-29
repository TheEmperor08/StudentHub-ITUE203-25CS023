<?php
// Practical 8: StudentHub Database - Database Connection using PDO
$host     = getenv("DB_HOST") ?: "localhost";
$dbname   = getenv("P8_DB_NAME") ?: "practical8_db";
$username = getenv("DB_USER") ?: "root";
$password = getenv("DB_PASS") ?: "";

try {
    $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8mb4", $username, $password, [
        PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES   => false,
    ]);
    // Only print the status when db.php is opened directly in the browser
    if (realpath($_SERVER["SCRIPT_FILENAME"] ?? "") === __FILE__) {
        echo "Database Connected Successfully (PDO → " . htmlspecialchars($dbname) . ")";
    }
} catch (PDOException $e) {
    http_response_code(500);
    // Do not leak connection details to the browser
    error_log("Practical 8 DB connection failed: " . $e->getMessage());
    exit("Connection Failed: could not connect to the '" . htmlspecialchars($dbname) . "' database. Import Practical-8/schema.sql first.");
}
?>
