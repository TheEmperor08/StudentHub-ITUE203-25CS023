<?php
// StudentHub – Practical 12: removes abandoned poster files (command line only).
//   C:\xampp\php\php.exe tools\cleanup_orphan_posters.php            (list only)
//   C:\xampp\php\php.exe tools\cleanup_orphan_posters.php --delete   (delete them)
// A file counts as abandoned when it has a valid poster name, no event refers to it and it is older than one hour
// (for example after a crash between storing a poster and saving the event). Other files are never touched.
declare(strict_types=1);

if (PHP_SAPI !== 'cli') {
    http_response_code(403);
    exit;
}
require dirname(__DIR__) . '/db.php';
require dirname(__DIR__) . '/includes/upload.php';
ini_set('display_errors', '1');

$delete = in_array('--delete', $argv, true);
$min_age = 3600;
$stmt = get_db()->prepare('SELECT poster_filename FROM events');
$stmt->execute();
$used = array_flip(array_column($stmt->get_result()->fetch_all(MYSQLI_NUM), 0));

$found = $removed = 0;
foreach (scandir(upload_dir()) ?: [] as $name) {
    if (!preg_match(POSTER_NAME_PATTERN, $name) || isset($used[$name])) {
        continue;
    }
    $path = poster_path($name);
    if ($path === null || time() - filemtime($path) < $min_age) {
        continue;
    }
    $found++;
    if ($delete && @unlink($path)) {
        $removed++;
        echo "deleted   $name\n";
    } else {
        echo "abandoned $name\n";
    }
}
echo "$found abandoned poster file(s)" . ($delete ? ", $removed deleted" : ' (run with --delete to remove them)') . ".\n";
