# Noise Removal & Speaker Diarization — Full Pipeline

This document explains, end to end, **how Lectra AI removes background noise and
identifies who is speaking when**, and — just as importantly — **how the current
"clean voice, near‑zero noise, words intact" result was achieved** through a
series of measured engineering decisions.

It reflects the live code in [`src/pipeline.py`](../src/pipeline.py),
[`src/diarization.py`](../src/diarization.py),
[`src/deepfilter_processor.py`](../src/deepfilter_processor.py) and
[`src/metricgan_processor.py`](../src/metricgan_processor.py), driven by
[`config.yaml`](../config.yaml).

---

## 1. Goals & constraints

| Goal | Meaning |
|------|---------|
| **Clean** | Background noise inaudible while the speaker talks; silence between utterances. |
| **Accurate** | The *real* recorded voice and words — no synthetic re‑generation, no dropped syllables. |
| **Not dim** | Consistent, broadcast‑level loudness regardless of how much energy is stripped. |
| **Smooth** | No pumping, musical noise, or robotic artifacts. |
| **Low compute** | Runs on **CPU** (no GPU required), no fragile/heavy dependencies. |

The headline result on the overlapped test clip: **~39 dB speech‑to‑noise,
≈ −61 dB noise floor, ≈ −20 dBFS loudness, words intact** — i.e. the background
goes *black* on a spectrogram while the voice and consonants remain.

---

## 2. The signal chain at a glance

```
 input (audio/video, any rate)
   │
   ▼
[1] Load → mono → 16 kHz                         media_loader.py
   │
   ▼
[2] Adaptive thresholds (per‑file)              compute_adaptive_thresholds()
   │     silence threshold • min‑segment • merge‑gap • tail‑pad
   ▼
[3] DIARIZATION — who speaks when               diarization.py (pyannote 3.1)
   │     → speaker turns  (VAD fallback if unavailable)
   ▼
[4] Build speech segments                       _merge_segments()
   │     drop sub‑threshold • tail‑pad • merge nearby
   ▼
[5] Zero‑background mask + 120 Hz high‑pass      STEP 3 in pipeline.py
   │     speech copied onto pure silence; rumble < 120 Hz removed
   ▼
[6] DeepFilterNet3  (48 kHz, chunked)            deepfilter_processor.py
   │     deep‑learning noise suppression (atten_lim_db = 30, post‑filter off)
   ▼
[7] MetricGAN+  neural enhancement               metricgan_processor.py
   │     final bounded‑mask polish → noise floor toward inaudible
   ▼
[8] Re‑mask + 10 ms cosine fades                 STEP 5 in pipeline.py
   │     hard‑silence everything outside speech, click‑free edges
   ▼
[9] Gain‑ride → clarity EQ → loudness norm       adaptive_gain_ride / eq_clarity_boost
   │     even levels, −20 dBFS target, brick‑wall limited
   ▼
[9.5] (optional) Voice Beautify                  voice_beautify.py
   │     tone EQ + loudness leveler + high‑band "air"; SNR‑guarded; OFF by default
   ▼
[10] Save cleaned WAV  (+ optional ASR/transcript, +video remux)
```

Both entry points — the CLI ([`clean_voice.py`](../clean_voice.py)) and the web
backend ([`backend.py`](../backend.py)) — run this exact pipeline from the same
[`config.yaml`](../config.yaml).

---

## 3. Speaker diarization (steps 3–4)

**Model:** `pyannote/speaker-diarization-3.1` (loaded locally from
`models/pyannote`, no network calls once cached).

**What it does:** segments the recording into *turns* — contiguous spans labelled
by speaker (`SPEAKER_00`, `SPEAKER_01`, …) with start/end times. Lectra uses this
two ways:

1. **As the speech detector.** The union of all speaker turns *is* the set of
   regions worth keeping; everything else is treated as non‑speech and silenced
   later (step 8). This is what makes the gaps between utterances perfectly clean.
2. **As transcription guidance.** When ASR is enabled, each speaker turn is
   transcribed separately so Whisper only ever sees single‑speaker audio (no
   cross‑talk confusion), and the transcript is labelled per speaker.

**Robustness:**
- Loads offline when the snapshot already exists (skips ~5 HuggingFace HEAD
  requests).
- Patches `torch.load` (PyTorch 2.6 `weights_only` default) and the
  `use_auth_token → token` rename so checkpoints load cleanly.
- Reads audio as an in‑memory tensor (`soundfile`) to bypass torchcodec/FFmpeg.
- **Fallback:** if the model or `HF_TOKEN` is unavailable, the pipeline falls
  back to WebRTC VAD ([`vad_processor.py`](../src/vad_processor.py)) so it never
  hard‑fails — it just won't have per‑speaker labels.

> **Gotcha that was fixed:** the CLI used not to load `.env`, so diarization
> silently fell back to VAD (whole file became one segment). `clean_voice.py` now
> calls `load_dotenv()` like the backend does.

**From turns to processing segments** (`_merge_segments` + the adaptive
thresholds):
- Convert each turn to sample indices, clip to bounds.
- **Drop** segments shorter than `min_segment_ms` (sub‑threshold noise transients).
- **Tail‑pad** each segment by `tail_pad_ms` so word endings aren't clipped.
- **Merge** segments closer than `merge_gap_ms` so natural pauses inside a
  sentence aren't chopped.

All three thresholds are derived **per file** from its own noise floor and speech
rhythm (`compute_adaptive_thresholds`), so the pipeline self‑tunes to quiet, loud,
clean, or noisy recordings instead of using fixed constants.

---

## 4. Noise removal, stage by stage

### Step 5 — Zero‑background mask + high‑pass
A silent buffer the length of the file is created, and **only** the speech regions
are copied into it. This guarantees absolute silence everywhere outside speech.
Each region is then high‑passed at **120 Hz** (4th‑order Butterworth, capped at
150 Hz) to strip sub‑bass rumble before the network sees it.

### Step 6 — DeepFilterNet3 (the workhorse)
- Runs at the model's native **48 kHz** (the whole masked buffer is resampled once,
  not per segment).
- Files longer than 30 s are processed in **30 s chunks with 2 s overlap** and
  cosine‑blended, bounding memory while staying seamless.
- `atten_lim_db = 30`, `post_filter = false` — strong, broadband suppression that
  removes the bulk of the noise. `post_filter` is **off** because it sharpens the
  mask and gates out quiet consonants.

### Step 7 — MetricGAN+ (the polish)
DeepFilterNet removes the bulk; **MetricGAN+** (`speechbrain/metricgan-plus-voicebank`,
16 kHz) is run on its output as a final neural pass to drive the residual toward
inaudible.

- It's a **bounded spectral mask** (values in [0, 1]) so — unlike a TasNet/SepFormer
  separator — it physically *cannot* amplify or hallucinate energy. No buzz, no
  artifacts.
- **Light & fast:** ~0.16× realtime on CPU (~22 s for a 140 s file). Chunked at
  30 s with 0.5 s overlap for long files.
- **Safe to install:** SpeechBrain‑native; the module bakes in Windows fixes
  (`os.symlink → copy` fallback, force `COPY` link strategy, `use_auth_token`
  strip, `snapshot_download(local_dir=…)`) so no admin/developer mode is needed.
- Config‑gated by `neural_enhancer.enabled`; if loading fails the pipeline logs a
  warning and continues with DeepFilterNet‑only output.

### Step 8 — Re‑mask + fades
DeepFilterNet/MetricGAN+ can bleed a little energy into the silenced regions, so
everything outside the speech segments is zeroed **again**, with **10 ms cosine
fades** at each segment edge to avoid clicks.

### Step 9 — Level & tone finishing
1. **`adaptive_gain_ride`** — per‑frame gain toward a −18 dBFS target, asymmetric
   attack/release smoothing. `MAX_GAIN = 6 dB`, `MIN_GAIN = −3 dB`, and a raised
   `SPEECH_FLOOR (≈ −38 dBFS)` so it lifts *speech* without amplifying the quiet
   noise between words.
2. **`eq_clarity_boost`** — a gentle **+3.5 dB peaking EQ at 1.2 kHz** for
   consonant clarity (a biquad via the bilinear transform).
3. **Final loudness normalization** — measured over speech‑active samples only,
   scaled to a **−20 dBFS** target and brick‑wall limited to 0.97 peak. This is
   what keeps the output from going *dim* after heavy noise removal.

### Step 9.5 — Voice Beautify (optional, off by default)
A post‑cleaning "master" ([`voice_beautify.py`](../src/voice_beautify.py)) applied to
the **speech segments only**, after all noise removal. It makes the clean voice sound
smooth/natural instead of "boxy / broken‑speaker", and is **SNR‑guarded so it can
never add noise back**:

1. **Tone EQ** — gentle corrective curve (tame low‑mid boom, add clarity, de‑harsh).
   Linear filtering → mathematically preserves SNR.
2. **Leveler** — *downward‑only* compression (tames loud jumps, never boosts quiet
   parts or the noise floor) + one linear makeup → even, broadcast‑consistent level.
3. **Air** — a **natural** high‑band extension above 8 kHz, output at 24 kHz. It is
   **adaptive**: it scales to the input's *own* HF energy (an anchor) and uses
   smooth spectral translation, so a band‑limited input (e.g. WhatsApp/Opus) gets
   almost none and can't grow a harsh shelf. Gated to speech.
4. **Loudness + true‑peak limit**, then a re‑mask to keep the gaps perfectly silent.

**Safety:** tone (linear) + downward compression + linear makeup are SNR‑preserving
by construction; the air is speech‑gated and self‑limiting; and a guard measures
speech‑to‑noise before/after and auto‑disables a stage (or the whole thing) if it
would drop SNR beyond a small budget. `beautify.enabled: false` (the default) = the
output is byte‑identical to the raw DeepFilterNet→MetricGAN+ result.

### Step 10 — Output
Saved as 16‑bit WAV (24 kHz when beautify+air is on, else 16 kHz). If ASR is enabled
it transcribes (per speaker when diarized); if the input was video, the cleaned audio
is remuxed back.

---

## 5. How we got here — the engineering journey

The final chain wasn't the first attempt. Each change was driven by a measured
problem:

### Problem 1 — "Syllables are missing"
DeepFilterNet over‑suppresses **quiet, high‑frequency speech** (consonants,
fricatives, plosives). Measurement: ~16 % of speech frames were attenuated by
> 12 dB; the cleaned envelope plunged into −45…−60 dB notches between vowels.

➡ **Fix:** lower `atten_lim_db` and blend a little of the original back
("dry mix"). Syllable loss dropped from 16 % to < 1 %.

### Problem 2 — "Now there's too much noise"
The dry mix was **full‑band**, so it re‑introduced the original's noise — which is
dominated by **low‑frequency rumble (0–500 Hz)**. Key insight from spectral
analysis: **the lost syllables are high‑frequency, but the noise is
low‑frequency — they don't overlap.**

➡ **Fixes (DSP):** high‑pass the dry mix so it only restores HF consonants;
a low‑band‑only `noisereduce` pass for residual rumble; tame the gain‑rider so it
stops lifting the noise floor; add the final loudness normalization. Rumble fell
~8 dB and SNR rose, words intact — but it still wasn't "zero".

### Problem 3 — "I want zero noise — use a separator"
We evaluated separator/enhancer models **on CPU, with measurements**, not vibes:

| Model | Speed (140 s file) | Result | Verdict |
|-------|--------------------|--------|---------|
| **SepFormer** (`sepformer-dns4-16k`) | ~17 min (7.3× realtime) | severe low‑freq buzz (gap +48 dB) | ❌ too heavy + artifacts |
| **DPRNN‑TasNet** | (lighter) | only in **Asteroid**, not SpeechBrain; install risks the torch env | ❌ not viable safely |
| **MetricGAN+** | **~22 s (0.16× realtime)** | gap −40…−61 dB, no artifacts | ✅ **chosen** |

We then picked the **chain order** by experiment — checking both noise *and*
consonant preservation:

| Chain | Speech‑to‑noise | Consonants (words) |
|-------|-----------------|--------------------|
| MetricGAN+ alone | 24.9 dB | −20.0 (too soft) |
| **DeepFilterNet → MetricGAN+** | **40.0 dB** | **−16.9 (intact)** |
| MetricGAN+ → DeepFilterNet | 43.5 dB | −21.0 (too soft) |

**DeepFilterNet → MetricGAN+** wins: DFN removes the bulk, MetricGAN+ polishes,
and consonants stay closest to the original. We also confirmed that trying to
restore consonants fully (an extra HF dry‑mix) costs ~15 dB of SNR — so plain
DFN→MetricGAN+ is the optimal clean‑vs‑words operating point. The full‑band dry
mix and low‑band denoise were therefore **disabled** (MetricGAN+ replaces them),
but they remain in the code as config‑gated options.

---

## 6. Configuration reference

The knobs that control all of the above ([`config.yaml`](../config.yaml)):

```yaml
deepfilternet:
  atten_lim_db: 30        # DeepFilterNet suppression strength
  post_filter: false      # off → preserves quiet consonants
  dry_wet_mix: 0.0        # original blended back (OFF — MetricGAN+ handles it)
  dry_mix_hpf_hz: 800     # if dry mix is used, only restore above this Hz

neural_enhancer:
  enabled: true           # MetricGAN+ final polish (set false → DFN‑only)
  model: "metricgan-plus-voicebank"

low_band_denoise:
  enabled: false          # low‑freq‑only rumble scrub (OFF — MetricGAN+ handles it)
  cutoff_hz: 700
  strength: 0.85

beautify:                 # optional post‑cleaning master (speech only); OFF by default
  enabled: false
  target_loudness_dbfs: -19
  max_snr_drop_db: 6      # guard: auto‑disable a stage if speech‑to‑noise drops more
  tone:    { enabled: true }
  leveler: { enabled: true, strength: 0.7, gate_dbfs: -50 }
  air:     { enabled: true, output_sr: 24000, amount_db: -9 }  # dB below the input's own HF

diarization:
  enabled: true
  min_speakers: 1
  max_speakers: 10
```

**Tuning cheatsheet**
- Want it *even* more aggressive? Leave `neural_enhancer.enabled: true` (it's
  already at the "black background" point); a second pass is possible but rarely
  needed.
- Want DeepFilterNet‑only (fastest, slightly noisier)? `neural_enhancer.enabled: false`.
- Hearing thin/soft consonants? raise `dry_wet_mix` to ~0.15 with
  `dry_mix_hpf_hz: 2000` (restores HF before MetricGAN+ cleans it).

---

## 7. Measured results (overlapped test clip)

| Metric | Original / early build | **Final (DFN → MetricGAN+)** |
|--------|------------------------|------------------------------|
| Speech‑to‑noise | ~10 dB | **~39 dB** |
| Noise floor under speech | −30 dB | **≈ −61 dB** |
| Low‑freq rumble (120–500 Hz) | −2 dB | down ~8 dB |
| Loudness | −20 dBFS | −20.9 dBFS (not dim) |
| Words (consonant band) | reference | −16.9 vs −14 (intact) |
| Processing (140 s, CPU) | — | DFN ~22 s + MetricGAN+ ~22 s (diarization dominates total) |

---

## 8. Honest limitations

- **Not literally zero.** Classical + masking enhancement drives noise *below
  audibility* during speech (~39 dB SNR) but not to mathematical zero. True zero
  requires *re‑generating* the voice (e.g. Resemble‑Enhance / TTS clone), which
  either needs `deepspeed` (won't install cleanly on Windows + CPU) or changes the
  actual words — both rejected to keep the voice authentic.
- **Diarization is the slow part.** pyannote on CPU dominates total runtime
  (several minutes for a few‑minute file); the denoise stages are comparatively
  cheap.
- **Overlap.** This clip's residual was stationary rumble, not a competing voice.
  For genuinely overlapping speakers, a 16 kHz target‑speaker‑extraction stage
  would be the principled addition — deliberately out of scope here.

---

## 9. File map

| File | Role |
|------|------|
| [`src/pipeline.py`](../src/pipeline.py) | Orchestrates steps 1–10; adaptive thresholds, masking, gain/EQ/loudness |
| [`src/diarization.py`](../src/diarization.py) | pyannote 3.1 speaker turns (+ VAD fallback) |
| [`src/deepfilter_processor.py`](../src/deepfilter_processor.py) | DeepFilterNet3 wrapper (native 48 kHz, chunked) |
| [`src/metricgan_processor.py`](../src/metricgan_processor.py) | MetricGAN+ enhancement (+ Windows/HF compat patches) |
| [`src/voice_beautify.py`](../src/voice_beautify.py) | Optional post‑cleaning master: tone EQ, leveler, adaptive air (SNR‑guarded) |
| [`src/vad_processor.py`](../src/vad_processor.py) | WebRTC VAD fallback speech detection |
| [`src/media_loader.py`](../src/media_loader.py) | Load/resample/save, video remux |
| [`config.yaml`](../config.yaml) | All tunable parameters |
