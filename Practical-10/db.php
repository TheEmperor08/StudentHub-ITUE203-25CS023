<?php
// StudentHub – Practical 10: settings and the MySQLi connection to the isolated studenthub_prac10 database.
//
// Settings: XAMPP defaults (root with no password on 127.0.0.1) and a 300-second inactivity timeout, which can
// be overridden by an optional config.local.php (git-ignored, copy config.example.php) or by P10_* environment
// variables. No password is stored in this file, and database errors are logged, never shown in the browser.
declare(strict_types=1);

ini_set('display_errors', '0');                 // never print PHP errors (and their details) in the page
ini_set('log_errors', '1');
date_default_timezone_set('Asia/Kolkata');      // XAMPP's php.ini uses Europe/Berlin; show Indian time like MySQL

function app_config(): array
{
    static $config = null;
    if ($config !== null) {
        return $config;
    }
    $config = ['host' => '127.0.0.1', 'port' => 3306, 'name' => 'studenthub_prac10', 'user' => 'root', 'pass' => '',
               'session_timeout' => 300];
    $local = __DIR__ . '/config.local.php';
    if (is_file($local)) {
        $config = array_merge($config, (array) require $local);
    }
    $env = ['host' => 'P10_DB_HOST', 'port' => 'P10_DB_PORT', 'name' => 'P10_DB_NAME', 'user' => 'P10_DB_USER',
            'pass' => 'P10_DB_PASS', 'session_timeout' => 'P10_SESSION_TIMEOUT'];
    foreach ($env as $key => $name) {
        $value = getenv($name);
        if ($value !== false) {
            $config[$key] = $value;
        }
    }
    return $config;
}

// Returns one shared mysqli connection. On failure the real error goes to the PHP error log and the caller
// receives a RuntimeException with a general message that contains no host, user or password.
function get_db(): mysqli
{
    static $db = null;
    if ($db instanceof mysqli) {
        return $db;
    }
    mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);   // every MySQL error throws mysqli_sql_exception
    $config = app_config();
    try {
        $db = new mysqli((string) $config['host'], (string) $config['user'], (string) $config['pass'],
                         (string) $config['name'], (int) $config['port']);
        $db->set_charset('utf8mb4');
    } catch (mysqli_sql_exception $exception) {
        $db = null;
        error_log('Practical 10 database connection failed: [' . $exception->getCode() . '] ' . $exception->getMessage());
        throw new RuntimeException('The database connection could not be established.');
    }
    return $db;
}

// Opening db.php directly in the browser shows nothing about the configuration
if (realpath($_SERVER['SCRIPT_FILENAME'] ?? '') === __FILE__) {
    http_response_code(403);
    header('Content-Type: text/plain; charset=utf-8');
    echo "db.php only provides the database connection. Open login.php instead.\n";
}
