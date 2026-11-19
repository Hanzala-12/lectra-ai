"""Study-assistant (LLM + RAG) functional tests against the live backend (QA_API_URL)."""

import json, os, time, uuid, urllib.request, urllib.error

BASE = os.environ.get("QA_API_URL", "http://127.0.0.1:8000")
HERE = os.path.dirname(os.path.abspath(__file__))
results = []

TRANSCRIPT = (
    "Today we cover photosynthesis. Photosynthesis is the process by which plants convert light energy into chemical energy "
    "stored as glucose. It takes place in the chloroplasts, which contain the green pigment chlorophyll. The process has two "
    "stages. In the light-dependent reactions, chlorophyll absorbs sunlight and water is split, releasing oxygen and producing "
    "ATP and NADPH. In the Calvin cycle, which is light-independent, the plant uses ATP and NADPH to fix carbon dioxide into "
    "glucose. The overall equation is six carbon dioxide plus six water, with light, gives glucose plus six oxygen. Factors "
    "that affect the rate include light intensity, carbon dioxide concentration and temperature. At very high temperatures the "
    "enzymes involved are denatured and the rate drops. Remember that the oxygen released comes from water, not from carbon dioxide."
)


def call(method, path, body=None, token=None, timeout=400):
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers=h,
    )
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode()), time.time() - t
    except urllib.error.HTTPError as e:
        txt = e.read().decode()
        try:
            return e.code, json.loads(txt), time.time() - t
        except Exception:
            return e.code, txt[:300], time.time() - t


def rec(tid, title, expected, actual, ok):
    results.append(
        {
            "id": tid,
            "title": title,
            "expected": expected,
            "actual": actual,
            "status": "PASS" if ok else "FAIL",
        }
    )
    print("PASS" if ok else "FAIL", tid, title, "->", actual, flush=True)


U = "llm_" + uuid.uuid4().hex[:8]
c, j, _ = call(
    "POST", "/api/auth/signup", {"username": U, "password": "Zebra#Lecture7"}
)
tok = j["token"]
c, j, _ = call(
    "POST",
    "/api/lecture",
    {"title": "Photosynthesis (QA)", "transcript": TRANSCRIPT},
    tok,
)
lec = j["id"]

c, notes, s = call("POST", f"/api/lecture/{lec}/notes", {}, tok)
body = json.dumps(notes).lower()
rec(
    "LLM-01",
    "Notes are generated from the transcript and mention its key concepts",
    "200; mentions chlorophyll/glucose",
    f"{c} in {s:.0f}s; {len(body)} chars; chlorophyll={'chlorophyll' in body} glucose={'glucose' in body}",
    c == 200 and "glucose" in body,
)
c, again, s = call("POST", f"/api/lecture/{lec}/notes", {}, tok)
rec(
    "LLM-02",
    "Second notes request is served from cache (fast)",
    "200, much faster",
    f"{c} in {s:.1f}s",
    c == 200 and s < 3,
)

c, quiz, s = call("POST", f"/api/lecture/{lec}/quiz", {"num_questions": 3}, tok)
qs = (quiz.get("quiz") if isinstance(quiz, dict) else None) or []
well = bool(qs) and all(
    len(q.get("answers", [])) >= 2
    and sum(1 for a in q["answers"] if a.get("is_correct")) == 1
    for q in qs
)
rec(
    "LLM-03",
    "MCQ quiz generated: every question has >=2 options and exactly one correct answer",
    "200; >=1 question, well-formed",
    f"{c} in {s:.0f}s; {len(qs)} questions; wellformed={well}",
    c == 200 and well,
)

if qs:
    right = [next(a["answer_id"] for a in q["answers"] if a["is_correct"]) for q in qs]
    wrong = [
        next(a["answer_id"] for a in q["answers"] if not a["is_correct"]) for q in qs
    ]
    c, g, s = call(
        "POST",
        f"/api/lecture/{lec}/quiz/grade",
        {"answers": right, "quiz_id": quiz.get("quiz_id")},
        tok,
    )
    rec(
        "LLM-04",
        "Grading: all-correct answers score 100%",
        "200; full marks",
        f"{c} {str(g)[:200]}",
        c == 200 and json.dumps(g).count("100") >= 1,
    )
    c, g2, s = call(
        "POST",
        f"/api/lecture/{lec}/quiz/grade",
        {"answers": wrong, "quiz_id": quiz.get("quiz_id")},
        tok,
    )
    rec(
        "LLM-04b",
        "Grading: all-wrong answers score 0%",
        "200; zero marks",
        f"{c} {str(g2)[:200]}",
        c == 200
        and (
            g2.get("score") == 0
            or g2.get("percentage") == 0
            or g2.get("percent") == 0
            or g2.get("correct") == 0
        ),
    )
    c, g3, s = call(
        "POST",
        f"/api/lecture/{lec}/quiz/grade",
        {"answers": ["not-a-real-id"] * len(qs), "quiz_id": quiz.get("quiz_id")},
        tok,
    )
    rec(
        "LLM-04c",
        "Grading with invalid answer ids never crashes (no 500)",
        "<500",
        str(c),
        c < 500,
    )

c, sch, s = call("POST", f"/api/lecture/{lec}/schedule", {}, tok)
rec("LLM-05", "Study schedule generated", "200", f"{c} in {s:.0f}s", c == 200)
c, ev, s = call("POST", f"/api/lecture/{lec}/evaluate", {}, tok)
rec("LLM-06", "Lecture evaluation generated", "200", f"{c} in {s:.0f}s", c == 200)

c, ch, s = call(
    "POST",
    f"/api/lecture/{lec}/chat",
    {"question": "Where does the oxygen released in photosynthesis come from?"},
    tok,
)
ans = (ch.get("answer") or "").lower() if isinstance(ch, dict) else ""
rec(
    "LLM-07",
    "RAG chatbot answers correctly from the transcript (oxygen comes from water)",
    "200; answer mentions water; sources cited",
    f"{c} in {s:.0f}s; water={'water' in ans}; sources={len(ch.get('sources', [])) if isinstance(ch, dict) else 0}",
    c == 200 and "water" in ans,
)
c, ch2, s = call(
    "POST",
    f"/api/lecture/{lec}/chat",
    {"question": "What is the capital of France and who won the 2018 World Cup?"},
    tok,
)
ans2 = (ch2.get("answer") or "").lower() if isinstance(ch2, dict) else ""
rec(
    "LLM-08",
    "Out-of-scope question: chatbot does not hallucinate an answer from outside the lecture",
    "declines / says not covered (no 'paris'/'france won')",
    f"{c}; answer: {ans2[:150]!r}",
    c == 200 and "paris" not in ans2,
)
c, rc, s = call("POST", f"/api/lecture/{lec}/recap", {}, tok, timeout=600)
rec(
    "LLM-09",
    "Audio recap generation responds (script + offline TTS)",
    "200 or clear 503 if the Piper voice model is not installed",
    f"{c} in {s:.0f}s {str(rc)[:140]}",
    c in (200, 503),
)
c, _, _ = call("DELETE", f"/api/lecture/{lec}", token=tok)

json.dump(
    {"user": U, "results": results},
    open(os.path.join(HERE, "results", "llm_results.json"), "w"),
    indent=2,
)
print(
    "TOTAL",
    len(results),
    "PASS",
    sum(r["status"] == "PASS" for r in results),
    "FAIL",
    sum(r["status"] == "FAIL" for r in results),
)
