<?php
// StudentHub – Practical 8: connection test. Connects through db.php, reads the three tables with PDO
// prepared statements and shows the connection status, table names, keys and records.
declare(strict_types=1);

require __DIR__ . '/db.php';

function e(mixed $value): string
{
    return htmlspecialchars((string) $value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

const TABLES = ['students', 'events', 'registrations'];   // fixed names: table names cannot be bound as parameters
const BRANCHES = ['CSE', 'CE', 'IT'];

$branch = is_string($_GET['branch'] ?? null) && in_array($_GET['branch'], BRANCHES, true) ? $_GET['branch'] : 'CSE';
$error = null;

try {
    $pdo = get_db();

    $stmt = $pdo->prepare('SELECT DATABASE() AS db_name, VERSION() AS server_version, @@character_set_connection AS charset');
    $stmt->execute();
    $server = $stmt->fetch();

    // Table names, engine and the primary/foreign keys, read from information_schema with a bound parameter
    $stmt = $pdo->prepare(
        "SELECT TABLE_NAME AS name, ENGINE AS engine FROM information_schema.TABLES
         WHERE TABLE_SCHEMA = :schema AND TABLE_TYPE = 'BASE TABLE'
         ORDER BY FIELD(TABLE_NAME, 'students', 'events', 'registrations')"
    );
    $stmt->execute([':schema' => $server['db_name']]);
    $tables = $stmt->fetchAll();

    $stmt = $pdo->prepare(
        "SELECT TABLE_NAME AS tbl, COLUMN_NAME AS col, CONSTRAINT_NAME AS name,
                REFERENCED_TABLE_NAME AS ref_table, REFERENCED_COLUMN_NAME AS ref_col
         FROM information_schema.KEY_COLUMN_USAGE
         WHERE TABLE_SCHEMA = :schema AND (CONSTRAINT_NAME = 'PRIMARY' OR REFERENCED_TABLE_NAME IS NOT NULL)
         ORDER BY TABLE_NAME, CONSTRAINT_NAME <> 'PRIMARY', CONSTRAINT_NAME"
    );
    $stmt->execute([':schema' => $server['db_name']]);
    $keys = [];
    foreach ($stmt->fetchAll() as $key) {
        $keys[$key['tbl']][] = $key['name'] === 'PRIMARY'
            ? 'PK ' . $key['col']
            : 'FK ' . $key['col'] . ' → ' . $key['ref_table'] . '.' . $key['ref_col'];
    }

    $counts = [];
    foreach (TABLES as $table) {
        $stmt = $pdo->prepare("SELECT COUNT(*) FROM `$table`");
        $stmt->execute();
        $counts[$table] = (int) $stmt->fetchColumn();
    }

    // Records of the three tables (LIMIT bound as an integer parameter)
    $limit = 50;
    $stmt = $pdo->prepare('SELECT student_id, student_code, full_name, email, branch, semester FROM students ORDER BY student_id LIMIT :limit');
    $stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
    $stmt->execute();
    $students = $stmt->fetchAll();

    $stmt = $pdo->prepare('SELECT event_id, title, event_date, venue, category, capacity FROM events ORDER BY event_date LIMIT :limit');
    $stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
    $stmt->execute();
    $events = $stmt->fetchAll();

    $stmt = $pdo->prepare(
        'SELECT r.registration_id, s.student_code, s.full_name, e.title, r.status
         FROM registrations AS r
         JOIN students AS s ON s.student_id = r.student_id
         JOIN events AS e ON e.event_id = r.event_id
         ORDER BY r.registration_id LIMIT :limit'
    );
    $stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
    $stmt->execute();
    $registrations = $stmt->fetchAll();

    // A prepared statement with a value from the address (?branch=CE); the value is sent separately from the SQL
    $stmt = $pdo->prepare('SELECT student_code, full_name, semester FROM students WHERE branch = :branch ORDER BY full_name');
    $stmt->execute([':branch' => $branch]);
    $byBranch = $stmt->fetchAll();

    // Stored procedure (advanced extension) called through a prepared statement
    $stmt = $pdo->prepare('CALL get_event_roster(:event_id)');
    $stmt->execute([':event_id' => 1]);
    $roster = $stmt->fetchAll();
    $stmt->closeCursor();
} catch (PDOException $exception) {            // a query failed (PDOException must come first: it extends RuntimeException)
    error_log('Practical 8 query failed: ' . $exception->getMessage());
    $errorTitle = 'Database query failed';
    $error = $exception->getCode() === '42S02'
        ? 'Connected, but the tables were not found. Import schema.sql in phpMyAdmin and reload this page.'
        : 'Connected, but a database query failed. The details were written to the PHP error log.';
} catch (RuntimeException $exception) {        // get_db() could not connect (already logged in db.php)
    $errorTitle = 'Database connection failed';
    $error = 'Could not connect to the studenthub_prac8 database. Check that MySQL is running in the XAMPP Control Panel and that schema.sql has been imported in phpMyAdmin.';
}
if ($error !== null) {
    http_response_code(500);
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Database Connection Test - StudentHub Practical 8</title>
    <link rel="stylesheet" href="assets/css/style.css">
</head>
<body>
    <header class="site-header">
        <div class="container">
            <p class="brand">StudentHub · Practical 8</p>
            <h1>Database Connection Test</h1>
            <p class="subtitle">PHP PDO connection to MySQL (XAMPP) with prepared statements</p>
        </div>
    </header>

    <main class="container">
<?php if ($error !== null): ?>
        <div class="alert alert-error" role="alert">
            <h2><?= e($errorTitle) ?></h2>
            <p><?= e($error) ?></p>
        </div>
<?php else: ?>
        <div class="alert alert-success" role="status">
            <h2>Connected successfully</h2>
            <p>Database <strong><?= e($server['db_name']) ?></strong> · server <?= e($server['server_version']) ?> · character set <?= e($server['charset']) ?> · PDO error mode: exceptions · prepared statements: native (emulation off)</p>
        </div>

        <section class="card">
            <h2>Tables in <?= e($server['db_name']) ?></h2>
            <table>
                <thead><tr><th scope="col">Table</th><th scope="col">Engine</th><th scope="col">Rows</th><th scope="col">Primary and foreign keys</th></tr></thead>
                <tbody>
<?php foreach ($tables as $table): ?>
                    <tr>
                        <td><strong><?= e($table['name']) ?></strong></td>
                        <td><?= e($table['engine']) ?></td>
                        <td class="num"><?= e($counts[$table['name']] ?? '–') ?></td>
                        <td><?= e(implode(' · ', $keys[$table['name']] ?? [])) ?></td>
                    </tr>
<?php endforeach; ?>
                </tbody>
            </table>
        </section>

        <section class="card">
            <h2>students <span class="count">(<?= count($students) ?> records)</span></h2>
            <table>
                <thead><tr><th scope="col">student_id</th><th scope="col">student_code</th><th scope="col">full_name</th><th scope="col">email</th><th scope="col">branch</th><th scope="col">semester</th></tr></thead>
                <tbody>
<?php foreach ($students as $row): ?>
                    <tr><td class="num"><?= e($row['student_id']) ?></td><td><?= e($row['student_code']) ?></td><td><?= e($row['full_name']) ?></td><td><?= e($row['email']) ?></td><td><?= e($row['branch']) ?></td><td class="num"><?= e($row['semester']) ?></td></tr>
<?php endforeach; ?>
                </tbody>
            </table>
        </section>

        <section class="card">
            <h2>events <span class="count">(<?= count($events) ?> records)</span></h2>
            <table>
                <thead><tr><th scope="col">event_id</th><th scope="col">title</th><th scope="col">event_date</th><th scope="col">venue</th><th scope="col">category</th><th scope="col">capacity</th></tr></thead>
                <tbody>
<?php foreach ($events as $row): ?>
                    <tr><td class="num"><?= e($row['event_id']) ?></td><td><?= e($row['title']) ?></td><td><?= e($row['event_date']) ?></td><td><?= e($row['venue']) ?></td><td><?= e($row['category']) ?></td><td class="num"><?= e($row['capacity']) ?></td></tr>
<?php endforeach; ?>
                </tbody>
            </table>
        </section>

        <section class="card">
            <h2>registrations <span class="count">(<?= count($registrations) ?> records, joined with students and events)</span></h2>
            <table>
                <thead><tr><th scope="col">registration_id</th><th scope="col">student_code</th><th scope="col">student</th><th scope="col">event</th><th scope="col">status</th></tr></thead>
                <tbody>
<?php foreach ($registrations as $row): ?>
                    <tr><td class="num"><?= e($row['registration_id']) ?></td><td><?= e($row['student_code']) ?></td><td><?= e($row['full_name']) ?></td><td><?= e($row['title']) ?></td><td><?= e($row['status']) ?></td></tr>
<?php endforeach; ?>
                </tbody>
            </table>
        </section>

        <section class="card two-col">
            <div>
                <h2>Prepared statement with a parameter</h2>
                <p class="code">SELECT … FROM students WHERE branch = :branch</p>
                <p>:branch = <strong><?= e($branch) ?></strong> → <?= count($byBranch) ?> students:
                    <?= e(implode(', ', array_map(fn($s) => $s['full_name'] . ' (sem ' . $s['semester'] . ')', $byBranch))) ?></p>
                <p class="hint">Try <a href="?branch=CE">?branch=CE</a> or <a href="?branch=IT">?branch=IT</a>.</p>
            </div>
            <div>
                <h2>Stored procedure</h2>
                <p class="code">CALL get_event_roster(:event_id)</p>
                <p>:event_id = <strong>1</strong> → <?= count($roster) ?> students: <?= e(implode(', ', array_column($roster, 'full_name'))) ?></p>
            </div>
        </section>
<?php endif; ?>
    </main>

    <footer class="site-footer">
        <div class="container"><p>&copy; <time datetime="2026">2026</time> StudentHub – ITUE203 Practical 8 by Shreyas (25CS023). Sample data is fictional.</p></div>
    </footer>
</body>
</html>
