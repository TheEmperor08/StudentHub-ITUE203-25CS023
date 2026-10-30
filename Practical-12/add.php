<?php
// StudentHub – Practical 12: add an event (CREATE). The fields and the poster are validated first; only then is the
// poster stored under a random name and the event inserted with a prepared statement. If the INSERT fails, the
// stored poster is removed again, so no abandoned file is left behind.
declare(strict_types=1);
require_once __DIR__ . '/includes/functions.php';

require_admin();
$db = get_db();
$categories = categories($db);
$event = ['status' => 'open'];
$errors = [];
$notice = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (post_too_large()) {
        $errors['poster'] = 'The upload was too large for the server. The maximum poster size is 2 MB.';
    } elseif (!csrf_is_valid($_POST['csrf_token'] ?? null)) {
        flash('error', 'The form could not be processed (security token missing or expired). Please try again.');
        redirect('index.php');
    } else {
        [$event, $errors] = validate_event($_POST, $categories);
        $poster = validate_poster($_FILES['poster'] ?? null);
        if (!$poster['ok']) {
            $errors['poster'] = $poster['error'];
        } elseif ($errors) {
            $notice = 'The poster was valid, but it must be chosen again because other fields need correcting.';
        }
        if (!$errors) {
            $name = store_poster($poster);
            if ($name === null) {
                $errors['poster'] = 'The poster could not be saved on the server. Please try again.';
            } else {
                try {
                    $stmt = $db->prepare('INSERT INTO events (event_title, description, category, event_date, event_time, venue, poster_filename, status)
                                          VALUES (?, ?, ?, ?, ?, ?, ?, ?)');
                    $stmt->bind_param('ssssssss', $event['event_title'], $event['description'], $event['category'], $event['event_date'],
                                      $event['event_time'], $event['venue'], $name, $event['status']);
                    $stmt->execute();
                    flash('success', 'Event “' . $event['event_title'] . '” was added successfully with its poster.', $stmt->insert_id);
                    redirect('index.php');
                } catch (Throwable $exception) {
                    discard_new_poster($name);
                    throw $exception;
                }
            }
        }
    }
    http_response_code(422);
}

page_start('Add event', 'add.php');
if ($errors) {
    echo '<div class="alert alert-danger" role="alert"><strong>The event was not added.</strong> ', e($errors['poster'] ?? 'Please correct the highlighted fields.'), '</div>', "\n";
}
if ($notice !== '') {
    echo '<div class="alert alert-warning">', e($notice), '</div>', "\n";
}
event_form('add.php', 'Add event', $event, $errors, $categories);
page_end();
