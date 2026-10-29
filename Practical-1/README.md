<div align="center">
  <h1>🎓 Practical 1</h1>
  <h3>Initiation & Planning of StudentHub Portal</h3>
</div>

---

### 👨‍🎓 Student Information
- **Name:** Shreyas
- **ID:** 25CS023
- **Course:** ITUE203 - WEB DEVELOPMENT FRAMEWORKS
- **Year:** 2026-27

---

### 🎯 Objective
> To initiate the development of the StudentHub Portal by analyzing project requirements, identifying user roles and modules, designing the sitemap and low-fidelity wireframes, organizing the project folder structure, and setting up a GitHub repository for future development.

---

### 📝 Problem Statement
Initiate the semester-long StudentHub portal by identifying the problem scope, user roles, key modules, navigation flow, and minimum 10 pages. Create a sitemap, low-fidelity wireframe, project folder structure, README file, and GitHub repository.

---

### 👥 User Roles
1. **Student:** Access dashboard, view timetable, attendance, marks, events, and manage profile. *(implemented)*
2. **Faculty:** Manage courses, upload assignments, update attendance, and check results. *(planned – not implemented in the main application)*
3. **Admin:** Manage users, student records, events and audit logs from the Admin Console. *(implemented)*

---

### 🗺️ Sitemap & Navigation Flow
The sitemap reflects the application as implemented in `studenthub/` (15 screens + logout; requirement: minimum 10 pages).

![StudentHub sitemap](sitemap.png)

- **Public:** Home ➔ Login | Register | Contact Us
- **Student area (login required, sidebar navigation):**
  - Overview: Dashboard, My Profile
  - Academics: Courses, Attendance, Assignments, Results, Achievements
  - Campus: Notices, Directory, Help & Contact
  - Account: Home Portal, Logout
- **Admin only:** Admin Console tabs – Overview, Students (CSV export), Events (poster upload), Users, Audit Logs
- **Access control:** non-admins opening the Admin Console see the 403 page.

---

### 🧩 Low-Fidelity Wireframes
Greyscale wireframes of the key screens (layout only – these are not screenshots).

| Screen | File |
|---|---|
| Student dashboard (desktop) | [`wireframe-1-dashboard-desktop.png`](wireframe-1-dashboard-desktop.png) |
| Home page and login (desktop) | [`wireframe-2-home-login-desktop.png`](wireframe-2-home-login-desktop.png) |
| Mobile: dashboard, navigation drawer, login | [`wireframe-3-mobile.png`](wireframe-3-mobile.png) |

![Dashboard wireframe](wireframe-1-dashboard-desktop.png)

---

### 📂 Project Structure
```text
StudentHub/
├── studenthub/        # Main application (PHP + MySQL)
├── Practical-1/       # This planning practical: sitemap + wireframes
├── Practical-2 … 15/  # Practical-wise deliverables
├── database/          # Safe demo SQL for studenthub_db
├── tools/             # CLI helper for creating local demo accounts
├── README.md
└── TEST_REPORT.md
```

```text
Practical-1/
├── README.md
├── sitemap.svg / sitemap.png
├── wireframe-1-dashboard-desktop.svg / .png
├── wireframe-2-home-login-desktop.svg / .png
├── wireframe-3-mobile.svg / .png
└── source/build_diagrams.py   # regenerates all diagrams: python Practical-1/source/build_diagrams.py
```
SVG files are the editable vector originals; the PNG files are for inserting into the Word report.

---

### 🔗 GitHub Repository
**Repository:** [https://github.com/TheEmperor08/StudentHub-ITUE203-25CS023](https://github.com/TheEmperor08/StudentHub-ITUE203-25CS023)

```bash
git clone https://github.com/TheEmperor08/StudentHub-ITUE203-25CS023.git
```
