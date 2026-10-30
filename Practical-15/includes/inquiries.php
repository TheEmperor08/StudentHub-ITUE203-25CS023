<?php
// StudentHub – contact inquiries (Practical 7 integrated into the portal). The Help & Contact form (contact.php) is
// validated and sanitised on the server and every valid inquiry is stored in studenthub_db.inquiries (migration 005) with a
// prepared statement – Practical 7 kept them in a JSON file with file locking; the database gives the same protection
// against simultaneous writes. Administrators read and resolve them in the Admin Console (Inquiries tab).

const INQUIRY_TOPICS = ['General', 'Academics', 'Events', 'Portal access', 'Other'];
const INQUIRY_FIELDS = ['name', 'mail', 'id', 'topic', 'msg'];          // form field names (unchanged from the old form)

// Returns [clean values, errors by form field]
function validate_inquiry(array $input): array
{
    $errors = [];
    $raw = [];
    foreach (INQUIRY_FIELDS as $field) {
        $value = $input[$field] ?? '';
        if (!is_string($value) || !mb_check_encoding($value, 'UTF-8')) {
            $errors[$field] = 'This field contains characters that are not allowed.';
            $value = '';
        }
        $raw[$field] = trim($value);
    }
    $clean = [
        'name'          => (string) preg_replace('/\s+/u', ' ', $raw['name']),
        'email'         => strtolower($raw['mail']),
        'enrollment_no' => $raw['id'] === '' ? null : strtoupper($raw['id']),
        'topic'         => $raw['topic'] === '' ? 'General' : $raw['topic'],
        'message'       => str_replace("\r\n", "\n", $raw['msg']),
    ];
    if (!isset($errors['name'])) {
        if ($clean['name'] === '') {
            $errors['name'] = 'Please enter your name.';
        } elseif (mb_strlen($clean['name'], 'UTF-8') < 2 || mb_strlen($clean['name'], 'UTF-8') > 100) {
            $errors['name'] = 'The name must be 2–100 characters long.';
        } elseif (!preg_match("/^\\p{L}[\\p{L}\\p{M} .'-]*$/u", $clean['name'])) {
            $errors['name'] = 'Use letters, spaces, apostrophes, dots and hyphens only.';
        }
    }
    if (!isset($errors['mail'])) {
        if ($clean['email'] === '') {
            $errors['mail'] = 'Please enter your email address.';
        } elseif (strlen($clean['email']) > 100 || filter_var($clean['email'], FILTER_VALIDATE_EMAIL) === false) {
            $errors['mail'] = 'Please enter a valid email address, e.g. name@example.com.';
        }
    }
    if (!isset($errors['id']) && $clean['enrollment_no'] !== null && !preg_match('/^[0-9]{2}[A-Z]{2}[0-9]{3}$/', $clean['enrollment_no'])) {
        $errors['id'] = 'Use the enrollment number format 2 digits, 2 letters, 3 digits (e.g. 25CS023), or leave it empty.';
    }
    if (!isset($errors['topic']) && !in_array($clean['topic'], INQUIRY_TOPICS, true)) {
        $errors['topic'] = 'Please choose a topic from the list.';
    }
    if (!isset($errors['msg'])) {
        $length = mb_strlen($clean['message'], 'UTF-8');
        if ($length === 0) {
            $errors['msg'] = 'Please enter your message.';
        } elseif ($length < 10 || $length > 2000) {
            $errors['msg'] = 'The message must be 10–2000 characters long.';
        }
    }
    if (($input['website'] ?? '') !== '') {                 // honeypot: invisible to people, often filled in by bots
        $errors['msg'] = 'The inquiry could not be accepted.';
    }
    return [$clean, $errors];
}

function save_inquiry(mysqli $db, array $clean, ?int $user_id): int
{
    $stmt = $db->prepare('INSERT INTO inquiries (user_id, name, email, enrollment_no, topic, message) VALUES (?, ?, ?, ?, ?, ?)');
    $stmt->bind_param('isssss', $user_id, $clean['name'], $clean['email'], $clean['enrollment_no'], $clean['topic'], $clean['message']);
    $stmt->execute();
    return (int) $stmt->insert_id;
}

// Newest inquiries; $status '' = all, 'new' or 'resolved'
function list_inquiries(mysqli $db, string $status = '', int $limit = 100): array
{
    $sql = 'SELECT i.id, i.name, i.email, i.enrollment_no, i.topic, i.message, i.status, i.created_at, i.resolved_at, u.username
            FROM inquiries i LEFT JOIN users u ON u.id = i.user_id' . ($status !== '' ? ' WHERE i.status = ?' : '') . ' ORDER BY i.id DESC LIMIT ?';
    $stmt = $db->prepare($sql);
    if ($status !== '') {
        $stmt->bind_param('si', $status, $limit);
    } else {
        $stmt->bind_param('i', $limit);
    }
    $stmt->execute();
    return $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
}

function inquiry_counts(mysqli $db): array
{
    $row = $db->query("SELECT COUNT(*), COALESCE(SUM(status = 'new'), 0) FROM inquiries")->fetch_row();
    return ['total' => (int) $row[0], 'new' => (int) $row[1]];
}

// Marks an open inquiry as resolved; false if it does not exist or is already resolved
function resolve_inquiry(mysqli $db, int $id): bool
{
    $stmt = $db->prepare("UPDATE inquiries SET status = 'resolved', resolved_at = NOW() WHERE id = ? AND status = 'new'");
    $stmt->bind_param('i', $id);
    $stmt->execute();
    return $stmt->affected_rows === 1;
}
