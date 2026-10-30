<?php
// Practical 15: Universal System Audit Logger
function log_audit($conn, $user_id, $username, $action, $details = '', $status = 'SUCCESS') {
    if (!$conn) return;

    $ip_address = $_SERVER['REMOTE_ADDR'] ?? '127.0.0.1';
    $user_agent = substr($_SERVER['HTTP_USER_AGENT'] ?? 'Unknown', 0, 255);

    $stmt = $conn->prepare("INSERT INTO audit_logs (user_id, username, action, details, ip_address, user_agent, status) VALUES (?, ?, ?, ?, ?, ?, ?)");
    if ($stmt) {
        $stmt->bind_param("issssss", $user_id, $username, $action, $details, $ip_address, $user_agent, $status);
        try {
            $stmt->execute();
        } catch (mysqli_sql_exception $e) {
            // audit_logs.user_id references users.id (migration 001). If the account was deleted while its session was
            // still open, keep the entry with its username but without the link, instead of failing the whole page.
            if ($e->getCode() !== 1452 || $user_id === null) {
                throw $e;
            }
            $user_id = null;
            $stmt->execute();
        }
        $stmt->close();
    }
}
?>
