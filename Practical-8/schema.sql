-- schema.sql
-- Practical 8: Relational Database Schema in 3NF (Third Normal Form) for MySQL / MariaDB
-- Import: mysql -u root < Practical-8/schema.sql

CREATE DATABASE IF NOT EXISTS practical8_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE practical8_db;

-- 1. Create 'students' table
CREATE TABLE IF NOT EXISTS students (
    student_id    INT AUTO_INCREMENT PRIMARY KEY,
    enrollment_no VARCHAR(20)  NOT NULL UNIQUE,
    full_name     VARCHAR(100) NOT NULL,
    branch        VARCHAR(50)  NOT NULL,
    semester      TINYINT UNSIGNED NOT NULL,
    email         VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Create 'events' table
CREATE TABLE IF NOT EXISTS events (
    event_id   INT AUTO_INCREMENT PRIMARY KEY,
    event_name VARCHAR(100) NOT NULL,
    event_date DATE         NOT NULL,
    location   VARCHAR(100) NOT NULL,
    category   VARCHAR(50)  NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Create 'registrations' table (junction table linking students and events)
CREATE TABLE IF NOT EXISTS registrations (
    registration_id   INT AUTO_INCREMENT PRIMARY KEY,
    student_id        INT NOT NULL,
    event_id          INT NOT NULL,
    registration_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (event_id)   REFERENCES events(event_id)     ON DELETE CASCADE,
    UNIQUE (student_id, event_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==========================================
-- Demo data (fictional students, example.com emails)
-- ==========================================

INSERT IGNORE INTO students (student_id, enrollment_no, full_name, branch, semester, email) VALUES
(1, '25CS023', 'Shreyas',     'CSE', 3, '25cs023@charusat.edu.in'),
(2, '25CE045', 'Diya Shah',   'CE',  5, 'diya@example.com'),
(3, '25IT012', 'Meet Desai',  'IT',  3, 'meet@example.com'),
(4, '25CS089', 'Kavya Mehta', 'CSE', 7, 'kavya@example.com');

INSERT IGNORE INTO events (event_id, event_name, event_date, location, category) VALUES
(1, 'Odoo Hackathon',   '2026-08-22', 'LDCE',       'Hackathon'),
(2, 'TechFest Spoural', '2026-09-10', 'CSPIT A7',   'TechFest'),
(3, 'AI Seminar',       '2026-09-15', 'Auditorium', 'Seminar');

INSERT IGNORE INTO registrations (student_id, event_id) VALUES
(1, 1), -- Shreyas registered for Odoo Hackathon
(1, 2), -- Shreyas registered for TechFest
(2, 3), -- Diya registered for AI Seminar
(3, 1), -- Meet registered for Odoo Hackathon
(4, 2); -- Kavya registered for TechFest
