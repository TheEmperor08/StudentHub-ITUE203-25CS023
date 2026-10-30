<?php
// StudentHub – Practical 8: database tests (run from the command line: C:\xampp\php\php.exe tests\test_db.php).
// Checks the imported schema, keys, constraints and seed data through db.php. Every change made by a test
// runs inside a transaction that is rolled back, so the sample data is left exactly as imported.
declare(strict_types=1);

require __DIR__ . '/../db.php';

$passed = 0;
$failed = 0;

function check(string $name, bool $ok, string $detail = ''): void
{
    global $passed, $failed;
    $ok ? $passed++ : $failed++;
    echo ($ok ? 'PASS' : 'FAIL') . "  $name" . ($detail !== '' ? "  [$detail]" : '') . PHP_EOL;
}

// Runs $sql (with bound $params) and returns the MySQL error number, or 0 when it succeeded
function error_number(PDO $pdo, string $sql, array $params = []): int
{
    try {
        $pdo->prepare($sql)->execute($params);
        return 0;
    } catch (PDOException $exception) {
        return (int) ($exception->errorInfo[1] ?? -1);
    }
}

function rows(PDO $pdo, string $sql, array $params = []): array
{
    $stmt = $pdo->prepare($sql);
    $stmt->execute($params);
    $result = $stmt->fetchAll();
    $stmt->closeCursor();
    return $result;
}

$pdo = get_db();
$schema = 'studenthub_prac8';

// 1. Connection and PDO configuration
echo "-- Connection\n";
check('connected to the isolated database', rows($pdo, 'SELECT DATABASE() AS d')[0]['d'] === $schema);
check('PDO error mode is exceptions', $pdo->getAttribute(PDO::ATTR_ERRMODE) === PDO::ERRMODE_EXCEPTION);
check('native prepared statements (emulation off)', (bool) $pdo->getAttribute(PDO::ATTR_EMULATE_PREPARES) === false);   // pdo_mysql reports int(0)
check('strict SQL mode for this connection', str_contains(rows($pdo, 'SELECT @@SESSION.sql_mode AS m')[0]['m'], 'STRICT_ALL_TABLES'));
check('default fetch mode is associative', $pdo->getAttribute(PDO::ATTR_DEFAULT_FETCH_MODE) === PDO::FETCH_ASSOC);
$charset = rows($pdo, 'SELECT @@character_set_connection AS c, @@character_set_client AS cl')[0];
check('connection character set is utf8mb4', $charset['c'] === 'utf8mb4' && $charset['cl'] === 'utf8mb4');
check('get_db() reuses one connection', get_db() === $pdo);

// 2. Tables
echo "-- Tables\n";
$tables = rows($pdo, "SELECT TABLE_NAME AS t, ENGINE AS e, TABLE_COLLATION AS c FROM information_schema.TABLES
                      WHERE TABLE_SCHEMA = ? ORDER BY TABLE_NAME", [$schema]);
check('exactly 3 tables: events, registrations, students', array_column($tables, 't') === ['events', 'registrations', 'students'],
      implode(', ', array_column($tables, 't')));
check('all tables InnoDB with utf8mb4_unicode_ci', count(array_filter($tables, fn($t) => $t['e'] === 'InnoDB' && $t['c'] === 'utf8mb4_unicode_ci')) === 3);
$nullable = rows($pdo, "SELECT COUNT(*) AS n FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = ? AND IS_NULLABLE = 'YES'", [$schema])[0]['n'];
check('no column allows NULL', (int) $nullable === 0, "nullable columns: $nullable");
$types = [];
foreach (rows($pdo, 'SELECT TABLE_NAME AS t, COLUMN_NAME AS c, COLUMN_TYPE AS ty, EXTRA AS x FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = ?', [$schema]) as $col) {
    $types[$col['t'] . '.' . $col['c']] = trim($col['ty'] . ' ' . $col['x']);
}
check('data types as designed', $types['students.student_id'] === 'int(10) unsigned auto_increment'
    && $types['students.branch'] === "enum('CSE','CE','IT')" && $types['students.semester'] === 'tinyint(3) unsigned'
    && $types['events.event_date'] === 'date' && $types['events.capacity'] === 'smallint(5) unsigned'
    && $types['registrations.status'] === "enum('registered','attended','cancelled')"
    && $types['registrations.registered_at'] === 'datetime', implode('; ', array_map(fn($k) => "$k=$types[$k]", ['students.branch', 'events.capacity'])));

// 3. Keys and indexes
echo "-- Keys and indexes\n";
$pks = rows($pdo, "SELECT TABLE_NAME AS t, COLUMN_NAME AS c FROM information_schema.KEY_COLUMN_USAGE
                   WHERE TABLE_SCHEMA = ? AND CONSTRAINT_NAME = 'PRIMARY' ORDER BY TABLE_NAME", [$schema]);
check('primary keys: event_id, registration_id, student_id',
      array_map(fn($k) => $k['t'] . '.' . $k['c'], $pks) === ['events.event_id', 'registrations.registration_id', 'students.student_id']);
$fks = rows($pdo, "SELECT k.CONSTRAINT_NAME AS n, k.COLUMN_NAME AS c, k.REFERENCED_TABLE_NAME AS rt, k.REFERENCED_COLUMN_NAME AS rc,
                          r.DELETE_RULE AS d, r.UPDATE_RULE AS u
                   FROM information_schema.KEY_COLUMN_USAGE AS k
                   JOIN information_schema.REFERENTIAL_CONSTRAINTS AS r
                     ON r.CONSTRAINT_SCHEMA = k.TABLE_SCHEMA AND r.CONSTRAINT_NAME = k.CONSTRAINT_NAME
                   WHERE k.TABLE_SCHEMA = ? ORDER BY k.CONSTRAINT_NAME", [$schema]);
check('foreign key registrations.event_id -> events.event_id (CASCADE)', isset($fks[0]) && $fks[0]['c'] === 'event_id'
      && $fks[0]['rt'] === 'events' && $fks[0]['rc'] === 'event_id' && $fks[0]['d'] === 'CASCADE' && $fks[0]['u'] === 'CASCADE');
check('foreign key registrations.student_id -> students.student_id (CASCADE)', isset($fks[1]) && $fks[1]['c'] === 'student_id'
      && $fks[1]['rt'] === 'students' && $fks[1]['rc'] === 'student_id' && $fks[1]['d'] === 'CASCADE' && $fks[1]['u'] === 'CASCADE');
check('exactly 2 foreign keys', count($fks) === 2);
$indexes = [];
foreach (rows($pdo, 'SELECT INDEX_NAME AS i, NON_UNIQUE AS nu FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = ? GROUP BY TABLE_NAME, INDEX_NAME, NON_UNIQUE', [$schema]) as $index) {
    $indexes[$index['i']] = (int) $index['nu'];
}
check('unique keys on student_code, email, (title, event_date), (student_id, event_id)',
      ($indexes['uq_students_code'] ?? 1) === 0 && ($indexes['uq_students_email'] ?? 1) === 0
      && ($indexes['uq_events_title_date'] ?? 1) === 0 && ($indexes['uq_registrations_student_event'] ?? 1) === 0);
check('indexes on branch, event_date, registrations.event_id', isset($indexes['idx_students_branch'], $indexes['idx_events_date'], $indexes['idx_registrations_event']));
$checks = rows($pdo, 'SELECT CONSTRAINT_NAME AS n FROM information_schema.CHECK_CONSTRAINTS WHERE CONSTRAINT_SCHEMA = ? ORDER BY CONSTRAINT_NAME', [$schema]);
check('CHECK constraints on capacity, email, semester', array_column($checks, 'n') === ['chk_events_capacity', 'chk_students_email', 'chk_students_semester']);

// 4. Seed data
echo "-- Seed data\n";
$counts = rows($pdo, 'SELECT (SELECT COUNT(*) FROM students) AS s, (SELECT COUNT(*) FROM events) AS e, (SELECT COUNT(*) FROM registrations) AS r')[0];
check('8 students, 5 events, 12 registrations', [(int) $counts['s'], (int) $counts['e'], (int) $counts['r']] === [8, 5, 12], json_encode($counts));
$fake = rows($pdo, "SELECT COUNT(*) AS n FROM students WHERE email LIKE '%@example.com' AND student_code REGEXP '^DEMO-S[0-9]{3}$'")[0]['n'];
check('all students fictional (DEMO-S codes, example.com emails)', (int) $fake === 8);
$orphans = rows($pdo, 'SELECT COUNT(*) AS n FROM registrations AS r LEFT JOIN students AS s ON s.student_id = r.student_id
                       LEFT JOIN events AS e ON e.event_id = r.event_id WHERE s.student_id IS NULL OR e.event_id IS NULL')[0]['n'];
check('no orphan registrations (every row joins a student and an event)', (int) $orphans === 0);
$over = rows($pdo, "SELECT COUNT(*) AS n FROM events AS e WHERE e.capacity < (SELECT COUNT(*) FROM registrations AS r WHERE r.event_id = e.event_id AND r.status <> 'cancelled')")[0]['n'];
check('no event has more registrations than its capacity', (int) $over === 0);

// 5. Prepared statements with parameters
echo "-- Prepared statements\n";
$byBranch = fn(string $branch) => array_column(rows($pdo, 'SELECT student_code FROM students WHERE branch = :branch ORDER BY student_id', [':branch' => $branch]), 'student_code');
check('branch = CSE returns 3 students', $byBranch('CSE') === ['DEMO-S001', 'DEMO-S005', 'DEMO-S008']);
check('branch = IT returns 3, CE returns 2', count($byBranch('IT')) === 3 && count($byBranch('CE')) === 2);
check("SQL injection text \"CSE' OR '1'='1\" is treated as a value (0 rows)", $byBranch("CSE' OR '1'='1") === []);
$stmt = $pdo->prepare('SELECT title FROM events WHERE event_date BETWEEN ? AND ? ORDER BY event_date');
$stmt->execute(['2026-08-01', '2026-08-31']);
check('positional placeholders: 2 events in August 2026', $stmt->fetchAll(PDO::FETCH_COLUMN) === ['Inter-college Hackathon', 'Web Development Bootcamp']);
$stmt = $pdo->prepare('SELECT student_id FROM students WHERE student_id = :id');
$stmt->bindValue(':id', 5, PDO::PARAM_INT);
$stmt->execute();
check('bindValue with PDO::PARAM_INT returns an integer', $stmt->fetchColumn() === 5);

// 6. Constraints and cascading (rolled back)
echo "-- Constraints (inside a rolled-back transaction)\n";
$pdo->beginTransaction();
$insertStudent = 'INSERT INTO students (student_code, full_name, email, branch, semester) VALUES (?, ?, ?, ?, ?)';
check("insert with an apostrophe through a bound parameter (O'Neil)", error_number($pdo, $insertStudent, ['DEMO-S099', "Anne-Marie O'Neil", 'anne.oneil@example.com', 'IT', 2]) === 0
      && rows($pdo, 'SELECT full_name FROM students WHERE student_code = ?', ['DEMO-S099'])[0]['full_name'] === "Anne-Marie O'Neil");
check('registration for a student that does not exist is rejected (FK, error 1452)', ($n = error_number($pdo, 'INSERT INTO registrations (student_id, event_id) VALUES (?, ?)', [999, 2])) === 1452, "error $n");
check('registration for an event that does not exist is rejected (FK, error 1452)', ($n = error_number($pdo, 'INSERT INTO registrations (student_id, event_id) VALUES (?, ?)', [3, 999])) === 1452, "error $n");
check('same student twice for one event is rejected (UNIQUE, error 1062)', ($n = error_number($pdo, 'INSERT INTO registrations (student_id, event_id) VALUES (?, ?)', [1, 1])) === 1062, "error $n");
check('duplicate email is rejected (UNIQUE, error 1062)', ($n = error_number($pdo, $insertStudent, ['DEMO-S098', 'Test Person', 'aarohi.menon@example.com', 'CSE', 1])) === 1062, "error $n");
check('semester 9 is rejected (CHECK, error 4025)', ($n = error_number($pdo, $insertStudent, ['DEMO-S097', 'Test Person', 'test.person@example.com', 'CSE', 9])) === 4025, "error $n");
check("email 'abc' is rejected (CHECK, error 4025)", ($n = error_number($pdo, $insertStudent, ['DEMO-S096', 'Test Person', 'abc', 'CSE', 1])) === 4025, "error $n");
check('event capacity 0 is rejected (CHECK, error 4025)', ($n = error_number($pdo, 'INSERT INTO events (title, event_date, venue, category, capacity) VALUES (?, ?, ?, ?, ?)', ['Test Event', '2026-12-01', 'Hall', 'Test', 0])) === 4025, "error $n");
check("branch 'XYZ' is rejected (ENUM, strict mode error 1265)", ($n = error_number($pdo, $insertStudent, ['DEMO-S095', 'Test Person', 'test.two@example.com', 'XYZ', 1])) === 1265, "error $n");
check('deleting a student cascades to the registrations', error_number($pdo, 'DELETE FROM students WHERE student_id = ?', [1]) === 0
      && (int) rows($pdo, 'SELECT COUNT(*) AS n FROM registrations WHERE student_id = ?', [1])[0]['n'] === 0
      && (int) rows($pdo, 'SELECT COUNT(*) AS n FROM registrations')[0]['n'] === 10);
check('changing an event_id cascades to the registrations', error_number($pdo, 'UPDATE events SET event_id = ? WHERE event_id = ?', [50, 5]) === 0
      && (int) rows($pdo, 'SELECT COUNT(*) AS n FROM registrations WHERE event_id = ?', [50])[0]['n'] === 1);
$pdo->rollBack();
$after = rows($pdo, 'SELECT (SELECT COUNT(*) FROM students) AS s, (SELECT COUNT(*) FROM events) AS e, (SELECT COUNT(*) FROM registrations) AS r')[0];
check('rollback restored 8 / 5 / 12 rows', [(int) $after['s'], (int) $after['e'], (int) $after['r']] === [8, 5, 12]);

// 7. Stored procedures (rolled back)
echo "-- Stored procedures\n";
$roster = rows($pdo, 'CALL get_event_roster(?)', [1]);
check('get_event_roster(1) lists the 4 hackathon students', count($roster) === 4, implode(', ', array_column($roster, 'student_code')));
$pdo->beginTransaction();
$message = function (int $student, int $event) use ($pdo): string {
    try {
        rows($pdo, 'CALL register_student_for_event(?, ?)', [$student, $event]);
        return 'ok';
    } catch (PDOException $exception) {
        return ($exception->errorInfo[0] ?? '') . ' ' . ($exception->errorInfo[2] ?? '');
    }
};
check("full event (capacity 4) is refused with 'Event is full'", ($m = $message(3, 1)) === '45000 Event is full', $m);
check("unknown event is refused with 'Event not found'", ($m = $message(3, 99)) === '45000 Event not found', $m);
$new = rows($pdo, 'CALL register_student_for_event(?, ?)', [3, 3]);
check('free place: registration created and its id returned', isset($new[0]['registration_id']) && (int) $new[0]['registration_id'] > 12);
$pdo->rollBack();
check('rollback removed the test registration', (int) rows($pdo, 'SELECT COUNT(*) AS n FROM registrations')[0]['n'] === 12);

echo PHP_EOL . "Result: $passed passed, $failed failed" . PHP_EOL;
exit($failed === 0 ? 0 : 1);
