<?php
require_once __DIR__ . "/student_profile.php";

$current_page = basename($_SERVER['PHP_SELF']);
$nav_profile = (isset($conn) && isset($_SESSION['user_id'])) ? get_student_profile($conn) : null;

// Grouped navigation: [file, icon, label, pages that mark it active]
$nav_groups = [
    "Overview" => [
        ["dashboard.php",     "bi-grid-1x2",         "Dashboard",     ["dashboard.php", "student_dashboard.php"]],
        ["profile.php",       "bi-person-circle",    "My Profile",    ["profile.php"]],
    ],
    "Academics" => [
        ["courses.php",       "bi-journal-bookmark", "Courses",       ["courses.php"]],
        ["attendance.php",    "bi-calendar-check",   "Attendance",    ["attendance.php"]],
        ["assignments.php",   "bi-pencil-square",    "Assignments",   ["assignments.php"]],
        ["results.php",       "bi-bar-chart-line",   "Results",       ["results.php"]],
        ["achievements.php",  "bi-award",            "Achievements",  ["achievements.php"]],
    ],
    "Campus" => [
        ["notifications.php", "bi-megaphone",        "Notices",       ["notifications.php"]],
        ["events_live.php",   "bi-lightning-charge", "Event Finder",  ["events_live.php"]],
        ["directory.php",     "bi-people",           "Directory",     ["directory.php"]],
        ["contact.php",       "bi-life-preserver",   "Help & Contact", ["contact.php"]],
    ],
    "Account" => [
        ["index.php",         "bi-house",            "Home Portal",   ["index.php"]],
    ],
];

// Role-based links from menu_items (Practical 14) that the groups above do not contain yet – e.g. the Admin Console tabs
// for an administrator. A user only gets the rows up to their own role; the pages still check the permission themselves.
require_once __DIR__ . "/includes/navigation.php";
$nav_role = in_array($_SESSION['role'] ?? '', ['admin', 'editor', 'student'], true) ? $_SESSION['role'] : null;
if ($nav_role !== null && isset($conn)) {
    $present = array_merge(...array_map(fn ($links) => array_column($links, 0), array_values($nav_groups)));
    $shortcuts = [];
    foreach (menu_for_role($conn, $nav_role) as $item) {
        if (!in_array($item['link'], $present, true)) {
            $shortcuts[] = [$item['link'], $item['icon'], $item['title'], [$item['link']]];
        }
    }
    if ($shortcuts) {
        $nav_groups = array_slice($nav_groups, 0, 3, true) + ["Shortcuts" => $shortcuts] + array_slice($nav_groups, 3, null, true);
    }
}
?>
<a class="skip-link" href="#main-content">Skip to main content</a>

<div class="mobile-topbar">
    <button type="button" class="nav-toggle" aria-controls="app-nav" aria-expanded="false" aria-label="Open navigation menu">
        <i class="bi bi-list" aria-hidden="true"></i>
    </button>
    <a class="mobile-brand" href="dashboard.php">
        <span class="brand-mark" aria-hidden="true"><i class="bi bi-mortarboard-fill"></i></span>
        <span>StudentHub</span>
    </a>
    <button type="button" class="theme-toggle-nav theme-toggle-icon" onclick="window.toggleTheme()" aria-pressed="false" aria-label="Switch to dark mode">
        <i class="bi bi-moon-stars" aria-hidden="true"></i>
    </button>
</div>
<div class="nav-backdrop" hidden></div>

<nav id="app-nav" aria-label="Main navigation">
    <div class="sidebar-brand">
        <span class="brand-mark" aria-hidden="true"><i class="bi bi-mortarboard-fill"></i></span>
        <div>
            <strong>StudentHub</strong>
            <small>CSPIT · CHARUSAT</small>
        </div>
    </div>

    <?php if ($nav_profile): ?>
        <div class="nav-user">
            <span class="nav-avatar" aria-hidden="true"><?= htmlspecialchars(mb_strtoupper(mb_substr($nav_profile["name"], 0, 1))) ?></span>
            <div>
                <strong><?= htmlspecialchars($nav_profile["name"]) ?></strong>
                <small><?= htmlspecialchars($nav_profile["enrollment_no"]) ?></small>
            </div>
        </div>
    <?php endif; ?>

    <?php foreach ($nav_groups as $group => $links): ?>
        <p class="nav-group-label"><?= $group ?></p>
        <ul>
            <?php foreach ($links as [$href, $icon, $label, $active_pages]): ?>
                <?php $is_active = in_array($current_page, $active_pages, true); ?>
                <li><a href="<?= e($href) ?>"<?= $is_active ? ' class="active" aria-current="page"' : '' ?>><i class="bi <?= e($icon) ?>" aria-hidden="true"></i><span><?= e($label) ?></span></a></li>
            <?php endforeach; ?>
            <?php if ($group === "Account"): ?>
                <?php if (isset($_SESSION["user_id"])): ?>
                    <li><?= logout_button("nav-logout", "Logout") ?></li>
                <?php else: ?>
                    <li><a href="login.php"><i class="bi bi-box-arrow-in-right" aria-hidden="true"></i><span>Sign in</span></a></li>
                <?php endif; ?>
            <?php endif; ?>
        </ul>
    <?php endforeach; ?>

    <div class="sidebar-footer">
        <button type="button" class="theme-toggle-nav" onclick="window.toggleTheme()" aria-pressed="false">
            <i class="bi bi-moon-stars" aria-hidden="true"></i> <span>Dark mode</span>
        </button>
    </div>
</nav>
