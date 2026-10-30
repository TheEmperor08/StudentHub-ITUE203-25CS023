<?php
// Practical 8 leftover: direct inserts are disabled in the main portal.
// Students are added through the admin console (RBAC-protected, prepared statements).
http_response_code(410);
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Feature Unavailable – StudentHub</title>
    <link rel="stylesheet" href="assets/css/global.css?v=8">
</head>
<body>
    <main style="max-width: 640px; margin: 60px auto;">
        <section>
            <h2>Direct student insert is not available</h2>
            <p>No record was added. This demo script never wrote to the database.</p>
            <p>Administrators can add students from the <a href="admin_dashboard.php?tab=students">Admin Console</a>. The working PDO insert demo lives in <code>Practical-8/insert.php</code>.</p>
        </section>
    </main>
</body>
</html>
