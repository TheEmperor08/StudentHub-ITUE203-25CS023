<?php
// StudentHub – Practical 12: edit an event (UPDATE). Without a new file the existing poster is kept. A replacement
// poster is validated and stored under a new random name BEFORE the update; the old file is deleted only after the
// UPDATE succeeded. If anything fails, the new file is removed and the old poster stays untouched.
declare(strict_types=1);
require_once __DIR__ . '/includes/functions.php';

require_admin();
$db = get_db();
$categories = categories($db);
$is_post = $_SERVER['REQUEST_METHOD'] === 'POST';
if ($is_post && post_too_large()) {
    $id = positive_id($_GET['id'] ?? '');
} else {
    $id = positive_id($is_post ? ($_POST['event_id'] ?? '') : ($_GET['id'] ?? ''));
}
$stored = $id > 0 ? find_event($db, $id) : null;
if ($stored === null) {
    flash('error', 'That event was not found.');
    redirect('index.php');
}
$event = $stored;
$errors = [];
$notice = '';

if ($is_post) {
    if (post_too_large()) {
        $errors['poster'] = 'The upload was too large for the server. The maximum poster size is 2 MB.';
    } elseif (!csrf_is_valid($_POST['csrf_token'] ?? null)) {
        flash('error', 'The form could not be processed (security token missing or expired). Please try again.');
        redirect('index.php');
    } else {
        [$event, $errors] = validate_event($_POST, $categories);
        $event['event_id'] = $id;
        $poster = validate_poster($_FILES['poster'] ?? null);
        $replace = $poster['ok'];
        if (!$poster['ok'] && empty($poster['none'])) {
            $errors['poster'] = $poster['error'];               // a file was chosen but rejected: nothing is changed
        } elseif ($replace && $errors) {
            $notice = 'The new poster was valid, but it must be chosen again because other fields need correcting.';
        }
        if (!$errors) {
            $new_name = $replace ? store_poster($poster) : null;
            if ($replace && $new_name === null) {
                $errors['poster'] = 'The new poster could not be saved on the server. The current poster was kept.';
            } else {
                $poster_name = $new_name ?? $stored['poster_filename'];
                try {
                    $stmt = $db->prepare('UPDATE events SET event_title = ?, description = ?, category = ?, event_date = ?, event_time = ?,
                                          venue = ?, poster_filename = ?, status = ? WHERE event_id = ?');
                    $stmt->bind_param('ssssssssi', $event['event_title'], $event['description'], $event['category'], $event['event_date'],
                                      $event['event_time'], $event['venue'], $poster_name, $event['status'], $id);
                    $stmt->execute();
                } catch (Throwable $exception) {
                    discard_new_poster($new_name);
                    throw $exception;
                }
                if ($new_name !== null) {
                    delete_poster_file($db, $stored['poster_filename']);   // the old file is no longer used by any event
                }
                flash('success', 'Event “' . $event['event_title'] . '” was updated successfully'
                    . ($new_name !== null ? ' and its poster was replaced.' : '; the existing poster was kept.'), $id);
                redirect('index.php');
            }
        }
    }
    http_response_code(422);
}

page_start('Edit event');
if ($errors) {
    echo '<div class="alert alert-danger" role="alert"><strong>The changes were not saved.</strong> ', e($errors['poster'] ?? 'Please correct the highlighted fields.'),
         isset($errors['poster']) ? ' The current poster was kept.' : '', '</div>', "\n";
}
if ($notice !== '') {
    echo '<div class="alert alert-warning">', e($notice), '</div>', "\n";
}
echo '<p class="text-secondary">Editing event <strong>#', $id, '</strong> · created ', e(date('d M Y, H:i', strtotime($stored['created_at']))),
     ' · last updated ', e(date('d M Y, H:i', strtotime($stored['updated_at']))), '</p>', "\n";
event_form('edit.php?id=' . $id, 'Save changes', $event, $errors, $categories, $stored['poster_filename']);
page_end();
