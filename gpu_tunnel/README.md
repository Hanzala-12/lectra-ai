# GPU tunnel — offload the audio pipeline to a free Kaggle GPU

No local GPU? This lets `LectraAIPipeline` (DeepFilterNet3, MetricGAN+,
Pyannote diarization, faster-whisper) run on a free Kaggle GPU instead of
your CPU, while your local frontend/backend keep running exactly as today.
If the tunnel isn't set up, isn't running, or drops mid-session, the backend
automatically falls back to local CPU processing — this is purely additive,
never required.

## How it works

Kaggle notebooks can't accept inbound connections, so the notebook opens an
**outbound** tunnel instead: it runs a small API (`worker_app.py`, reusing
the real pipeline unmodified) and punches a public HTTPS URL to it with
[`cloudflared`](https://github.com/cloudflare/cloudflared) (no account
needed, unlike ngrok). Your local backend POSTs audio files to that URL and
gets back the cleaned audio + transcript, same as if it ran locally — see
`src/remote_pipeline.py` for the client side.

## One-time setup

1. Go to [kaggle.com/code](https://kaggle.com/code) → **New Notebook**.
2. Upload/paste in `kaggle_worker.ipynb` (this folder).
3. **Notebook Settings** (right sidebar): **Accelerator → GPU T4 x2** (or
   P100) · **Internet → On**.
4. **Add-ons → Secrets**, add and attach two secrets to this notebook:
   - `GPU_TUNNEL_TOKEN` — make up any long random string. This is the shared
     password your local backend uses to talk to the worker — required,
     since the tunnel URL itself is public and anyone who has it could
     otherwise submit jobs to your Kaggle GPU quota.
   - `HF_TOKEN` — your HuggingFace token (same one as your local `.env`), so
     speaker diarization works. Optional — without it, diarization falls
     back to VAD, same as running locally without `HF_TOKEN`.

## Every time you want GPU processing

1. Open the notebook on Kaggle, **Run All**.
2. Watch the output of the second-to-last cell for a line like:
   ```
   TUNNEL URL:  https://random-words-here.trycloudflare.com
   ```
3. In your local `.env`:
   ```
   GPU_TUNNEL_URL=https://random-words-here.trycloudflare.com
   GPU_TUNNEL_TOKEN=<the same string you put in the GPU_TUNNEL_TOKEN secret>
   ```
4. Restart your local backend (`python backend.py`) — it loads env vars once
   at startup.
5. Process a lecture as normal. Check `GET /api/health`'s `gpu_tunnel` field
   to confirm it's connected (`{"configured": true, "reachable": true}`).

The last notebook cell blocks on purpose, to keep the session (and tunnel)
alive — leave it running for as long as you want GPU processing available.
Stopping it (or closing the notebook) ends the tunnel; your local backend
will just fall back to local CPU processing on the next request, no restart
needed on your end.

## Limits to know about (Kaggle free tier, as of this writing)

- **~9-12 hours per session** — Kaggle stops the kernel after that; re-run
  the notebook to get a new session (and a new tunnel URL — paste the new
  one into `.env` and restart the backend).
- **~30 GPU-hours/week**, resets weekly.
- **The URL changes every session** — there's no fixed address. This is
  deliberately manual (copy-paste once per session) rather than
  auto-discovered, to keep this feature simple; if that gets annoying, a
  small always-on relay (a GitHub Gist, a tiny key-value store) that the
  notebook updates and the backend polls would remove the manual step, but
  isn't needed for this to work.
- Video files (`.mp4`, `.avi`, etc.) aren't sent over the tunnel — only
  audio. They're processed locally on CPU as before; only audio uploads get
  offloaded.

## Troubleshooting

- **"No GPU detected"** at the top of the notebook — check the Accelerator
  setting (step 3 above); GPU notebooks aren't the default.
- **"GPU was available before installing requirements but NOT after"** — a
  package in `kaggle_requirements.txt` pulled in a CPU-only torch build.
  Don't add `torch`/`torchaudio`/`numpy`/`scipy` to that file; Kaggle's
  preinstalled versions are what provide GPU support in the first place.
- **`/api/health`'s `gpu_tunnel.reachable` is `false`** — the notebook
  session probably ended (check the session's still running on Kaggle) or
  `GPU_TUNNEL_URL`/`GPU_TUNNEL_TOKEN` don't match what's actually running.
  Either way, processing still works — it's just running locally on CPU
  until this is fixed.
- **Couldn't read the `GPU_TUNNEL_TOKEN` secret** — it needs to be both
  *created* under Add-ons → Secrets *and* explicitly attached/enabled for
  this specific notebook (a checkbox next to it in that same panel).
