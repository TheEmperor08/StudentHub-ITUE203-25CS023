<?php
// StudentHub – admin dashboard (Practical 14 integrated): live statistics, latest registrations, account status
// management and the filtered audit log. All numbers are counted from the database on every page load.
// Requires mysqli in exception mode (the PHP 8.1+ default).

const AUDIT_STATUSES = ['SUCCESS', 'FAILED', 'SECURITY_BLOCK', 'INFO'];

// Counts for the overview cards (one query per table group)
function dashboard_stats(mysqli $db): array
{
    $one = fn (string $sql): array => $db->query($sql)->fetch_assoc();
    $students = $one("SELECT COUNT(*) AS total, COALESCE(SUM(TRIM(status) = 'Inactive'), 0) AS inactive, COALESCE(SUM(user_id IS NOT NULL), 0) AS linked FROM students");
    $events = $one("SELECT COUNT(*) AS total, COALESCE(SUM(event_date >= CURDATE()), 0) AS upcoming,
                           COALESCE(SUM(event_date >= CURDATE() AND status = 'open'), 0) AS open_upcoming FROM events");
    $registrations = $one("SELECT COUNT(*) AS total, COALESCE(SUM(status = 'registered'), 0) AS registered, COALESCE(SUM(status = 'attended'), 0) AS attended,
                                  COALESCE(SUM(status = 'cancelled'), 0) AS cancelled FROM registrations");
    $users = $one("SELECT COUNT(*) AS total, COALESCE(SUM(role = 'admin'), 0) AS admins, COALESCE(SUM(role = 'editor'), 0) AS editors,
                          COALESCE(SUM(role = 'student'), 0) AS students, COALESCE(SUM(status = 'disabled'), 0) AS disabled FROM users");
    $audit = $one("SELECT COUNT(*) AS total, COALESCE(SUM(status = 'SECURITY_BLOCK' AND created_at >= NOW() - INTERVAL 7 DAY), 0) AS blocked_week FROM audit_logs");
    $int = fn (array $row): array => array_map('intval', $row);
    return ['students' => $int($students) + ['active' => (int) $students['total'] - (int) $students['inactive']], 'events' => $int($events),
            'registrations' => $int($registrations), 'users' => $int($users), 'audit' => $int($audit)];
}

// The newest event registrations with student and event
function latest_registrations(mysqli $db, int $limit = 5): array
{
    $stmt = $db->prepare('SELECT r.registered_at, r.status, s.name, s.enrollment_no, e.title, e.event_date
                          FROM registrations r JOIN students s ON s.id = r.student_id JOIN events e ON e.id = r.event_id
                          ORDER BY r.registered_at DESC, r.registration_id DESC LIMIT ?');
    $stmt->bind_param('i', $limit);
    $stmt->execute();
    return $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
}

// The newest accounts (self-registrations and accounts created by an administrator)
function newest_accounts(mysqli $db, int $limit = 5): array
{
    $stmt = $db->prepare('SELECT username, role, status, created_at FROM users ORDER BY created_at DESC, id DESC LIMIT ?');
    $stmt->bind_param('i', $limit);
    $stmt->execute();
    return $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
}

// ---------------------------------------------------------------- account status (active / disabled)
function active_admin_count(mysqli $db): int
{
    return (int) $db->query("SELECT COUNT(*) FROM users WHERE role = 'admin' AND status = 'active'")->fetch_row()[0];
}

function find_account(mysqli $db, int $id): ?array
{
    $stmt = $db->prepare('SELECT id, username, role, status FROM users WHERE id = ?');
    $stmt->bind_param('i', $id);
    $stmt->execute();
    return $stmt->get_result()->fetch_assoc() ?: null;
}

// Disables or enables another account. Returns null on success or an error message. The own account and the last active
// administrator can never be disabled (the portal must always keep one administrator who can sign in).
function set_account_status(mysqli $db, int $id, string $status, int $current_user_id): ?string
{
    $account = find_account($db, $id);
    if ($account === null) {
        return 'That account was not found.';
    }
    if ($status === 'disabled') {
        if ($id === $current_user_id) {
            return 'You cannot disable your own account.';
        }
        if ($account['role'] === 'admin' && $account['status'] === 'active' && active_admin_count($db) <= 1) {
            return 'The last active administrator cannot be disabled.';
        }
    }
    if ($account['status'] === $status) {
        return "The account “{$account['username']}” is already $status.";
    }
    $stmt = $db->prepare('UPDATE users SET status = ? WHERE id = ?');
    $stmt->bind_param('si', $status, $id);
    $stmt->execute();
    return null;
}

// ---------------------------------------------------------------- audit log
function audit_actions(mysqli $db): array
{
    return array_column($db->query('SELECT DISTINCT action FROM audit_logs ORDER BY action')->fetch_all(MYSQLI_NUM), 0);
}

// Filters from the query string (own parameter names, so they never mix with the student or event filters)
function audit_filters(array $query, array $actions): array
{
    $text = fn (string $key): string => is_string($query[$key] ?? null) && mb_check_encoding($query[$key], 'UTF-8') ? trim($query[$key]) : '';
    $action = $text('audit_action');
    $status = $text('audit_status');
    return [
        'action' => in_array($action, $actions, true) ? $action : '',
        'status' => in_array($status, AUDIT_STATUSES, true) ? $status : '',
        'user'   => mb_substr($text('audit_user'), 0, 50),
    ];
}

// The newest matching entries (at most $limit)
function audit_list(mysqli $db, array $filters, int $limit = 100): array
{
    $where = [];
    $types = '';
    $params = [];
    foreach (['action' => 'action = ?', 'status' => 'status = ?'] as $key => $sql) {
        if ($filters[$key] !== '') {
            $where[] = $sql;
            $types .= 's';
            $params[] = $filters[$key];
        }
    }
    if ($filters['user'] !== '') {
        $where[] = 'username LIKE ?';
        $types .= 's';
        $params[] = '%' . addcslashes($filters['user'], '\\%_') . '%';
    }
    $stmt = $db->prepare('SELECT id, created_at, username, action, details, ip_address, status FROM audit_logs'
                         . ($where ? ' WHERE ' . implode(' AND ', $where) : '') . ' ORDER BY id DESC LIMIT ?');
    $types .= 'i';
    $params[] = $limit;
    $stmt->bind_param($types, ...$params);
    $stmt->execute();
    return $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
}
