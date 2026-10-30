-- =====================================================================================================================
-- StudentHub migration 003 - event management (Practical 12)
-- Target: the shared StudentHub database (studenthub_db) after migration 002, MariaDB 10.4+ / XAMPP.
--
-- Brings Practical 12's event design into the portal's existing events table without replacing it:
--   * event_categories        new lookup table (Practical 12's six categories + every category already used by an event)
--   * events.category         foreign key -> event_categories.name (ON UPDATE CASCADE; a used category cannot be deleted)
--   * events.status           'open' / 'closed' (existing events: 'open'); closed events take no new registrations
--   * events.updated_at       set automatically on every change (existing events: NULL = not changed since)
--   * events.poster           UNIQUE (two events can never share one poster file); existing values are kept as they are
-- Nothing is renamed or removed: titles, dates, times, locations, capacities, categories, posters and registrations stay.
--
-- Apply  (in the repository folder):  C:\xampp\mysql\bin\mysql.exe -u root studenthub_db < database\migrations\003_event_management.sql
-- Undo:                               database\migrations\003_event_management.down.sql   (see database\README.md)
--
-- Safe to run more than once (IF [NOT] EXISTS, INSERT IGNORE). The preconditions run first; if one fails the script
-- stops with a message and nothing is altered. MariaDB commits each ALTER/CREATE immediately: take a mysqldump first.
-- =====================================================================================================================

SET NAMES utf8mb4;

DELIMITER //

-- ---------------------------------------------------------------------------------------------------------------------
-- 0. Preconditions (read-only)
-- ---------------------------------------------------------------------------------------------------------------------
BEGIN NOT ATOMIC
    IF DATABASE() IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 003: no database selected. Run: mysql -u root studenthub_db < 003_event_management.sql';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'schema_migrations') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 003: apply migrations 001 and 002 first.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '002') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 003: apply migrations 001 and 002 first.';
    END IF;
    IF (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'events'
        AND ((COLUMN_NAME = 'category' AND COLUMN_TYPE = 'varchar(50)') OR (COLUMN_NAME = 'poster' AND COLUMN_TYPE = 'varchar(255)'))) <> 2 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 003: events.category VARCHAR(50) and events.poster VARCHAR(255) are required.';
    END IF;
    IF EXISTS (SELECT 1 FROM events WHERE poster IS NOT NULL GROUP BY poster HAVING COUNT(*) > 1) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 003: two events use the same poster value. Correct them first (see database/README.md).';
    END IF;
    IF EXISTS (SELECT 1 FROM events WHERE TRIM(category) = '') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 003: some events have an empty category. Correct them first.';
    END IF;
END //

DELIMITER ;

-- ---------------------------------------------------------------------------------------------------------------------
-- 1. Categories: Practical 12's list plus every category already used (so no event changes)
-- ---------------------------------------------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS event_categories (
    name        VARCHAR(50)  NOT NULL,
    description VARCHAR(200) DEFAULT NULL,
    PRIMARY KEY (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO event_categories (name, description) VALUES
    ('Cultural',  'Music, dance, drama and festivals'),
    ('Hackathon', 'Team coding competitions'),
    ('Seminar',   'Talks and guest lectures'),
    ('Sports',    'Matches and tournaments'),
    ('Technical', 'Technical talks and project expos'),
    ('Workshop',  'Hands-on training sessions');
INSERT IGNORE INTO event_categories (name) SELECT DISTINCT category FROM events;

-- ---------------------------------------------------------------------------------------------------------------------
-- 2. Events: status, updated_at, unique poster, category foreign key
-- ---------------------------------------------------------------------------------------------------------------------
ALTER TABLE events
    ADD COLUMN IF NOT EXISTS status ENUM('open', 'closed') NOT NULL DEFAULT 'open' AFTER capacity,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP AFTER created_at,
    ADD UNIQUE KEY IF NOT EXISTS uq_events_poster (poster),
    ADD KEY IF NOT EXISTS idx_events_status (status),
    ADD KEY IF NOT EXISTS idx_events_category (category);

ALTER TABLE events
    ADD CONSTRAINT fk_events_category FOREIGN KEY IF NOT EXISTS (category) REFERENCES event_categories (name)
        ON UPDATE CASCADE ON DELETE RESTRICT;

-- ---------------------------------------------------------------------------------------------------------------------
-- 3. Verification and migration record
-- ---------------------------------------------------------------------------------------------------------------------
DELIMITER //
BEGIN NOT ATOMIC
    IF NOT EXISTS (SELECT 1 FROM information_schema.REFERENTIAL_CONSTRAINTS
                   WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = 'events' AND CONSTRAINT_NAME = 'fk_events_category'
                     AND REFERENCED_TABLE_NAME = 'event_categories' AND UPDATE_RULE = 'CASCADE' AND DELETE_RULE = 'RESTRICT') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 003 verification failed: fk_events_category is missing or has unexpected rules.';
    END IF;
    IF (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'events'
        AND INDEX_NAME = 'uq_events_poster' AND NON_UNIQUE = 0 AND COLUMN_NAME = 'poster') <> 1 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 003 verification failed: uq_events_poster is missing.';
    END IF;
    IF (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'events'
        AND ((COLUMN_NAME = 'status' AND COLUMN_TYPE = 'enum(''open'',''closed'')' AND IS_NULLABLE = 'NO')
          OR (COLUMN_NAME = 'updated_at' AND IS_NULLABLE = 'YES'))) <> 2 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 003 verification failed: events.status / events.updated_at are missing.';
    END IF;
END //
DELIMITER ;

INSERT IGNORE INTO schema_migrations (version, description)
VALUES ('003', 'Practical 12 event management: event_categories + FK, events.status, events.updated_at, UNIQUE events.poster');
