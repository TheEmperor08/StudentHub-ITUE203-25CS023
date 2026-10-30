<?php
// StudentHub – Practical 9: server-side validation, duplicate checks and the user + audit-log insert.
// Every query that contains a value from the form is a MySQLi prepared statement.
declare(strict_types=1);

const FIELDS = ['full_name', 'username', 'email', 'password', 'confirm_password'];
const AUDIT_REGISTERED = 'USER_REGISTERED';

// Reads one form value. Returns null when the value is not a plain string (for example name[]=x sends an
// array), so the caller can reject it instead of passing an array on to string functions.
function form_string(array $input, string $key): ?string
{
    $value = $input[$key] ?? '';
    return is_string($value) ? $value : null;
}

// Password rules shared by the server and (as a copy in register.js) the browser. Returns the rules not met.
function password_problems(string $password): array
{
    $problems = [];
    if (mb_strlen($password, 'UTF-8') < 8) {
        $problems[] = 'at least 8 characters';
    }
    if (strlen($password) > 72) {                       // bcrypt uses only the first 72 bytes
        $problems[] = 'at most 72 characters';
    }
    if (!preg_match('/[A-Z]/', $password)) {
        $problems[] = 'an uppercase letter';
    }
    if (!preg_match('/[a-z]/', $password)) {
        $problems[] = 'a lowercase letter';
    }
    if (!preg_match('/[0-9]/', $password)) {
        $problems[] = 'a number';
    }
    if (!preg_match('/[^A-Za-z0-9]/', $password)) {
        $problems[] = 'a special character such as ! @ # ?';
    }
    return $problems;
}

// Validates the submitted form. Returns [clean values, errors by field]; nothing from the browser is trusted.
function validate_registration(array $input): array
{
    $errors = [];
    $values = [];
    foreach (FIELDS as $field) {
        $value = form_string($input, $field);
        if ($value === null) {
            $errors[$field] = 'This field must be sent as text.';
            $value = '';
        } elseif (!mb_check_encoding($value, 'UTF-8')) {
            $errors[$field] = 'This field contains characters that are not allowed.';
            $value = '';
        }
        $values[$field] = $value;
    }
    // Names are trimmed and repeated spaces removed; passwords are used exactly as typed
    $fullName = trim((string) preg_replace('/\s+/u', ' ', $values['full_name']));
    $username = trim($values['username']);
    $email = trim($values['email']);
    $password = $values['password'];
    $confirm = $values['confirm_password'];

    if (!isset($errors['full_name'])) {
        if ($fullName === '') {
            $errors['full_name'] = 'Full name is required.';
        } elseif (mb_strlen($fullName, 'UTF-8') < 2 || mb_strlen($fullName, 'UTF-8') > 100) {
            $errors['full_name'] = 'Full name must be 2 to 100 characters long.';
        } elseif (!preg_match("/^\\p{L}[\\p{L}\\p{M} .'-]*$/u", $fullName)) {
            $errors['full_name'] = 'Full name may contain only letters, spaces, apostrophes, hyphens and full stops.';
        }
    }
    if (!isset($errors['username'])) {
        if ($username === '') {
            $errors['username'] = 'Username is required.';
        } elseif (strlen($username) < 3 || strlen($username) > 30) {
            $errors['username'] = 'Username must be 3 to 30 characters long.';
        } elseif (!preg_match('/^[A-Za-z][A-Za-z0-9_]*$/', $username)) {
            $errors['username'] = 'Username must start with a letter and contain only letters, numbers and underscores.';
        }
    }
    if (!isset($errors['email'])) {
        if ($email === '') {
            $errors['email'] = 'Email address is required.';
        } elseif (strlen($email) > 254 || filter_var($email, FILTER_VALIDATE_EMAIL) === false) {
            $errors['email'] = 'Enter a valid email address, for example name@example.com.';
        }
    }
    if (!isset($errors['password'])) {
        if ($password === '') {
            $errors['password'] = 'Password is required.';
        } elseif ($problems = password_problems($password)) {
            $errors['password'] = 'Password must contain ' . implode(', ', $problems) . '.';
        }
    }
    if (!isset($errors['confirm_password'])) {
        if ($confirm === '') {
            $errors['confirm_password'] = 'Please confirm your password.';
        } elseif (!hash_equals($password, $confirm)) {
            $errors['confirm_password'] = 'Passwords do not match.';
        }
    }
    if (($input['terms'] ?? null) !== '1') {
        $errors['terms'] = 'You must accept the terms and conditions.';
    }

    $clean = ['full_name' => $fullName, 'username' => $username, 'email' => $email, 'password' => $password];
    return [$clean, $errors];
}

// Checks username and email separately with prepared statements and returns a friendly error for each one
// that is already registered. The UNIQUE keys in MySQL still guard against two requests at the same moment.
function find_duplicates(mysqli $db, string $username, string $email): array
{
    $errors = [];
    $stmt = $db->prepare('SELECT 1 FROM users WHERE username = ? LIMIT 1');
    $stmt->bind_param('s', $username);
    $stmt->execute();
    if ($stmt->get_result()->num_rows > 0) {
        $errors['username'] = 'This username is already taken. Please choose another one.';
    }
    $stmt->close();

    $stmt = $db->prepare('SELECT 1 FROM users WHERE email = ? LIMIT 1');
    $stmt->bind_param('s', $email);
    $stmt->execute();
    if ($stmt->get_result()->num_rows > 0) {
        $errors['email'] = 'An account with this email address already exists.';
    }
    $stmt->close();
    return $errors;
}

// Inserts the user and the audit-log entry in one transaction: either both rows are saved or neither.
// Returns ['user_id' => id] on success or ['errors' => [...]] when a UNIQUE key rejected the row.
function create_user(mysqli $db, string $fullName, string $username, string $email, string $passwordHash): array
{
    $db->begin_transaction();
    try {
        $stmt = $db->prepare('INSERT INTO users (full_name, username, email, password_hash) VALUES (?, ?, ?, ?)');
        $stmt->bind_param('ssss', $fullName, $username, $email, $passwordHash);
        $stmt->execute();
        $userId = (int) $db->insert_id;
        $stmt->close();

        $action = AUDIT_REGISTERED;
        $stmt = $db->prepare('INSERT INTO audit_logs (user_id, action) VALUES (?, ?)');
        $stmt->bind_param('is', $userId, $action);
        $stmt->execute();
        $stmt->close();

        $db->commit();
        return ['user_id' => $userId];
    } catch (mysqli_sql_exception $exception) {
        $db->rollback();
        if ($exception->getCode() === 1062) {         // duplicate key: another request registered it first
            $key = str_contains($exception->getMessage(), 'uq_users_email') ? 'email' : 'username';
            return ['errors' => [$key => $key === 'email'
                ? 'An account with this email address already exists.'
                : 'This username is already taken. Please choose another one.']];
        }
        throw $exception;
    }
}

// The whole registration after validation: duplicate check, password_hash() and the transaction.
// Database problems are logged (without any password or hash) and reported as a RuntimeException.
function register_user(mysqli $db, array $clean): array
{
    try {
        $duplicates = find_duplicates($db, $clean['username'], $clean['email']);
        if ($duplicates) {
            return ['errors' => $duplicates];
        }
        $hash = password_hash($clean['password'], PASSWORD_DEFAULT);
        return create_user($db, $clean['full_name'], $clean['username'], $clean['email'], $hash);
    } catch (mysqli_sql_exception $exception) {
        error_log('Practical 9 registration failed: [' . $exception->getCode() . '] ' . $exception->getMessage());
        throw new RuntimeException('Registration could not be completed.');
    }
}
