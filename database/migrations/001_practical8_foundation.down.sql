-- =====================================================================================================================
-- StudentHub migration 001 - ROLLBACK (schema only)
--
-- Removes exactly what 001_practical8_foundation.sql added and restores the previous table structure.
-- WARNING: this deletes data that only exists in the new structure - every row of `registrations`, every
-- events.event_time / events.capacity value and the students.user_id links. All other data is untouched.
-- The preferred way back is restoring the mysqldump taken before the migration (see database/README.md);
-- use this script when that dump is older than data you want to keep.
--
-- Run:  C:\xampp\mysql\bin\mysql.exe -u root studenthub_db < database\migrations\001_practical8_foundation.down.sql
-- Safe to run more than once (IF EXISTS everywhere).
-- =====================================================================================================================

SET NAMES utf8mb4;

-- 4. audit_logs: foreign key and the index MariaDB created for it
ALTER TABLE audit_logs DROP FOREIGN KEY IF EXISTS fk_audit_logs_user;
ALTER TABLE audit_logs DROP INDEX IF EXISTS fk_audit_logs_user;

-- 3. registrations
DROP TABLE IF EXISTS registrations;

-- 2. events
ALTER TABLE events DROP CONSTRAINT IF EXISTS chk_events_capacity;
ALTER TABLE events
    DROP INDEX IF EXISTS idx_events_date,
    DROP COLUMN IF EXISTS capacity,
    DROP COLUMN IF EXISTS event_time;

-- 1. students
ALTER TABLE students DROP FOREIGN KEY IF EXISTS fk_students_user;
ALTER TABLE students DROP CONSTRAINT IF EXISTS chk_students_semester;
ALTER TABLE students
    DROP INDEX IF EXISTS uq_students_user_id,
    DROP COLUMN IF EXISTS user_id;

-- 5. migration record (the table is removed when no other migration is recorded)
DELIMITER //
BEGIN NOT ATOMIC
    IF EXISTS (SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'schema_migrations') THEN
        DELETE FROM schema_migrations WHERE version = '001';
        IF NOT EXISTS (SELECT 1 FROM schema_migrations) THEN
            DROP TABLE schema_migrations;
        END IF;
    END IF;
END //
DELIMITER ;
