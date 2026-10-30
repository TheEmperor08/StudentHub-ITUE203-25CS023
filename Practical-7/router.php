<?php
// Router for PHP's built-in web server (start-server.bat). Apache ignores this file and uses the
// .htaccess files in private/ and includes/ instead. It blocks the stored submissions, the PHP include
// files and hidden files, and lets the server handle every other request normally.
$path = rawurldecode((string) parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH));
$path = strtolower(str_replace('\\', '/', $path));

if (preg_match('#(^|/)(private|includes|tests)(/|$)#', $path) || preg_match('#(^|/)\.#', $path)
    || in_array(basename($path), ['router.php', 'start-server.bat'], true)) {
    http_response_code(403);
    header('Content-Type: text/plain; charset=utf-8');
    echo "403 Forbidden\n";
    return true;
}
return false;
