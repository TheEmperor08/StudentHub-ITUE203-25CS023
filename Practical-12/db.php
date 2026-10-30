<?php
// StudentHub – Practical 12: settings and the MySQLi connection to the isolated studenthub_prac12 database.
//
// Settings: XAMPP defaults (root with no password on 127.0.0.1), posters in ./uploads and a 30-minute
// inactivity timeout. They can be overridden by an optional config.local.php (git-ignored, copy
// config.example.php) or by P12_* environment variables (used by the tests). No password is stored in this file,
// and database errors are logged, never shown in the browser.
declare(strict_types=1);

ini_set('display_errors', '0');                 // never print PHP errors (and their details) in the page
ini_set('log_errors', '1');
date_default_timezone_set('Asia/Kolkata');

function app_config(): array
{
    static $config = null;
    if ($config !== null) {
        return $config;
    }
    $config = ['host' => '127.0.0.1', 'port' => 3306, 'name' => 'studenthub_prac12', 'user' => 'root', 'pass' => '',
               'upload_dir' => __DIR__ . DIRECTORY_SEPARATOR . 'uploads', 'session_timeout' => 1800];
    $local = __DIR__ . '/config.local.php';
    if (is_file($local)) {
        $config = array_merge($config, (array) require $local);
    }
    $env = ['host' => 'P12_DB_HOST', 'port' => 'P12_DB_PORT', 'name' => 'P12_DB_NAME', 'user' => 'P12_DB_USER',
            'pass' => 'P12_DB_PASS', 'upload_dir' => 'P12_UPLOAD_DIR', 'session_timeout' => 'P12_SESSION_TIMEOUT'];
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
        error_log('Practical 12 database connection failed: [' . $exception->getCode() . '] ' . $exception->getMessage());
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
