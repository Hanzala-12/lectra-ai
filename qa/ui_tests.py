"""Browser-driven UI tests (Playwright + installed Chrome) against the running frontend (QA_WEB_URL, default http://localhost:3000).
Saves screenshots to results/screenshots and results to results/ui_results.json."""

import json, os, re, uuid, urllib.request
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(HERE, "results", "screenshots")
os.makedirs(SHOTS, exist_ok=True)
BASE = os.environ.get("QA_WEB_URL", "http://localhost:3000")
API = os.environ.get("QA_API_URL", "http://127.0.0.1:8000")
results = []
PW = "Zebra#Lecture7"
USER = "ui_" + uuid.uuid4().hex[:8]


def rec(tid, title, expected, actual, ok, shot=None):
    results.append(
        {
            "id": tid,
            "title": title,
            "expected": expected,
            "actual": actual,
            "status": "PASS" if ok else "FAIL",
            "screenshot": shot,
        }
    )
    print("PASS" if ok else "FAIL", tid, title, "->", actual)


def shot(page, name):
    page.screenshot(path=os.path.join(SHOTS, name + ".png"))
    return name + ".png"


def fresh(browser, **kw):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, **kw)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.errs = errs
    return ctx, pg


def goto(pg, path):
    pg.goto(BASE + path)
    pg.wait_for_timeout(900)


def fill_signup(pg, username=None, pw=None, confirm=None, name=None, email=None):
    if name is not None:
        pg.fill('input[autocomplete="name"]', name)
    if email is not None:
        pg.fill('input[autocomplete="email"]', email)
    if username is not None:
        pg.fill('input[autocomplete="username"]', username)
    pws = pg.locator('input[autocomplete="new-password"]')
    if pw is not None:
        pws.nth(0).fill(pw)
    if confirm is not None:
        pws.nth(1).fill(confirm)


with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)

    # ---- route protection (logged out)
    ctx, pg = fresh(browser)
    for tid, path in [
        ("UI-01", "/"),
        ("UI-02", "/app/dashboard"),
        ("UI-03", "/features"),
        ("UI-04", "/app/library"),
        ("UI-05", "/docs"),
        ("UI-06", "/does-not-exist"),
    ]:
        goto(pg, path)
        rec(
            tid,
            f"Logged-out visit to {path} redirects to /login",
            "/login",
            pg.url.replace(BASE, ""),
            pg.url.endswith("/login"),
            shot(pg, tid) if tid == "UI-02" else None,
        )

    # ---- login page
    goto(pg, "/login")
    ok = (
        pg.locator('input[autocomplete="username"]').count() == 1
        and pg.locator('input[autocomplete="current-password"]').count() == 1
        and pg.get_by_text("Sign up for free").count() == 1
    )
    rec(
        "UI-07",
        "Login page renders username, password and sign-up link",
        "all present",
        str(ok),
        ok,
        shot(pg, "UI-07_login"),
    )
    pg.click("button[type=submit]")
    pg.wait_for_timeout(300)
    msg = (
        pg.locator("[class*=error]").first.inner_text()
        if pg.locator("[class*=error]").count()
        else ""
    )
    rec(
        "UI-08",
        "Empty login submit shows a validation message",
        "'Enter your username and password.'",
        msg.strip(),
        "username and password" in msg.lower(),
    )
    pg.fill('input[autocomplete="username"]', "nobody_here")
    pg.fill('input[autocomplete="current-password"]', "Wrong#Pass123")
    pg.click("button[type=submit]")
    pg.wait_for_timeout(1500)
    body = pg.inner_text("body")
    rec(
        "UI-09",
        "Wrong credentials show 'Invalid username or password' and stay on /login",
        "error shown, no redirect",
        "Invalid username or password" in body
        and pg.url.endswith("/login")
        and "yes"
        or "no",
        "Invalid username or password" in body and pg.url.endswith("/login"),
        shot(pg, "UI-09_wrong_login"),
    )
    inp = pg.locator('input[autocomplete="current-password"]')
    t1 = inp.get_attribute("type")
    pg.click('button[aria-label="Show password"]')
    t2 = pg.locator('input[autocomplete="current-password"]').get_attribute("type")
    rec(
        "UI-10",
        "Login show/hide password toggle switches input type",
        "password -> text",
        f"{t1} -> {t2}",
        t1 == "password" and t2 == "text",
    )

    # ---- signup validation
    goto(pg, "/signup")
    rec(
        "UI-11",
        "Signup page has Confirm Password field",
        "2 password fields",
        str(pg.locator('input[autocomplete="new-password"]').count()),
        pg.locator('input[autocomplete="new-password"]').count() == 2,
        shot(pg, "UI-11_signup_empty"),
    )
    fill_signup(pg, username="23454", pw="abc12345", confirm="different")
    pg.click("button[type=submit]")
    pg.wait_for_timeout(500)
    body = pg.inner_text("body")
    rec(
        "UI-12",
        "Numeric username '23454' rejected",
        "'must start with a letter'",
        "shown" if "must start with a letter" in body else "NOT shown",
        "must start with a letter" in body,
        shot(pg, "UI-12_signup_errors"),
    )
    rec(
        "UI-13",
        "Weak password rejected with specific reason",
        "'needs at least one uppercase letter'",
        "shown" if "uppercase letter." in body else "NOT shown",
        "needs at least one uppercase letter" in body,
    )
    rec(
        "UI-14",
        "Mismatched confirm password rejected",
        "'Passwords do not match.'",
        "shown" if "Passwords do not match" in body else "NOT shown",
        "Passwords do not match" in body,
    )
    rec(
        "UI-15",
        "Still on /signup (no account created, no redirect)",
        "/signup",
        pg.url.replace(BASE, ""),
        pg.url.endswith("/signup"),
    )
    goto(pg, "/signup")
    fill_signup(pg, username="validname", email="not-an-email", pw=PW, confirm=PW)
    pg.click("button[type=submit]")
    pg.wait_for_timeout(400)
    rec(
        "UI-16",
        "Malformed email rejected",
        "'valid email address'",
        "shown" if "valid email address" in pg.inner_text("body") else "NOT shown",
        "valid email address" in pg.inner_text("body"),
    )
    goto(pg, "/signup")
    fill_signup(pg, username="validname", name="R2D2 99", pw=PW, confirm=PW)
    pg.click("button[type=submit]")
    pg.wait_for_timeout(400)
    rec(
        "UI-17",
        "Invalid full name (digits) rejected",
        "'Name can only contain letters'",
        (
            "shown"
            if "Name can only contain letters" in pg.inner_text("body")
            else "NOT shown"
        ),
        "Name can only contain letters" in pg.inner_text("body"),
    )
    goto(pg, "/signup")
    fill_signup(pg, username="hanzala", pw="Hanzala#2026", confirm="Hanzala#2026")
    pg.click("button[type=submit]")
    pg.wait_for_timeout(400)
    rec(
        "UI-18",
        "Password containing the username rejected",
        "'cannot contain your username'",
        (
            "shown"
            if "cannot contain your username" in pg.inner_text("body")
            else "NOT shown"
        ),
        "cannot contain your username" in pg.inner_text("body"),
    )
    goto(pg, "/signup")
    fill_signup(pg, username="validname", pw="Password1!", confirm="Password1!")
    pg.click("button[type=submit]")
    pg.wait_for_timeout(400)
    rec(
        "UI-19",
        "Common password ('Password1!') rejected",
        "'too common'",
        "shown" if "too common" in pg.inner_text("body") else "NOT shown",
        "too common" in pg.inner_text("body"),
    )

    # strength meter
    goto(pg, "/signup")
    fill_signup(pg, username="strengthy", pw="abc")
    weak = pg.inner_text("body")
    fill_signup(pg, pw=PW, confirm=PW)
    pg.wait_for_timeout(200)
    strong = pg.inner_text("body")
    rec(
        "UI-20",
        "Strength meter updates live (Weak -> Very strong) and shows 'Passwords match'",
        "Weak ... Very strong + Passwords match",
        f"{'Weak' in weak} / {'Very strong' in strong} / {'Passwords match' in strong}",
        "Weak" in weak and "Very strong" in strong and "Passwords match" in strong,
        shot(pg, "UI-20_strength_strong"),
    )
    t1 = pg.locator('input[autocomplete="new-password"]').nth(0).get_attribute("type")
    pg.click('button[aria-label="Show password"]')
    t2 = pg.locator('input[autocomplete="new-password"]').nth(0).get_attribute("type")
    rec(
        "UI-21",
        "Signup show/hide password toggle",
        "password -> text",
        f"{t1} -> {t2}",
        t1 == "password" and t2 == "text",
    )

    # ---- successful signup
    goto(pg, "/signup")
    fill_signup(
        pg, username=USER, name="UI Tester", email="ui@example.com", pw=PW, confirm=PW
    )
    pg.click("button[type=submit]")
    pg.wait_for_timeout(2500)
    tok = pg.evaluate("localStorage.getItem('lectra_token')")
    rec(
        "UI-22",
        "Valid signup creates the account, stores a session and opens the dashboard",
        "/app/dashboard + token",
        f"{pg.url.replace(BASE, '')} token={'yes' if tok else 'no'}",
        pg.url.endswith("/app/dashboard") and bool(tok),
        shot(pg, "UI-22_dashboard"),
    )

    # ---- logged-in behaviour
    goto(pg, "/login")
    rec(
        "UI-23",
        "Logged-in user visiting /login is sent to the dashboard",
        "/app/dashboard",
        pg.url.replace(BASE, ""),
        pg.url.endswith("/app/dashboard"),
    )
    goto(pg, "/signup")
    rec(
        "UI-24",
        "Logged-in user visiting /signup is sent to the dashboard",
        "/app/dashboard",
        pg.url.replace(BASE, ""),
        pg.url.endswith("/app/dashboard"),
    )
    goto(pg, "/")
    rec(
        "UI-25",
        "Logged-in user can open the home page",
        "/",
        pg.url.replace(BASE, "") or "/",
        pg.url.rstrip("/") == BASE,
    )
    for tid, path, label in [
        ("UI-26", "/app/library", "Library"),
        ("UI-27", "/app/analytics", "Analytics"),
        ("UI-28", "/app/chat", "Chat"),
        ("UI-29", "/app/upload", "Upload"),
    ]:
        pg.errs.clear()
        goto(pg, path)
        txt = pg.inner_text("body")
        rec(
            tid,
            f"Logged-in: {label} page loads without crashing",
            "stays on page, content rendered, no JS exception",
            f"{pg.url.replace(BASE, '')}, {len(txt)} chars, {len([e for e in pg.errs if 'pageerror' in e or 'Uncaught' in e])} JS errors",
            pg.url.endswith(path)
            and len(txt) > 50
            and not any("Uncaught" in e for e in pg.errs),
            shot(pg, f"{tid}_{label.lower()}") if tid in ("UI-26", "UI-29") else None,
        )

    # logout through the UI
    goto(pg, "/app/dashboard")
    try:
        pg.locator("header button, nav button, button").filter(
            has_text=re.compile(USER, re.I)
        ).first.click(timeout=2500)
    except Exception:
        # profile menu trigger may only show initials/name
        pg.locator(
            "button:has(svg.lucide-chevron-down), button[aria-haspopup]"
        ).first.click(timeout=2500)
    pg.wait_for_timeout(300)
    pg.get_by_text("Log out").first.click()
    pg.wait_for_timeout(1200)
    tok = pg.evaluate("localStorage.getItem('lectra_token')")
    rec(
        "UI-30",
        "Logout from the profile menu returns to /login and clears the session",
        "/login, no token",
        f"{pg.url.replace(BASE, '')}, token={'yes' if tok else 'no'}",
        pg.url.endswith("/login") and not tok,
        shot(pg, "UI-30_after_logout"),
    )
    goto(pg, "/app/dashboard")
    rec(
        "UI-31",
        "After logout the dashboard is no longer reachable (back button / URL)",
        "/login",
        pg.url.replace(BASE, ""),
        pg.url.endswith("/login"),
    )

    # duplicate username
    goto(pg, "/signup")
    fill_signup(pg, username=USER.upper(), pw=PW, confirm=PW)
    pg.click("button[type=submit]")
    pg.wait_for_timeout(1500)
    body = pg.inner_text("body")
    rec(
        "UI-32",
        "Duplicate username (different case) shows 'already taken'",
        "'already taken'",
        "shown" if "already taken" in body else "NOT shown",
        "already taken" in body and pg.url.endswith("/signup"),
        shot(pg, "UI-32_duplicate"),
    )

    # valid login
    goto(pg, "/login")
    pg.fill('input[autocomplete="username"]', USER)
    pg.fill('input[autocomplete="current-password"]', PW)
    pg.click("button[type=submit]")
    pg.wait_for_timeout(2000)
    rec(
        "UI-33",
        "Login with correct credentials opens the dashboard",
        "/app/dashboard",
        pg.url.replace(BASE, ""),
        pg.url.endswith("/app/dashboard"),
    )

    # tampered token
    pg.evaluate("localStorage.setItem('lectra_token','tampered-token-value')")
    goto(pg, "/app/dashboard")
    pg.wait_for_timeout(1500)
    tok = pg.evaluate("localStorage.getItem('lectra_token')")
    rec(
        "UI-34",
        "Tampered/expired token is rejected: redirected to /login and token cleared",
        "/login, no token",
        f"{pg.url.replace(BASE, '')}, token={'yes' if tok else 'no'}",
        pg.url.endswith("/login") and not tok,
    )
    ctx.close()

    # ---- lockout in the UI
    ctx, pg = fresh(browser)
    LU = "lk_" + uuid.uuid4().hex[:8]
    req = urllib.request.Request(
        API + "/api/auth/signup",
        data=json.dumps({"username": LU, "password": PW}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req)
    goto(pg, "/login")
    for _ in range(6):
        pg.fill('input[autocomplete="username"]', LU)
        pg.fill('input[autocomplete="current-password"]', "Bad#Guess1234")
        pg.click("button[type=submit]")
        pg.wait_for_timeout(700)
    body = pg.inner_text("body")
    rec(
        "UI-35",
        "Repeated wrong passwords show the 'Too many failed attempts' lock-out message",
        "'Too many failed attempts'",
        "shown" if "Too many failed attempts" in body else "NOT shown",
        "Too many failed attempts" in body,
        shot(pg, "UI-35_lockout"),
    )
    ctx.close()

    # ---- responsive + console cleanliness
    ctx, pg = fresh(browser)
    pg.set_viewport_size({"width": 375, "height": 812})
    for tid, path in [("UI-36", "/login"), ("UI-37", "/signup")]:
        goto(pg, path)
        sw, cw = pg.evaluate(
            "[document.documentElement.scrollWidth, document.documentElement.clientWidth]"
        )
        rec(
            tid,
            f"{path} at 375px mobile width has no horizontal scroll",
            "scrollWidth <= clientWidth",
            f"{sw} vs {cw}",
            sw <= cw + 1,
            shot(pg, f"{tid}_mobile{path.replace('/', '_')}"),
        )
    pg.set_viewport_size({"width": 1280, "height": 900})
    pg.errs.clear()
    goto(pg, "/login")
    goto(pg, "/signup")
    bad = [e for e in pg.errs if "favicon" not in e.lower()]
    rec(
        "UI-38",
        "No JavaScript errors in the console on /login and /signup",
        "0 errors",
        f"{len(bad)} errors" + (f": {bad[:2]}" if bad else ""),
        len(bad) == 0,
    )
    ctx.close()
    browser.close()

json.dump(
    {"user": USER, "results": results},
    open(os.path.join(HERE, "results", "ui_results.json"), "w"),
    indent=2,
)
print(
    "\nTOTAL",
    len(results),
    "PASS",
    sum(r["status"] == "PASS" for r in results),
    "FAIL",
    sum(r["status"] == "FAIL" for r in results),
)
