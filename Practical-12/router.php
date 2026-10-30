<?php
// Router for PHP's built-in web server (start-server.bat). Apache ignores this file and uses the .htaccess files
// instead. It blocks the upload folder (posters are delivered only by poster.php, so nothing in it can ever be run),
// includes, tools, tests, configuration files, documents and hidden files, and lets the server handle every other
// request normally (db.php answers a direct request with 403 by itself).
$path = rawurldecode((string) parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH));
$path = strtolower(str_replace('\\', '/', $path));

if (preg_match('#(^|/)(uploads|includes|tools|tests|screenshots)(/|$)#', $path) || preg_match('#(^|/)\.#', $path)
    || preg_match('#\.(sql|md|docx|pdf|bat|txt|py)$#', $path)
    || in_array(basename($path), ['config.local.php', 'config.example.php', 'router.php'], true)) {
    http_response_code(403);
    header('Content-Type: text/plain; charset=utf-8');
    echo "403 Forbidden\n";
    return true;
}
if ($path === '/' || $path === '') {
    header('Location: /login.php', true, 302);
    return true;
}
return false;
