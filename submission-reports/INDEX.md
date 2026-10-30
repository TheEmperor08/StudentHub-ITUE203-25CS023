# Corrected ITUE203 practical reports – index

These files are the corrected submissions for manual upload after checking. They describe each practical as part of the
one integrated StudentHub portal (`studenthub/`, database `studenthub_db`). The original reports are **not** changed and stay
in their `Practical-N/` folders. Nothing has been uploaded to Microsoft Teams automatically.

| Practical | Corrected report (DOCX / PDF) | Supersedes | Why it was replaced |
|---|---|---|---|
| 5 | `PRAC_5_ITUE203_25CS023_corrected.docx` / `PRAC_5_ITUE203_25CS023_corrected.pdf` | `Practical-5/PRAC_5_ITUE203_25CS023.docx` | The original described the standalone page Practical-5/register.html; the validation now runs on the portal's real registration page studenthub/register.php (the Canvas CAPTCHA was not carried over). |
| 6 | `PRAC_6_ITUE203_25CS023_corrected.docx` / `PRAC_6_ITUE203_25CS023_corrected.pdf` | `Practical-6/PRAC_6_ITUE203_25CS023.docx` | The original described the standalone Practical-6/directory.html served by Python; the JSON datasets are now rendered on the portal's Campus Data Explorer page (studenthub/data_explorer.php). |
| 7 | `PRAC_7_ITUE203_25CS023_corrected.docx` / `PRAC_7_ITUE203_25CS023_corrected.pdf` | `Practical-7/PRAC_7_ITUE203_25CS023.docx` | The original described the standalone Practical-7 app with a JSON file; the portal's Help & Contact form now stores validated inquiries in the inquiries table, with an Admin Console view. |
| 8 | `PRAC_8_ITUE203_25CS023_corrected.docx` / `PRAC_8_ITUE203_25CS023_corrected.pdf` | `Practical-8/PRAC_8_ITUE203_25CS023.docx` | The original describes a standalone database studenthub_prac8 with PDO and stored procedures; the Practical 8 design is now part of the one portal database studenthub_db (migration 001). |
| 9 | `PRAC_9_ITUE203_25CS023_corrected.docx` / `PRAC_9_ITUE203_25CS023_corrected.pdf` | `Practical-9/PRAC_9_ITUE203_25CS023.docx` | The original describes a standalone registration page with its own database studenthub_prac9; registration now runs in the integrated portal and creates the account together with its linked student record. |
| 10 | `PRAC_10_ITUE203_25CS023_corrected.docx` / `PRAC_10_ITUE203_25CS023_corrected.pdf` | `Practical-10/PRAC_10_ITUE203_25CS023.docx` | The original describes a standalone login with its own database studenthub_prac10 and two dashboards; login, sessions and RBAC are now the one authentication system of the integrated portal. |
| 11 | `PRAC_11_ITUE203_25CS023_corrected.docx` / `PRAC_11_ITUE203_25CS023_corrected.pdf` | `Practical-11/PRAC_11_ITUE203_25CS023.docx` | The original describes a standalone app with its own database studenthub_prac11 and no login; Practical 11 now runs inside the integrated portal (Admin Console → Student Records). |
| 12 | `PRAC_12_ITUE203_25CS023_corrected.docx` / `PRAC_12_ITUE203_25CS023_corrected.pdf` | `Practical-12/PRAC_12_ITUE203_25CS023.docx` | The original describes a standalone app with its own database studenthub_prac12 and its own admin login; Practical 12 now runs inside the integrated portal (Admin Console → Campus Events, Campus Events page). |
| 13 | `PRAC_13_ITUE203_25CS023_corrected.docx` / `PRAC_13_ITUE203_25CS023_corrected.pdf` | `Practical-13/PRAC_13_ITUE203_25CS023.docx` | The original describes a standalone page and api.php with their own database studenthub_prac13; Practical 13 now runs inside the integrated portal (Event Finder + api/events.php, portal login and roles). |
| 14 | `PRAC_14_ITUE203_25CS023.docx` / `PRAC_14_ITUE203_25CS023.pdf` | — (no earlier report) | new report – no earlier Word/PDF report existed |
| 15 | `PRAC_15_ITUE203_25CS023.docx` / `PRAC_15_ITUE203_25CS023.pdf` | — (no earlier report) | new report – no earlier Word/PDF report existed |

Practicals 1–4 were not rewritten: their reports describe planning, static pages, layout and DOM features that are
unchanged in the integrated portal (see TEST_REPORT.md, section 12).
