-- =====================================================================================================================
-- StudentHub migration 001 - Practical 8 database foundation
-- Target: the shared StudentHub database (studenthub_db), MariaDB 10.4+ / XAMPP.
--
-- Brings Practical 8's normalised design (students - events - registrations, with foreign keys and checks) into the
-- existing portal database WITHOUT replacing it:
--   * students.user_id      nullable link to the login account (users.id); filled only for unique, verified e-mail matches
--   * students.semester     validated 1-8 (NULL stays allowed for legacy rows)
--   * events.event_time, events.capacity   new nullable fields (existing events get NULL = not set / no limit)
--   * registrations         new table: one row per student per event, CASCADE foreign keys, UNIQUE (student_id, event_id)
--   * audit_logs.user_id    nullable foreign key to users.id; deleting an account keeps its log entries (user_id -> NULL)
--   * schema_migrations     records which migrations have been applied
-- Nothing is renamed or removed: students.enrollment_no, events.location, status values, course names, roles and
-- password hashes stay exactly as they are. All key columns are signed INT(11), matching the existing primary keys.
--
-- Apply  (in the repository folder):  C:\xampp\mysql\bin\mysql.exe -u root studenthub_db < database\migrations\001_practical8_foundation.sql
-- Undo   (schema only):               database\migrations\001_practical8_foundation.down.sql   (see database\README.md)
--
-- Safe to run more than once: every change uses IF [NOT] EXISTS or only touches rows that are not linked yet.
-- The preconditions run before any change; if one fails the script stops with a message and nothing is altered.
-- MariaDB commits each ALTER/CREATE TABLE immediately (DDL cannot be rolled back), so take a mysqldump first.
-- =====================================================================================================================

SET NAMES utf8mb4;

DELIMITER //

-- ---------------------------------------------------------------------------------------------------------------------
-- 0. Preconditions (read-only)
-- ---------------------------------------------------------------------------------------------------------------------
BEGIN NOT ATOMIC
    IF DATABASE() IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 001: no database selected. Run: mysql -u root studenthub_db < 001_practical8_foundation.sql';
    END IF;
    IF (SELECT COUNT(*) FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN ('users', 'students', 'events', 'audit_logs') AND ENGINE = 'InnoDB') <> 4 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 001: tables users, students, events and audit_logs (InnoDB) are required.';
    END IF;
    IF (SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND COLUMN_TYPE = 'int(11)'
          AND ((TABLE_NAME = 'users' AND COLUMN_NAME = 'id') OR (TABLE_NAME = 'students' AND COLUMN_NAME = 'id')
            OR (TABLE_NAME = 'events' AND COLUMN_NAME = 'id') OR (TABLE_NAME = 'audit_logs' AND COLUMN_NAME = 'user_id'))) <> 4 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 001: users.id, students.id, events.id and audit_logs.user_id must be signed INT(11).';
    END IF;
    IF EXISTS (SELECT 1 FROM audit_logs a LEFT JOIN users u ON u.id = a.user_id WHERE a.user_id IS NOT NULL AND u.id IS NULL) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 001: audit_logs has user_id values of deleted accounts. Review them (see database/README.md) before migrating.';
    END IF;
    IF EXISTS (SELECT 1 FROM students WHERE semester IS NOT NULL AND semester NOT BETWEEN 1 AND 8) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 001: students has semester values outside 1-8. Correct them before migrating.';
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'registrations')
       AND NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'registrations'
                       AND COLUMN_NAME = 'registration_id' AND COLUMN_TYPE = 'int(11)') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 001: a different registrations table already exists. Rename or remove it first.';
    END IF;
END //

DELIMITER ;

-- ---------------------------------------------------------------------------------------------------------------------
-- 1. students: link to the login account and Practical 8's semester rule
-- ---------------------------------------------------------------------------------------------------------------------
ALTER TABLE students
    ADD COLUMN IF NOT EXISTS user_id INT(11) NULL DEFAULT NULL AFTER id,
    ADD UNIQUE KEY IF NOT EXISTS uq_students_user_id (user_id);

ALTER TABLE students
    ADD CONSTRAINT fk_students_user FOREIGN KEY IF NOT EXISTS (user_id) REFERENCES users (id)
        ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE students
    ADD CONSTRAINT IF NOT EXISTS chk_students_semester CHECK (semester IS NULL OR semester BETWEEN 1 AND 8);

-- Link a student record to an account only when the e-mail (trimmed, case-insensitive) belongs to exactly one account,
-- that account has the role 'student', exactly one student record has that e-mail, and neither side is linked yet.
-- Everything else (no account, ambiguous e-mail, admin/editor account) stays unlinked; no account is created.
UPDATE students AS s
JOIN (
    SELECT MIN(st.id) AS student_id, MIN(u.id) AS user_id
    FROM users AS u
    JOIN students AS st ON LOWER(TRIM(st.email)) = LOWER(TRIM(u.email))
    GROUP BY LOWER(TRIM(u.email))
    HAVING COUNT(DISTINCT st.id) = 1 AND COUNT(DISTINCT u.id) = 1 AND MIN(u.role) = 'student'
) AS verified ON verified.student_id = s.id
LEFT JOIN students AS already ON already.user_id = verified.user_id
SET s.user_id = verified.user_id
WHERE s.user_id IS NULL AND already.id IS NULL;

-- ---------------------------------------------------------------------------------------------------------------------
-- 2. events: time and capacity (NULL for existing events - nothing is invented)
-- ---------------------------------------------------------------------------------------------------------------------
ALTER TABLE events
    ADD COLUMN IF NOT EXISTS event_time TIME NULL DEFAULT NULL AFTER event_date,
    ADD COLUMN IF NOT EXISTS capacity SMALLINT(5) UNSIGNED NULL DEFAULT NULL AFTER location,
    ADD INDEX IF NOT EXISTS idx_events_date (event_date, event_time);

ALTER TABLE events
    ADD CONSTRAINT IF NOT EXISTS chk_events_capacity CHECK (capacity IS NULL OR capacity > 0);

-- ---------------------------------------------------------------------------------------------------------------------
-- 3. registrations: Practical 8's many-to-many table between students and events
--    (capacity is enforced in PHP with a transaction that locks the event row: studenthub/includes/event_registration.php)
-- ---------------------------------------------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS registrations (
    registration_id INT(11)  NOT NULL AUTO_INCREMENT,
    student_id      INT(11)  NOT NULL,
    event_id        INT(11)  NOT NULL,
    registered_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status          ENUM('registered', 'attended', 'cancelled') NOT NULL DEFAULT 'registered',
    PRIMARY KEY (registration_id),
    UNIQUE KEY uq_registrations_student_event (student_id, event_id),
    KEY idx_registrations_event (event_id),
    CONSTRAINT fk_registrations_student FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_registrations_event FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------------------------------------------------
-- 4. audit_logs: optional link to the account; anonymous entries keep user_id NULL, deleted accounts become NULL
-- ---------------------------------------------------------------------------------------------------------------------
ALTER TABLE audit_logs
    ADD CONSTRAINT fk_audit_logs_user FOREIGN KEY IF NOT EXISTS (user_id) REFERENCES users (id)
        ON DELETE SET NULL ON UPDATE CASCADE;

-- ---------------------------------------------------------------------------------------------------------------------
-- 5. Verification and migration record
-- ---------------------------------------------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     VARCHAR(20)  NOT NULL,
    description VARCHAR(200) NOT NULL,
    applied_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DELIMITER //

BEGIN NOT ATOMIC
    IF (SELECT COUNT(*) FROM information_schema.REFERENTIAL_CONSTRAINTS
        WHERE CONSTRAINT_SCHEMA = DATABASE()
          AND ((CONSTRAINT_NAME = 'fk_students_user'         AND REFERENCED_TABLE_NAME = 'users'    AND DELETE_RULE = 'SET NULL')
            OR (CONSTRAINT_NAME = 'fk_registrations_student' AND REFERENCED_TABLE_NAME = 'students' AND DELETE_RULE = 'CASCADE')
            OR (CONSTRAINT_NAME = 'fk_registrations_event'   AND REFERENCED_TABLE_NAME = 'events'   AND DELETE_RULE = 'CASCADE')
            OR (CONSTRAINT_NAME = 'fk_audit_logs_user'       AND REFERENCED_TABLE_NAME = 'users'    AND DELETE_RULE = 'SET NULL'))) <> 4 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 001 verification failed: foreign keys are missing or have unexpected rules.';
    END IF;
    IF (SELECT COUNT(*) FROM information_schema.CHECK_CONSTRAINTS
        WHERE CONSTRAINT_SCHEMA = DATABASE() AND CONSTRAINT_NAME IN ('chk_students_semester', 'chk_events_capacity')) <> 2 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 001 verification failed: CHECK constraints are missing.';
    END IF;
    IF (SELECT COUNT(*) FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE() AND NON_UNIQUE = 0
          AND ((TABLE_NAME = 'students' AND INDEX_NAME = 'uq_students_user_id')
            OR (TABLE_NAME = 'registrations' AND INDEX_NAME = 'uq_registrations_student_event' AND COLUMN_NAME = 'event_id'))) <> 2 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 001 verification failed: unique keys are missing.';
    END IF;
    IF EXISTS (SELECT 1 FROM students s JOIN users u ON u.id = s.user_id WHERE u.role <> 'student') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 001 verification failed: a student record is linked to a non-student account.';
    END IF;
END //

DELIMITER ;

INSERT IGNORE INTO schema_migrations (version, description)
VALUES ('001', 'Practical 8 database foundation: students.user_id, registrations, event time/capacity, semester check, audit_logs FK');
