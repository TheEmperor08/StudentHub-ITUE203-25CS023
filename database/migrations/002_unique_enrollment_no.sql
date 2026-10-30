-- =====================================================================================================================
-- StudentHub migration 002 - unique enrollment numbers (Practical 11 student management)
-- Target: the shared StudentHub database (studenthub_db) after migration 001, MariaDB 10.4+ / XAMPP.
--
-- The Admin Console now adds and edits student records (Practical 11). Two records must never share an enrollment
-- number, so the database enforces it as well as the application:
--   * students.enrollment_no   UNIQUE index uq_students_enrollment_no (NULL stays allowed, several times, for legacy rows)
-- Nothing else changes: no column, value, status, course name, account link or registration is touched.
--
-- Apply  (in the repository folder):  C:\xampp\mysql\bin\mysql.exe -u root studenthub_db < database\migrations\002_unique_enrollment_no.sql
-- Undo:                               database\migrations\002_unique_enrollment_no.down.sql   (see database\README.md)
--
-- Safe to run more than once (ADD ... IF NOT EXISTS). The preconditions run first; if one fails the script stops with a
-- message and nothing is altered. Duplicate or empty enrollment numbers are NOT corrected automatically: they are real
-- data and must be reviewed by a person (the query in database\README.md lists them).
-- =====================================================================================================================

SET NAMES utf8mb4;

DELIMITER //

-- ---------------------------------------------------------------------------------------------------------------------
-- 0. Preconditions (read-only)
-- ---------------------------------------------------------------------------------------------------------------------
BEGIN NOT ATOMIC
    IF DATABASE() IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 002: no database selected. Run: mysql -u root studenthub_db < 002_unique_enrollment_no.sql';
    END IF;
    -- two separate checks: schema_migrations may not exist yet, and MariaDB resolves a table when the statement runs
    IF NOT EXISTS (SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'schema_migrations') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 002: apply migration 001 (001_practical8_foundation.sql) first.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '001') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 002: apply migration 001 (001_practical8_foundation.sql) first.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS
                   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'students' AND COLUMN_NAME = 'enrollment_no') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 002: students.enrollment_no is missing.';
    END IF;
    -- the column collation is case-insensitive, so "25cs001" and "25CS001" count as the same number
    IF EXISTS (SELECT 1 FROM students WHERE enrollment_no IS NOT NULL GROUP BY enrollment_no HAVING COUNT(*) > 1) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 002: some enrollment numbers are used by more than one student. Correct them first (see database/README.md).';
    END IF;
END //

DELIMITER ;

-- ---------------------------------------------------------------------------------------------------------------------
-- 1. The unique index
-- ---------------------------------------------------------------------------------------------------------------------
ALTER TABLE students ADD UNIQUE KEY IF NOT EXISTS uq_students_enrollment_no (enrollment_no);

-- ---------------------------------------------------------------------------------------------------------------------
-- 2. Verification and migration record
-- ---------------------------------------------------------------------------------------------------------------------
DELIMITER //
BEGIN NOT ATOMIC
    IF (SELECT COUNT(*) FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'students' AND INDEX_NAME = 'uq_students_enrollment_no'
          AND NON_UNIQUE = 0 AND COLUMN_NAME = 'enrollment_no') <> 1
       OR (SELECT COUNT(*) FROM information_schema.STATISTICS
           WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'students' AND INDEX_NAME = 'uq_students_enrollment_no') <> 1 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 002 verification failed: uq_students_enrollment_no is missing or covers other columns.';
    END IF;
END //
DELIMITER ;

INSERT IGNORE INTO schema_migrations (version, description)
VALUES ('002', 'Practical 11 student management: UNIQUE students.enrollment_no');
