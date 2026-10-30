-- =====================================================================================================
-- StudentHub – Practical 13: schema and seed data of studenthub_prac13 (events for the AJAX/Fetch CRUD app)
-- ITUE203, Shreyas 25CS023 – exported with mysqldump from XAMPP's MariaDB 10.4.32
--
-- Import: phpMyAdmin → Import → Choose File → schema.sql → Import
--     or: C:\xampp\mysql\bin\mysql.exe -u root < schema.sql
-- Only the database studenthub_prac13 is created and used. Importing again replaces the events table with
-- the 12 fictional seed events below (9 open, 3 closed).
-- =====================================================================================================

-- MariaDB dump 10.19  Distrib 10.4.32-MariaDB, for Win64 (AMD64)
--
-- Host: localhost    Database: studenthub_prac13
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
-- Current Database: `studenthub_prac13`
--

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `studenthub_prac13` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */;

USE `studenthub_prac13`;

--
-- Table structure for table `events`
--

DROP TABLE IF EXISTS `events`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `events` (
  `event_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `title` varchar(120) NOT NULL,
  `description` varchar(1000) NOT NULL,
  `category` varchar(30) NOT NULL,
  `event_date` date NOT NULL,
  `start_time` time NOT NULL,
  `venue` varchar(120) NOT NULL,
  `capacity` smallint(5) unsigned NOT NULL,
  `status` enum('open','closed') NOT NULL DEFAULT 'open',
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`event_id`),
  KEY `idx_events_date` (`event_date`,`start_time`),
  KEY `idx_events_category` (`category`),
  KEY `idx_events_title` (`title`),
  CONSTRAINT `chk_events_category` CHECK (`category` in ('Cultural','Hackathon','Seminar','Sports','Technical','Workshop')),
  CONSTRAINT `chk_events_capacity` CHECK (`capacity` between 1 and 5000),
  CONSTRAINT `chk_events_title` CHECK (char_length(`title`) >= 3)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `events`
--

LOCK TABLES `events` WRITE;
/*!40000 ALTER TABLE `events` DISABLE KEYS */;
INSERT INTO `events` VALUES (1,'Code Sprint 2026','A 24-hour team coding challenge to build a prototype for a campus problem.','Hackathon','2026-11-14','09:00:00','Innovation Lab, Block A',120,'open','2026-07-01 10:00:00','2026-07-01 10:00:00');
INSERT INTO `events` VALUES (2,'Web Frameworks Workshop','Hands-on session on building a CRUD application with PHP, MySQL and JavaScript.','Workshop','2026-11-20','10:30:00','Computer Lab 3',60,'open','2026-07-02 10:00:00','2026-07-02 10:00:00');
INSERT INTO `events` VALUES (3,'AI in Healthcare Seminar','Guest lecture on machine learning for diagnosis and hospital planning.','Seminar','2026-11-25','14:00:00','Seminar Hall 1',200,'open','2026-07-03 10:00:00','2026-07-03 10:00:00');
INSERT INTO `events` VALUES (4,'Annual Cultural Night','Music, dance and drama performed by student clubs.','Cultural','2026-12-05','18:00:00','Open-Air Theatre',800,'open','2026-07-04 10:00:00','2026-07-04 10:00:00');
INSERT INTO `events` VALUES (5,'Inter-Department Cricket Cup','Eight department teams in a one-day T10 tournament.','Sports','2026-12-12','08:00:00','Main Sports Ground',300,'open','2026-07-05 10:00:00','2026-07-05 10:00:00');
INSERT INTO `events` VALUES (6,'Robotics Expo','Line-following robots, drones and robotic arms built by student teams.','Technical','2027-01-09','11:00:00','Exhibition Hall',400,'open','2026-07-06 10:00:00','2026-07-06 10:00:00');
INSERT INTO `events` VALUES (7,'Open Source Contribution Day','Mentors help first-time contributors make their first pull request.','Technical','2027-01-23','10:00:00','Library Seminar Room',50,'open','2026-07-07 10:00:00','2026-07-07 10:00:00');
INSERT INTO `events` VALUES (8,'Startup Pitch Hackathon','Teams build a business idea and a demo in one day and pitch it to a panel.','Hackathon','2027-02-06','09:00:00','Incubation Centre',90,'open','2026-07-08 10:00:00','2026-07-08 10:00:00');
INSERT INTO `events` VALUES (9,'JavaScript Fetch API Bootcamp','Asynchronous JavaScript, promises and the Fetch API with JSON back ends.','Workshop','2027-02-13','09:30:00','Computer Lab 1',45,'open','2026-07-09 10:00:00','2026-07-09 10:00:00');
INSERT INTO `events` VALUES (10,'Cyber Security Awareness Talk','Phishing, strong passwords and safe use of public Wi-Fi.','Seminar','2026-10-10','15:00:00','Auditorium',250,'closed','2026-07-10 10:00:00','2026-07-10 10:00:00');
INSERT INTO `events` VALUES (11,'Photography Walk','Early-morning photo walk around the campus with composition tips.','Cultural','2026-09-19','07:00:00','Campus Garden Gate',30,'closed','2026-07-11 10:00:00','2026-07-11 10:00:00');
INSERT INTO `events` VALUES (12,'Freshers Football League','Five-a-side football league for first-year students.','Sports','2026-08-08','16:00:00','Football Turf',100,'closed','2026-07-12 10:00:00','2026-07-12 10:00:00');
/*!40000 ALTER TABLE `events` ENABLE KEYS */;
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
