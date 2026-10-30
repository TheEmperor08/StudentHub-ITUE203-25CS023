<?php
// Optional local settings for db.php. Copy this file to config.local.php (git-ignored) and change only
// the values that differ from the defaults. Never commit config.local.php or a real password.
return [
    'host' => '127.0.0.1',
    'port' => 3306,
    'name' => 'studenthub_prac12',
    'user' => 'root',
    'pass' => '',
    // 'upload_dir' => 'C:\path\outside\htdocs\uploads',   // default: the uploads folder next to db.php
    'session_timeout' => 1800,                                 // seconds of inactivity before the session ends
];
