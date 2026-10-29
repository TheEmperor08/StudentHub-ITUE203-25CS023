-- StudentHub demo database (safe to publish)
-- Schema exported from the working studenthub_db. Contains NO user accounts, password hashes,
-- audit logs or real student records. All student rows except the owner are fictional (example.com).
-- Safe to re-run: tables use IF NOT EXISTS and rows use INSERT IGNORE (nothing is dropped).
--
-- Import:  mysql -u root -e "CREATE DATABASE IF NOT EXISTS studenthub_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
--          mysql -u root studenthub_db < database/studenthub_demo.sql
-- Accounts: php tools/create_demo_user.php --db=studenthub_db --username=<name> --email=<email> --role=admin|student

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL,
  `role` varchar(20) NOT NULL DEFAULT 'student',
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `last_login` datetime DEFAULT NULL,
  `remember_token_hash` varchar(255) DEFAULT NULL,
  `remember_token_expiry` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS `students` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `enrollment_no` varchar(20) DEFAULT NULL,
  `name` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL,
  `course` varchar(50) NOT NULL,
  `gender` varchar(10) NOT NULL,
  `semester` int(11) DEFAULT 3,
  `status` varchar(20) DEFAULT 'Active',
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS `events` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(150) NOT NULL,
  `event_date` date NOT NULL,
  `location` varchar(150) NOT NULL,
  `description` text DEFAULT NULL,
  `category` varchar(50) NOT NULL,
  `poster` varchar(255) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS `menu_items` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(50) NOT NULL,
  `link` varchar(150) NOT NULL,
  `min_role` enum('user','editor','admin') DEFAULT 'user',
  `icon` varchar(50) DEFAULT 'bi-link',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
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
  PRIMARY KEY (`id`)
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
(1, 'Student Dashboard',         'dashboard.php',                   'user',  'bi-speedometer2'),
(2, 'My Profile',                'profile.php',                     'user',  'bi-person-badge'),
(3, 'Campus Events',             'notifications.php',               'user',  'bi-calendar-event'),
(5, 'Attendance',                'attendance.php',                  'editor','bi-check2-square'),
(6, 'Admin Management Console',  'admin_dashboard.php',             'admin', 'bi-shield-lock'),
(7, 'Student Management (CRUD)', 'admin_dashboard.php?tab=students','admin', 'bi-people'),
(8, 'Campus Event Manager',      'admin_dashboard.php?tab=events',  'admin', 'bi-calendar-plus'),
(9, 'Asynchronous SPA Manager',  '../Practical-13/index.html',      'admin', 'bi-lightning-charge'),
(10,'Security Audit Logs',       'admin_dashboard.php?tab=audits',  'admin', 'bi-journal-text');
