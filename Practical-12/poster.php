<?php
// StudentHub – Practical 12: delivers a poster image to logged-in administrators. The upload folder itself is not
// reachable over HTTP, so this is the only way to see a poster. Only names of the form "<32 hex>.<jpg|png|webp>"
// inside the upload folder are accepted (no path traversal), and the file is always sent as an image – never run.
declare(strict_types=1);
require_once __DIR__ . '/includes/functions.php';

require_admin();
$name = is_string($_GET['file'] ?? null) ? $_GET['file'] : '';
$path = poster_path($name);
if ($path === null) {
    http_response_code(404);
    header('Content-Type: text/plain; charset=utf-8');
    echo "Poster not found.\n";
    exit;
}
$types = ['jpg' => 'image/jpeg', 'png' => 'image/png', 'webp' => 'image/webp'];
header('Content-Type: ' . $types[pathinfo($path, PATHINFO_EXTENSION)]);
header('Content-Length: ' . filesize($path));
header('Content-Disposition: inline; filename="poster.' . pathinfo($path, PATHINFO_EXTENSION) . '"');
header("Content-Security-Policy: default-src 'none'; sandbox");
header('Cache-Control: private, max-age=300');
readfile($path);
