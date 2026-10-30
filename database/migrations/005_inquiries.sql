-- =====================================================================================================================
-- StudentHub migration 005 - stored contact inquiries (Practical 7 integrated into the portal)
-- Target: the shared StudentHub database (studenthub_db) after migration 004, MariaDB 10.4+ / XAMPP.
--
-- The portal's Help & Contact form (contact.php) now stores every valid inquiry, so the helpdesk can answer it in the
-- Admin Console. Practical 7 stored them in a JSON file with file locking; the portal uses this table instead:
--   * inquiries   name, e-mail, optional enrollment number, topic, message, status new/resolved, optional link to the
--                 signed-in account (users.id, ON DELETE SET NULL: deleting an account keeps its inquiries)
-- Nothing else changes.
--
-- Apply:  C:\xampp\mysql\bin\mysql.exe -u root studenthub_db < database\migrations\005_inquiries.sql
-- Undo:   database\migrations\005_inquiries.down.sql   (deletes the stored inquiries)
-- =====================================================================================================================

SET NAMES utf8mb4;

DELIMITER //
BEGIN NOT ATOMIC
    IF DATABASE() IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 005: no database selected. Run: mysql -u root studenthub_db < 005_inquiries.sql';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'schema_migrations') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 005: apply migrations 001 to 004 first.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '004') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 005: apply migrations 001 to 004 first.';
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'inquiries')
       AND NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'inquiries' AND COLUMN_NAME = 'topic') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 005: a different inquiries table already exists. Rename or remove it first.';
    END IF;
END //
DELIMITER ;

CREATE TABLE IF NOT EXISTS inquiries (
    id            INT(11)      NOT NULL AUTO_INCREMENT,
    user_id       INT(11)      DEFAULT NULL,
    name          VARCHAR(100) NOT NULL,
    email         VARCHAR(100) NOT NULL,
    enrollment_no VARCHAR(20)  DEFAULT NULL,
    topic         ENUM('General', 'Academics', 'Events', 'Portal access', 'Other') NOT NULL DEFAULT 'General',
    message       TEXT         NOT NULL,
    status        ENUM('new', 'resolved') NOT NULL DEFAULT 'new',
    created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at   DATETIME     DEFAULT NULL,
    PRIMARY KEY (id),
    KEY idx_inquiries_status (status, created_at),
    KEY idx_inquiries_user (user_id),
    CONSTRAINT fk_inquiries_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_inquiries_message CHECK (CHAR_LENGTH(message) BETWEEN 10 AND 2000)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DELIMITER //
BEGIN NOT ATOMIC
    IF NOT EXISTS (SELECT 1 FROM information_schema.REFERENTIAL_CONSTRAINTS WHERE CONSTRAINT_SCHEMA = DATABASE() AND CONSTRAINT_NAME = 'fk_inquiries_user'
                   AND REFERENCED_TABLE_NAME = 'users' AND DELETE_RULE = 'SET NULL') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Migration 005 verification failed: fk_inquiries_user is missing.';
    END IF;
END //
DELIMITER ;

INSERT IGNORE INTO schema_migrations (version, description)
VALUES ('005', 'Practical 7 contact inquiries: inquiries table (FK users ON DELETE SET NULL)');
