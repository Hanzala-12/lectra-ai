# QA test suite

Black-box and end-to-end test scripts used for the QA Test Report
(`docs/QA_Test_Report.docx`). The automated unit/integration tests live in
`tests/` and run with `pytest`; the scripts here test the **running** system.

| Script | Level | Needs |
|---|---|---|
| `system_tests.py` | API / security black-box tests (36 checks) | backend on `QA_API_URL` (default `http://127.0.0.1:8000`) |
| `ui_tests.py` | Real-browser UI tests with screenshots (38 checks) | backend + frontend (`QA_WEB_URL`, default `http://localhost:3000`), `pip install playwright`, Google Chrome |
| `e2e_test.py <clip.wav>` | Full audio pipeline + every study feature (14 checks) | backend, a short (about 30 s) lecture recording, LLM key for the study steps |
| `llm_tests.py` | Study-assistant (LLM + RAG) functional tests (11 checks) | backend with a valid LLM key |
| `cleanup_test_data.py` | Removes the throw-away accounts the scripts create | local `data/` folder |

Each script writes a JSON result file (and, for the UI tests, screenshots) to `qa/results/`.

```powershell
python qa/system_tests.py
python qa/ui_tests.py
python qa/e2e_test.py path/to/short_lecture.wav
python qa/llm_tests.py
python qa/cleanup_test_data.py
```

The scripts use only the Python standard library, except `ui_tests.py` (Playwright).
Test accounts use the prefixes `qa_`, `qb_`, `qc_`, `ui_`, `e2e_`, `llm_` so they can be removed safely.
