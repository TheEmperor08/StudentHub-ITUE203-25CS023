<?php
// StudentHub – role-based navigation (Practical 14 integrated). The links come from the menu_items table; each row has a
// minimum role (student < editor < admin, migration 004). A user sees the rows up to their own role – an editor never sees
// an admin link, and the pages behind the links still check the permission on the server (require_permission()).
// Links to pages that do not exist in the portal (e.g. the old faculty.php) or outside it are not shown.

const ROLE_RANK = ['student' => 1, 'editor' => 2, 'admin' => 3];

// True if the link points to an existing page of this portal ("page.php", "page.php?tab=x", "page.php#part")
function portal_page_exists(string $link): bool
{
    $page = preg_split('/[?#]/', $link, 2)[0];
    return preg_match('/^[A-Za-z0-9_\-]+\.php$/', $page) === 1 && is_file(dirname(__DIR__) . DIRECTORY_SEPARATOR . $page);
}

// The menu rows this role may see, in table order: [['title', 'link', 'icon', 'min_role'], ...]
function menu_for_role(mysqli $db, string $role): array
{
    $rank = ROLE_RANK[$role] ?? 0;
    $items = [];
    foreach ($db->query('SELECT title, link, icon, min_role FROM menu_items ORDER BY id')->fetch_all(MYSQLI_ASSOC) as $item) {
        if ($rank >= (ROLE_RANK[$item['min_role']] ?? PHP_INT_MAX) && portal_page_exists($item['link'])) {
            $items[] = $item;
        }
    }
    return $items;
}
