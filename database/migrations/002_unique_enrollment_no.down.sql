-- =====================================================================================================================
-- StudentHub migration 002 - ROLLBACK
--
-- Removes the UNIQUE index on students.enrollment_no and the migration record. No data is changed or deleted.
-- After the rollback the database no longer refuses duplicate enrollment numbers (the application still checks them).
--
-- Run:  C:\xampp\mysql\bin\mysql.exe -u root studenthub_db < database\migrations\002_unique_enrollment_no.down.sql
-- Safe to run more than once (IF EXISTS).
-- =====================================================================================================================

SET NAMES utf8mb4;

ALTER TABLE students DROP INDEX IF EXISTS uq_students_enrollment_no;

DELIMITER //
BEGIN NOT ATOMIC
    IF EXISTS (SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'schema_migrations') THEN
        DELETE FROM schema_migrations WHERE version = '002';
    END IF;
END //
DELIMITER ;
