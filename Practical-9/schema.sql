-- =====================================================================================================
-- StudentHub – Practical 9: Secure User Registration (ITUE203, Shreyas 25CS023)
-- Database: studenthub_prac9 (isolated – no other database is created or changed by this file)
--
-- Import: phpMyAdmin → Import → Choose File → schema.sql → Import
--     or: C:\xampp\mysql\bin\mysql.exe -u root < schema.sql
--
-- Safe to import again: the tables are created only if they do not exist yet and the sample rows are
-- added only if they are missing, so users registered through the form are kept.
--
-- Sample data is fictional (example.com addresses). The three password hashes were made with
-- password_hash() from random passwords that were thrown away, so nobody knows a password for these
-- demo accounts. No plaintext password appears anywhere in this project.
-- =====================================================================================================

SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS studenthub_prac9 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE studenthub_prac9;

-- -----------------------------------------------------------------------------------------------------
-- users: one row per registered account
-- -----------------------------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id       INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    full_name     VARCHAR(100)  NOT NULL,
    username      VARCHAR(30)   NOT NULL,
    email         VARCHAR(254)  NOT NULL,
    password_hash VARCHAR(255)  NOT NULL,            -- output of password_hash(), never the password itself
    role          ENUM('student', 'admin') NOT NULL DEFAULT 'student',
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    UNIQUE KEY uq_users_username (username),         -- the collation ignores case: Asha_1 = asha_1
    UNIQUE KEY uq_users_email (email),
    CONSTRAINT chk_users_username CHECK (username REGEXP '^[A-Za-z][A-Za-z0-9_]{2,29}$'),
    CONSTRAINT chk_users_email CHECK (email LIKE '%_@_%._%'),
    -- the database itself refuses a value that does not look like a bcrypt or Argon2 hash
    CONSTRAINT chk_users_password_hash CHECK ((password_hash LIKE '$2y$%' OR password_hash LIKE '$argon2%')
                                              AND CHAR_LENGTH(password_hash) >= 60)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------------------------------
-- audit_logs: one row per successful registration (advanced extension); never contains passwords or hashes
-- -----------------------------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
    audit_id   INT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id    INT UNSIGNED NOT NULL,
    action     VARCHAR(50)  NOT NULL,
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (audit_id),
    KEY idx_audit_logs_user (user_id),
    -- RESTRICT: a user who has audit entries cannot be deleted by accident, so the history is kept
    CONSTRAINT fk_audit_logs_user FOREIGN KEY (user_id) REFERENCES users (user_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------------------------------
-- Fictional sample accounts (used to demonstrate the duplicate email and duplicate username checks)
-- -----------------------------------------------------------------------------------------------------
-- Only rows whose username and email are not in the table yet are added (a re-import changes nothing).
INSERT INTO users (full_name, username, email, password_hash, role)
SELECT s.full_name, s.username, s.email, s.password_hash, s.role
FROM (
    SELECT 'Asha Demo' AS full_name, 'demo_asha' AS username, 'asha.demo@example.com' AS email,
           '$2y$10$adduyE7sugKzOGIikxjzpOD2h4.DA1ojMHy5RA1IP3xS5QIAdIHxO' AS password_hash, 'student' AS role
    UNION ALL
    SELECT 'Kabir Sample', 'demo_kabir', 'kabir.sample@example.com',
           '$2y$10$zsn.rCDdKbGQy7/fnThnje9C4Po3M2oDqCGQiiyuJbbzX/zHR0vTC', 'student'
    UNION ALL
    SELECT 'Meera Test', 'demo_meera', 'meera.test@example.com',
           '$2y$10$aSxkzen/sJ6DvKpMCZrBxuv6Dcqpxm0EZTMvtCJmcSXaxGP1JDNou', 'admin'
) AS s
WHERE NOT EXISTS (SELECT 1 FROM users AS u WHERE u.username = s.username OR u.email = s.email);

INSERT INTO audit_logs (user_id, action)
SELECT u.user_id, 'USER_REGISTERED'
FROM users AS u
WHERE u.username IN ('demo_asha', 'demo_kabir', 'demo_meera')
  AND NOT EXISTS (SELECT 1 FROM audit_logs AS a WHERE a.user_id = u.user_id AND a.action = 'USER_REGISTERED');
