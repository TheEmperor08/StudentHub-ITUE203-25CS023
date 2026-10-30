-- =====================================================================================================================
-- StudentHub migration 004 - admin dashboard, role-based navigation and account status (Practical 14)
-- Target: the shared StudentHub database (studenthub_db) after migration 003, MariaDB 10.4+ / XAMPP.
--
--   * menu_items.min_role   the role names now match the portal's roles: 'user' becomes 'student'
--                           (ENUM('student','editor','admin') NOT NULL DEFAULT 'student')
--   * menu_items.link       links to the old standalone pages or to anchors that do not exist are pointed at the
--                           integrated pages (dashboard.php, profile.php, notifications.php, attendance.php, events_live.php); a link to
--                           a page that does not exist at all (faculty.php) is kept and hidden by the portal
--   * users.status          'active' / 'disabled' (existing accounts: 'active'); a disabled account cannot sign in
--   * users.role            CHECK: only 'admin', 'editor' or 'student'
-- Nothing else changes: accounts, password hashes, roles, students, events and registrations stay as they are.
--
-- Apply:  C:\xampp\mysql\bin\mysql.exe -u root studenthub_db < database\migrations\004_admin_dashboard.sql
-- Undo:   database\migrations\004_admin_dashboard.down.sql
-- Safe to run more than once. The preconditions run first; if one fails nothing is altered.
-- =====================================================================================================================

SET NAMES utf8mb4;

DELIMITER //

BEGIN NOT ATOMIC
    IF DATABASE() IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 004: no database selected. Run: mysql -u root studenthub_db < 004_admin_dashboard.sql';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'schema_migrations') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 004: apply migrations 001 to 003 first.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '003') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 004: apply migrations 001 to 003 first.';
    END IF;
    IF EXISTS (SELECT 1 FROM users WHERE role NOT IN ('admin', 'editor', 'student')) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 004: some accounts have a role other than admin, editor or student. Correct them first.';
    END IF;
END //

DELIMITER ;

-- 1. menu_items.min_role: 'user' -> 'student' (widen, convert, narrow)
ALTER TABLE menu_items MODIFY min_role ENUM('user', 'student', 'editor', 'admin') NOT NULL DEFAULT 'student';
UPDATE menu_items SET min_role = 'student' WHERE min_role = 'user';
ALTER TABLE menu_items MODIFY min_role ENUM('student', 'editor', 'admin') NOT NULL DEFAULT 'student';

-- 2. links to old standalone pages or missing anchors -> the integrated pages
UPDATE menu_items SET link = 'profile.php'       WHERE link = 'student_dashboard.php' AND title LIKE 'My Profile%';
UPDATE menu_items SET link = 'dashboard.php'     WHERE link = 'student_dashboard.php' AND title = 'Student Dashboard';
UPDATE menu_items SET link = 'notifications.php' WHERE link = 'student_dashboard.php#events';
UPDATE menu_items SET link = 'attendance.php'    WHERE link = 'student_dashboard.php#attendance';
UPDATE menu_items SET link = 'events_live.php', title = 'Event Finder (Fetch API)', min_role = 'student', icon = 'bi-lightning-charge'
    WHERE link = '../Practical-13/index.html';

-- 3. account status and a role check
ALTER TABLE users ADD COLUMN IF NOT EXISTS status ENUM('active', 'disabled') NOT NULL DEFAULT 'active' AFTER role;
ALTER TABLE users ADD CONSTRAINT IF NOT EXISTS chk_users_role CHECK (role IN ('admin', 'editor', 'student'));

-- 4. verification and migration record
DELIMITER //
BEGIN NOT ATOMIC
    IF (SELECT COLUMN_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'menu_items' AND COLUMN_NAME = 'min_role')
       <> 'enum(''student'',''editor'',''admin'')' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 004 verification failed: menu_items.min_role was not converted.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'status'
                   AND COLUMN_TYPE = 'enum(''active'',''disabled'')' AND IS_NULLABLE = 'NO') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 004 verification failed: users.status is missing.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.CHECK_CONSTRAINTS WHERE CONSTRAINT_SCHEMA = DATABASE() AND CONSTRAINT_NAME = 'chk_users_role') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 004 verification failed: chk_users_role is missing.';
    END IF;
END //
DELIMITER ;

INSERT IGNORE INTO schema_migrations (version, description)
VALUES ('004', 'Practical 14 admin dashboard: menu roles student/editor/admin + integrated links, users.status, role check');
