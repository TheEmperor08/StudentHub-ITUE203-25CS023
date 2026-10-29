-- schema.sql
-- Database Schema for Practical 9: User Registration System
-- The users table matches Practicals 10 and 14, which share the user_registration database.

CREATE DATABASE IF NOT EXISTS user_registration CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE user_registration;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    role VARCHAR(20) NOT NULL DEFAULT 'student',
    last_login DATETIME NULL,
    remember_token_hash VARCHAR(255) NULL,
    remember_token_expiry DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
