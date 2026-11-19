"""End-to-end functional test of the core product against the live backend:
audio upload -> noise removal + diarization + ASR -> stored lecture -> notes,
quiz, grading, schedule, evaluation, chat, recap."""

import json, os, sys, time, uuid, urllib.request, urllib.error

BASE = os.environ.get("QA_API_URL", "http://127.0.0.1:8000")
HERE = os.path.dirname(os.path.abspath(__file__))
results = []
PW = "Zebra#Lecture7"


def call(method, path, body=None, token=None, timeout=900):
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


def multipart(path, fields, filepath, token, timeout=1800):
    b = "----qa" + uuid.uuid4().hex
    parts = []
    for k, v in fields.items():
        parts.append(
            f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
        )
    parts.append(
        f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{os.path.basename(filepath)}"\r\nContent-Type: audio/wav\r\n\r\n'.encode()
    )
    parts.append(open(filepath, "rb").read())
    parts.append(f"\r\n--{b}--\r\n".encode())
    req = urllib.request.Request(
        BASE + path,
        data=b"".join(parts),
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={b}",
            "Authorization": f"Bearer {token}",
        },
    )
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode()), time.time() - t
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400], time.time() - t


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


U = "e2e_" + uuid.uuid4().hex[:8]
c, j, _ = call(
    "POST", "/api/auth/signup", {"username": U, "password": PW, "confirm_password": PW}
)
tok = j["token"]

# invalid upload type
bad = os.path.join(HERE, "results", "bad_upload.txt")
open(bad, "w").write("not audio")
c, j, _ = multipart("/api/process-lecture", {"whisper_model": "base"}, bad, tok)
rec("E2E-01", "Non-audio upload is rejected cleanly", "400", str(c), c == 400)

# Path to a short (about 30 s) lecture recording: argument 1 or QA_CLIP env var.
clip = (
    sys.argv[1]
    if len(sys.argv) > 1
    else os.environ.get("QA_CLIP", os.path.join(HERE, "sample_lecture.wav"))
)
c, j, secs = multipart(
    "/api/process-lecture",
    {"whisper_model": "base", "enable_diarization": "true", "title": "QA E2E lecture"},
    clip,
    tok,
)
lec = None
if c == 200 and isinstance(j, dict):
    lec = j.get("lecture_id") or j.get("id") or (j.get("lecture") or {}).get("id")
    seg = j.get("transcript_segments") or []
    txt = j.get("transcript") or ""
    rec(
        "E2E-02",
        "30 s lecture upload runs noise removal + diarization + ASR and returns a transcript",
        "200, transcript text, segments",
        f"{c} in {secs:.0f}s; {len(txt)} chars, {len(seg)} segments, lecture_id={lec}",
        bool(txt) and len(seg) > 0,
    )
    rec(
        "E2E-03",
        "Original and cleaned audio files are downloadable",
        "200 on both",
        str(
            [
                urllib.request.urlopen(BASE + j[k]).status
                for k in ("original_audio_url", "audio_url")
                if j.get(k)
            ]
        ),
        all(
            urllib.request.urlopen(BASE + j[k]).status == 200
            for k in ("original_audio_url", "audio_url")
        ),
    )
    rec(
        "E2E-04",
        "Speaker labels present in segments (diarization)",
        ">=1 labelled segment",
        str(sorted({s.get("speaker") for s in seg})),
        any(s.get("speaker") for s in seg),
    )
    rec(
        "E2E-05",
        "Audio duration metadata is returned",
        "numeric duration",
        f"duration_original={j.get('duration_original')} s",
        isinstance(j.get("duration_original"), (int, float)),
    )
else:
    rec(
        "E2E-02",
        "30 s lecture upload runs the pipeline",
        "200",
        f"{c}: {str(j)[:300]}",
        False,
    )

if lec:
    c, j, _ = call("GET", "/api/library", token=tok)
    rec(
        "E2E-06",
        "Processed lecture appears in the student's library",
        "lecture listed",
        f"{c}",
        c == 200 and lec in json.dumps(j),
    )
    # LLM-backed features: 503 means no key; accept PASS only on 200
    for tid, name, path, body in [
        (
            "E2E-07",
            "Study notes generated from transcript (LLM)",
            f"/api/lecture/{lec}/notes",
            {},
        ),
        (
            "E2E-08",
            "MCQ quiz generated (LLM)",
            f"/api/lecture/{lec}/quiz",
            {"num_questions": 3},
        ),
        (
            "E2E-09",
            "Study schedule generated (LLM)",
            f"/api/lecture/{lec}/schedule",
            {},
        ),
        (
            "E2E-10",
            "Lecture evaluation generated (LLM)",
            f"/api/lecture/{lec}/evaluate",
            {},
        ),
        (
            "E2E-11",
            "RAG chatbot answers a question about the lecture",
            f"/api/lecture/{lec}/chat",
            {"question": "What is this lecture about?"},
        ),
    ]:
        c, j, secs = call("POST", path, body, tok, timeout=300)
        detail = j.get("detail") if isinstance(j, dict) else j
        extra = ""
        if c == 200 and isinstance(j, dict):
            extra = " keys=" + ",".join(list(j.keys())[:5])
        rec(
            tid,
            name,
            "200",
            f"{c} in {secs:.0f}s{extra}"
            + ("" if c == 200 else f" - {str(detail)[:140]}"),
            c == 200,
        )
    c, j, _ = call("GET", f"/api/lecture/{lec}/review-schedule", token=tok)
    rec(
        "E2E-12",
        "Spaced-repetition review schedule endpoint responds",
        "200",
        str(c),
        c == 200,
    )
    c, j, _ = call("DELETE", f"/api/lecture/{lec}", token=tok)
    rec("E2E-13", "Lecture can be deleted by its owner", "200", str(c), c == 200)
    c, j, _ = call("GET", f"/api/lecture/{lec}", token=tok)
    rec("E2E-14", "Deleted lecture is gone (404)", "404", str(c), c == 404)

json.dump(
    {"user": U, "results": results},
    open(os.path.join(HERE, "results", "e2e_results.json"), "w"),
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
