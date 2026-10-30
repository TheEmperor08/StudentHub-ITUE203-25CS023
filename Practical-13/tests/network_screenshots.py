"""StudentHub – Practical 13: captures the three Network screenshots from the REAL Microsoft Edge DevTools (optional;
needs  pip install playwright websocket-client).

1. A headless Edge opens the app (http://127.0.0.1:8613/index.html, start-server.bat) with remote debugging on port 9335.
2. Edge's own DevTools front end (http://127.0.0.1:9335/devtools/inspector.html) is opened in a second headless Edge and
   connected to that page, so it records the page's genuine network traffic (with a live screencast of the page).
3. The app's real buttons are pressed through the DevTools protocol, so every request is a genuine fetch() from script.js.
4. Each request is opened with DevTools' "Open in Sources panel" (shows the real JSON response) while the Network panel in
   the drawer shows method, status code and headers. Nothing on the user's desktop is used.
It ADDS, EDITS and DELETES an event, so re-import schema.sql afterwards.
Usage:  python tests\network_screenshots.py <screenshots folder>
"""
import json, os, re, subprocess, sys, tempfile, time, urllib.request
import websocket
from playwright.sync_api import sync_playwright

OUT = sys.argv[1]
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
profile = tempfile.mkdtemp(prefix="p13-edge-")
target_browser = subprocess.Popen([EDGE, "--headless=new", f"--user-data-dir={profile}", "--remote-debugging-port=9335",
                                   "--window-size=1280,800", "--no-first-run", "http://127.0.0.1:8613/index.html"])
time.sleep(4)

def target():
    return next(t for t in json.load(urllib.request.urlopen("http://127.0.0.1:9335/json")) if t["type"] == "page" and "8613" in t["url"])

def cdp(method, params=None):
    ws = websocket.create_connection(target()["webSocketDebuggerUrl"], timeout=30, suppress_origin=True)
    ws.send(json.dumps({"id": 1, "method": method, "params": params or {}}))
    while True:
        m = json.loads(ws.recv())
        if m.get("id") == 1:
            ws.close()
            return m

def page_js(expression):
    """Runs JavaScript in the app page (used to press its real buttons)."""
    r = cdp("Runtime.evaluate", {"expression": expression, "awaitPromise": True, "returnByValue": True})
    return r.get("result", {}).get("result", {}).get("value")

def command(dt, text, item):
    """DevTools Command Menu (Ctrl+Shift+P); item is a regex for the exact entry."""
    import re
    dt.keyboard.press("Control+Shift+P"); dt.wait_for_timeout(700)
    dt.keyboard.type(text); dt.wait_for_timeout(900)
    dt.locator(".filtered-list-widget-item", has_text=re.compile(item)).first.click()
    dt.wait_for_timeout(1200)

def open_devtools(p, width=1800, height=1050, split_x=760):
    b = p.chromium.launch(channel="msedge", headless=True)
    dt = b.new_page(viewport={"width": width, "height": height})
    dt.goto("http://127.0.0.1:9335/devtools/inspector.html?ws=127.0.0.1:9335/devtools/page/" + target()["id"])
    dt.wait_for_timeout(3500)
    command(dt, "Network", r"^Show Network\s*Panel")
    close = dt.locator('[aria-label="Close drawer"]')
    if close.count() and close.first.is_visible():
        close.first.click(); dt.wait_for_timeout(500)
    # drag the splitter between the page screencast and DevTools to the left (inside this headless page)
    box = dt.locator(".tabbed-pane-header").first.bounding_box()
    dt.mouse.move(box["x"] - 3, 400); dt.mouse.down(); dt.mouse.move(split_x, 400, steps=15); dt.mouse.up()
    dt.wait_for_timeout(800)
    cdp("Page.bringToFront")
    cdp("Emulation.setFocusEmulationEnabled", {"enabled": True})
    return b, dt



FILL_ADD = """(async () => {
  document.getElementById('new-event-btn').click();
  const set = (id, v) => { const el = document.getElementById(id); el.value = v; el.dispatchEvent(new Event('input', {bubbles: true})); };
  set('title', 'Hack Night 2027'); set('category', 'Hackathon');
  set('description', 'An overnight mini-hackathon: build a small web app with the Fetch API and a JSON back end.');
  set('event_date', '2027-03-06'); set('start_time', '19:00'); set('capacity', '80'); set('venue', 'Innovation Lab, Block A');
  document.getElementById('save-btn').click();
  await new Promise(r => setTimeout(r, 1500));
  return document.getElementById('message').textContent;
})()"""
EDIT = """(async () => {
  document.querySelector('button[aria-label="Edit Web Frameworks Workshop"]').click();
  const set = (id, v) => { const el = document.getElementById(id); el.value = v; };
  set('title', 'Web Frameworks Workshop (Advanced)'); set('venue', 'Computer Lab 4'); set('capacity', '75');
  document.getElementById('save-btn').click();
  await new Promise(r => setTimeout(r, 1500));
  return document.getElementById('message').textContent;
})()"""
DELETE = """(async () => {
  document.querySelector('button[aria-label="Delete Hack Night 2027"]').click();
  await new Promise(r => setTimeout(r, 400));
  document.getElementById('confirm-yes').click();
  await new Promise(r => setTimeout(r, 1500));
  return document.getElementById('message').textContent;
})()"""


def show_in_sources(dt, row_text, nth=0):
    """Right-click a request in the Network drawer → 'Open in Sources panel', then pretty-print the JSON."""
    rows = dt.locator(".drawer-tabbed-pane td.name-column", has_text=re.compile(row_text))
    rows.nth(nth).click(button="right"); dt.wait_for_timeout(600)
    dt.locator(".soft-context-menu-item", has_text="Open in Sources panel").first.click(); dt.wait_for_timeout(1500)
    if dt.locator(".cm-content .cm-line").count() <= 1:             # minified JSON on one line → pretty-print it
        buttons = dt.locator('[aria-label*="retty" i], [title*="retty" i]')
        print("   pretty-print buttons:", buttons.count())
        for i in range(buttons.count()):
            if buttons.nth(i).is_visible():
                buttons.nth(i).click(); dt.wait_for_timeout(1200); break
    print("   editor lines:", dt.locator(".cm-content .cm-line").count())
    rows.nth(nth).click(); dt.wait_for_timeout(400)               # highlight the row in the table


with sync_playwright() as p:
    b, dt = open_devtools(p, width=1800, height=1080)
    # Network panel → drawer, so the request table keeps all its columns while the response is shown above
    dt.get_by_role("tab", name="Network").first.click(button="right"); dt.wait_for_timeout(600)
    dt.locator(".soft-context-menu-item", has_text="Move to drawer").first.click(); dt.wait_for_timeout(1500)
    # make the drawer taller: drag its top edge upwards
    head = dt.locator(".drawer-tabbed-pane .tabbed-pane-header").first.bounding_box()
    dt.mouse.move(head["x"] + 300, head["y"] - 2); dt.mouse.down(); dt.mouse.move(head["x"] + 300, 560, steps=15); dt.mouse.up()
    dt.wait_for_timeout(800)
    cdp("Page.reload", {"ignoreCache": True}); dt.wait_for_timeout(3000)
    drawer = dt.locator(".drawer-tabbed-pane")
    drawer.locator("text=Fetch/XHR").first.click(); dt.wait_for_timeout(500)
    # add the Method column (right-click a column header)
    drawer.locator("th", has_text="Status").first.click(button="right"); dt.wait_for_timeout(600)
    dt.locator(".soft-context-menu-item", has_text=re.compile(r"^Method$")).first.click(); dt.wait_for_timeout(600)

    # 10 GET list
    show_in_sources(dt, r"api\.php\?action=list")
    dt.screenshot(path=f"{OUT}/network-get-json.png")
    print("10 done")

    # 11 POST create
    print("add:", page_js(FILL_ADD)); dt.wait_for_timeout(1500)
    show_in_sources(dt, r"api\.php\?action=create")
    dt.screenshot(path=f"{OUT}/network-post-add.png")
    print("11 done")

    # 12 update + delete
    print("update:", page_js(EDIT)); dt.wait_for_timeout(1200)
    print("delete:", page_js(DELETE)); dt.wait_for_timeout(1500)
    show_in_sources(dt, r"api\.php\?action=delete")
    hb = drawer.get_by_role("tab", name="Headers").first.bounding_box()  # close the details pane → full table with Status
    dt.mouse.click(hb["x"] - 30, hb["y"] + hb["height"] / 2); dt.wait_for_timeout(1000)
    dt.screenshot(path=f"{OUT}/network-crud-operations.png")
    print("12 done")
    names = drawer.locator("td.name-column").all_inner_texts()
    statuses = drawer.locator("td.status-column").all_inner_texts()
    methods = drawer.locator("td.method-column").all_inner_texts()
    print("table:", list(zip(methods, names, statuses)))
    b.close()

target_browser.terminate()
