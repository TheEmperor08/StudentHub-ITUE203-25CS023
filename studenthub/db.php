<?php
// StudentHub – MySQLi connection to the shared portal database (studenthub_db).
//
// Settings come from the environment (DB_HOST, DB_USER, DB_PASS, DB_NAME) with XAMPP defaults. There is NO fallback
// to another database: if the configured database is unavailable, the real reason is written to the PHP error log and
// visitors only see a general "service unavailable" page (HTTP 503) – never credentials, SQL or stack traces.
// Also used by: includes/auth.php (sessions, roles), includes/registration.php.

ini_set('display_errors', '0');          // PHP errors go to the error log, not into the page
ini_set('log_errors', '1');

// Dates (CSV file names, today's date in forms, the academic year for enrollment numbers) use the institute's time zone,
// the same as MariaDB on this server - not XAMPP's php.ini default (Europe/Berlin). STUDENTHUB_TIMEZONE overrides it.
$app_timezone = getenv('STUDENTHUB_TIMEZONE') ?: 'Asia/Kolkata';
date_default_timezone_set(in_array($app_timezone, timezone_identifiers_list(), true) ? $app_timezone : 'Asia/Kolkata');

$db_host = getenv('DB_HOST') ?: 'localhost';
$db_user = getenv('DB_USER') ?: 'root';
$db_pass = getenv('DB_PASS') ?: '';
$db_name = getenv('DB_NAME') ?: 'studenthub_db';

// General error page for visitors (used when the database cannot be reached and for unexpected errors)
function studenthub_fail(int $status, string $title, string $message): void
{
    if (defined('STUDENTHUB_API')) {                 // JSON API (api/*.php): the same general message, as JSON
        if (!headers_sent()) {
            http_response_code($status);
            header('Content-Type: application/json; charset=utf-8');
            header('Cache-Control: no-store');
            if ($status === 503) {
                header('Retry-After: 60');
            }
        }
        echo json_encode(['ok' => false, 'error' => $message]);
        return;
    }
    if (!headers_sent()) {
        http_response_code($status);
        header('Content-Type: text/html; charset=utf-8');
        header('Cache-Control: no-store');
        if ($status === 503) {
            header('Retry-After: 60');
        }
    }
    $t = htmlspecialchars($title, ENT_QUOTES, 'UTF-8');
    $m = htmlspecialchars($message, ENT_QUOTES, 'UTF-8');
    echo "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"UTF-8\">\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n",
         "<title>$t – StudentHub</title>\n<link rel=\"stylesheet\" href=\"assets/css/auth.css?v=2\">\n</head>\n<body class=\"auth\">\n",
         "<main class=\"auth-main\"><div class=\"auth-card\" role=\"alert\">\n<h1>$t</h1>\n<p class=\"auth-sub\">$m</p>\n",
         "<p class=\"auth-links\"><a href=\"index.php\">&larr; Back to Home</a></p>\n</div></main>\n</body>\n</html>\n";
}

// Uncaught errors: log the details, show a general page
set_exception_handler(function (Throwable $e): void {
    error_log('StudentHub error: ' . get_class($e) . ' [' . $e->getCode() . '] ' . $e->getMessage() . ' in ' . $e->getFile() . ':' . $e->getLine());
    studenthub_fail(500, 'Something went wrong', 'The page could not be completed. Please try again later.');
});

mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);   // every MySQL error throws mysqli_sql_exception
try {
    $conn = new mysqli($db_host, $db_user, $db_pass, $db_name);
    $conn->set_charset('utf8mb4');
} catch (mysqli_sql_exception $e) {
    // Diagnostic for the administrator (server log only); the password is never logged
    error_log('StudentHub: cannot connect to the configured database "' . $db_name . '" on host "' . $db_host . '" as user "'
        . $db_user . '": [' . $e->getCode() . '] ' . $e->getMessage() . '. No fallback database is used.');
    studenthub_fail(503, 'Service temporarily unavailable', 'StudentHub cannot reach its database right now. Please try again in a few minutes.');
    exit;
}
unset($db_pass);

// PDO handle for later Fetch/AJAX modules – same database, same rules (null if it cannot be opened)
try {
    $pdo = new PDO("mysql:host=$db_host;dbname=$db_name;charset=utf8mb4", $db_user, getenv('DB_PASS') ?: '', [
        PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    ]);
} catch (PDOException $e) {
    error_log('StudentHub: PDO connection to "' . $db_name . '" failed: [' . $e->getCode() . '] ' . $e->getMessage());
    $pdo = null;
}
