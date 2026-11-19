"""Remove the throw-away accounts (and their records) created by the QA scripts."""

import json, os, glob, re

root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
pref = re.compile(r"^(qa_|qb_|qc_|ui_|lk_|e2e_|llm_|qp_|sc_)[0-9a-f]{8}$")
ids = set()
for f in glob.glob(f"{root}/students/*.json"):
    try:
        r = json.load(open(f, encoding="utf-8"))
    except Exception:
        continue
    if pref.match(r.get("username", "")):
        ids.add(r["id"])
        os.remove(f)
print("students removed:", len(ids))
removed = {}
for sub in os.listdir(root):
    d = os.path.join(root, sub)
    if not os.path.isdir(d) or sub == "students":
        continue
    n = 0
    for f in glob.glob(f"{d}/*.json"):
        try:
            r = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        if isinstance(r, dict) and r.get("student_id") in ids:
            os.remove(f)
            n += 1
    if n:
        removed[sub] = n
print("records removed per collection:", removed)
sf = f"{root}/sessions.json"
if os.path.exists(sf):
    s = json.load(open(sf, encoding="utf-8"))
    before = len(s)
    s = {
        k: v
        for k, v in s.items()
        if (
            v
            if isinstance(v, str)
            else (v.get("student_id") if isinstance(v, dict) else None)
        )
        not in ids
    }
    json.dump(s, open(sf, "w", encoding="utf-8"))
    print("sessions:", before, "->", len(s))
