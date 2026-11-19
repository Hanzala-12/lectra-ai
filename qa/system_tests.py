"""Black-box system tests against the live backend (QA_API_URL, default http://127.0.0.1:8000).
Writes results/system_results.json. Run cleanup_test_data.py afterwards to remove the throw-away accounts.
"""

import json, os, sys, time, uuid, urllib.request, urllib.error

BASE = os.environ.get("QA_API_URL", "http://127.0.0.1:8000")
OUT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "results", "system_results.json"
)
results = []


def call(method, path, body=None, token=None, raw=None, headers=None):
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    if headers:
        h.update(headers)
    data = (
        raw
        if raw is not None
        else (json.dumps(body).encode() if body is not None else None)
    )
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=h)
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            txt = r.read().decode()
            code = r.status
    except urllib.error.HTTPError as e:
        txt = e.read().decode()
        code = e.code
    ms = int((time.time() - t) * 1000)
    try:
        js = json.loads(txt)
    except Exception:
        js = txt[:200]
    return code, js, ms


def record(tid, title, expected, actual, ok):
    results.append(
        {
            "id": tid,
            "title": title,
            "expected": expected,
            "actual": actual,
            "status": "PASS" if ok else "FAIL",
        }
    )
    print(("PASS" if ok else "FAIL"), tid, title, "->", actual)


U = "qa_" + uuid.uuid4().hex[:8]
PW = "Zebra#Lecture7"

# --- signup validation
c, j, _ = call("POST", "/api/auth/signup", {"username": "23454", "password": PW})
record(
    "ST-01",
    "Signup rejects numeric-only username",
    "400",
    f"{c}: {j.get('detail') if isinstance(j, dict) else j}",
    c == 400,
)
c, j, _ = call("POST", "/api/auth/signup", {"username": U, "password": "abc12345"})
record(
    "ST-02", "Signup rejects weak password", "400", f"{c}: {j.get('detail')}", c == 400
)
c, j, _ = call(
    "POST",
    "/api/auth/signup",
    {"username": U, "password": PW, "confirm_password": "Other#Pass99"},
)
record(
    "ST-03",
    "Signup rejects mismatched confirm password",
    "400",
    f"{c}: {j.get('detail')}",
    c == 400,
)
c, j, _ = call(
    "POST", "/api/auth/signup", {"username": U, "password": PW, "email": "bad-email"}
)
record(
    "ST-04",
    "Signup rejects malformed email",
    "400",
    f"{c}: {j.get('detail')}",
    c == 400,
)
c, j, _ = call(
    "POST", "/api/auth/signup", {"username": U, "password": PW + "x", "name": "R2D2!!"}
)
record(
    "ST-05",
    "Signup rejects invalid full name",
    "400",
    f"{c}: {j.get('detail')}",
    c == 400,
)
c, j, _ = call("POST", "/api/auth/signup", {"username": U})
record("ST-06", "Signup with missing password field rejected", "422", str(c), c == 422)
c, j, _ = call("POST", "/api/auth/signup", raw=b"{not json")
record("ST-07", "Signup with malformed JSON rejected (no 500)", "422", str(c), c == 422)

# --- successful signup + session
c, j, ms = call(
    "POST",
    "/api/auth/signup",
    {
        "username": U,
        "password": PW,
        "confirm_password": PW,
        "name": "QA Tester",
        "email": "qa@example.com",
    },
)
ok = (
    c == 200
    and "token" in j
    and "password" not in json.dumps(j["student"]).lower().replace("password_hash", "X")
    and "password_hash" not in j["student"]
)
record(
    "ST-08",
    "Valid signup succeeds, returns token, never leaks password/hash",
    "200 + token",
    f"{c} in {ms} ms",
    ok,
)
tok = j.get("token") if isinstance(j, dict) else None
c, j, _ = call("POST", "/api/auth/signup", {"username": U.upper(), "password": PW})
record(
    "ST-09", "Duplicate username (case-insensitive) rejected", "409", str(c), c == 409
)
c, j, _ = call("GET", "/api/auth/me", token=tok)
record(
    "ST-10",
    "/me returns the logged-in student",
    "200 + username",
    f"{c} {j.get('username') if isinstance(j, dict) else j}",
    c == 200 and j.get("username") == U,
)

# --- login
c, j, ms = call("POST", "/api/auth/login", {"username": U.upper(), "password": PW})
record(
    "ST-11",
    "Login succeeds (username case-insensitive)",
    "200",
    f"{c} in {ms} ms",
    c == 200,
)
c, j, _ = call("POST", "/api/auth/login", {"username": U, "password": "Wrong#Pass99"})
record(
    "ST-12",
    "Login with wrong password rejected with generic message",
    "401 'Invalid username or password'",
    f"{c}: {j.get('detail')}",
    c == 401 and j.get("detail") == "Invalid username or password",
)
c, j2, _ = call(
    "POST", "/api/auth/login", {"username": "no_such_user_x", "password": PW}
)
record(
    "ST-13",
    "Unknown username gives the SAME message as wrong password (no user enumeration)",
    "401, identical detail",
    f"{c}: {j2.get('detail')}",
    c == 401 and j2.get("detail") == j.get("detail"),
)

# --- access control
for tid, m, p in [
    ("ST-14", "GET", "/api/auth/me"),
    ("ST-15", "GET", "/api/library"),
    ("ST-16", "POST", "/api/process-lecture"),
    ("ST-17", "POST", "/api/process"),
    ("ST-18", "GET", "/api/lecture/abc123"),
    ("ST-19", "POST", "/api/lecture/abc123/notes"),
    ("ST-20", "POST", "/api/lecture/abc123/chat"),
    ("ST-21", "DELETE", "/api/lecture/abc123"),
]:
    c, j, _ = call(m, p, {} if m in ("POST",) else None)
    record(
        tid,
        f"{m} {p} without token blocked",
        "401 (or 422 before auth)",
        str(c),
        c in (401, 422) and c != 200,
    )
c, j, _ = call("GET", "/api/library", token="garbage.token.value")
record("ST-22", "Forged/garbage bearer token rejected", "401", str(c), c == 401)

# --- authorization (cross-student isolation)
U2 = "qb_" + uuid.uuid4().hex[:8]
c, j, _ = call(
    "POST", "/api/auth/signup", {"username": U2, "password": "Yankee#Delta5"}
)
tok2 = j["token"]
c, j, _ = call(
    "POST",
    "/api/lecture",
    {
        "title": "QA lecture",
        "transcript": "Photosynthesis converts light energy into chemical energy. "
        * 20,
    },
    token=tok,
)
lec = j.get("id") if isinstance(j, dict) else None
record(
    "ST-23",
    "Student A can create a lecture from a transcript",
    "200 + id",
    f"{c} id={lec}",
    c == 200 and bool(lec),
)
c, j, _ = call("GET", f"/api/lecture/{lec}", token=tok2)
record(
    "ST-24",
    "Student B cannot read Student A's lecture (404, no existence leak)",
    "404",
    str(c),
    c == 404,
)
c, j, _ = call("DELETE", f"/api/lecture/{lec}", token=tok2)
record("ST-25", "Student B cannot delete Student A's lecture", "404", str(c), c == 404)
c, j, _ = call("GET", "/api/library", token=tok2)
record(
    "ST-26",
    "Student B's library does not list A's lecture",
    "no lecture ids from A",
    (
        f"{c}, A's lecture not listed"
        if lec not in json.dumps(j)
        else f"{c}, A's lecture LEAKED"
    ),
    c == 200 and lec not in json.dumps(j),
)
c, j, _ = call("GET", f"/api/lecture/{lec}", token=tok)
record("ST-27", "Student A can read own lecture", "200", str(c), c == 200)

# --- injection / robustness
c, j, _ = call("POST", "/api/auth/login", {"username": "' OR '1'='1", "password": "x"})
record("ST-28", "SQL-injection style username does not log in", "401", str(c), c == 401)
c, j, _ = call(
    "POST",
    "/api/auth/signup",
    {"username": "<script>alert(1)</script>", "password": PW},
)
record("ST-29", "Script-tag username rejected by validation", "400", str(c), c == 400)
c, j, _ = call("GET", "/api/download/..%2Fconfig.yaml")
record(
    "ST-30",
    "Path traversal on /api/download blocked (forward-slash form)",
    "404/400, no file content",
    f"{c}",
    c in (400, 403, 404),
)
c, j, _ = call("GET", "/api/download/..%5Cconfig.yaml")
leaked = c == 200
record(
    "ST-30b",
    "Path traversal on /api/download blocked (Windows backslash form)",
    "404/400, no file content",
    f"{c}{' - FILE CONTENTS RETURNED' if leaked else ''}",
    not leaked,
)
c, j, _ = call("POST", "/api/auth/signup", {"username": "a" * 5000, "password": PW})
record("ST-31", "Oversized username rejected (no crash)", "400", str(c), c == 400)

# --- health / metrics
c, j, ms = call("GET", "/api/health")
record("ST-32", "Health endpoint reports healthy", "200", f"{c} in {ms} ms", c == 200)
c, j, ms = call("GET", "/api/llm-status")
record(
    "ST-33",
    "LLM status endpoint reports configuration",
    "200 configured",
    f"{c} {j}",
    c == 200,
)

# --- lockout (last: uses its own user)
U3 = "qc_" + uuid.uuid4().hex[:8]
call("POST", "/api/auth/signup", {"username": U3, "password": "Xray#Whiskey9"})
codes = [
    call("POST", "/api/auth/login", {"username": U3, "password": "Bad#Guess123"})[0]
    for _ in range(5)
]
c, j, _ = call("POST", "/api/auth/login", {"username": U3, "password": "Xray#Whiskey9"})
record(
    "ST-34",
    "Account locks after 5 failed logins (correct password then refused)",
    "5x401 then 429",
    f"{codes} then {c}",
    codes == [401] * 5 and c == 429,
)

# --- logout
c, _, _ = call("POST", "/api/auth/logout", token=tok)
c2, _, _ = call("GET", "/api/auth/me", token=tok)
record(
    "ST-35",
    "Logout invalidates the session token",
    "200 then 401",
    f"{c} then {c2}",
    c == 200 and c2 == 401,
)

json.dump(
    {"users": [U, U2, U3], "lecture": lec, "results": results}, open(OUT, "w"), indent=2
)
print(
    "\nTOTAL",
    len(results),
    "PASS",
    sum(r["status"] == "PASS" for r in results),
    "FAIL",
    sum(r["status"] == "FAIL" for r in results),
)
