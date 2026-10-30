-- =====================================================================================================
-- StudentHub – Practical 10: exported database studenthub_prac10 (users and their roles)
-- ITUE203, Shreyas 25CS023 – exported with mysqldump from XAMPP's MariaDB 10.4.32
--
-- Import: phpMyAdmin → Import → Choose File → user_registration.sql → Import
--     or: C:\xampp\mysql\bin\mysql.exe -u root < user_registration.sql
-- Only the database studenthub_prac10 is created and used. Importing again replaces the users table.
--
-- The accounts are fictional (example.com). Passwords are stored only as password_hash() hashes; the
-- demo passwords are not part of this repository. Set your own with tools\set_password.php (see README.md).
-- =====================================================================================================

-- MariaDB dump 10.19  Distrib 10.4.32-MariaDB, for Win64 (AMD64)
--
-- Host: localhost    Database: studenthub_prac10
-- ------------------------------------------------------
-- Server version	10.4.32-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Current Database: `studenthub_prac10`
--

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `studenthub_prac10` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */;

USE `studenthub_prac10`;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `users` (
  `user_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `email` varchar(254) NOT NULL,
  `password_hash` varchar(255) NOT NULL COMMENT 'password_hash() output, never the password',
  `role` enum('admin','student') NOT NULL DEFAULT 'student',
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `uq_users_email` (`email`),
  KEY `idx_users_role` (`role`),
  CONSTRAINT `chk_users_email` CHECK (`email` like '%_@_%._%'),
  CONSTRAINT `chk_users_password_hash` CHECK ((`password_hash` like '$2y$%' or `password_hash` like '$argon2%') and char_length(`password_hash`) >= 60)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'Demo Admin','admin.demo@example.com','$2y$10$hTjxLKPF3BR.xrpSYB2mD.h2DVTljmNC1Kxi1OOL5lxFweW9NF/5a','admin','2026-10-30 17:04:06'),(2,'Demo Student','student.demo@example.com','$2y$10$uNEHuuNadpK2OSmyb1dYvO0KgN7tjixiI6k2QjeS8LgfrKwJtjU8a','student','2026-10-30 17:04:06'),(3,'Demo Student Two','student2.demo@example.com','$2y$10$HjH2Cr2uH8niycsyZ4nOdu.hvYaoU4CPT..EXVnshn/leT.Iozgwq','student','2026-10-30 17:04:06');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed
