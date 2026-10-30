<?php
// StudentHub – Practical 8: secure PDO connection to the isolated studenthub_prac8 database.
//
// Settings: XAMPP defaults (root with no password on 127.0.0.1), which can be overridden by an optional
// config.local.php (git-ignored, copy config.example.php) or by P8_DB_* environment variables.
// No password is stored in this file, and database errors are logged, never shown in the browser.
declare(strict_types=1);

ini_set('display_errors', '0');                 // never print PHP errors (and their details) in the page
ini_set('log_errors', '1');

function db_config(): array
{
    $config = ['host' => '127.0.0.1', 'port' => 3306, 'name' => 'studenthub_prac8', 'user' => 'root', 'pass' => ''];
    $local = __DIR__ . '/config.local.php';
    if (is_file($local)) {
        $config = array_merge($config, (array) require $local);
    }
    foreach (['host' => 'P8_DB_HOST', 'port' => 'P8_DB_PORT', 'name' => 'P8_DB_NAME', 'user' => 'P8_DB_USER', 'pass' => 'P8_DB_PASS'] as $key => $env) {
        $value = getenv($env);
        if ($value !== false) {
            $config[$key] = $value;
        }
    }
    return $config;
}

// Returns one shared PDO connection. On failure the real error goes to the PHP error log and the caller
// receives a RuntimeException with a general message that contains no host, user or password.
function get_db(): PDO
{
    static $pdo = null;
    if ($pdo instanceof PDO) {
        return $pdo;
    }
    $config = db_config();
    $dsn = sprintf('mysql:host=%s;port=%d;dbname=%s;charset=utf8mb4', $config['host'], (int) $config['port'], $config['name']);
    try {
        $pdo = new PDO($dsn, (string) $config['user'], (string) $config['pass'], [
            PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,   // every SQL error throws a PDOException
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES   => false,                    // real server-side prepared statements
            PDO::ATTR_STRINGIFY_FETCHES  => false,
            // XAMPP's my.ini is not strict, so invalid values (e.g. branch 'XYZ') would be silently changed;
            // strict mode for this connection makes MySQL reject them with an error instead
            PDO::MYSQL_ATTR_INIT_COMMAND => "SET SESSION sql_mode = 'STRICT_ALL_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ZERO_IN_DATE,NO_ZERO_DATE,NO_ENGINE_SUBSTITUTION'",
        ]);
    } catch (PDOException $exception) {
        error_log('Practical 8 database connection failed: ' . $exception->getMessage());
        throw new RuntimeException('The database connection could not be established.');
    }
    return $pdo;
}

// Opening db.php directly in the browser shows nothing about the configuration
if (realpath($_SERVER['SCRIPT_FILENAME'] ?? '') === __FILE__) {
    http_response_code(403);
    header('Content-Type: text/plain; charset=utf-8');
    echo "db.php only provides the database connection. Open test_connection.php instead.\n";
}
