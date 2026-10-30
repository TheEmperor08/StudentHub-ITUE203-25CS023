-- =====================================================================================================
-- StudentHub – Practical 11: exported database studenthub_prac11 (student records for the CRUD application)
-- ITUE203, Shreyas 25CS023 – exported with mysqldump from XAMPP's MariaDB 10.4.32
--
-- Import: phpMyAdmin → Import → Choose File → studenthub_prac11.sql → Import
--     or: C:\xampp\mysql\bin\mysql.exe -u root < studenthub_prac11.sql
-- Only the database studenthub_prac11 is created and used. Importing again replaces the students table
-- (and its data) with the 24 seed records below.
--
-- All 24 students are fictional (example.com addresses); 22 are active and 2 are inactive (soft deleted).
-- =====================================================================================================

-- MariaDB dump 10.19  Distrib 10.4.32-MariaDB, for Win64 (AMD64)
--
-- Host: localhost    Database: studenthub_prac11
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
-- Current Database: `studenthub_prac11`
--

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `studenthub_prac11` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */;

USE `studenthub_prac11`;

--
-- Table structure for table `students`
--

DROP TABLE IF EXISTS `students`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `students` (
  `student_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `full_name` varchar(100) NOT NULL,
  `email` varchar(254) NOT NULL,
  `course` varchar(60) NOT NULL,
  `semester` tinyint(3) unsigned NOT NULL,
  `status` enum('active','inactive') NOT NULL DEFAULT 'active',
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `deleted_at` datetime DEFAULT NULL,
  PRIMARY KEY (`student_id`),
  UNIQUE KEY `uq_students_email` (`email`),
  KEY `idx_students_course` (`course`),
  KEY `idx_students_status` (`status`),
  KEY `idx_students_full_name` (`full_name`),
  CONSTRAINT `chk_students_semester` CHECK (`semester` between 1 and 8),
  CONSTRAINT `chk_students_soft_delete` CHECK (`status` = 'active' and `deleted_at` is null or `status` = 'inactive' and `deleted_at` is not null)
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `students`
--

LOCK TABLES `students` WRITE;
/*!40000 ALTER TABLE `students` DISABLE KEYS */;
INSERT INTO `students` VALUES (1,'Aarav Patel','aarav.patel@example.com','Computer Engineering',3,'active','2026-07-01 09:10:00','2026-07-01 09:10:00',NULL);
INSERT INTO `students` VALUES (2,'Diya Shah','diya.shah@example.com','Information Technology',3,'active','2026-07-01 09:15:00','2026-07-01 09:15:00',NULL);
INSERT INTO `students` VALUES (3,'Vihaan Mehta','vihaan.mehta@example.com','Computer Science',5,'active','2026-07-01 09:20:00','2026-07-01 09:20:00',NULL);
INSERT INTO `students` VALUES (4,'Ananya Desai','ananya.desai@example.com','Data Science',1,'active','2026-07-01 09:25:00','2026-07-01 09:25:00',NULL);
INSERT INTO `students` VALUES (5,'Kabir Joshi','kabir.joshi@example.com','Electronics & Communication',5,'active','2026-07-01 09:30:00','2026-07-01 09:30:00',NULL);
INSERT INTO `students` VALUES (6,'Isha Trivedi','isha.trivedi@example.com','Computer Engineering',7,'active','2026-07-02 10:00:00','2026-07-02 10:00:00',NULL);
INSERT INTO `students` VALUES (7,'Reyansh Bhatt','reyansh.bhatt@example.com','Information Technology',1,'active','2026-07-02 10:05:00','2026-07-02 10:05:00',NULL);
INSERT INTO `students` VALUES (8,'Saanvi Pandya','saanvi.pandya@example.com','Computer Science',3,'active','2026-07-02 10:10:00','2026-07-02 10:10:00',NULL);
INSERT INTO `students` VALUES (9,'Arjun Nair','arjun.nair@example.com','Data Science',5,'active','2026-07-02 10:15:00','2026-07-02 10:15:00',NULL);
INSERT INTO `students` VALUES (10,'Myra Kapoor','myra.kapoor@example.com','Electronics & Communication',3,'active','2026-07-02 10:20:00','2026-07-02 10:20:00',NULL);
INSERT INTO `students` VALUES (11,'Advik Rao','advik.rao@example.com','Computer Engineering',1,'active','2026-07-03 11:00:00','2026-07-03 11:00:00',NULL);
INSERT INTO `students` VALUES (12,'Kiara Iyer','kiara.iyer@example.com','Information Technology',5,'active','2026-07-03 11:05:00','2026-07-03 11:05:00',NULL);
INSERT INTO `students` VALUES (13,'Dhruv Chauhan','dhruv.chauhan@example.com','Computer Science',7,'active','2026-07-03 11:10:00','2026-07-03 11:10:00',NULL);
INSERT INTO `students` VALUES (14,'Aditi Kulkarni','aditi.kulkarni@example.com','Data Science',3,'active','2026-07-03 11:15:00','2026-07-03 11:15:00',NULL);
INSERT INTO `students` VALUES (15,'Rohan Verma','rohan.verma@example.com','Computer Engineering',5,'active','2026-07-03 11:20:00','2026-07-03 11:20:00',NULL);
INSERT INTO `students` VALUES (16,'Tara Menon','tara.menon@example.com','Information Technology',7,'active','2026-07-04 12:00:00','2026-07-04 12:00:00',NULL);
INSERT INTO `students` VALUES (17,'Ishaan Reddy','ishaan.reddy@example.com','Electronics & Communication',1,'active','2026-07-04 12:05:00','2026-07-04 12:05:00',NULL);
INSERT INTO `students` VALUES (18,'Navya Gupta','navya.gupta@example.com','Computer Science',1,'active','2026-07-04 12:10:00','2026-07-04 12:10:00',NULL);
INSERT INTO `students` VALUES (19,'Yash Solanki','yash.solanki@example.com','Data Science',7,'active','2026-07-04 12:15:00','2026-07-04 12:15:00',NULL);
INSERT INTO `students` VALUES (20,'Riya Parmar','riya.parmar@example.com','Computer Engineering',3,'active','2026-07-04 12:20:00','2026-07-04 12:20:00',NULL);
INSERT INTO `students` VALUES (21,'Krish Malhotra','krish.malhotra@example.com','Information Technology',3,'active','2026-07-05 09:00:00','2026-07-05 09:00:00',NULL);
INSERT INTO `students` VALUES (22,'Meera Pillai','meera.pillai@example.com','Computer Science',5,'active','2026-07-05 09:05:00','2026-07-05 09:05:00',NULL);
INSERT INTO `students` VALUES (23,'Om Thakkar','om.thakkar@example.com','Computer Engineering',7,'inactive','2026-07-05 09:10:00','2026-08-20 14:30:00','2026-08-20 14:30:00');
INSERT INTO `students` VALUES (24,'Pooja Sinha','pooja.sinha@example.com','Data Science',5,'inactive','2026-07-05 09:15:00','2026-09-02 16:45:00','2026-09-02 16:45:00');
/*!40000 ALTER TABLE `students` ENABLE KEYS */;
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
