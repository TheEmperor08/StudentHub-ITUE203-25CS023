<?php
// StudentHub – Practical 12: event list (READ) with poster thumbnails, category and Open/Closed status filters.
// Administrators only. GET requests only; every change is a POST on add.php, edit.php or delete.php.
declare(strict_types=1);
require_once __DIR__ . '/includes/functions.php';

require_admin();
$db = get_db();
$categories = categories($db);
$category = is_string($_GET['category'] ?? null) && in_array($_GET['category'], $categories, true) ? $_GET['category'] : '';
$status = is_string($_GET['status'] ?? null) && isset(STATUSES[$_GET['status']]) ? $_GET['status'] : '';

// WHERE clause from fixed pieces with ? placeholders; the values were checked against the allowed lists above
$where = [];
$types = '';
$params = [];
if ($category !== '') {
    $where[] = 'category = ?';
    $types .= 's';
    $params[] = $category;
}
if ($status !== '') {
    $where[] = 'status = ?';
    $types .= 's';
    $params[] = $status;
}
$stmt = $db->prepare('SELECT event_id, event_title, category, event_date, event_time, venue, poster_filename, status FROM events'
    . ($where ? ' WHERE ' . implode(' AND ', $where) : '') . ' ORDER BY event_date, event_time, event_id');
if ($types !== '') {
    $stmt->bind_param($types, ...$params);
}
$stmt->execute();
$events = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);

$count = $db->prepare("SELECT COUNT(*), COALESCE(SUM(status = 'open'), 0) FROM events");
$count->execute();
[$total, $open] = array_map('intval', $count->get_result()->fetch_row());

$flash = take_flash();
$highlight = (int) ($flash['event_id'] ?? 0);
page_start('Event management', 'index.php');
render_flash($flash);
?>
<div class="row g-3 mb-3">
  <div class="col-sm-4"><div class="card stat-card shadow-sm"><div class="card-body"><div class="text-secondary small">All events</div><div class="fs-4 fw-semibold"><?= $total ?></div></div></div></div>
  <div class="col-sm-4"><div class="card stat-card shadow-sm"><div class="card-body"><div class="text-secondary small">Open</div><div class="fs-4 fw-semibold text-success"><?= $open ?></div></div></div></div>
  <div class="col-sm-4"><div class="card stat-card shadow-sm"><div class="card-body"><div class="text-secondary small">Closed</div><div class="fs-4 fw-semibold text-secondary"><?= $total - $open ?></div></div></div></div>
</div>

<form class="card shadow-sm mb-3" method="get" action="index.php" aria-label="Filter events">
  <div class="card-body row g-2 align-items-end">
    <div class="col-sm-5 col-md-4">
      <label class="form-label fw-semibold" for="category">Category</label>
      <select class="form-select" id="category" name="category">
        <option value="">All categories</option>
<?php foreach ($categories as $c): ?>
        <option value="<?= e($c) ?>"<?= $c === $category ? ' selected' : '' ?>><?= e($c) ?></option>
<?php endforeach; ?>
      </select>
    </div>
    <div class="col-sm-4 col-md-3">
      <label class="form-label fw-semibold" for="status">Status</label>
      <select class="form-select" id="status" name="status">
        <option value="">Open and closed</option>
<?php foreach (STATUSES as $key => $label): ?>
        <option value="<?= $key ?>"<?= $key === $status ? ' selected' : '' ?>><?= $label ?></option>
<?php endforeach; ?>
      </select>
    </div>
    <div class="col-sm-3 col-md-5 d-flex gap-2">
      <button type="submit" class="btn btn-primary">Filter</button>
      <a class="btn btn-outline-secondary" href="index.php">Reset</a>
      <a class="btn btn-success ms-auto" href="add.php">+ Add event</a>
    </div>
  </div>
</form>

<p class="text-secondary mb-2" id="result-summary">
  Showing <strong><?= count($events) ?></strong> of <?= $total ?> event<?= $total === 1 ? '' : 's' ?><?php
  if ($category !== ''): ?> in category <strong><?= e($category) ?></strong><?php endif;
  if ($status !== ''): ?> with status <strong><?= e(STATUSES[$status]) ?></strong><?php endif; ?>.
</p>

<div class="card shadow-sm">
  <div class="table-responsive">
    <table class="table table-hover align-middle mb-0 event-table">
      <thead class="table-light">
        <tr>
          <th scope="col">Poster</th>
          <th scope="col">Event</th>
          <th scope="col">Category</th>
          <th scope="col">Date &amp; time</th>
          <th scope="col">Venue</th>
          <th scope="col">Status</th>
          <th scope="col" class="text-end">Actions</th>
        </tr>
      </thead>
      <tbody>
<?php if (!$events): ?>
        <tr><td colspan="7" class="text-center text-secondary py-4">No events match the selected filters. <a href="index.php">Show all events</a></td></tr>
<?php endif; ?>
<?php foreach ($events as $event): $id = (int) $event['event_id']; ?>
        <tr class="<?= $id === $highlight ? 'table-warning' : '' ?>" data-event-id="<?= $id ?>">
          <td><a href="view.php?id=<?= $id ?>"><img class="poster-thumb" src="<?= e(poster_url($event['poster_filename'])) ?>" alt="Poster: <?= e($event['event_title']) ?>"></a></td>
          <td class="fw-semibold"><a class="link-body-emphasis text-decoration-none" href="view.php?id=<?= $id ?>"><?= e($event['event_title']) ?></a></td>
          <td><span class="badge text-bg-light border"><?= e($event['category']) ?></span></td>
          <td class="text-nowrap"><?= e(format_date($event['event_date'])) ?><br><span class="text-secondary small"><?= e(format_time($event['event_time'])) ?></span></td>
          <td><?= e($event['venue']) ?></td>
          <td><?= status_badge($event['status']) ?></td>
          <td class="text-end text-nowrap">
            <a class="btn btn-sm btn-outline-primary" href="view.php?id=<?= $id ?>">View</a>
            <a class="btn btn-sm btn-outline-secondary" href="edit.php?id=<?= $id ?>">Edit</a>
            <a class="btn btn-sm btn-outline-danger" href="delete.php?id=<?= $id ?>">Delete</a>
          </td>
        </tr>
<?php endforeach; ?>
      </tbody>
    </table>
  </div>
</div>
<?php page_end(); ?>
