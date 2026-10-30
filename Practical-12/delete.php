<?php
// StudentHub – Practical 12: delete an event. GET delete.php?id=N only shows a confirmation page; the event is deleted
// after the administrator confirms with a POST (CSRF token required). The poster file is removed only after the
// row was deleted, and only through delete_poster_file(), which accepts nothing but a valid stored poster name.
declare(strict_types=1);
require_once __DIR__ . '/includes/functions.php';

require_admin();
$db = get_db();

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!csrf_is_valid($_POST['csrf_token'] ?? null)) {
        flash('error', 'The event was not deleted: the security token was missing or expired. Please try again.');
        redirect('index.php');
    }
    $id = positive_id($_POST['event_id'] ?? '');
    $event = $id > 0 ? find_event($db, $id) : null;
    if ($event === null) {
        flash('error', 'That event was not found, so nothing was deleted.');
        redirect('index.php');
    }
    $stmt = $db->prepare('DELETE FROM events WHERE event_id = ?');
    $stmt->bind_param('i', $id);
    $stmt->execute();
    if ($stmt->affected_rows !== 1) {
        flash('error', 'The event could not be deleted. Please try again.');
        redirect('index.php');
    }
    $file_removed = delete_poster_file($db, $event['poster_filename']);
    flash('success', 'Event “' . $event['event_title'] . '” was deleted' . ($file_removed ? ' together with its poster file.' : '. Its poster file was already missing.'));
    redirect('index.php');
}

$id = positive_id($_GET['id'] ?? '');
$event = $id > 0 ? find_event($db, $id) : null;
if ($event === null) {
    flash('error', 'That event was not found.');
    redirect('index.php');
}
page_start('Delete event');
?>
<div class="card border-danger shadow-sm confirm-card">
  <div class="card-body p-4">
    <div class="row g-4">
      <div class="col-sm-4"><img class="img-fluid rounded border" src="<?= e(poster_url($event['poster_filename'])) ?>" alt="Poster: <?= e($event['event_title']) ?>"></div>
      <div class="col-sm-8">
        <div class="alert alert-danger" role="alert"><strong>Are you sure you want to delete “<?= e($event['event_title']) ?>”?</strong><br>The event record and its poster file will be removed permanently. This cannot be undone.</div>
        <dl class="row mb-3">
          <dt class="col-4">Event ID</dt><dd class="col-8"><?= $id ?></dd>
          <dt class="col-4">Category</dt><dd class="col-8"><?= e($event['category']) ?></dd>
          <dt class="col-4">Date &amp; time</dt><dd class="col-8"><?= e(format_date($event['event_date'])) ?>, <?= e(format_time($event['event_time'])) ?></dd>
          <dt class="col-4">Venue</dt><dd class="col-8"><?= e($event['venue']) ?></dd>
          <dt class="col-4">Status</dt><dd class="col-8"><?= status_badge($event['status']) ?></dd>
        </dl>
        <form method="post" action="delete.php" class="d-flex gap-2">
          <?= csrf_field() ?>
          <input type="hidden" name="event_id" value="<?= $id ?>">
          <button type="submit" class="btn btn-danger">Yes, delete event</button>
          <a class="btn btn-outline-secondary" href="index.php">Cancel</a>
        </form>
      </div>
    </div>
  </div>
</div>
<?php page_end(); ?>
