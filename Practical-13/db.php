<?php
// StudentHub – Practical 13: MySQLi connection to the isolated studenthub_prac13 database.
//
// Settings: XAMPP defaults (root with no password on 127.0.0.1). They can be overridden by an optional
// config.local.php (git-ignored, copy config.example.php) or by P13_* environment variables (used by the tests).
// No password is stored in this file; connection errors are logged and never sent to the browser.
declare(strict_types=1);

ini_set('display_errors', '0');
ini_set('log_errors', '1');
date_default_timezone_set('Asia/Kolkata');

function app_config(): array
{
    static $config = null;
    if ($config !== null) {
        return $config;
    }
    $config = ['host' => '127.0.0.1', 'port' => 3306, 'name' => 'studenthub_prac13', 'user' => 'root', 'pass' => ''];
    $local = __DIR__ . '/config.local.php';
    if (is_file($local)) {
        $config = array_merge($config, (array) require $local);
    }
    foreach (['host' => 'P13_DB_HOST', 'port' => 'P13_DB_PORT', 'name' => 'P13_DB_NAME', 'user' => 'P13_DB_USER', 'pass' => 'P13_DB_PASS'] as $key => $env) {
        $value = getenv($env);
        if ($value !== false) {
            $config[$key] = $value;
        }
    }
    return $config;
}

// One shared connection. Every MySQL error becomes a mysqli_sql_exception, which api.php turns into a JSON error.
function get_db(): mysqli
{
    static $db = null;
    if ($db instanceof mysqli) {
        return $db;
    }
    mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);
    $c = app_config();
    try {
        $db = new mysqli((string) $c['host'], (string) $c['user'], (string) $c['pass'], (string) $c['name'], (int) $c['port']);
        $db->set_charset('utf8mb4');
    } catch (mysqli_sql_exception $e) {
        $db = null;
        error_log('Practical 13 database connection failed: [' . $e->getCode() . '] ' . $e->getMessage());
        throw new RuntimeException('database unavailable');
    }
    return $db;
}

if (realpath($_SERVER['SCRIPT_FILENAME'] ?? '') === __FILE__) {
    http_response_code(403);
    header('Content-Type: text/plain; charset=utf-8');
    echo "db.php only provides the database connection.\n";
}
