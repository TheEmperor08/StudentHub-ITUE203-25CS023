-- Practical 10: user_registration database (MariaDB 10.4+ / MySQL 8 compatible)
-- Adapted from the original MySQL 8 dump: utf8mb4_0900_ai_ci collation, GTID and ENCRYPTION
-- statements removed, and no user rows or password hashes are included.
-- Import: mysql -u root < Practical-10/user_registration.sql
-- Then create demo accounts: php tools/create_demo_user.php --db=user_registration ...

CREATE DATABASE IF NOT EXISTS `user_registration` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `user_registration`;

CREATE TABLE IF NOT EXISTS `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `role` varchar(20) NOT NULL DEFAULT 'student',
  `last_login` datetime DEFAULT NULL,
  `remember_token_hash` varchar(255) DEFAULT NULL,
  `remember_token_expiry` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
