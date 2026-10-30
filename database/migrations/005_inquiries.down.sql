-- =====================================================================================================================
-- StudentHub migration 005 - ROLLBACK
-- WARNING: deletes the inquiries table and every stored inquiry. Export them first if they are still needed.
-- Run:  C:\xampp\mysql\bin\mysql.exe -u root studenthub_db < database\migrations\005_inquiries.down.sql
-- =====================================================================================================================

SET NAMES utf8mb4;

DROP TABLE IF EXISTS inquiries;

DELIMITER //
BEGIN NOT ATOMIC
    IF EXISTS (SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'schema_migrations') THEN
        DELETE FROM schema_migrations WHERE version = '005';
    END IF;
END //
DELIMITER ;
