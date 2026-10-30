"""StudentHub – Practical 11: browser test + screenshots 1-11 (optional; needs  pip install playwright).

Drives the installed Microsoft Edge (headless, via Playwright) through the real application on 127.0.0.1:8611
(start-server.bat), checks every step (13 checks) and saves the screenshots, then downloads the CSV export.
It ADDS, EDITS and DEACTIVATES students in studenthub_prac11, so re-import studenthub_prac11.sql afterwards.
Run on freshly imported data:  python tests\\browser_screenshots.py screenshots <download folder>
csv-export.png and csv-opened-in-excel.png were captured from a normal Edge window and Microsoft Excel (see README).
"""
import pathlib, sys, time
from playwright.sync_api import sync_playwright

SHOTS, DL = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
SHOTS.mkdir(parents=True, exist_ok=True)
DL.mkdir(parents=True, exist_ok=True)
BASE = "http://127.0.0.1:8611/"
results = []


def check(name, ok):
    results.append((name, ok))
    print(("PASS  " if ok else "FAIL  ") + name)


with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    ctx = browser.new_context(viewport={"width": 1280, "height": 800}, accept_downloads=True)
    page = ctx.new_page()
    errors = []
    page.on("console", lambda m: errors.append(page.url + " :: " + m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))

    def shot(name, full=True, clip=None):
        page.screenshot(path=str(SHOTS / name), full_page=full and clip is None, clip=clip)

    # 1 student list
    page.goto(BASE + "index.php")
    check("list: 10 rows on page 1 of 24", page.locator("tbody tr").count() == 10 and "of 24 students" in page.inner_text("#result-summary"))
    shot("students-list.png")

    # 6 search
    page.fill("#q", "sha")
    page.click("button:has-text('Search')")
    names = page.locator("td[data-label='Full name']").all_inner_texts()
    check("search 'sha' -> Diya Shah, Isha Trivedi, Ishaan Reddy", sorted(names) == ["Diya Shah", "Isha Trivedi", "Ishaan Reddy"])
    shot("search-result.png")

    # 7 course filter
    page.click("a:has-text('Reset')")
    page.select_option("#course", "Data Science")
    page.click("button:has-text('Search')")
    courses = set(page.locator("td[data-label='Course']").all_inner_texts())
    check("course filter Data Science -> only Data Science", courses == {"Data Science"} and "course=Data+Science" in page.url)
    shot("course-filter.png")

    # frontend validation: an empty form is not sent
    page.goto(BASE + "add.php")
    page.click("button:has-text('Add student')")
    check("browser validation stops an empty form (still on add.php, :invalid fields)",
          page.url.endswith("add.php") and page.locator("input:invalid").count() == 2)

    # 2 add form, 3 successful add
    page.fill("#full_name", "Neha Raval")
    page.fill("#email", "neha.raval@example.com")
    page.select_option("#course", "Information Technology")
    page.select_option("#semester", "3")
    shot("add-student.png")
    page.click("button:has-text('Add student')")
    page.wait_for_url(BASE + "index.php")
    first = page.locator("tbody tr").first
    check("added: success message and Neha Raval first, highlighted",
          "was added successfully" in page.inner_text(".alert-success") and "Neha Raval" in first.inner_text()
          and "row-highlight" in first.get_attribute("class"))
    shot("successful-add.png")

    # 4 edit form, 5 successful update (Diya Shah: Information Technology sem 3 -> Computer Science sem 4)
    time.sleep(1.1)
    page.goto(BASE + "edit.php?id=2")
    check("edit form filled from MySQL", page.input_value("#full_name") == "Diya Shah" and page.input_value("#course") == "Information Technology")
    page.select_option("#course", "Computer Science")
    page.select_option("#semester", "4")
    shot("edit-student.png")
    page.click("button:has-text('Save changes')")
    page.wait_for_url(BASE + "index.php")
    first = page.locator("tbody tr").first
    check("updated: message and Diya Shah first with Computer Science / 4",
          "was updated successfully" in page.inner_text(".alert-success") and "Computer Science" in first.inner_text()
          and first.locator("td[data-label='Semester']").inner_text() == "4")
    shot("successful-update.png")

    # 8 confirmation, 9 soft delete (Rohan Verma, ID 15)
    time.sleep(1.1)
    page.goto(BASE + "index.php?q=Rohan")
    page.click("a:has-text('Deactivate')")
    check("confirmation page for Rohan Verma", page.url.endswith("delete.php?id=15") and "Are you sure" in page.inner_text(".alert-warning"))
    shot("delete-confirmation.png")
    page.click("button:has-text('Yes, deactivate student')")
    page.wait_for_url(BASE + "index.php")
    first = page.locator("tbody tr").first
    check("soft deleted: message, Rohan Verma first with Inactive badge",
          "was deactivated" in page.inner_text(".alert-success") and "Rohan Verma" in first.inner_text()
          and first.locator(".badge").inner_text() == "Inactive")
    shot("successful-soft-delete.png")

    # 10 success message close-up (a second, separate add)
    time.sleep(1.1)
    page.goto(BASE + "add.php")
    page.fill("#full_name", "Farhan Qureshi")
    page.fill("#email", "farhan.qureshi@example.com")
    page.select_option("#course", "Computer Engineering")
    page.select_option("#semester", "1")
    page.click("button:has-text('Add student')")
    page.wait_for_url(BASE + "index.php")
    check("second add: success message", "Student “Farhan Qureshi” was added successfully" in page.inner_text(".alert-success"))
    shot("success-message.png", clip={"x": 0, "y": 0, "width": 1280, "height": 560})

    # 11 error message: duplicate email (passes browser validation, refused by the server)
    page.goto(BASE + "add.php")
    page.fill("#full_name", "Diya Sharma")
    page.fill("#email", "diya.shah@example.com")
    page.select_option("#course", "Data Science")
    page.select_option("#semester", "2")
    page.click("button:has-text('Add student')")
    check("duplicate email: error summary and field error",
          "was not added" in page.inner_text(".alert-error") and "already registered" in page.inner_text("#email-error"))
    shot("error-message.png")

    # 12 CSV export: click the button on the list, then show the download in Edge's downloads page
    page.goto(BASE + "index.php")
    with page.expect_download() as info:
        page.click("a:has-text('Export CSV')")
    download = info.value
    target = DL / download.suggested_filename
    download.save_as(str(target))
    check("download " + download.suggested_filename, target.stat().st_size > 1000)
    print("DOWNLOADED", target)
    unexpected = [x for x in errors if "status of 422" not in x]
    check("no JavaScript errors (only the intended HTTP 422 of the rejected form is logged)", not unexpected and len(errors) == 1)
    print(*errors, sep=chr(10))
    browser.close()

print(f"browser checks: {sum(ok for _, ok in results)} passed, {sum(not ok for _, ok in results)} failed")
