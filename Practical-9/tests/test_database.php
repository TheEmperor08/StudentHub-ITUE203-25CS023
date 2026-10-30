<?php
// StudentHub – Practical 9: creates and removes the disposable test database studenthub_prac9_test.
// It is built from schema.sql with only the database name changed, so the tests never write to
// studenthub_prac9. A marker table makes sure that only a database created by these tests is ever dropped.
//   php tests/test_database.php create   |   php tests/test_database.php drop
declare(strict_types=1);

const TEST_DB = 'studenthub_prac9_test';

function test_server(): mysqli
{
    mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);
    $db = new mysqli(getenv('P9_DB_HOST') ?: '127.0.0.1', getenv('P9_DB_USER') ?: 'root', getenv('P9_DB_PASS') ?: '',
                     '', (int) (getenv('P9_DB_PORT') ?: 3306));
    $db->set_charset('utf8mb4');
    return $db;
}

function test_db_exists(mysqli $server): bool
{
    $stmt = $server->prepare('SELECT 1 FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = ?');
    $name = TEST_DB;
    $stmt->bind_param('s', $name);
    $stmt->execute();
    return $stmt->get_result()->num_rows > 0;
}

function test_db_is_ours(mysqli $server): bool
{
    $stmt = $server->prepare("SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA = ? AND TABLE_NAME = 'p9_test_marker'");
    $name = TEST_DB;
    $stmt->bind_param('s', $name);
    $stmt->execute();
    return $stmt->get_result()->num_rows > 0;
}

function test_db_drop(): void
{
    $server = test_server();
    if (test_db_exists($server)) {
        if (!test_db_is_ours($server)) {
            throw new RuntimeException(TEST_DB . ' exists but was not created by these tests - not dropped.');
        }
        $server->query('DROP DATABASE ' . TEST_DB);
    }
    $server->close();
}

function test_db_create(): void
{
    test_db_drop();                                   // a leftover from an interrupted run
    $sql = file_get_contents(dirname(__DIR__) . '/schema.sql');
    $sql = str_replace('studenthub_prac9', TEST_DB, $sql);
    if (!str_contains($sql, 'CREATE DATABASE IF NOT EXISTS ' . TEST_DB) || !str_contains($sql, 'USE ' . TEST_DB . ';')) {
        throw new RuntimeException('schema.sql no longer creates and selects the database as expected');
    }
    $server = test_server();
    $server->multi_query($sql);
    do {
        if ($result = $server->store_result()) {
            $result->free();
        }
    } while ($server->more_results() && $server->next_result());
    $server->query('CREATE TABLE ' . TEST_DB . '.p9_test_marker (id INT) ENGINE = InnoDB');
    $server->close();
}

if (realpath($_SERVER['SCRIPT_FILENAME'] ?? '') === __FILE__) {
    if (PHP_SAPI !== 'cli') {
        http_response_code(403);
        exit;
    }
    $command = $argv[1] ?? '';
    if ($command === 'create') {
        test_db_create();
        echo 'created ' . TEST_DB . PHP_EOL;
    } elseif ($command === 'drop') {
        test_db_drop();
        echo 'dropped ' . TEST_DB . PHP_EOL;
    } else {
        fwrite(STDERR, "usage: php tests/test_database.php create|drop\n");
        exit(2);
    }
}
