<?php
// StudentHub – delivers an event poster to signed-in users (Practical 12). The upload folder is not reachable over HTTP
// on Apache (uploads/.htaccess), so posters are shown only through this page. It takes an event ID – never a file name –
// and serves the event's poster only if it is a stored poster ("<32 hex>.<jpg|png|webp>" inside the upload folder).
// The file is always sent as an image with nosniff and a sandboxing CSP, so it can never run as a script.
require_once "db.php";
require_once __DIR__ . "/includes/auth.php";
require_once __DIR__ . "/includes/event_management.php";

require_permission("portal.view");
$event = ($id = event_id_from($_GET["event"] ?? "")) > 0 ? find_event($conn, $id) : null;
$path  = $event !== null && $event["poster"] !== null ? poster_path((string) $event["poster"]) : null;
if ($path === null) {
    http_response_code(404);
    header("Content-Type: text/plain; charset=utf-8");
    echo "Poster not found.\n";
    exit;
}
$types = ["jpg" => "image/jpeg", "png" => "image/png", "webp" => "image/webp"];
$ext = pathinfo($path, PATHINFO_EXTENSION);
header("Content-Type: " . $types[$ext]);
header("Content-Length: " . filesize($path));
header('Content-Disposition: inline; filename="poster.' . $ext . '"');
header("Content-Security-Policy: default-src 'none'; sandbox");
header("Cache-Control: private, max-age=300");
readfile($path);
