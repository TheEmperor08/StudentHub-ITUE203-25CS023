<?php
// StudentHub – Practical 11: CSV export. Uses the same search/course/status filters as index.php and exports
// every matching record (all pages). Inactive (soft-deleted) students are included unless status=active is chosen;
// the Status and Deactivated at columns show which records are inactive.
//
// Excel compatibility: UTF-8 with a byte-order mark (so names like "Electronics & Communication" and any
// accented letters display correctly), comma separator, CRLF line endings, RFC 4180 quoting.
// Formula injection: a cell that starts with = + - @, tab or carriage return is prefixed with an apostrophe,
// so Excel shows it as text instead of running it as a formula.
declare(strict_types=1);
require_once __DIR__ . '/includes/functions.php';

function csv_safe(mixed $value): string
{
    $text = (string) $value;
    return $text !== '' && strpbrk($text[0], "=+-@\t\r") !== false ? "'" . $text : $text;
}

start_app();
$filters = list_filters($_GET);
$students = fetch_students(get_db(), $filters);           // read everything before sending any CSV output

header('Content-Type: text/csv; charset=utf-8');
header('Content-Disposition: attachment; filename="students_' . date('Ymd_His') . '.csv"');

$out = fopen('php://output', 'w');
fwrite($out, "\xEF\xBB\xBF");
fputcsv($out, ['Student ID', 'Full Name', 'Email', 'Course', 'Semester', 'Status', 'Created At', 'Updated At', 'Deactivated At'],
        ',', '"', '', "\r\n");
foreach ($students as $s) {
    fputcsv($out, array_map('csv_safe', [
        $s['student_id'], $s['full_name'], $s['email'], $s['course'], $s['semester'],
        STATUSES[$s['status']] ?? $s['status'], $s['created_at'], $s['updated_at'], $s['deleted_at'] ?? '',
    ]), ',', '"', '', "\r\n");
}
fclose($out);
