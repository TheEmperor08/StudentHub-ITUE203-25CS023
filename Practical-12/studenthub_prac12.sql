-- =====================================================================================================
-- StudentHub – Practical 12: exported database studenthub_prac12 (events, event categories, administrators)
-- ITUE203, Shreyas 25CS023 – exported with mysqldump from XAMPP's MariaDB 10.4.32
--
-- Import: phpMyAdmin → Import → Choose File → studenthub_prac12.sql → Import
--     or: C:\xampp\mysql\bin\mysql.exe -u root < studenthub_prac12.sql
-- Only the database studenthub_prac12 is created and used. Importing again replaces its three tables with
-- the seed data below (6 categories, 12 events - 8 open and 4 closed - and 1 administrator).
--
-- All data is fictional. The 12 poster files named in poster_filename are in the uploads folder.
-- The administrator password is stored only as a password_hash() hash of a random password that is not
-- part of this repository; set your own with tools\set_admin_password.php (see README.md).
-- =====================================================================================================

-- MariaDB dump 10.19  Distrib 10.4.32-MariaDB, for Win64 (AMD64)
--
-- Host: localhost    Database: studenthub_prac12
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
-- Current Database: `studenthub_prac12`
--

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `studenthub_prac12` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */;

USE `studenthub_prac12`;

--
-- Table structure for table `admins`
--

DROP TABLE IF EXISTS `admins`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `admins` (
  `admin_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `full_name` varchar(100) NOT NULL,
  `email` varchar(254) NOT NULL,
  `password_hash` varchar(255) NOT NULL COMMENT 'password_hash() output, never the password',
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `last_login_at` datetime DEFAULT NULL,
  PRIMARY KEY (`admin_id`),
  UNIQUE KEY `uq_admins_email` (`email`),
  CONSTRAINT `chk_admins_password_hash` CHECK (`password_hash` like '$2y$%' or `password_hash` like '$argon2%')
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `admins`
--

LOCK TABLES `admins` WRITE;
/*!40000 ALTER TABLE `admins` DISABLE KEYS */;
INSERT INTO `admins` VALUES (1,'Demo Admin','admin.demo@example.com','$2y$10$NWu8jKd1cAVdSExycvffEuF8vhdVgmHfWkotSMAbikTyRBPDioNsS','2026-07-01 09:00:00',NULL);
/*!40000 ALTER TABLE `admins` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `event_categories`
--

DROP TABLE IF EXISTS `event_categories`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `event_categories` (
  `category_name` varchar(40) NOT NULL,
  `description` varchar(150) NOT NULL,
  PRIMARY KEY (`category_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `event_categories`
--

LOCK TABLES `event_categories` WRITE;
/*!40000 ALTER TABLE `event_categories` DISABLE KEYS */;
INSERT INTO `event_categories` VALUES ('Cultural','Music, dance, drama and art events');
INSERT INTO `event_categories` VALUES ('Hackathon','Team coding and innovation challenges');
INSERT INTO `event_categories` VALUES ('Seminar','Talks and guest lectures');
INSERT INTO `event_categories` VALUES ('Sports','Tournaments and sports meets');
INSERT INTO `event_categories` VALUES ('Technical','Technical exhibitions and contribution days');
INSERT INTO `event_categories` VALUES ('Workshop','Hands-on training sessions');
/*!40000 ALTER TABLE `event_categories` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `events`
--

DROP TABLE IF EXISTS `events`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `events` (
  `event_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `event_title` varchar(150) NOT NULL,
  `description` text NOT NULL,
  `category` varchar(40) NOT NULL,
  `event_date` date NOT NULL,
  `event_time` time NOT NULL,
  `venue` varchar(150) NOT NULL,
  `poster_filename` varchar(64) NOT NULL,
  `status` enum('open','closed') NOT NULL DEFAULT 'open',
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`event_id`),
  UNIQUE KEY `uq_events_poster_filename` (`poster_filename`),
  KEY `idx_events_category` (`category`),
  KEY `idx_events_status` (`status`),
  KEY `idx_events_date` (`event_date`,`event_time`),
  CONSTRAINT `fk_events_category` FOREIGN KEY (`category`) REFERENCES `event_categories` (`category_name`) ON UPDATE CASCADE,
  CONSTRAINT `chk_events_poster_filename` CHECK (`poster_filename` regexp '^[a-f0-9]{32}[.](jpg|png|webp)$'),
  CONSTRAINT `chk_events_title` CHECK (char_length(`event_title`) >= 3)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `events`
--

LOCK TABLES `events` WRITE;
/*!40000 ALTER TABLE `events` DISABLE KEYS */;
INSERT INTO `events` VALUES (1,'Code Sprint 2026','A 24-hour team coding challenge. Build a working prototype for a campus problem and present it to a jury of faculty members.','Hackathon','2026-11-14','09:00:00','Innovation Lab, Block A','1a023e38c1e411c26656d6a75e9ede04.jpg','open','2026-07-01 10:00:00','2026-07-01 10:00:00');
INSERT INTO `events` VALUES (2,'Web Frameworks Workshop','Hands-on session on building a CRUD application with PHP, MySQL and Bootstrap. Bring your laptop with XAMPP installed.','Workshop','2026-11-20','10:30:00','Computer Lab 3','189f38346771ce306b070701ed32a6d7.png','open','2026-07-02 10:00:00','2026-07-02 10:00:00');
INSERT INTO `events` VALUES (3,'AI in Healthcare Seminar','Guest lecture on how machine learning supports diagnosis and hospital planning, followed by a question-and-answer round.','Seminar','2026-11-25','14:00:00','Seminar Hall 1','b86f00edf3e60cab8d84782859f1bd6e.webp','open','2026-07-03 10:00:00','2026-07-03 10:00:00');
INSERT INTO `events` VALUES (4,'Annual Cultural Night','An evening of music, dance and drama performed by student clubs. Entry with a valid student ID card.','Cultural','2026-12-05','18:00:00','Open-Air Theatre','281eb187b837277bbffdf72095b33ba1.jpg','open','2026-07-04 10:00:00','2026-07-04 10:00:00');
INSERT INTO `events` VALUES (5,'Inter-Department Cricket Cup','Eight department teams compete in a one-day T10 cricket tournament. Team registration closes one week before the event.','Sports','2026-12-12','08:00:00','Main Sports Ground','fa6bfa70286a08f7959899224060da27.png','open','2026-07-05 10:00:00','2026-07-05 10:00:00');
INSERT INTO `events` VALUES (6,'Robotics Expo','Student teams exhibit line-following robots, drones and robotic arms. Visitors can vote for the most innovative project.','Technical','2027-01-09','11:00:00','Exhibition Hall','24aea1675b4723e44b23c7521aef17c9.webp','open','2026-07-06 10:00:00','2026-07-06 10:00:00');
INSERT INTO `events` VALUES (7,'Open Source Contribution Day','Mentors help first-time contributors make their first pull request to an open-source project.','Technical','2027-01-23','10:00:00','Library Seminar Room','942775d2f289ce18f77706a6c271c1cd.png','open','2026-07-07 10:00:00','2026-07-07 10:00:00');
INSERT INTO `events` VALUES (8,'Startup Pitch Hackathon','Teams develop a business idea and a demo in one day and pitch it to a panel of fictional investors.','Hackathon','2027-02-06','09:00:00','Incubation Centre','6cf39e54487c9daae01912c9926572de.jpg','open','2026-07-08 10:00:00','2026-07-08 10:00:00');
INSERT INTO `events` VALUES (9,'Cyber Security Awareness Talk','Talk on phishing, strong passwords and safe use of public Wi-Fi. Registration for this event is closed.','Seminar','2026-10-10','15:00:00','Auditorium','78911d469726744f9fbf4b7ff95bb7e2.jpg','closed','2026-07-09 10:00:00','2026-07-09 10:00:00');
INSERT INTO `events` VALUES (10,'Photography Walk','Early-morning photo walk around the campus with tips on composition and light. The event has already taken place.','Cultural','2026-09-19','07:00:00','Campus Garden Gate','f171c291e8a806104aa02c753fe78da4.png','closed','2026-07-10 10:00:00','2026-07-10 10:00:00');
INSERT INTO `events` VALUES (11,'Cloud Computing Bootcamp','Two-session bootcamp introducing virtual machines, containers and deployment basics. Registration is closed.','Workshop','2026-08-22','09:30:00','Computer Lab 1','92f36efd81e5c457f14928495b861af1.webp','closed','2026-07-11 10:00:00','2026-07-11 10:00:00');
INSERT INTO `events` VALUES (12,'Freshers\' Football League','Five-a-side football league for first-year students. The league has finished.','Sports','2026-08-08','16:00:00','Football Turf','166c180d722b0fa14692e2c975319c4e.webp','closed','2026-07-12 10:00:00','2026-07-12 10:00:00');
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
