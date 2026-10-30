-- =====================================================================================================================
-- StudentHub migration 004 - ROLLBACK
--
-- Removes users.status and chk_users_role and gives menu_items.min_role its old values back ('student' -> 'user').
-- WARNING: the information which accounts were disabled is lost (all accounts can sign in again). The corrected menu
-- links (profile.php, notifications.php, attendance.php, events_live.php) are kept: they point at existing pages.
--
-- Run:  C:\xampp\mysql\bin\mysql.exe -u root studenthub_db < database\migrations\004_admin_dashboard.down.sql
-- Safe to run more than once.
-- =====================================================================================================================

SET NAMES utf8mb4;

ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_role;
ALTER TABLE users DROP COLUMN IF EXISTS status;

ALTER TABLE menu_items MODIFY min_role ENUM('user', 'student', 'editor', 'admin') DEFAULT 'user';
UPDATE menu_items SET min_role = 'user' WHERE min_role = 'student';
ALTER TABLE menu_items MODIFY min_role ENUM('user', 'editor', 'admin') DEFAULT 'user';

DELIMITER //
BEGIN NOT ATOMIC
    IF EXISTS (SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'schema_migrations') THEN
        DELETE FROM schema_migrations WHERE version = '004';
    END IF;
END //
DELIMITER ;
