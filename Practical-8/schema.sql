-- =====================================================================
-- StudentHub – ITUE203 Practical 8: MySQL schema (Third Normal Form)
-- Database : studenthub_prac8 (isolated practical database)
-- Tables   : students, events, registrations
-- Server   : MySQL / MariaDB (tested on XAMPP MariaDB 10.4.32)
--
-- Import with phpMyAdmin: Import tab -> choose this file -> Import
--   or from Command Prompt: C:\xampp\mysql\bin\mysql.exe -u root < schema.sql
-- Re-importing resets the three tables to the sample data below.
--
-- All sample data is FICTIONAL: names, DEMO-S codes and example.com
-- email addresses do not belong to real students.
-- =====================================================================

SET NAMES utf8mb4;
SET time_zone = '+05:30';

CREATE DATABASE IF NOT EXISTS studenthub_prac8
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE studenthub_prac8;

-- Drop in child-to-parent order so the foreign keys never block a re-import
DROP PROCEDURE IF EXISTS register_student_for_event;
DROP PROCEDURE IF EXISTS get_event_roster;
DROP TABLE IF EXISTS registrations;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS students;

-- ---------------------------------------------------------------------
-- 1. students – one row per student; every column depends only on student_id
-- ---------------------------------------------------------------------
CREATE TABLE students (
    student_id    INT UNSIGNED NOT NULL AUTO_INCREMENT,
    student_code  VARCHAR(12)  NOT NULL,
    full_name     VARCHAR(100) NOT NULL,
    email         VARCHAR(120) NOT NULL,
    branch        ENUM('CSE', 'CE', 'IT') NOT NULL,
    semester      TINYINT UNSIGNED NOT NULL,
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (student_id),
    CONSTRAINT uq_students_code UNIQUE (student_code),
    CONSTRAINT uq_students_email UNIQUE (email),
    CONSTRAINT chk_students_semester CHECK (semester BETWEEN 1 AND 8),
    CONSTRAINT chk_students_email CHECK (email LIKE '%_@_%._%'),
    INDEX idx_students_branch (branch)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 2. events – one row per event; every column depends only on event_id
-- ---------------------------------------------------------------------
CREATE TABLE events (
    event_id    INT UNSIGNED NOT NULL AUTO_INCREMENT,
    title       VARCHAR(120) NOT NULL,
    event_date  DATE NOT NULL,
    venue       VARCHAR(100) NOT NULL,
    category    VARCHAR(30)  NOT NULL,
    capacity    SMALLINT UNSIGNED NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (event_id),
    CONSTRAINT uq_events_title_date UNIQUE (title, event_date),
    CONSTRAINT chk_events_capacity CHECK (capacity > 0),
    INDEX idx_events_date (event_date)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 3. registrations – resolves the many-to-many relationship
--    (a student registers for many events; an event has many students)
-- ---------------------------------------------------------------------
CREATE TABLE registrations (
    registration_id  INT UNSIGNED NOT NULL AUTO_INCREMENT,
    student_id       INT UNSIGNED NOT NULL,
    event_id         INT UNSIGNED NOT NULL,
    registered_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status           ENUM('registered', 'attended', 'cancelled') NOT NULL DEFAULT 'registered',
    PRIMARY KEY (registration_id),
    CONSTRAINT uq_registrations_student_event UNIQUE (student_id, event_id),
    INDEX idx_registrations_event (event_id),
    CONSTRAINT fk_registrations_student FOREIGN KEY (student_id)
        REFERENCES students (student_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_registrations_event FOREIGN KEY (event_id)
        REFERENCES events (event_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Fictional seed data
-- ---------------------------------------------------------------------
INSERT INTO students (student_id, student_code, full_name, email, branch, semester) VALUES
    (1, 'DEMO-S001', 'Aarohi Menon',   'aarohi.menon@example.com',   'CSE', 3),
    (2, 'DEMO-S002', 'Eshan Kapoor',   'eshan.kapoor@example.com',   'IT',  3),
    (3, 'DEMO-S003', 'Farah Siddiqui', 'farah.siddiqui@example.com', 'CE',  5),
    (4, 'DEMO-S004', 'Karan Sethi',    'karan.sethi@example.com',    'IT',  1),
    (5, 'DEMO-S005', 'Devika Iyer',    'devika.iyer@example.com',    'CSE', 7),
    (6, 'DEMO-S006', 'Omkar Jadhav',   'omkar.jadhav@example.com',   'CE',  1),
    (7, 'DEMO-S007', 'Naina Kohli',    'naina.kohli@example.com',    'IT',  5),
    (8, 'DEMO-S008', 'Ishaan Bose',    'ishaan.bose@example.com',    'CSE', 3);

INSERT INTO events (event_id, title, event_date, venue, category, capacity) VALUES
    (1, 'Inter-college Hackathon',         '2026-08-22', 'Engineering Block Lab 1', 'Hackathon', 4),
    (2, 'Web Development Bootcamp',        '2026-08-30', 'Computer Lab 3',          'Workshop',  30),
    (3, 'AI and Machine Learning Seminar', '2026-09-15', 'Seminar Hall',            'Seminar',   100),
    (4, 'Robotics Expo',                   '2026-09-25', 'Main Foyer',              'TechFest',  50),
    (5, 'Annual Sports Week',              '2026-11-01', 'Sports Complex',          'Sports',    200);

INSERT INTO registrations (registration_id, student_id, event_id, registered_at, status) VALUES
    (1,  1, 1, '2026-08-01 10:15:00', 'registered'),
    (2,  2, 1, '2026-08-01 11:30:00', 'registered'),
    (3,  5, 1, '2026-08-02 09:05:00', 'registered'),
    (4,  8, 1, '2026-08-03 14:40:00', 'registered'),
    (5,  1, 2, '2026-08-05 16:20:00', 'attended'),
    (6,  3, 2, '2026-08-06 12:00:00', 'attended'),
    (7,  6, 2, '2026-08-06 12:45:00', 'cancelled'),
    (8,  2, 3, '2026-08-20 10:00:00', 'registered'),
    (9,  5, 3, '2026-08-21 15:10:00', 'registered'),
    (10, 7, 3, '2026-08-22 09:30:00', 'registered'),
    (11, 4, 4, '2026-09-01 11:00:00', 'registered'),
    (12, 7, 5, '2026-09-10 17:25:00', 'registered');

-- ---------------------------------------------------------------------
-- Stored procedures (advanced extension)
-- ---------------------------------------------------------------------
DELIMITER $$

-- Registers a student only if the event exists and still has free places
CREATE PROCEDURE register_student_for_event(IN p_student_id INT UNSIGNED, IN p_event_id INT UNSIGNED)
BEGIN
    DECLARE v_capacity SMALLINT UNSIGNED DEFAULT NULL;
    DECLARE v_taken INT DEFAULT 0;

    SELECT capacity INTO v_capacity FROM events WHERE event_id = p_event_id FOR UPDATE;
    IF v_capacity IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Event not found';
    END IF;

    SELECT COUNT(*) INTO v_taken FROM registrations
    WHERE event_id = p_event_id AND status <> 'cancelled';
    IF v_taken >= v_capacity THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Event is full';
    END IF;

    INSERT INTO registrations (student_id, event_id) VALUES (p_student_id, p_event_id);
    SELECT LAST_INSERT_ID() AS registration_id;
END$$

-- Lists the students registered for one event
CREATE PROCEDURE get_event_roster(IN p_event_id INT UNSIGNED)
BEGIN
    SELECT r.registration_id, s.student_code, s.full_name, s.branch, r.status
    FROM registrations AS r
    JOIN students AS s ON s.student_id = r.student_id
    WHERE r.event_id = p_event_id
    ORDER BY s.full_name;
END$$

DELIMITER ;
