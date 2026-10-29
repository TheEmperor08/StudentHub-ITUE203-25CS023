<div align="center">
  <h1>🎓 Practical 7</h1>
  <h3>PHP Form with POST, Validation & File Storage</h3>
</div>

---

### 👨‍🎓 Student Information
- **Name:** Shreyas
- **ID:** 25CS023
- **Course:** ITUE203 - WEB DEVELOPMENT FRAMEWORKS
- **Year:** 2026-27

---

### 🎯 Objective
> Create a PHP contact/registration form using POST method, validate and sanitize input, and store data securely in a CSV file.

---

### 🚀 Main Features
- ✅ **PHP Form Handling: Using POST method securely via api/contact.php.**
- ✅ **Sanitization & Validation: htmlspecialchars, filtering, and empty checks.**
- ✅ **CSV File Storage: Using fputcsv() to store records.**
- ✅ **Concurrency handling: Using flock() with LOCK_EX for safe writing.**
- ✅ **URL Parameters: Success/Error redirects with query parameters.**

---

### 📂 Project Structure
```text
Practical-7/
├── api
│   └── contact.php
├── assets
│   └── css
│       └── global.css
├── contact.html
└── private
    └── contacts.csv
```

---

### 💻 How to Run
1. Start a local server from the repository root (`php -S localhost:8000`) and open `http://localhost:8000/Practical-7/contact.html` (the form posts to `api/contact.php`, which needs PHP). Submissions are written to `private/contacts.csv`, which is git-ignored and blocked by `private/.htaccess` on Apache.
