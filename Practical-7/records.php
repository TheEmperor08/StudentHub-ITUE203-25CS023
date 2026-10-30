<?php
// StudentHub – Practical 7: shows the records stored in the JSON file (intermediate extension).
// Every value is escaped with e(), so submitted text is displayed as text and never runs as HTML.
declare(strict_types=1);

require __DIR__ . '/includes/functions.php';
require __DIR__ . '/includes/storage.php';

date_default_timezone_set('Asia/Kolkata');
$result = read_submissions();
$records = $result['records'];
$newestFirst = array_reverse($records);

// Values from the file are only used if they are plain text or numbers (a hand-edited file cannot break the page)
$text = fn(mixed $value): string => is_scalar($value) ? (string) $value : '';
$formatTime = function (mixed $iso): string {
    $time = is_string($iso) ? strtotime($iso) : false;
    return $time ? date('d M Y, H:i', $time) : '';
};
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stored Submissions - StudentHub</title>
    <link rel="stylesheet" href="assets/css/style.css">
</head>
<body>
    <header class="site-header">
        <div class="container">
            <p class="brand">StudentHub</p>
            <h1>Stored Submissions</h1>
            <p class="subtitle">Records read by PHP from the JSON storage file (private/submissions.json by default).</p>
        </div>
    </header>

    <main class="container" id="main-content">
        <nav class="page-nav" aria-label="Practical 7 pages">
            <a href="index.php">Inquiry form</a>
            <a href="records.php" aria-current="page">Stored submissions (JSON)</a>
        </nav>

        <p class="notice">Local demonstration page. A real website would show these records only to logged-in staff; the JSON file itself is never served to browsers.</p>

<?php if ($result['error'] !== null): ?>
        <div class="alert alert-error" role="alert">
            <h2>Stored data could not be read</h2>
            <p><?= e($result['error']) ?></p>
        </div>
<?php elseif (!$records): ?>
        <div class="alert alert-info" role="status">
            <h2>No submissions yet</h2>
            <p>The JSON file does not exist yet or is empty. It is created by the first valid submission.</p>
        </div>
<?php else: ?>
        <section class="card" aria-labelledby="table-title">
            <h2 id="table-title"><?= count($records) ?> stored <?= count($records) === 1 ? 'submission' : 'submissions' ?> (newest first)</h2>
            <div class="table-wrap">
                <table class="records">
                    <thead>
                        <tr><th scope="col">ID</th><th scope="col">Submitted</th><th scope="col">Name</th><th scope="col">Email</th><th scope="col">Category</th><th scope="col">Message</th></tr>
                    </thead>
                    <tbody>
<?php foreach ($newestFirst as $record): ?>
                        <tr>
                            <td data-label="ID"><?= e($text($record['id'] ?? '')) ?></td>
                            <td data-label="Submitted"><?= e($formatTime($record['submitted_at'] ?? null)) ?></td>
                            <td data-label="Name"><?= e($text($record['name'] ?? '')) ?></td>
                            <td data-label="Email"><?= e($text($record['email'] ?? '')) ?></td>
                            <td data-label="Category"><?= e(CATEGORIES[$text($record['category'] ?? '')] ?? $text($record['category'] ?? '')) ?></td>
                            <td data-label="Message" class="message"><?= nl2br(e($text($record['message'] ?? ''))) ?></td>
                        </tr>
<?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        </section>

        <section class="card" aria-labelledby="json-title">
            <h2 id="json-title">Contents of the JSON storage file</h2>
            <pre class="json-view" tabindex="0"><code><?= e(records_as_json($records)) ?></code></pre>
        </section>
<?php endif; ?>
    </main>

    <footer class="site-footer">
        <div class="container">
            <p>&copy; <time datetime="2026">2026</time> StudentHub – ITUE203 Practical 7 by Shreyas (25CS023).</p>
        </div>
    </footer>
</body>
</html>
