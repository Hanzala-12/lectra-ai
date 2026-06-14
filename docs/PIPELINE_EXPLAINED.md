# Lectra AI — Noise Removal Pipeline (Full Explanation)

A plain-language, point-by-point walkthrough of the whole speech-cleaning process —
written so you can read it top-to-bottom and explain it to another person.

For the deeper technical version (parameters, measurements, engineering decisions),
see [NOISE_REMOVAL_AND_DIARIZATION.md](NOISE_REMOVAL_AND_DIARIZATION.md).

---

## 0. The core idea (one-sentence version)

> "We find exactly *when* each person is speaking, then surgically clean only the
> speech with two AI denoisers stacked together, put it on a perfectly silent
> background, and level it — so the output is clean voice with true silence in between."

**The key insight that shapes everything:** noise that sits *between* words is easy
(just silence it); noise *mixed into* the voice is the hard part, so we use AI models
for that and never touch the parts that aren't speech.

---

## 1. Load the audio
- Accept any audio/video file (mp3, wav, mp4, …).
- Convert to **mono** and resample to **16 kHz** (the rate the speech models work at).
- **Why:** one consistent format so every later stage behaves predictably.

## 2. Analyze the file (adaptive thresholds)
- Measure the file's *own* **noise floor** (quiet 5%) and **speech level** (loud 70%).
- From those, auto-compute: a **silence threshold**, a **minimum speech length**, a
  **merge gap**, and a **tail padding**.
- **Why:** every recording is different (quiet, loud, noisy). Instead of fixed numbers,
  the pipeline **tunes itself to each file**.

## 3. Speaker Diarization — "who speaks when"
- Run **pyannote 3.1** (a deep-learning model) to split the audio into **speaker turns**
  (e.g. SPEAKER_00 from 0–4 s, SPEAKER_01 from 4–7 s…).
- This serves **two jobs**:
  1. It tells us **which regions are actually speech** (everything else = silence to remove).
  2. Later it lets transcription run **per speaker** (no cross-talk confusion).
- **Fallback:** if the model/token is unavailable, a simpler **VAD** (Voice Activity
  Detector) finds speech instead, so it never fully fails.

## 4. Build clean speech segments
- Convert the speaker turns into precise start/end sample positions.
- **Drop** segments that are too short (noise blips, not real words).
- **Pad** the end of each segment slightly (so word endings aren't clipped).
- **Merge** segments that are very close together (don't chop a sentence at a natural pause).
- **Why:** turn raw model output into clean, natural speech chunks.

## 5. Put speech on a silent background + remove rumble
- Create a buffer of **pure digital silence** the length of the file.
- Copy **only the speech segments** into it (everything outside stays absolute silence).
- Apply a **120 Hz high-pass filter** to each segment (removes low-frequency rumble/hum
  before the AI sees it).
- **Why:** this single step eliminates *all* noise that happens between words/sentences —
  that's why the gaps are dead silent.

## 6. Stage 1 denoiser — DeepFilterNet3 (the heavy lifter)
- Upsample the speech to **48 kHz** (the model's native rate) and run **DeepFilterNet3**,
  a deep-learning noise-suppression model.
- Settings: strong suppression (`atten_lim_db = 30`), `post_filter` **off** (post-filter
  would gate out quiet consonants).
- Long files are processed in **30-second chunks with 2-second overlaps**, blended
  smoothly (keeps memory low, no seams).
- **Why:** removes the *bulk* of the noise that's mixed into the voice.

## 7. Stage 2 denoiser — MetricGAN+ (the polish)
- Run **MetricGAN+** (a SpeechBrain model) on DeepFilterNet's output as a **second,
  finishing pass**.
- It's a **bounded spectral mask** (values 0–1) → it can only *attenuate*, never invent
  energy → **no buzzing/robotic artifacts**.
- Light and **faster-than-real-time on CPU**.
- **Why:** DeepFilterNet removes the bulk; MetricGAN+ drives the leftover noise down to
  **near-inaudible (~39 dB speech-to-noise)** while keeping the words intact.
- *(This two-model chain, **DFN → MetricGAN+**, was chosen by measurement — it preserved
  consonants better than either model alone.)*

## 8. Re-mask + smooth edges
- The denoisers can bleed a tiny bit of sound into the silent gaps, so we **zero
  everything outside the speech segments again**.
- Apply **10 ms fade-in/fade-out** at each segment edge.
- **Why:** guarantees clean silence and prevents "click" sounds at the joins.

## 9. Level & tone finishing
- **Gain-riding:** gently evens out the volume frame-by-frame (lifts speech, *not* the
  noise between words).
- **Clarity EQ:** a small **+3.5 dB boost at 1.2 kHz** for consonant intelligibility.
- **Loudness normalization:** bring the whole thing to a consistent **−20 dBFS** target
  and hard-limit the peaks (so it's never clipped and never "dim").
- **Why:** makes the result sound consistent and properly loud, like a finished recording.

## 10. (Optional) Voice Beautify
- An **off-by-default** "mastering" stage: adaptive tone EQ + loudness leveler + subtle
  high-frequency "air".
- It's **SNR-guarded** — it auto-disables itself if it would ever add noise back.
- **Why:** makes the voice smoother/fuller when wanted; left off by default so the output
  stays exactly the clean denoised voice.

## 11. Save & extras
- Write the final **16-bit WAV**.
- **Optional:** run **Whisper** speech-to-text (transcribes per speaker, using the
  diarization), and if the input was a video, **merge the cleaned audio back** into it.

---

## The 4 talking points to remember (for explaining quickly)
1. **Detect speech precisely** (diarization) → know exactly what to keep.
2. **Silence everything else** → all between-word noise just disappears.
3. **Two AI denoisers stacked** (DeepFilterNet3 → MetricGAN+) → clean the noise *inside*
   the voice without killing the words.
4. **Level & finish** → consistent, broadcast-ready clean voice.

## A simple analogy (for non-technical people)
> "Imagine a noisy classroom recording. First we mark exactly when someone is talking and
> mute everything else — so all the background chatter in the pauses is gone. Then, for the
> parts where someone *is* talking, we run it through two smart filters: the first scrubs
> most of the noise, the second polishes whatever's left. Finally we balance the volume so
> every word is clear and even. The result: just the voice, on silence."

---

## Quick reference — stage → tool

| # | Stage | Tool / method |
|---|-------|---------------|
| 1 | Load → mono → 16 kHz | media loader |
| 2 | Adaptive thresholds | per-file statistics |
| 3 | Diarization (who speaks when) | pyannote 3.1 (VAD fallback) |
| 4 | Build speech segments | drop / pad / merge |
| 5 | Silent-background mask + 120 Hz HPF | DSP |
| 6 | Stage-1 denoise | DeepFilterNet3 (48 kHz) |
| 7 | Stage-2 denoise (polish) | MetricGAN+ (SpeechBrain) |
| 8 | Re-mask + fades | DSP |
| 9 | Gain-ride → clarity EQ → loudness | DSP |
| 10 | (optional) Voice Beautify | tone / leveler / air |
| 11 | Save (+ Whisper transcript, + video remux) | output |

## One-line tech summary (for a CV / report)
> *An open, CPU-only speech-cleaning pipeline: pyannote speaker diarization drives
> segment-level masking, a DeepFilterNet3 → MetricGAN+ two-stage neural denoiser cleans
> the speech, followed by DSP leveling/EQ/loudness normalization — plus optional Whisper
> transcription and video remux.*
