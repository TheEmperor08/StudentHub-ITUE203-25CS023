-- StudentHub demo database (safe to publish)
-- Schema of the working studenthub_db (including migrations 001 - Practical 8 foundation -, 002 - unique enrollment
-- numbers -, 003 - Practical 12 event management - and 004 - Practical 14 admin dashboard) plus fictional demo rows.
-- Contains NO user accounts, password hashes, audit logs or real student records. All student rows except the owner
-- are fictional (example.com).
-- Safe to re-run: tables use IF NOT EXISTS and rows use INSERT IGNORE (nothing is dropped).
--
-- NEW database:      mysql -u root -e "CREATE DATABASE IF NOT EXISTS studenthub_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
--                    mysql -u root studenthub_db < database/studenthub_demo.sql
-- EXISTING database created before migration 001: do not use this file; apply the migrations instead:
--                    mysql -u root studenthub_db < database/migrations/001_practical8_foundation.sql
--                    mysql -u root studenthub_db < database/migrations/002_unique_enrollment_no.sql
--                    mysql -u root studenthub_db < database/migrations/003_event_management.sql
--                    mysql -u root studenthub_db < database/migrations/004_admin_dashboard.sql
--                    (a database made by an earlier version of this file: apply only the migrations it is missing)
-- Accounts:          php tools/create_demo_user.php --db=studenthub_db --username=<name> --email=<email> --role=admin|student
-- Details:           database/README.md

SET NAMES utf8mb4;

-- An older StudentHub database would be skipped by CREATE TABLE IF NOT EXISTS and keep its old structure: refuse it.
-- (The second check is nested because MariaDB resolves schema_migrations only when that statement runs.)
DELIMITER //
BEGIN NOT ATOMIC
    IF EXISTS (SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'students')
       AND NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'students' AND COLUMN_NAME = 'user_id') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'This database was created before migration 001. Apply database/migrations/001_practical8_foundation.sql instead.';
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'schema_migrations') THEN
        IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '004') THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'This database was created by an earlier version of this file. Apply the missing migrations in database/migrations/ instead.';
        END IF;
    END IF;
END //
DELIMITER ;

CREATE TABLE IF NOT EXISTS `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL,
  `role` varchar(20) NOT NULL DEFAULT 'student',
  `status` enum('active','disabled') NOT NULL DEFAULT 'active',
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `last_login` datetime DEFAULT NULL,
  `remember_token_hash` varchar(255) DEFAULT NULL,
  `remember_token_expiry` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`),
  CONSTRAINT `chk_users_role` CHECK (`role` in ('admin','editor','student'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- students.user_id: optional link to the login account (one account per student record)
-- students.enrollment_no: unique (migration 002); NULL is allowed for legacy rows
CREATE TABLE IF NOT EXISTS `students` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) DEFAULT NULL,
  `enrollment_no` varchar(20) DEFAULT NULL,
  `name` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL,
  `course` varchar(50) NOT NULL,
  `gender` varchar(10) NOT NULL,
  `semester` int(11) DEFAULT 3,
  `status` varchar(20) DEFAULT 'Active',
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`),
  UNIQUE KEY `uq_students_user_id` (`user_id`),
  UNIQUE KEY `uq_students_enrollment_no` (`enrollment_no`),
  CONSTRAINT `fk_students_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `chk_students_semester` CHECK (`semester` is null or `semester` between 1 and 8)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- event_categories: lookup table for events.category (migration 003)
CREATE TABLE IF NOT EXISTS `event_categories` (
  `name` varchar(50) NOT NULL,
  `description` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO `event_categories` (`name`, `description`) VALUES
('Conference', NULL),
('Cultural',   'Music, dance, drama and festivals'),
('Hackathon',  'Team coding competitions'),
('Seminar',    'Talks and guest lectures'),
('Sports',     'Matches and tournaments'),
('Technical',  'Technical talks and project expos'),
('Workshop',   'Hands-on training sessions');

-- events.event_time / events.capacity: NULL = not set (capacity NULL = no limit)
-- events.status: open/closed (closed = no new registrations); events.poster: a stored poster name, UNIQUE (migration 003)
CREATE TABLE IF NOT EXISTS `events` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(150) NOT NULL,
  `event_date` date NOT NULL,
  `event_time` time DEFAULT NULL,
  `location` varchar(150) NOT NULL,
  `capacity` smallint(5) unsigned DEFAULT NULL,
  `status` enum('open','closed') NOT NULL DEFAULT 'open',
  `description` text DEFAULT NULL,
  `category` varchar(50) NOT NULL,
  `poster` varchar(255) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NULL DEFAULT NULL ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_events_poster` (`poster`),
  KEY `idx_events_date` (`event_date`,`event_time`),
  KEY `idx_events_status` (`status`),
  KEY `idx_events_category` (`category`),
  CONSTRAINT `fk_events_category` FOREIGN KEY (`category`) REFERENCES `event_categories` (`name`) ON UPDATE CASCADE,
  CONSTRAINT `chk_events_capacity` CHECK (`capacity` is null or `capacity` > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- registrations: Practical 8's many-to-many table (one row per student per event)
CREATE TABLE IF NOT EXISTS `registrations` (
  `registration_id` int(11) NOT NULL AUTO_INCREMENT,
  `student_id` int(11) NOT NULL,
  `event_id` int(11) NOT NULL,
  `registered_at` datetime NOT NULL DEFAULT current_timestamp(),
  `status` enum('registered','attended','cancelled') NOT NULL DEFAULT 'registered',
  PRIMARY KEY (`registration_id`),
  UNIQUE KEY `uq_registrations_student_event` (`student_id`,`event_id`),
  KEY `idx_registrations_event` (`event_id`),
  CONSTRAINT `fk_registrations_event` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_registrations_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `menu_items` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(50) NOT NULL,
  `link` varchar(150) NOT NULL,
  `min_role` enum('student','editor','admin') NOT NULL DEFAULT 'student',
  `icon` varchar(50) DEFAULT 'bi-link',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- audit_logs.user_id: NULL for anonymous entries; set to NULL when the account is deleted (the username is kept)
CREATE TABLE IF NOT EXISTS `audit_logs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) DEFAULT NULL,
  `username` varchar(100) NOT NULL,
  `action` varchar(100) NOT NULL,
  `details` text DEFAULT NULL,
  `ip_address` varchar(45) NOT NULL,
  `user_agent` varchar(255) DEFAULT NULL,
  `status` varchar(20) DEFAULT 'SUCCESS',
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `fk_audit_logs_user` (`user_id`),
  CONSTRAINT `fk_audit_logs_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `schema_migrations` (
  `version` varchar(20) NOT NULL,
  `description` varchar(200) NOT NULL,
  `applied_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO `students` (`id`, `enrollment_no`, `name`, `email`, `course`, `gender`, `semester`, `status`) VALUES
(1, '25CS023', 'Shreyas',     '25cs023@charusat.edu.in', 'Computer Science',      'Male',   3, 'Active'),
(2, '25CE045', 'Diya Shah',   'diya@example.com',        'Web Development',       'Female', 5, 'Active'),
(3, '25IT012', 'Meet Desai',  'meet@example.com',        'Data Science',          'Male',   3, 'Active'),
(4, '25CS089', 'Kavya Mehta', 'kavya@example.com',       'Web Development',       'Female', 7, 'Active'),
(5, '25CS104', 'Rohan Patel', 'rohan@example.com',       'Cyber Security',        'Male',   3, 'Active'),
(6, '25CE078', 'Pooja Sharma','pooja@example.com',       'AI & Machine Learning', 'Female', 5, 'Active'),
(7, '25IT056', 'John Doe',    'john@example.com',        'Computer Science',      'Male',   3, 'Inactive');

INSERT IGNORE INTO `events` (`id`, `title`, `event_date`, `location`, `description`, `category`, `poster`) VALUES
(1, 'Odoo Hackathon 2026',              '2026-08-22', 'LDCE Ahmedabad',      NULL, 'Hackathon',  NULL),
(2, 'TechFest Spoural 2026',            '2026-09-10', 'CSPIT A7 Building',   NULL, 'Workshop',   NULL),
(3, 'AI & Cloud Computing Seminar',     '2026-09-15', 'Auditorium CHARUSAT', NULL, 'Conference', NULL),
(4, 'Robotics & Automation Exhibition', '2026-11-10', 'CSPIT Foyer',         NULL, 'Workshop',   NULL),
(5, 'Full-Stack Web Dev Bootcamp',      '2026-10-07', 'CSPIT Lab 3',         NULL, 'Workshop',   NULL);

-- Navigation links point at pages that exist (the unbuilt faculty page is omitted)
INSERT IGNORE INTO `menu_items` (`id`, `title`, `link`, `min_role`, `icon`) VALUES
(1, 'Student Dashboard',         'dashboard.php',                   'student', 'bi-speedometer2'),
(2, 'My Profile',                'profile.php',                     'student', 'bi-person-badge'),
(3, 'Campus Events',             'notifications.php',               'student', 'bi-calendar-event'),
(5, 'Attendance',                'attendance.php',                  'editor','bi-check2-square'),
(6, 'Admin Management Console',  'admin_dashboard.php',             'admin', 'bi-shield-lock'),
(7, 'Student Management (CRUD)', 'admin_dashboard.php?tab=students','admin', 'bi-people'),
(8, 'Campus Event Manager',      'admin_dashboard.php?tab=events',  'admin', 'bi-calendar-plus'),
(9, 'Event Finder (Fetch API)',  'events_live.php',                 'student', 'bi-lightning-charge'),
(10,'Security Audit Logs',       'admin_dashboard.php?tab=audits',  'admin', 'bi-journal-text');

-- This structure already includes migrations 001 to 004
INSERT IGNORE INTO `schema_migrations` (`version`, `description`) VALUES
('001', 'Practical 8 database foundation: students.user_id, registrations, event time/capacity, semester check, audit_logs FK'),
('002', 'Practical 11 student management: UNIQUE students.enrollment_no'),
('003', 'Practical 12 event management: event_categories + FK, events.status, events.updated_at, UNIQUE events.poster'),
('004', 'Practical 14 admin dashboard: menu roles student/editor/admin + integrated links, users.status, role check');
