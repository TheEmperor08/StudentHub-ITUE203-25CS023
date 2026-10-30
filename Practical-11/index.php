<?php
// StudentHub – Practical 11: student list (READ) with search, course filter, status filter, pagination,
// success/error messages and the CSV export link. Only GET requests; every change is a POST on another page.
declare(strict_types=1);
require_once __DIR__ . '/includes/functions.php';

start_app();
$db = get_db();
$filters = list_filters($_GET);
$total = count_students($db, $filters);
$pages = max(1, (int) ceil($total / PER_PAGE));
$page = min(max(1, positive_id($_GET['page'] ?? '1')), $pages);   // out-of-range page numbers are clamped
$students = fetch_students($db, $filters, PER_PAGE, ($page - 1) * PER_PAGE);
$flash = take_flash();
$highlight = (int) ($flash['student_id'] ?? 0);
$filtered = $filters['q'] !== '' || $filters['course'] !== '' || $filters['status'] !== '';

page_start('Student Management', 'index.php');
render_flash($flash);
?>
<section class="card" aria-labelledby="search-title">
    <h2 id="search-title">Search and filter</h2>
    <form class="filter-form" method="get" action="index.php" role="search">
        <div class="form-field grow">
            <label for="q">Search name, email or course</label>
            <input type="search" id="q" name="q" maxlength="100" value="<?= e($filters['q']) ?>" placeholder="e.g. Patel, diya.shah@example.com, Data">
        </div>
        <div class="form-field">
            <label for="course">Course</label>
            <select id="course" name="course"><?= course_options($filters['course'], 'All courses') ?></select>
        </div>
        <div class="form-field">
            <label for="status">Status</label>
            <select id="status" name="status">
                <option value="">All statuses</option>
<?php foreach (STATUSES as $value => $label): ?>
                <option value="<?= e($value) ?>"<?= $filters['status'] === $value ? ' selected' : '' ?>><?= e($label) ?></option>
<?php endforeach; ?>
            </select>
        </div>
        <div class="filter-actions">
            <button type="submit" class="btn btn-primary">Search</button>
            <a class="btn btn-secondary" href="index.php">Reset</a>
        </div>
    </form>
</section>

<section aria-labelledby="list-title">
    <div class="list-header">
        <div>
            <h2 id="list-title">Student records</h2>
            <p class="muted" id="result-summary">
<?php if ($total === 0): ?>
                No students found<?= $filtered ? ' for the selected search and filter' : '' ?>.
<?php else: ?>
                Showing <?= ($page - 1) * PER_PAGE + 1 ?>–<?= ($page - 1) * PER_PAGE + count($students) ?> of <?= $total ?> student<?= $total === 1 ? '' : 's' ?><?php
                if ($filters['q'] !== ''): ?> matching “<strong><?= e($filters['q']) ?></strong>”<?php endif;
                if ($filters['course'] !== ''): ?> in <strong><?= e($filters['course']) ?></strong><?php endif;
                if ($filters['status'] !== ''): ?> with status <strong><?= e(STATUSES[$filters['status']]) ?></strong><?php endif; ?>.
<?php endif; ?>
            </p>
        </div>
        <div class="list-actions">
            <a class="btn btn-primary" href="add.php">+ Add student</a>
            <a class="btn btn-export" href="<?= e(list_url('export.php', $filters)) ?>" download>Export CSV</a>
        </div>
    </div>

    <div class="table-wrap">
        <table class="student-table">
            <thead>
                <tr>
                    <th scope="col">ID</th>
                    <th scope="col">Full name</th>
                    <th scope="col">Email</th>
                    <th scope="col">Course</th>
                    <th scope="col">Sem.</th>
                    <th scope="col">Status</th>
                    <th scope="col">Last updated</th>
                    <th scope="col">Actions</th>
                </tr>
            </thead>
            <tbody>
<?php if (!$students): ?>
                <tr><td colspan="8" class="empty">No student records match. <a href="index.php">Show all students</a></td></tr>
<?php endif; ?>
<?php foreach ($students as $student): ?>
<?php $id = (int) $student['student_id']; ?>
                <tr class="<?= $student['status'] === 'inactive' ? 'row-inactive' : '' ?><?= $id === $highlight ? ' row-highlight' : '' ?>">
                    <td data-label="ID"><?= $id ?></td>
                    <td data-label="Full name"><?= e($student['full_name']) ?></td>
                    <td data-label="Email"><?= e($student['email']) ?></td>
                    <td data-label="Course"><?= e($student['course']) ?></td>
                    <td data-label="Semester"><?= (int) $student['semester'] ?></td>
                    <td data-label="Status"><?= status_badge($student['status']) ?></td>
                    <td data-label="Last updated"><time datetime="<?= e(str_replace(' ', 'T', $student['updated_at'])) ?>"><?= e(date('d M Y, H:i', strtotime($student['updated_at']))) ?></time></td>
                    <td data-label="Actions" class="actions">
                        <a class="btn btn-small btn-secondary" href="edit.php?id=<?= $id ?>">Edit</a>
<?php if ($student['status'] === 'active'): ?>
                        <a class="btn btn-small btn-danger" href="delete.php?id=<?= $id ?>">Deactivate</a>
<?php else: ?>
                        <span class="muted small">Soft deleted</span>
<?php endif; ?>
                    </td>
                </tr>
<?php endforeach; ?>
            </tbody>
        </table>
    </div>

<?php if ($pages > 1): ?>
    <nav class="pagination" aria-label="Pages">
<?php if ($page > 1): ?>
        <a href="<?= e(list_url('index.php', $filters, $page - 1)) ?>" rel="prev">‹ Previous</a>
<?php endif; ?>
<?php for ($p = 1; $p <= $pages; $p++): ?>
<?php if ($p === $page): ?>
        <span aria-current="page"><?= $p ?></span>
<?php else: ?>
        <a href="<?= e(list_url('index.php', $filters, $p)) ?>"><?= $p ?></a>
<?php endif; ?>
<?php endfor; ?>
<?php if ($page < $pages): ?>
        <a href="<?= e(list_url('index.php', $filters, $page + 1)) ?>" rel="next">Next ›</a>
<?php endif; ?>
    </nav>
<?php endif; ?>
    <p class="muted small">“Deactivate” is a soft delete: the record stays in MySQL with status <strong>Inactive</strong>. The CSV export contains every record that matches the current search and filters (all pages, active and inactive unless a status is selected).</p>
</section>
<?php page_end(); ?>
