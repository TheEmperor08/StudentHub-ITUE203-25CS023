-- StudentHub - test fixture: the studenthub_db structure BEFORE migration 001 (exported with mysqldump --no-data
-- from the working database on 2026-10-30) plus FICTIONAL rows. Used only by database/tests/test_001_practical8_foundation.py
-- to test the upgrade path. No real people, no password hashes (the placeholder below can never log in).
--
-- Linking cases covered by the rows:
--   student 1 / user 3   same email, different letter case            -> must be linked
--   student 2 / user 4   same email, surrounding spaces in students   -> must be linked (trimmed match)
--   students 5 and 6     ' dup@example.com' and 'dup@example.com' both match user 7 -> ambiguous, must NOT be linked
--   student 3 / user 6   email matches an EDITOR account              -> must NOT be linked (roles stay distinct)
--   student 4            no account                                   -> stays unlinked, record kept
--   user 5               student account without a students row       -> stays as it is
--   student 7            semester NULL (legacy)                       -> allowed and kept
SET NAMES utf8mb4;

CREATE TABLE `audit_logs` (
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
CREATE TABLE `events` (
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
CREATE TABLE `menu_items` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(50) NOT NULL,
  `link` varchar(150) NOT NULL,
  `min_role` enum('user','editor','admin') DEFAULT 'user',
  `icon` varchar(50) DEFAULT 'bi-link',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE `students` (
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
CREATE TABLE `users` (
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

INSERT INTO `users` (`id`, `username`, `email`, `password`, `role`, `created_at`, `last_login`) VALUES
(1, 'fixture_admin',   'admin.fixture@example.com',  'placeholder-not-a-password-hash', 'admin',   '2026-07-01 09:00:00', '2026-10-01 10:00:00'),
(2, 'fixture_editor',  'editor.fixture@example.com', 'placeholder-not-a-password-hash', 'editor',  '2026-07-01 09:05:00', NULL),
(3, 'asha_rao',        'Asha.Rao@Example.com',       'placeholder-not-a-password-hash', 'student', '2026-07-02 10:00:00', '2026-10-02 11:00:00'),
(4, 'bilal_khan',      'bilal.khan@example.com',     'placeholder-not-a-password-hash', 'student', '2026-07-02 10:05:00', NULL),
(5, 'no_record',       'nostudentrow@example.com',   'placeholder-not-a-password-hash', 'student', '2026-07-03 08:00:00', NULL),
(6, 'meera_editor',    'meera.iyer@example.com',     'placeholder-not-a-password-hash', 'editor',  '2026-07-03 08:30:00', NULL),
(7, 'dup_user',        'dup@example.com',            'placeholder-not-a-password-hash', 'student', '2026-07-03 09:00:00', NULL);

INSERT INTO `students` (`id`, `enrollment_no`, `name`, `email`, `course`, `gender`, `semester`, `status`, `created_at`) VALUES
(1, '26CS101', 'Asha Rao',      'asha.rao@example.com',     'Computer Science',      'Female', 3,    'Active',   '2026-07-02 10:00:00'),
(2, '26IT102', 'Bilal Khan',    ' bilal.khan@example.com ', 'Information Technology','Male',   5,    'Active',   '2026-07-02 10:05:00'),
(3, '26DS103', 'Meera Iyer',    'meera.iyer@example.com',   'Data Science',          'Female', 7,    'Active',   '2026-07-03 08:30:00'),
(4, '26WD104', 'Nikhil Sen',    'unmatched@example.com',    'Web Development',       'Male',   1,    'Active',   '2026-07-04 12:00:00'),
(5, '26CS105', 'Dup Spaced',    ' dup@example.com',         'Computer Science',      'Male',   3,    'Active',   '2026-07-05 12:00:00'),
(6, '26CS106', 'Dup Plain',     'dup@example.com',          'Computer Science',      'Female', 3,    'Active',   '2026-07-05 12:05:00'),
(7, NULL,      'Legacy Record', 'legacy@example.com',       'AI & Machine Learning', 'Female', NULL, 'Inactive', '2026-07-06 12:00:00');

INSERT INTO `events` (`id`, `title`, `event_date`, `location`, `description`, `category`, `poster`, `created_at`) VALUES
(1, 'Fixture Hackathon',  '2026-08-22', 'Innovation Lab', 'A fictional hackathon.', 'Hackathon',  'uploads/missing_poster.jpg', '2026-07-01 09:00:00'),
(2, 'Fixture Workshop',   '2026-09-10', 'Lab 3',          NULL,                     'Workshop',   NULL,                         '2026-07-01 09:10:00'),
(3, 'Fixture Conference', '2026-11-15', 'Auditorium',     'A fictional seminar.',   'Conference', NULL,                         '2026-07-01 09:20:00');

INSERT INTO `menu_items` (`id`, `title`, `link`, `min_role`, `icon`) VALUES
(1, 'Student Dashboard',        'dashboard.php',       'user',   'bi-speedometer2'),
(2, 'Attendance',               'attendance.php',      'editor', 'bi-check2-square'),
(3, 'Admin Management Console', 'admin_dashboard.php', 'admin',  'bi-shield-lock');

INSERT INTO `audit_logs` (`id`, `user_id`, `username`, `action`, `details`, `ip_address`, `user_agent`, `status`, `created_at`) VALUES
(1, NULL, 'unknown@example.com', 'LOGIN_FAILED', 'Failed login attempt', '127.0.0.1', 'fixture', 'FAILED',   '2026-10-01 09:00:00'),
(2, 1,    'fixture_admin',       'USER_LOGIN',   'User logged in',       '127.0.0.1', 'fixture', 'SUCCESS',  '2026-10-01 10:00:00'),
(3, 3,    'asha_rao',            'VIEW_DASHBOARD', 'Viewed dashboard',   '127.0.0.1', 'fixture', 'SUCCESS',  '2026-10-02 11:00:00'),
(4, 2,    'fixture_editor',      'ACCESS_DENIED', 'Editor opened admin_dashboard.php', '127.0.0.1', 'fixture', 'SECURITY_BLOCK', '2026-10-02 12:00:00');
