<?php
// Access check for the Student Management System (admins only).
// Accounts live in the user_registration database; sign in through Practical-10/login.php.
if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

if (!isset($_SESSION['user_id'])) {
    header("Location: ../Practical-10/login.php?error=" . urlencode("Please log in as an administrator to manage students."));
    exit();
}

if (($_SESSION['role'] ?? '') !== 'admin') {
    http_response_code(403);
    exit("403 Forbidden – only administrators can manage student records.");
}
