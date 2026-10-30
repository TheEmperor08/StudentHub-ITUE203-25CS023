<?php
// StudentHub – Practical 10: session timeout. Protected pages send the browser here when the session has been
// inactive for longer than the configured limit (session_timeout in db.php, 300 seconds by default).
// The expired session is destroyed and the user is redirected to the login page with a timeout message.
declare(strict_types=1);

require __DIR__ . '/includes/auth.php';

start_secure_session();
send_security_headers();

// A session that is still active is not ended here (only logout.php does that)
if (current_user() !== null && !session_has_expired()) {
    redirect('dashboard.php');
}
end_session();
redirect('login.php?status=timeout');
