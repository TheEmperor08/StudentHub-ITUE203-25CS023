-- =====================================================================================================================
-- StudentHub migration 003 - ROLLBACK
--
-- Removes exactly what 003_event_management.sql added: the category foreign key and indexes, the unique poster index,
-- events.status and events.updated_at, the event_categories table and the migration record.
-- WARNING: event status values (open/closed) and update times are lost; titles, dates, categories (as text), posters,
-- capacities and registrations stay. The preferred way back is restoring the dump taken before the migration.
--
-- Run:  C:\xampp\mysql\bin\mysql.exe -u root studenthub_db < database\migrations\003_event_management.down.sql
-- Safe to run more than once (IF EXISTS everywhere).
-- =====================================================================================================================

SET NAMES utf8mb4;

ALTER TABLE events DROP FOREIGN KEY IF EXISTS fk_events_category;
ALTER TABLE events
    DROP INDEX IF EXISTS idx_events_category,
    DROP INDEX IF EXISTS idx_events_status,
    DROP INDEX IF EXISTS uq_events_poster,
    DROP COLUMN IF EXISTS updated_at,
    DROP COLUMN IF EXISTS status;
DROP TABLE IF EXISTS event_categories;

DELIMITER //
BEGIN NOT ATOMIC
    IF EXISTS (SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'schema_migrations') THEN
        DELETE FROM schema_migrations WHERE version = '003';
    END IF;
END //
DELIMITER ;
