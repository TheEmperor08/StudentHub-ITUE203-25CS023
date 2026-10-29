<div align="center">
  <h1>🎓 Practical 8</h1>
  <h3>Database Connection with PDO & Prepared Statements</h3>
</div>

---

### 👨‍🎓 Student Information
- **Name:** Shreyas
- **ID:** 25CS023
- **Course:** ITUE203 - WEB DEVELOPMENT FRAMEWORKS
- **Year:** 2026-27

---

### 🎯 Objective
> To create a database connection using PHP PDO, design relational 3NF tables (students, events, registrations), execute operations using Prepared Statements to prevent SQL injection vulnerabilities, and render dynamic records in PHP.

---

### 🚀 Main Features
- ✅ **Database Connection:** Established secure PHP PDO connection with try-catch error handling in `db.php`.
- ✅ **Prepared Statements:** Safely fetching and inserting records to prevent SQL injection in `test_connection.php` and `insert.php`.
- ✅ **3NF Relational Schema:** Third Normal Form database schema in `schema.sql` with Primary and Foreign key constraints.
- ✅ **Dynamic PHP Rendering:** Outputting student list and event registrations dynamically in `students.php` and `test_connection.php`.

---

### 📂 Project Structure
```text
Practical-8/
├── db.php
├── insert.php
├── schema.sql
├── students.php
└── test_connection.php
```

---

### 💻 How to Run
1. Import the MySQL/MariaDB schema (creates `practical8_db` with demo data):
   ```bash
   mysql -u root < Practical-8/schema.sql
   ```
2. Start the PHP development server from the repository root:
   ```bash
   php -S localhost:8000
   ```
3. Open the following URLs in your browser:
   - Database Connection: `http://localhost:8000/Practical-8/db.php`
   - Student List: `http://localhost:8000/Practical-8/students.php`
   - Data Retrieval & JOIN (with `?branch=CSE` filter): `http://localhost:8000/Practical-8/test_connection.php`
   - Insert Record (validated form): `http://localhost:8000/Practical-8/insert.php`
