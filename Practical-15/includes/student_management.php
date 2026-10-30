<?php
// StudentHub – student management in the Admin Console (Practical 11 integrated into the portal).
//
// The records are the portal's own studenthub_db.students rows – the same table used by self-registration, the profile
// pages and event registrations:
//   list / search / filter   student_filters() + student_filter_sql(): one parameterised WHERE clause shared by the
//                            table, the page count and the CSV export
//   add / edit               validate_student_record() + save_student_record(): server-side validation, unique
//                            enrollment number and e-mail (checked here and by the UNIQUE keys), prepared statements
//   soft delete              set_student_status(): status 'Active' <-> 'Inactive'. The row, its account link (user_id)
//                            and its event registrations are kept – nothing is ever deleted
//   CSV export               send_students_csv(): the filtered records, UTF-8 with BOM, formula injection neutralised
//
// Enrollment numbers keep the existing scheme YY + 2-letter code + 3 digits (e.g. 25CS011). Left empty on the add form,
// the next free number is assigned the same way as a self-registration: admission year (derived from the semester) +
// course code. No login account is created here; students.user_id is set only by self-registration.
// Requires mysqli in exception mode (the PHP 8.1+ default).

require_once __DIR__ . '/registration.php';

const STUDENT_STATUSES   = ['Active', 'Inactive'];
const STUDENTS_PER_PAGE  = 10;
const ENROLLMENT_PATTERN = '/^[0-9]{2}[A-Z]{2}[0-9]{3}$/';
const STUDENT_FIELDS     = ['enrollment_no', 'name', 'email', 'course', 'semester', 'gender'];

// Courses offered in the form and the filter: the registration courses plus every course already stored, so existing
// records keep their course names (nothing is renamed)
function student_courses(mysqli $db): array
{
    $courses = array_keys(REGISTRATION_COURSES);
    foreach ($db->query("SELECT DISTINCT course FROM students WHERE course <> ''")->fetch_all(MYSQLI_NUM) as [$course]) {
        if (!in_array($course, $courses, true)) {
            $courses[] = $course;
        }
    }
    sort($courses, SORT_NATURAL | SORT_FLAG_CASE);
    return $courses;
}

// Anything but 'Inactive' counts as active – the same rule as the event registration (includes/event_registration.php)
function student_is_active(array $student): bool
{
    return strcasecmp(trim((string) ($student['status'] ?? '')), 'Inactive') !== 0;
}

// Positive record ID from a request value, otherwise 0
function student_id_from($value): int
{
    return is_string($value) && preg_match('/^[1-9][0-9]{0,9}$/', $value) && (int) $value <= 2147483647 ? (int) $value : 0;
}

// ---------------------------------------------------------------- search, filters and pagination
// List options from the query string. Unknown courses, semesters and statuses are ignored, never used in SQL.
function student_filters(array $query, array $courses): array
{
    $text = fn (string $key): string => is_string($query[$key] ?? null) && mb_check_encoding($query[$key], 'UTF-8') ? trim($query[$key]) : '';
    $course = $text('course');
    $semester = $text('semester');
    $status = $text('status');
    $page = $text('page');
    return [
        'q'        => mb_substr($text('q'), 0, 100),
        'course'   => in_array($course, $courses, true) ? $course : '',
        'semester' => preg_match('/^[1-8]$/', $semester) ? $semester : '',
        'status'   => in_array($status, STUDENT_STATUSES, true) ? $status : '',
        'page'     => preg_match('/^[1-9][0-9]{0,5}$/', $page) ? (int) $page : 1,
    ];
}

// WHERE clause with ? placeholders. The search text is matched against name, e-mail and enrollment number; % and _
// typed by the user are escaped, so they are searched literally.
function student_filter_sql(array $filters): array
{
    $where = [];
    $types = '';
    $params = [];
    if ($filters['q'] !== '') {
        $like = '%' . addcslashes($filters['q'], '\\%_') . '%';
        $where[] = '(name LIKE ? OR email LIKE ? OR enrollment_no LIKE ?)';
        $types .= 'sss';
        array_push($params, $like, $like, $like);
    }
    if ($filters['course'] !== '') {
        $where[] = 'course = ?';
        $types .= 's';
        $params[] = $filters['course'];
    }
    if ($filters['semester'] !== '') {
        $where[] = 'semester = ?';
        $types .= 'i';
        $params[] = (int) $filters['semester'];
    }
    if ($filters['status'] === 'Inactive') {
        $where[] = "TRIM(status) = 'Inactive'";
    } elseif ($filters['status'] === 'Active') {
        $where[] = "COALESCE(TRIM(status), '') <> 'Inactive'";
    }
    return [$where ? ' WHERE ' . implode(' AND ', $where) : '', $types, $params];
}

function student_count(mysqli $db, array $filters): int
{
    [$where, $types, $params] = student_filter_sql($filters);
    $stmt = $db->prepare('SELECT COUNT(*) FROM students' . $where);
    if ($types !== '') {
        $stmt->bind_param($types, ...$params);
    }
    $stmt->execute();
    return (int) $stmt->get_result()->fetch_row()[0];
}

// Matching records, newest first. $limit = null returns every match (used by the CSV export).
function student_list(mysqli $db, array $filters, ?int $limit = null, int $offset = 0): array
{
    [$where, $types, $params] = student_filter_sql($filters);
    $sql = 'SELECT id, user_id, enrollment_no, name, email, course, semester, gender, status, created_at FROM students'
         . $where . ' ORDER BY id DESC';
    if ($limit !== null) {
        $sql .= ' LIMIT ? OFFSET ?';
        $types .= 'ii';
        array_push($params, $limit, $offset);
    }
    $stmt = $db->prepare($sql);
    if ($types !== '') {
        $stmt->bind_param($types, ...$params);
    }
    $stmt->execute();
    return $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
}

function student_status_counts(mysqli $db): array
{
    $row = $db->query("SELECT COUNT(*), COALESCE(SUM(TRIM(status) = 'Inactive'), 0) FROM students")->fetch_row();
    return ['Active' => (int) $row[0] - (int) $row[1], 'Inactive' => (int) $row[1]];
}

// admin_dashboard.php URL of the student list with the given filters (empty filters and page 1 are left out)
function student_list_url(array $filters, array $extra = []): string
{
    $params = ['tab' => 'students'];
    foreach (['q', 'course', 'semester', 'status'] as $key) {
        if ($filters[$key] !== '') {
            $params[$key] = $filters[$key];
        }
    }
    return 'admin_dashboard.php?' . http_build_query(array_merge($params, $extra));
}

function find_student_record(mysqli $db, int $id): ?array
{
    $stmt = $db->prepare('SELECT id, user_id, enrollment_no, name, email, course, semester, gender, status, created_at FROM students WHERE id = ?');
    $stmt->bind_param('i', $id);
    $stmt->execute();
    return $stmt->get_result()->fetch_assoc() ?: null;
}

function student_registration_count(mysqli $db, int $id): int
{
    $stmt = $db->prepare('SELECT COUNT(*) FROM registrations WHERE student_id = ?');
    $stmt->bind_param('i', $id);
    $stmt->execute();
    return (int) $stmt->get_result()->fetch_row()[0];
}

// ---------------------------------------------------------------- add and edit
// Returns [clean values, errors by field]. $existing is the stored record when editing (null when adding): a value
// that is not changed is kept as it is, even if it predates the current rules (e.g. a legacy enrollment number).
function validate_student_record(array $input, array $courses, ?array $existing = null): array
{
    $errors = [];
    $raw = [];
    foreach (STUDENT_FIELDS as $field) {
        $value = registration_text($input, $field);
        if ($value === null) {
            $errors[$field] = 'This field contains characters that are not allowed.';
            $value = '';
        }
        $raw[$field] = trim($value);
    }
    $old = fn (string $field): string => $existing === null ? '' : (string) ($existing[$field] ?? '');
    $clean = [
        'enrollment_no' => strtoupper($raw['enrollment_no']),
        'name'          => trim((string) preg_replace('/\s+/u', ' ', $raw['name'])),
        'email'         => strtolower($raw['email']),
        'course'        => $raw['course'],
        'semester'      => $raw['semester'],
        'gender'        => $raw['gender'],
    ];

    if (!isset($errors['enrollment_no'])) {
        if ($existing !== null && $clean['enrollment_no'] === strtoupper($old('enrollment_no'))) {
            $clean['enrollment_no'] = $existing['enrollment_no'];             // unchanged (NULL or a legacy value stays)
        } elseif ($clean['enrollment_no'] === '') {
            if ($existing !== null) {
                $errors['enrollment_no'] = 'Please enter the enrollment number.';
            }
            $clean['enrollment_no'] = null;                                   // add form: assigned automatically
        } elseif (strlen($clean['enrollment_no']) > 20 || !preg_match(ENROLLMENT_PATTERN, $clean['enrollment_no'])) {
            $errors['enrollment_no'] = 'Use 2 digits, 2 letters and 3 digits, e.g. 26IT004.';
        }
    }
    if (!isset($errors['name']) && !($existing !== null && $clean['name'] === $old('name'))) {
        if ($clean['name'] === '') {
            $errors['name'] = 'Please enter the full name.';
        } elseif (mb_strlen($clean['name'], 'UTF-8') < 2 || mb_strlen($clean['name'], 'UTF-8') > 100) {
            $errors['name'] = 'The name must be 2–100 characters long.';
        } elseif (!preg_match("/^\\p{L}[\\p{L}\\p{M} .'-]*$/u", $clean['name'])) {
            $errors['name'] = 'Use letters, spaces, apostrophes, dots and hyphens only.';
        }
    }
    if (!isset($errors['email'])) {
        if ($existing !== null && $clean['email'] === strtolower(trim($old('email')))) {
            $clean['email'] = $existing['email'];
        } elseif ($clean['email'] === '') {
            $errors['email'] = 'Please enter the email address.';
        } elseif (strlen($clean['email']) > 100 || filter_var($clean['email'], FILTER_VALIDATE_EMAIL) === false) {
            $errors['email'] = 'Please enter a valid email address, e.g. name@example.com.';
        }
    }
    if (!isset($errors['course']) && !in_array($clean['course'], $courses, true)) {
        $errors['course'] = 'Please select a course from the list.';
    }
    if (!isset($errors['semester'])) {
        if ($existing !== null && $clean['semester'] === '' && $existing['semester'] === null) {
            $clean['semester'] = null;                                        // legacy record without a semester
        } elseif ($clean['semester'] === '') {
            $errors['semester'] = 'Please select a semester.';
        } elseif (!preg_match('/^[1-8]$/', $clean['semester'])) {
            $errors['semester'] = 'The semester must be a number from 1 to 8.';
        } else {
            $clean['semester'] = (int) $clean['semester'];
        }
    }
    if (!isset($errors['gender']) && !in_array($clean['gender'], REGISTRATION_GENDERS, true)
        && !($existing !== null && $clean['gender'] === $old('gender'))) {
        $errors['gender'] = 'Please choose Male, Female or Other.';
    }
    if ($existing === null && $clean['enrollment_no'] === null && !isset($errors['course'])
        && !isset(REGISTRATION_COURSES[$clean['course']])) {
        $errors['enrollment_no'] = 'Automatic numbers exist only for ' . implode(', ', array_keys(REGISTRATION_COURSES))
                                 . '. Please enter the enrollment number for this course.';
    }
    return [$clean, $errors];
}

// Admission year of a student in this semester (the inverse of registration_semester(): semester 1/2 -> this year)
function student_admission_year(int $semester): int
{
    return registration_academic_year() - intdiv($semester - 1, 2);
}

// Validation plus the duplicate checks, so every problem is reported at once (save_student_record() repeats the
// duplicate checks inside its transaction, and the UNIQUE keys catch simultaneous requests)
function check_student_record(mysqli $db, array $input, array $courses, ?array $existing, int $id): array
{
    [$clean, $errors] = validate_student_record($input, $courses, $existing);
    $conflicts = student_conflicts($db, isset($errors['enrollment_no']) ? null : $clean['enrollment_no'],
                                   isset($errors['email']) ? null : $clean['email'], $id);
    return [$clean, $errors + $conflicts];
}

// Other records that already use this enrollment number or e-mail (any status – inactive records keep theirs)
function student_conflicts(mysqli $db, ?string $enrollment, ?string $email, int $except_id): array
{
    $errors = [];
    if ($enrollment !== null) {
        $stmt = $db->prepare('SELECT 1 FROM students WHERE enrollment_no = ? AND id <> ? LIMIT 1');
        $stmt->bind_param('si', $enrollment, $except_id);
        $stmt->execute();
        if ($stmt->get_result()->num_rows > 0) {
            $errors['enrollment_no'] = 'This enrollment number is already used by another student.';
        }
    }
    if ($email !== null) {
        $stmt = $db->prepare('SELECT 1 FROM students WHERE LOWER(TRIM(email)) = ? AND id <> ? LIMIT 1');
        $lower = strtolower(trim($email));
        $stmt->bind_param('si', $lower, $except_id);
        $stmt->execute();
        if ($stmt->get_result()->num_rows > 0) {
            $errors['email'] = 'Another student record already uses this email address.';
        }
    }
    return $errors;
}

// Adds ($id = null) or updates a record. Returns ['id', 'enrollment_no'] or ['errors' => [...]].
// Only the form fields are written: user_id (the account link), status, created_at and registrations are not touched.
function save_student_record(mysqli $db, array $clean, ?int $id = null): array
{
    $db->begin_transaction();
    try {
        $enrollment = $clean['enrollment_no'];
        if ($id === null && $enrollment === null) {
            $prefix = sprintf('%02d', student_admission_year($clean['semester']) % 100) . REGISTRATION_COURSES[$clean['course']];
            $enrollment = next_enrollment_number($db, $prefix);               // locks the prefix range until commit
        }
        $errors = student_conflicts($db, $enrollment, $clean['email'], $id ?? 0);
        if ($errors) {
            $db->rollback();
            return ['errors' => $errors];
        }
        if ($id === null) {
            $stmt = $db->prepare("INSERT INTO students (enrollment_no, name, email, course, semester, gender, status) VALUES (?, ?, ?, ?, ?, ?, 'Active')");
            $stmt->bind_param('ssssis', $enrollment, $clean['name'], $clean['email'], $clean['course'], $clean['semester'], $clean['gender']);
            $stmt->execute();
            $id = (int) $stmt->insert_id;
        } else {
            $stmt = $db->prepare('UPDATE students SET enrollment_no = ?, name = ?, email = ?, course = ?, semester = ?, gender = ? WHERE id = ?');
            $stmt->bind_param('ssssisi', $enrollment, $clean['name'], $clean['email'], $clean['course'], $clean['semester'], $clean['gender'], $id);
            $stmt->execute();
        }
        $db->commit();
        return ['id' => $id, 'enrollment_no' => $enrollment];
    } catch (mysqli_sql_exception $e) {
        $db->rollback();
        if ($e->getCode() === 1062) {                       // the same number or e-mail was saved by someone else meanwhile
            return ['errors' => str_contains($e->getMessage(), 'uq_students_enrollment_no')
                ? ['enrollment_no' => 'This enrollment number is already used by another student.']
                : ['email' => 'Another student record already uses this email address.']];
        }
        throw $e;
    }
}

// ---------------------------------------------------------------- soft delete and reactivation
// Only the status changes. Returns false if the record does not exist or already has that status.
function set_student_status(mysqli $db, int $id, bool $active): bool
{
    $stmt = $db->prepare($active
        ? "UPDATE students SET status = 'Active' WHERE id = ? AND TRIM(status) = 'Inactive'"
        : "UPDATE students SET status = 'Inactive' WHERE id = ? AND COALESCE(TRIM(status), '') <> 'Inactive'");
    $stmt->bind_param('i', $id);
    $stmt->execute();
    return $stmt->affected_rows === 1;
}

// ---------------------------------------------------------------- CSV export
// A cell starting with = + - @, tab or carriage return gets a leading apostrophe, so a spreadsheet shows it as text
// instead of running it as a formula.
function csv_safe_cell($value): string
{
    $text = (string) $value;
    return $text !== '' && strpbrk($text[0], "=+-@\t\r") !== false ? "'" . $text : $text;
}

// Sends the records as a CSV download: UTF-8 with a byte-order mark (Excel shows accents and "&" correctly), comma
// separated, CRLF line endings. Only record fields – no account data, password hashes or session information.
function send_students_csv(array $students): void
{
    header('Content-Type: text/csv; charset=utf-8');
    header('Content-Disposition: attachment; filename="studenthub_students_' . date('Ymd_His') . '.csv"');
    $out = fopen('php://output', 'w');
    fwrite($out, "\xEF\xBB\xBF");
    fputcsv($out, ['Record ID', 'Enrollment No', 'Name', 'Email', 'Course', 'Semester', 'Status', 'Login Account', 'Created At'],
            ',', '"', '', "\r\n");
    foreach ($students as $s) {
        fputcsv($out, array_map('csv_safe_cell', [
            $s['id'], $s['enrollment_no'] ?? '', $s['name'], $s['email'], $s['course'], $s['semester'] ?? '',
            student_is_active($s) ? 'Active' : 'Inactive', $s['user_id'] !== null ? 'Linked' : 'None', $s['created_at'] ?? '',
        ]), ',', '"', '', "\r\n");
    }
    fclose($out);
}
