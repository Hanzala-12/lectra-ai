# Kaggle GPU tunnel — Console runner commands

Manual, step-by-step commands for starting the GPU tunnel worker via
Kaggle's **Console** panel (the Python prompt at the bottom of the
notebook editor — not the notebook cells, not "Run All").

**Why this exists:** "Run All" starts the server inside a background
thread, and if anything fails there it can silently show the cell as
"completed" with no visible error. The Console runs each step one at a
time, in the same place you can immediately see its output — so you know
exactly which step you're on and whether it actually worked, before
moving to the next one.

**When to use it:** any time you're setting up the GPU tunnel and want
to *see* it work step by step, rather than trusting a "Run All" that
might be silently stuck or failed. This is the proven-reliable path —
used successfully many times over.

## How

1. Open `https://www.kaggle.com/code/muhammadhanzalat/lectra-ai-gpu-tunnel-worker/edit`.
2. Make sure the session has GPU + Internet on (Notebook Settings, right
   sidebar) and the `GPU_TUNNEL_TOKEN` / `HF_TOKEN` secrets are attached
   (Add-ons → Secrets).
3. Open the **Console** tab at the bottom of the editor.
4. Paste each block below into the console input, press Enter, and wait
   for its printed result before pasting the next one.

### 1. GPU check + get the latest code

```python
exec("import torch\nassert torch.cuda.is_available()\nprint('GPU OK:', torch.cuda.get_device_name(0))\nimport subprocess, os\nsubprocess.run(['bash','-c','cd /kaggle/working && rm -rf repo && git clone --depth 1 https://github.com/Hanzala-12/lectra-ai.git repo'])\nos.chdir('/kaggle/working/repo')\nprint('cwd now:', os.getcwd())")
```

Expect: `GPU OK: Tesla T4` (or similar) and `cwd now: /kaggle/working/repo`.

### 2. Load secrets

Uses Kaggle's own Secrets API — never types the actual token values.

```python
exec("import os\nfrom kaggle_secrets import UserSecretsClient\nsecrets = UserSecretsClient()\nos.environ['HF_TOKEN'] = secrets.get_secret('HF_TOKEN')\nos.environ['HUGGING_FACE_HUB_TOKEN'] = os.environ['HF_TOKEN']\nos.environ['GPU_TUNNEL_TOKEN'] = secrets.get_secret('GPU_TUNNEL_TOKEN')\nprint('secrets loaded:', bool(os.environ.get('HF_TOKEN')), bool(os.environ.get('GPU_TUNNEL_TOKEN')))")
```

Expect: `secrets loaded: True True`.

### 3. Install Rust + all Python packages

The slow step — can take a minute or two. Also restores numpy to
whatever version it was before this install — pip's resolver can
silently downgrade it as a side effect of some other package's
transitive constraint even though `kaggle_requirements.txt` never names
numpy itself (confirmed live: this broke scipy with
`ModuleNotFoundError: No module named 'numpy.strings'` — only exists on
numpy>=2.0 — after numpy got silently swapped from Kaggle's preinstalled
2.0.2 down to 1.26.4 partway through the install).

```python
exec("import subprocess, os\nr = subprocess.run(['bash','-c',\"curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable\"], capture_output=True, text=True)\nprint('RUST RC:', r.returncode)\nos.environ['PATH'] = os.path.expanduser('~/.cargo/bin') + ':' + os.environ['PATH']\nimport sys, numpy\nnumpy_before = numpy.__version__\ninstall = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', '/kaggle/working/repo/gpu_tunnel/kaggle_requirements.txt'], capture_output=True, text=True)\nprint('install rc=', install.returncode)\nrestore = subprocess.run([sys.executable, '-m', 'pip', 'install', '--force-reinstall', '--no-deps', f'numpy=={numpy_before}'], capture_output=True, text=True)\nprint('numpy restore rc=', restore.returncode, '(back to', numpy_before, ')')")
```

Expect: `RUST RC: 0`, `install rc= 0`, `numpy restore rc= 0`. If
`install rc=` is non-zero, re-run this same block once (transient PyPI
resolution failures are common and usually clear on retry) before
treating it as a real problem.

**If you already hit `ModuleNotFoundError: No module named 'numpy.strings'`
(or `'numpy.char'` / `'numpy.rec'`) in step 4 before reading this** — the
above block already fixes it for next time, but to recover the *current*
session without starting over, run this once, then retry step 4:

```python
exec("import sys, subprocess\nr = subprocess.run([sys.executable, '-m', 'pip', 'install', '--force-reinstall', '--no-deps', 'numpy==2.0.2'], capture_output=True, text=True)\nprint('rc=', r.returncode)\nfor m in list(sys.modules):\n if m == 'numpy' or m.startswith('numpy.') or m == 'scipy' or m.startswith('scipy.') or m.startswith('gpu_tunnel'):\n  del sys.modules[m]\nimport numpy\nprint('numpy now', numpy.__version__, '- has strings:', hasattr(numpy, 'strings'))")
```

(`2.0.2` above is what this project has seen Kaggle ship — if a fresh
session reports a different version in step 3's own check, use that
instead.)

### 4. Start the worker server

```python
exec("import sys, os\nsys.path.insert(0, '/kaggle/working/repo')\nos.chdir('/kaggle/working/repo')\nfrom gpu_tunnel.worker_app import app as server_app\nimport asyncio, uvicorn.config, threading, time, uvicorn, requests\nuvicorn.config.Config.get_loop_factory = lambda self: asyncio.new_event_loop\ndef _run():\n uvicorn.run(server_app, host='0.0.0.0', port=8800, log_level='info')\nthreading.Thread(target=_run, daemon=True).start()\ntime.sleep(8)\ntry:\n requests.get('http://localhost:8800/docs', timeout=5)\n print('SERVER CONFIRMED RUNNING')\nexcept Exception as e:\n print('SERVER NOT RESPONDING:', e)")
```

Must print `SERVER CONFIRMED RUNNING`. If it prints `SERVER NOT
RESPONDING: ...` instead, that's a real error to fix before continuing —
don't proceed to step 5 until this one is clean.

### 5. Open the tunnel and get the URL

```python
exec("import os, subprocess, threading, time\nif not os.path.exists('/kaggle/working/repo/cloudflared'):\n subprocess.run(['wget', '-q', 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64', '-O', '/kaggle/working/repo/cloudflared'])\n subprocess.run(['chmod', '+x', '/kaggle/working/repo/cloudflared'])\nlines = []\nproc = subprocess.Popen(['/kaggle/working/repo/cloudflared', 'tunnel', '--url', 'http://localhost:8800'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)\nthreading.Thread(target=lambda: [lines.append(l) for l in proc.stdout], daemon=True).start()\ntime.sleep(10)\nfor l in lines:\n if 'trycloudflare.com' in l:\n  print('TUNNEL URL:', l.strip())")
```

Prints a line like `TUNNEL URL: ... | https://<random-words>.trycloudflare.com |`.

## After you have the URL

1. Paste the URL into `GPU_TUNNEL_URL` in `D:\fyp\.env` (it's a new
   random URL every time — this always changes, that's expected).
2. Restart the local backend (`python backend.py`) — it only reads
   `GPU_TUNNEL_URL` at startup, so a running backend won't pick up the
   new value until restarted.
3. Confirm via `GET /api/health` that `gpu_tunnel.reachable` is `true`.

## Notes

- The Console and the notebook's own **Cells** run in separate kernels —
  environment changes made in one (installed packages, `os.environ`,
  `sys.path`) are invisible to the other. This runbook is fully
  self-contained in the Console on purpose, so it never depends on any
  notebook cell having been run first.
- The underlying Kaggle session stays alive as long as the browser tab
  does — no keep-alive loop is required when driving it from the
  Console (unlike the notebook's own cell 7, which exists for the
  "Run All and walk away" case).
- If the Kaggle tab goes idle long enough, Kaggle may show an "Are you
  still there?" prompt or end the session outright. If the session
  actually ends, everything above needs to be re-run from step 1 (new
  container, new port state, new tunnel).
