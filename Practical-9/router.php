<?php
// Router for PHP's built-in web server (start-server.bat). Apache ignores this file and uses .htaccess
// instead. It blocks the configuration files, includes, tests and hidden files, and lets the server handle
// every other request normally (db.php answers a direct request with 403 by itself).
$path = rawurldecode((string) parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH));
$path = strtolower(str_replace('\\', '/', $path));

if (preg_match('#(^|/)(tests|includes)(/|$)#', $path) || preg_match('#(^|/)\.#', $path)
    || in_array(basename($path), ['config.local.php', 'config.example.php', 'router.php', 'start-server.bat'], true)) {
    http_response_code(403);
    header('Content-Type: text/plain; charset=utf-8');
    echo "403 Forbidden\n";
    return true;
}
return false;
