<?php
// StudentHub – student self-registration (Practical 9 integrated into the portal).
//
// validate_registration()        every field checked on the server (the browser checks are only a convenience)
// register_student_account()     duplicate checks, password_hash() and ONE transaction that creates
//                                  1. the login account in users (role always 'student' – never taken from the form)
//                                  2. the student record in students with students.user_id = the new users.id
//                                Either both rows are saved or neither (rollback on any error).
//
// Enrollment numbers follow the existing scheme YY + course code + 3 digits (e.g. 26CS001): the next free number for
// that prefix is taken while the students rows are locked, so two registrations at the same moment never get the same
// number. A pre-existing student record with the same e-mail is NOT linked automatically; the registration is refused
// and the student is asked to contact the administrator (nothing is overwritten).

const REGISTRATION_COURSES = [                     // value shown in the form => code in the enrollment number
    'Information Technology'       => 'IT',
    'Computer Science Engineering' => 'CS',
    'Data Science'                 => 'DS',
    'Web Development'              => 'WD',
];
const REGISTRATION_GENDERS = ['Male', 'Female', 'Other'];
const REGISTRATION_FIELDS  = ['name', 'username', 'email', 'gender', 'course', 'adm_year', 'password', 'confirm_password'];

// Start year of the current academic year (July–June): Oct 2026 -> 2026, Mar 2027 -> 2026
function registration_academic_year(?int $now = null): int
{
    $now = $now ?? time();
    $year = (int) date('Y', $now);
    return (int) date('n', $now) >= 7 ? $year : $year - 1;
}

// Admission years offered in the form: the current academic year and the two before it
function registration_admission_years(): array
{
    $y = registration_academic_year();
    return [(string) $y, (string) ($y - 1), (string) ($y - 2)];
}

// Odd (first-half) semester of the current academic year: admitted this year -> 1, last year -> 3, two years ago -> 5
function registration_semester(int $admission_year): int
{
    return max(1, min(8, (registration_academic_year() - $admission_year) * 2 + 1));
}

// A form value as text, or null if it was not sent as a plain string (e.g. name[]=x)
function registration_text(array $input, string $key): ?string
{
    $value = $input[$key] ?? '';
    return is_string($value) && mb_check_encoding($value, 'UTF-8') ? $value : null;
}

// Returns [clean values, errors by field]
function validate_registration(array $input): array
{
    $errors = [];
    $raw = [];
    foreach (REGISTRATION_FIELDS as $field) {
        $value = registration_text($input, $field);
        if ($value === null) {
            $errors[$field] = 'This field contains characters that are not allowed.';
            $value = '';
        }
        $raw[$field] = $value;
    }
    $name     = trim((string) preg_replace('/\s+/u', ' ', $raw['name']));
    $username = trim($raw['username']);
    $email    = strtolower(trim($raw['email']));

    if (!isset($errors['name'])) {
        if ($name === '') {
            $errors['name'] = 'Please enter your full name.';
        } elseif (mb_strlen($name, 'UTF-8') < 2 || mb_strlen($name, 'UTF-8') > 100) {
            $errors['name'] = 'The name must be 2–100 characters long.';
        } elseif (!preg_match("/^\\p{L}[\\p{L}\\p{M} .'-]*$/u", $name)) {
            $errors['name'] = 'Use letters, spaces, apostrophes, dots and hyphens only.';
        }
    }
    if (!isset($errors['username'])) {
        if ($username === '') {
            $errors['username'] = 'Please choose a username.';
        } elseif (strlen($username) < 3 || strlen($username) > 30) {
            $errors['username'] = 'The username must be 3–30 characters long.';
        } elseif (!preg_match('/^[A-Za-z][A-Za-z0-9_]*$/', $username)) {
            $errors['username'] = 'Start with a letter; then use letters, numbers and underscores only.';
        }
    }
    if (!isset($errors['email'])) {
        if ($email === '') {
            $errors['email'] = 'Please enter your email address.';
        } elseif (strlen($email) > 100 || filter_var($email, FILTER_VALIDATE_EMAIL) === false) {
            $errors['email'] = 'Please enter a valid email address, e.g. name@example.com.';
        }
    }
    if (!isset($errors['gender']) && !in_array($raw['gender'], REGISTRATION_GENDERS, true)) {
        $errors['gender'] = 'Please choose Male, Female or Other.';
    }
    if (!isset($errors['course']) && !isset(REGISTRATION_COURSES[$raw['course']])) {
        $errors['course'] = 'Please select a course from the list.';
    }
    if (!isset($errors['adm_year']) && !in_array($raw['adm_year'], registration_admission_years(), true)) {
        $errors['adm_year'] = 'Please select an admission year from the list.';
    }
    if (!isset($errors['password'])) {
        $problems = password_problems($raw['password']);
        if ($raw['password'] === '') {
            $errors['password'] = 'Please choose a password.';
        } elseif ($problems) {
            $errors['password'] = 'The password needs ' . implode(', ', $problems) . '.';
        }
    }
    if (!isset($errors['confirm_password']) && !isset($errors['password']) && !hash_equals($raw['password'], $raw['confirm_password'])) {
        $errors['confirm_password'] = 'The passwords do not match.';
    }
    if (($input['agree'] ?? null) !== '1') {
        $errors['agree'] = 'Please accept the Terms & Conditions.';
    }

    $clean = [
        'name' => $name, 'username' => $username, 'email' => $email, 'gender' => $raw['gender'], 'course' => $raw['course'],
        'adm_year' => $raw['adm_year'], 'password' => $raw['password'],
    ];
    if (!isset($errors['adm_year'])) {
        $clean['semester'] = registration_semester((int) $raw['adm_year']);
    }
    return [$clean, $errors];
}

// Existing accounts and student records that block this registration (checked with prepared statements;
// the UNIQUE keys on users.username, users.email and students.email still guard against simultaneous requests)
function find_registration_conflicts(mysqli $db, string $username, string $email): array
{
    $errors = [];
    $stmt = $db->prepare('SELECT 1 FROM users WHERE username = ? LIMIT 1');
    $stmt->bind_param('s', $username);
    $stmt->execute();
    if ($stmt->get_result()->num_rows > 0) {
        $errors['username'] = 'This username is already taken. Please choose another one.';
    }
    $stmt->close();

    $stmt = $db->prepare('SELECT 1 FROM users WHERE LOWER(TRIM(email)) = ? LIMIT 1');
    $stmt->bind_param('s', $email);
    $stmt->execute();
    if ($stmt->get_result()->num_rows > 0) {
        $errors['email'] = 'An account with this email address already exists. Please sign in instead.';
    }
    $stmt->close();

    if (!isset($errors['email'])) {
        $stmt = $db->prepare('SELECT 1 FROM students WHERE LOWER(TRIM(email)) = ? LIMIT 1');
        $stmt->bind_param('s', $email);
        $stmt->execute();
        if ($stmt->get_result()->num_rows > 0) {
            // A record created by the administrator (or an older record): do not link it automatically
            $errors['email'] = 'A student record with this email address already exists. Please contact the administrator to activate your account.';
        }
        $stmt->close();
    }
    return $errors;
}

// Next enrollment number for the prefix (e.g. "26CS" -> "26CS004"); must run inside the registration transaction
function next_enrollment_number(mysqli $db, string $prefix): string
{
    $like = $prefix . '%';
    $stmt = $db->prepare('SELECT enrollment_no FROM students WHERE enrollment_no LIKE ? FOR UPDATE');
    $stmt->bind_param('s', $like);
    $stmt->execute();
    $max = 0;
    foreach ($stmt->get_result()->fetch_all(MYSQLI_NUM) as [$number]) {
        if (preg_match('/^' . preg_quote($prefix, '/') . '(\d{3})$/', (string) $number, $m)) {
            $max = max($max, (int) $m[1]);
        }
    }
    $stmt->close();
    if ($max >= 999) {
        throw new RuntimeException("No enrollment numbers left for prefix $prefix.");
    }
    return $prefix . sprintf('%03d', $max + 1);
}

// Creates the account and the linked student record in one transaction.
// Returns ['user_id', 'student_id', 'enrollment_no'] or ['errors' => [...]]; throws RuntimeException on server problems.
function register_student_account(mysqli $db, array $clean): array
{
    try {
        $conflicts = find_registration_conflicts($db, $clean['username'], $clean['email']);
        if ($conflicts) {
            return ['errors' => $conflicts];
        }
        $hash   = password_hash($clean['password'], PASSWORD_DEFAULT);
        $prefix = substr($clean['adm_year'], 2, 2) . REGISTRATION_COURSES[$clean['course']];

        $db->begin_transaction();
        try {
            $enrollment = next_enrollment_number($db, $prefix);

            $stmt = $db->prepare("INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, 'student')");
            $stmt->bind_param('sss', $clean['username'], $clean['email'], $hash);
            $stmt->execute();
            $user_id = (int) $stmt->insert_id;
            $stmt->close();

            $stmt = $db->prepare("INSERT INTO students (user_id, enrollment_no, name, email, course, gender, semester, status)
                                  VALUES (?, ?, ?, ?, ?, ?, ?, 'Active')");
            $stmt->bind_param('isssssi', $user_id, $enrollment, $clean['name'], $clean['email'], $clean['course'], $clean['gender'], $clean['semester']);
            $stmt->execute();
            $student_id = (int) $stmt->insert_id;
            $stmt->close();

            $db->commit();
            return ['user_id' => $user_id, 'student_id' => $student_id, 'enrollment_no' => $enrollment];
        } catch (Throwable $e) {
            $db->rollback();
            if ($e instanceof mysqli_sql_exception && $e->getCode() === 1062) {      // registered by someone else meanwhile
                return ['errors' => str_contains($e->getMessage(), "'username'")
                    ? ['username' => 'This username is already taken. Please choose another one.']
                    : ['email' => 'This email address is already registered. Please sign in or contact the administrator.']];
            }
            throw $e;
        }
    } catch (Throwable $e) {
        // Logged without any password or hash
        error_log('StudentHub registration failed: ' . get_class($e) . ' [' . $e->getCode() . '] ' . $e->getMessage());
        throw new RuntimeException('Registration could not be completed.');
    }
}
