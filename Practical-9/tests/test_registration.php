<?php
// StudentHub – Practical 9: database and validation tests (PHP CLI).
//   C:\xampp\php\php.exe tests\test_registration.php
// Runs against the disposable database studenthub_prac9_test (created from schema.sql and removed again).
// Test passwords are random, never printed, and never written to any file.
declare(strict_types=1);

if (PHP_SAPI !== 'cli') {
    http_response_code(403);
    exit;
}
require __DIR__ . '/test_database.php';
$logFile = tempnam(sys_get_temp_dir(), 'p9log');
ini_set('error_log', $logFile);                    // check later that no password or hash was logged
putenv('P9_DB_NAME=' . TEST_DB);
require dirname(__DIR__) . '/db.php';
require dirname(__DIR__) . '/includes/registration.php';
ini_set('display_errors', '1');                    // db.php turns it off; the CLI tests want to see problems

$passed = 0;
$failed = 0;
function check(string $name, bool $ok, string $detail = ''): void
{
    global $passed, $failed;
    $ok ? $passed++ : $failed++;
    echo ($ok ? 'PASS' : 'FAIL') . "  $name" . ($detail !== '' ? "  [$detail]" : '') . PHP_EOL;
}

function random_password(): string
{
    return 'Aa1!' . bin2hex(random_bytes(8));      // meets every rule; kept only in memory
}

function valid_input(array $override = []): array
{
    static $n = 0;
    $n++;
    $password = $override['password'] ?? random_password();
    return array_merge(['full_name' => "Test User", 'username' => "test_user_$n", 'email' => "test.user$n@example.com",
                        'password' => $password, 'confirm_password' => $password, 'terms' => '1'], $override);
}

function scalar(mysqli $db, string $sql, array $params = []): mixed
{
    $stmt = $db->prepare($sql);
    if ($params) {
        $stmt->bind_param(str_repeat('s', count($params)), ...$params);
    }
    $stmt->execute();
    $row = $stmt->get_result()->fetch_row();
    return $row[0] ?? null;
}

function mysql_error_code(callable $fn): int
{
    try {
        $fn();
        return 0;
    } catch (mysqli_sql_exception $exception) {
        return $exception->getCode();
    }
}

test_db_create();
$secrets = [];                                     // every password and hash used, to search the log for them
try {
    $db = get_db();

    echo "-- database structure\n";
    check('connected to ' . TEST_DB, scalar($db, 'SELECT DATABASE()') === TEST_DB);
    $tables = $db->query("SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME <> 'p9_test_marker' ORDER BY TABLE_NAME")->fetch_all();
    check('tables audit_logs and users, both InnoDB', $tables === [['audit_logs', 'InnoDB'], ['users', 'InnoDB']], json_encode($tables));
    $nullable = (int) scalar($db, "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN ('users','audit_logs') AND IS_NULLABLE = 'YES'");
    check('every column is NOT NULL', $nullable === 0);
    $keys = $db->query("SELECT CONSTRAINT_NAME, CONSTRAINT_TYPE FROM information_schema.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN ('users','audit_logs') ORDER BY CONSTRAINT_NAME")->fetch_all();
    $keyNames = array_map(fn($k) => $k[0] . ':' . $k[1], $keys);
    foreach (['uq_users_username:UNIQUE', 'uq_users_email:UNIQUE', 'fk_audit_logs_user:FOREIGN KEY', 'chk_users_password_hash:CHECK'] as $expected) {
        check("constraint $expected", in_array($expected, $keyNames, true));
    }
    check('role defaults to student', scalar($db, "SELECT COLUMN_DEFAULT FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'role'") === "'student'");
    check('sample data: 3 fictional users with example.com addresses and 3 audit entries',
        (int) scalar($db, "SELECT COUNT(*) FROM users WHERE email LIKE '%@example.com'") === 3
        && (int) scalar($db, 'SELECT COUNT(*) FROM audit_logs') === 3);
    check('sample password hashes are bcrypt hashes', (int) scalar($db, "SELECT COUNT(*) FROM users WHERE password_hash LIKE '\$2y\$10\$%' AND CHAR_LENGTH(password_hash) = 60") === 3);
    check('strict SQL mode on this connection', str_contains((string) scalar($db, 'SELECT @@SESSION.sql_mode'), 'STRICT_ALL_TABLES'));

    echo "-- server-side validation\n";
    [, $errors] = validate_registration([]);
    check('empty form: an error for all six fields', array_keys($errors) === ['full_name', 'username', 'email', 'password', 'confirm_password', 'terms'], implode(',', array_keys($errors)));
    check('empty form: "Full name is required."', ($errors['full_name'] ?? '') === 'Full name is required.');
    [, $errors] = validate_registration(valid_input(['full_name' => '   ', 'username' => '  ']));
    check('fields of spaces only count as empty', isset($errors['full_name'], $errors['username']) && $errors['username'] === 'Username is required.');
    foreach (['plainaddress', 'name@', '@example.com', 'name@example', 'na me@example.com', 'name@@example.com', "x@example.com' OR '1'='1"] as $bad) {
        [, $errors] = validate_registration(valid_input(['email' => $bad]));
        check("invalid email rejected: $bad", ($errors['email'] ?? '') === 'Enter a valid email address, for example name@example.com.');
    }
    $password = random_password();
    [, $errors] = validate_registration(valid_input(['password' => $password, 'confirm_password' => $password . 'x']));
    check('password mismatch rejected', ($errors['confirm_password'] ?? '') === 'Passwords do not match.' && count($errors) === 1);
    foreach (['short' => 'Aa1!a', 'no uppercase' => 'abcdef1!', 'no lowercase' => 'ABCDEF1!', 'no number' => 'Abcdefg!', 'no special' => 'Abcdefg1', 'over 72 bytes' => 'Aa1!' . str_repeat('x', 69)] as $case => $weak) {
        [, $errors] = validate_registration(valid_input(['password' => $weak, 'confirm_password' => $weak]));
        check("weak password rejected ($case)", isset($errors['password']));
    }
    foreach (['ab' => 'too short', 'a' . str_repeat('b', 30) => 'too long', '1student' => 'starts with a digit', 'stu dent' => 'space', 'stu-dent' => 'hyphen', "admin' OR '1'='1" => 'SQL injection text', 'ünï' => 'non-ASCII'] as $bad => $case) {
        [, $errors] = validate_registration(valid_input(['username' => $bad]));
        check("invalid username rejected ($case)", isset($errors['username']));
    }
    foreach (['<script>alert(1)</script>', "Robert'); DROP TABLE users;--", 'A', 'Name123'] as $bad) {
        [, $errors] = validate_registration(valid_input(['full_name' => $bad]));
        check('invalid full name rejected: ' . $bad, isset($errors['full_name']));
    }
    [$clean, $errors] = validate_registration(valid_input(['full_name' => "  Zoë   O'Neil-Fernandes ", 'username' => ' new_user ']));
    check("valid input accepted; name trimmed (Zoë O'Neil-Fernandes)", $errors === [] && $clean['full_name'] === "Zoë O'Neil-Fernandes" && $clean['username'] === 'new_user');
    [, $errors] = validate_registration(valid_input(['username' => ['x'], 'email' => ['a' => 'b']]));
    check('array values instead of text rejected', ($errors['username'] ?? '') === 'This field must be sent as text.' && isset($errors['email']));
    [, $errors] = validate_registration(valid_input(['full_name' => "Bad \xC3\x28 UTF-8"]));
    check('invalid UTF-8 rejected', ($errors['full_name'] ?? '') === 'This field contains characters that are not allowed.');
    foreach ([null, '', '0', 'on', ['1']] as $terms) {
        $input = valid_input();
        if ($terms === null) {
            unset($input['terms']);
        } else {
            $input['terms'] = $terms;
        }
        [, $errors] = validate_registration($input);
        check('terms not accepted: ' . json_encode($terms), isset($errors['terms']));
    }

    echo "-- duplicate checks (prepared statements)\n";
    check('duplicate username found', array_keys(find_duplicates($db, 'demo_asha', 'new@example.com')) === ['username']);
    check('duplicate username found regardless of case (DEMO_ASHA)', array_keys(find_duplicates($db, 'DEMO_ASHA', 'new@example.com')) === ['username']);
    check('duplicate email found', array_keys(find_duplicates($db, 'brand_new', 'kabir.sample@example.com')) === ['email']);
    check('duplicate email found regardless of case', array_keys(find_duplicates($db, 'brand_new', 'Kabir.Sample@Example.com')) === ['email']);
    check('both duplicates reported', array_keys(find_duplicates($db, 'demo_meera', 'meera.test@example.com')) === ['username', 'email']);
    check("injection text is only data: \"x' OR '1'='1\" finds nothing", find_duplicates($db, "x' OR '1'='1", "x' OR '1'='1") === []);

    echo "-- successful registration\n";
    $usersBefore = (int) scalar($db, 'SELECT COUNT(*) FROM users');
    $auditBefore = (int) scalar($db, 'SELECT COUNT(*) FROM audit_logs');
    $password = random_password();
    [$clean, $errors] = validate_registration(valid_input(['full_name' => "Zoë O'Neil", 'username' => 'zoe_oneil', 'email' => 'zoe.oneil@example.com', 'password' => $password, 'confirm_password' => $password]));
    $result = register_user($db, $clean);
    $userId = $result['user_id'] ?? 0;
    check('register_user() returns the new user_id', $userId > 3, json_encode(array_keys($result)));
    $row = $db->query("SELECT * FROM users WHERE user_id = $userId")->fetch_assoc();
    check("row inserted with the submitted values (Zoë O'Neil, zoe_oneil, zoe.oneil@example.com)", $row && $row['full_name'] === "Zoë O'Neil" && $row['username'] === 'zoe_oneil' && $row['email'] === 'zoe.oneil@example.com');
    check('role is student', ($row['role'] ?? '') === 'student');
    check('users table has exactly one more row', (int) scalar($db, 'SELECT COUNT(*) FROM users') === $usersBefore + 1);
    $hash = (string) ($row['password_hash'] ?? '');
    $secrets[] = $password;
    $secrets[] = $hash;
    check('stored value is a bcrypt hash ($2y$, 60 characters)', str_starts_with($hash, '$2y$') && strlen($hash) === 60, substr($hash, 0, 7) . '…');
    check('stored value is not the password', $hash !== $password && !str_contains($hash, $password));
    check('password_info() reports bcrypt', password_get_info($hash)['algoName'] === 'bcrypt');
    check('password_verify(correct password, stored hash) is true', password_verify($password, $hash));
    check('password_verify(wrong password, stored hash) is false', !password_verify($password . 'x', $hash));
    check('no column of the new row contains the password', !in_array($password, $row, true));
    $audit = $db->query("SELECT * FROM audit_logs WHERE user_id = $userId")->fetch_all(MYSQLI_ASSOC);
    check('audit log: exactly one USER_REGISTERED entry for the new user', count($audit) === 1 && $audit[0]['action'] === 'USER_REGISTERED');
    check('audit log has no password or hash column', array_keys($audit[0] ?? []) === ['audit_id', 'user_id', 'action', 'created_at']);
    check('audit_logs grew by exactly one row', (int) scalar($db, 'SELECT COUNT(*) FROM audit_logs') === $auditBefore + 1);
    check('two hashes of the same password differ (random salt)', password_hash($password, PASSWORD_DEFAULT) !== $hash);

    echo "-- failed registrations create no user and no audit entry\n";
    $usersBefore = (int) scalar($db, 'SELECT COUNT(*) FROM users');
    $auditBefore = (int) scalar($db, 'SELECT COUNT(*) FROM audit_logs');
    [$clean] = validate_registration(valid_input(['username' => 'ZOE_ONEIL']));
    $result = register_user($db, $clean);
    check('duplicate username (ZOE_ONEIL) refused with a friendly message', ($result['errors']['username'] ?? '') === 'This username is already taken. Please choose another one.');
    [$clean] = validate_registration(valid_input(['email' => 'ZOE.ONEIL@example.com']));
    $result = register_user($db, $clean);
    check('duplicate email refused with a friendly message', ($result['errors']['email'] ?? '') === 'An account with this email address already exists.');
    check('no user row added by the refused attempts', (int) scalar($db, 'SELECT COUNT(*) FROM users') === $usersBefore);
    check('no audit entry added by the refused attempts', (int) scalar($db, 'SELECT COUNT(*) FROM audit_logs') === $auditBefore);

    echo "-- database constraints (direct SQL, bypassing the PHP checks)\n";
    $insert = function (string $username, string $email, string $hash) use ($db): void {
        $stmt = $db->prepare('INSERT INTO users (full_name, username, email, password_hash) VALUES (?, ?, ?, ?)');
        $name = 'Constraint Test';
        $stmt->bind_param('ssss', $name, $username, $email, $hash);
        $stmt->execute();
    };
    $validHash = password_hash(random_password(), PASSWORD_DEFAULT);
    $secrets[] = $validHash;
    check('UNIQUE username rejects a duplicate (error 1062)', mysql_error_code(fn() => $insert('demo_asha', 'other1@example.com', $validHash)) === 1062);
    check('UNIQUE email rejects a duplicate (error 1062)', mysql_error_code(fn() => $insert('other_user1', 'asha.demo@example.com', $validHash)) === 1062);
    check('UNIQUE keys ignore case (Demo_Asha → 1062)', mysql_error_code(fn() => $insert('Demo_Asha', 'other2@example.com', $validHash)) === 1062);
    check('CHECK refuses a plaintext password in password_hash (error 4025)', mysql_error_code(fn() => $insert('other_user2', 'other3@example.com', 'NotAHash123!')) === 4025);
    check('CHECK refuses an invalid username (error 4025)', mysql_error_code(fn() => $insert('9 bad', 'other4@example.com', $validHash)) === 4025);
    check('FOREIGN KEY refuses an audit entry for an unknown user (error 1452)', mysql_error_code(fn() => $db->query("INSERT INTO audit_logs (user_id, action) VALUES (999999, 'USER_REGISTERED')")) === 1452);
    check('FOREIGN KEY (RESTRICT) keeps users that have audit entries (error 1451)', mysql_error_code(fn() => $db->query("DELETE FROM users WHERE user_id = $userId")) === 1451);
    check('strict mode refuses a too-long full name (error 1406)', mysql_error_code(fn() => $db->query("INSERT INTO users (full_name, username, email, password_hash) VALUES (REPEAT('a', 101), 'long_name', 'long@example.com', '$validHash')")) === 1406);

    echo "-- two requests at the same moment (race condition)\n";
    // Connection B checks for duplicates while A's insert is not committed yet, so B's check finds nothing;
    // A then commits and B's insert must be stopped by the UNIQUE key with a friendly message.
    $other = test_server();
    $other->select_db(TEST_DB);
    $other->begin_transaction();
    $raceHash = password_hash(random_password(), PASSWORD_DEFAULT);
    $secrets[] = $raceHash;
    $stmt = $other->prepare("INSERT INTO users (full_name, username, email, password_hash) VALUES ('Race One', 'race_user', 'race@example.com', ?)");
    $stmt->bind_param('s', $raceHash);
    $stmt->execute();
    $other->query("INSERT INTO audit_logs (user_id, action) VALUES ({$other->insert_id}, 'USER_REGISTERED')");
    check('race: B\'s duplicate check does not see A\'s uncommitted row', find_duplicates($db, 'race_user', 'race@example.com') === []);
    $other->commit();
    $auditBefore = (int) scalar($db, 'SELECT COUNT(*) FROM audit_logs');
    $result = create_user($db, 'Race Two', 'race_user', 'race2@example.com', $raceHash);
    check('race: UNIQUE key stops B with "This username is already taken"', ($result['errors']['username'] ?? '') === 'This username is already taken. Please choose another one.');
    $result = create_user($db, 'Race Three', 'race_user3', 'RACE@example.com', $raceHash);
    check('race: same for the email ("An account with this email address already exists.")', ($result['errors']['email'] ?? '') === 'An account with this email address already exists.');
    check('race: B added no audit entry (transaction rolled back)', (int) scalar($db, 'SELECT COUNT(*) FROM audit_logs') === $auditBefore);
    check('race: only one race_user exists', (int) scalar($db, "SELECT COUNT(*) FROM users WHERE username = 'race_user' OR email = 'race@example.com'") === 1);
    $other->close();

    echo "-- transaction rollback when the audit insert fails\n";
    $usersBefore = (int) scalar($db, 'SELECT COUNT(*) FROM users');
    $db->query('RENAME TABLE audit_logs TO audit_logs_offline');      // makes the second INSERT fail
    [$clean] = validate_registration(valid_input(['username' => 'rollback_user', 'email' => 'rollback@example.com']));
    $thrown = null;
    try {
        register_user($db, $clean);
    } catch (RuntimeException $exception) {
        $thrown = $exception;
    }
    $db->query('RENAME TABLE audit_logs_offline TO audit_logs');
    check('register_user() reports a general RuntimeException', $thrown !== null && $thrown->getMessage() === 'Registration could not be completed.');
    check('the user insert was rolled back (no rollback_user row)', (int) scalar($db, "SELECT COUNT(*) FROM users WHERE username = 'rollback_user'") === 0 && (int) scalar($db, 'SELECT COUNT(*) FROM users') === $usersBefore);
    $logged = (string) file_get_contents($logFile);
    check('the real database error was written to the error log', str_contains($logged, 'Practical 9 registration failed: [1146]'));

    echo "-- multiple registrations\n";
    $ids = [];
    $auditBefore = (int) scalar($db, 'SELECT COUNT(*) FROM audit_logs');
    for ($i = 1; $i <= 5; $i++) {
        $password = random_password();
        [$clean, $errors] = validate_registration(valid_input(['username' => "batch_user_$i", 'email' => "batch$i@example.com", 'password' => $password, 'confirm_password' => $password]));
        $result = register_user($db, $clean);
        $ids[] = $result['user_id'] ?? 0;
        $hash = (string) scalar($db, 'SELECT password_hash FROM users WHERE username = ?', ["batch_user_$i"]);
        $secrets[] = $password;
        $secrets[] = $hash;
        if (!password_verify($password, $hash)) {
            $ids[] = 0;
        }
    }
    check('5 registrations in a row all succeed with different user IDs', !in_array(0, $ids, true) && count(array_unique($ids)) === 5, implode(',', $ids));
    check('5 new audit entries, one per user', (int) scalar($db, 'SELECT COUNT(*) FROM audit_logs') === $auditBefore + 5);
    check('each batch user has a different hash that verifies its own password', (int) scalar($db, "SELECT COUNT(DISTINCT password_hash) FROM users WHERE username LIKE 'batch\\_user\\_%'") === 5);
    check('every user has exactly one USER_REGISTERED entry', (int) scalar($db, "SELECT COUNT(*) FROM users u WHERE (SELECT COUNT(*) FROM audit_logs a WHERE a.user_id = u.user_id AND a.action = 'USER_REGISTERED') <> 1") === 0);

    echo "-- error log\n";
    $logged = (string) file_get_contents($logFile);
    $leaks = array_filter($secrets, fn($s) => $s !== '' && str_contains($logged, $s));
    check('no test password or password hash appears in the error log', $leaks === [] && !str_contains($logged, '$2y$'));
} finally {
    if (isset($db) && $db instanceof mysqli) {
        $db->close();
    }
    test_db_drop();
    @unlink($logFile);
}
check('test database removed again', !test_db_exists(test_server()));

echo PHP_EOL . "Result: $passed passed, $failed failed" . PHP_EOL;
exit($failed === 0 ? 0 : 1);
