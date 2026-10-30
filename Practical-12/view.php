<?php
// StudentHub – Practical 12: event details with the full-size poster (administrators only).
declare(strict_types=1);
require_once __DIR__ . '/includes/functions.php';

require_admin();
$id = positive_id($_GET['id'] ?? '');
$event = $id > 0 ? find_event(get_db(), $id) : null;
if ($event === null) {
    flash('error', 'That event was not found.');
    redirect('index.php');
}
$flash = take_flash();
page_start($event['event_title']);
render_flash($flash);
?>
<div class="card shadow-sm">
  <div class="card-body p-4">
    <div class="row g-4">
      <div class="col-md-5">
        <img class="img-fluid rounded border poster-full" src="<?= e(poster_url($event['poster_filename'])) ?>" alt="Poster: <?= e($event['event_title']) ?>">
      </div>
      <div class="col-md-7">
        <p class="mb-3"><?= status_badge($event['status']) ?> <span class="badge text-bg-light border"><?= e($event['category']) ?></span></p>
        <dl class="row">
          <dt class="col-sm-4">Date</dt><dd class="col-sm-8"><?= e(format_date($event['event_date'])) ?></dd>
          <dt class="col-sm-4">Time</dt><dd class="col-sm-8"><?= e(format_time($event['event_time'])) ?></dd>
          <dt class="col-sm-4">Venue</dt><dd class="col-sm-8"><?= e($event['venue']) ?></dd>
          <dt class="col-sm-4">Poster file</dt><dd class="col-sm-8"><code><?= e($event['poster_filename']) ?></code></dd>
          <dt class="col-sm-4">Last updated</dt><dd class="col-sm-8"><?= e(date('d M Y, H:i', strtotime($event['updated_at']))) ?></dd>
        </dl>
        <h2 class="h6 fw-semibold">Description</h2>
        <p class="description"><?= nl2br(e($event['description'])) ?></p>
        <div class="d-flex gap-2 mt-4">
          <a class="btn btn-outline-secondary" href="edit.php?id=<?= $id ?>">Edit</a>
          <a class="btn btn-outline-danger" href="delete.php?id=<?= $id ?>">Delete</a>
          <a class="btn btn-link" href="index.php">Back to all events</a>
        </div>
      </div>
    </div>
  </div>
</div>
<?php page_end(); ?>
