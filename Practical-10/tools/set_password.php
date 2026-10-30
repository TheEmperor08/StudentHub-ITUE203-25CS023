<?php
// StudentHub – Practical 10: sets the password of a demo account (command line only).
//   C:\xampp\php\php.exe tools\set_password.php admin.demo@example.com
// The password is typed when asked (or piped in) and stored only as a password_hash() hash. No password is
// kept in the repository, so every installation chooses its own demo passwords.
declare(strict_types=1);

if (PHP_SAPI !== 'cli') {
    http_response_code(403);
    exit;
}
require dirname(__DIR__) . '/db.php';
ini_set('display_errors', '1');

$email = $argv[1] ?? '';
if ($email === '') {
    fwrite(STDERR, "Usage: php tools/set_password.php <email>\n");
    exit(2);
}
fwrite(STDERR, "New password for $email (8-72 characters): ");
$password = rtrim((string) fgets(STDIN), "\r\n");
if (strlen($password) < 8 || strlen($password) > 72) {
    fwrite(STDERR, "\nThe password must be 8 to 72 characters long. Nothing was changed.\n");
    exit(1);
}

$hash = password_hash($password, PASSWORD_DEFAULT);
$stmt = get_db()->prepare('UPDATE users SET password_hash = ? WHERE email = ?');
$stmt->bind_param('ss', $hash, $email);
$stmt->execute();
if ($stmt->affected_rows !== 1) {
    fwrite(STDERR, "\nNo account with this email address. Nothing was changed.\n");
    exit(1);
}
fwrite(STDERR, "\nPassword updated for $email.\n");
