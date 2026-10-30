<?php
// Router for PHP's built-in web server (start-server.bat). Apache ignores this file and uses .htaccess instead.
// It blocks configuration files, tests, documents, the SQL file and hidden files; everything else is served normally.
$path = rawurldecode((string) parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH));
$path = strtolower(str_replace(chr(92), "/", $path));      // chr(92) = backslash

if (preg_match('#(^|/)(tests|screenshots)(/|$)#', $path) || preg_match('#(^|/)\.#', $path)
    || preg_match('#\.(sql|md|docx|pdf|bat|txt|py)$#', $path)
    || in_array(basename($path), ['config.local.php', 'config.example.php', 'router.php'], true)) {
    http_response_code(403);
    header('Content-Type: text/plain; charset=utf-8');
    echo "403 Forbidden\n";
    return true;
}
if ($path === '/' || $path === '') {
    header('Location: /index.html', true, 302);
    return true;
}
return false;
