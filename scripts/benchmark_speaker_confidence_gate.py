"""
Throwaway benchmark - NOT part of the pipeline or test suite.

Measures real wall-clock cost of the batched speaker-embedding similarity
check speaker_confidence_gate.py's similarity_curve() will perform, on a
real multi-minute lecture file, on THIS machine's CPU. Exists specifically
to answer one question before shipping a default: is
speaker_confidence_gate.require_gpu: false actually safe, or does this
need require_gpu: true like target_voice_isolation (measured at ~7x
realtime for a different, heavier model in that case - see
docs/NOISE_REMOVAL_AND_DIARIZATION.md "Problem 3")?

Also doubles as the first real proof this embedding-loading path
(PretrainedSpeakerEmbedding via hf_hub_download) works at all on a plain
Windows/CPU box - so far it's only been proven live on the Kaggle GPU
worker (require_gpu: true there).

Usage:
    venv\\Scripts\\python.exe scripts\\benchmark_speaker_confidence_gate.py [path/to/audio]

Defaults to whatever real lecture audio it can find under outputs/ or
data/ if no path is given.
"""

import os
import sys
import time
import glob

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import numpy as np
import torch

WINDOW_S = 0.75
HOP_S = 0.2
BATCH_SIZE = 32
EMBEDDING_MODEL = "pyannote/wespeaker-voxceleb-resnet34-LM"
SR = 16000


def find_default_audio():
    candidates = []
    for pattern in (
        "outputs/cleaned_*.wav",
        "outputs/original_*.mp3",
        "data/lectures/../..*",
    ):
        candidates.extend(
            glob.glob(os.path.join(os.path.dirname(__file__), "..", pattern))
        )
    candidates = [c for c in candidates if os.path.getsize(c) > 2_000_000]
    if not candidates:
        raise SystemExit(
            "No suitable audio file found automatically - pass a path explicitly:\n"
            "  venv\\Scripts\\python.exe scripts\\benchmark_speaker_confidence_gate.py <path>"
        )
    # Prefer the longest file (closest to a real multi-minute lecture).
    return max(candidates, key=os.path.getsize)


def main():
    audio_path = sys.argv[1] if len(sys.argv) > 1 else find_default_audio()
    print(f"Benchmark audio: {audio_path}")

    import librosa

    y, _ = librosa.load(audio_path, sr=SR, mono=True)
    duration_s = len(y) / SR
    print(f"Duration: {duration_s:.1f}s")

    # Build a real SpeakerDiarization() first, purely to get its already-
    # applied huggingface_hub/torchaudio/speechbrain compat monkeypatches
    # for free (see diarization.py::_load_model()) and its ACTUAL embedding
    # model name (dia.pipeline.embedding) rather than assuming one - this
    # is also exactly how TargetVoiceIsolator/SpeakerConfidenceGate get it
    # in production.
    print(
        "Loading SpeakerDiarization() first (for its compat patches + real embedding name)..."
    )
    from diarization import SpeakerDiarization

    dia = SpeakerDiarization()
    if dia.pipeline is None:
        raise SystemExit(
            "SpeakerDiarization failed to load (check HF_TOKEN in .env) - "
            "can't benchmark the embedding model without it."
        )
    embedding_model_name = getattr(dia.pipeline, "embedding", EMBEDDING_MODEL)
    print(f"Actual embedding model in use: {embedding_model_name}")

    print(f"Loading embedding model ({embedding_model_name}) on cpu ...")
    load_start = time.time()
    from pyannote.audio.pipelines.speaker_verification import (
        PretrainedSpeakerEmbedding,
    )

    embedder = PretrainedSpeakerEmbedding(
        embedding_model_name, device=torch.device("cpu")
    )
    load_elapsed = time.time() - load_start
    print(f"Model load time: {load_elapsed:.2f}s (one-time cost, not per-file)")

    window_samples = int(WINDOW_S * SR)
    hop_samples = int(HOP_S * SR)
    starts = list(range(0, max(1, len(y) - window_samples), hop_samples))
    windows = [y[s : s + window_samples] for s in starts]
    # Pad the last few windows if the file doesn't divide evenly.
    windows = [
        w if len(w) == window_samples else np.pad(w, (0, window_samples - len(w)))
        for w in windows
    ]
    print(f"Total windows: {len(windows)} (window={WINDOW_S}s, hop={HOP_S}s)")

    n_batches = (len(windows) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"Batches: {n_batches} (batch_size={BATCH_SIZE})")

    embed_start = time.time()
    embeddings = []
    with torch.no_grad():
        for i in range(0, len(windows), BATCH_SIZE):
            batch = windows[i : i + BATCH_SIZE]
            tensor = torch.from_numpy(np.stack(batch)).float().unsqueeze(1)  # (B,1,T)
            emb = embedder(tensor)  # (B, dimension) numpy array
            embeddings.append(emb)
    embed_elapsed = time.time() - embed_start

    total_embeddings = sum(e.shape[0] for e in embeddings)
    rtf = embed_elapsed / duration_s

    print()
    print("=" * 60)
    print(f"RESULT: {total_embeddings} embeddings computed in {embed_elapsed:.2f}s")
    print(f"        (excludes one-time {load_elapsed:.2f}s model load)")
    print(f"        RTF (embedding time / audio duration): {rtf:.3f}x")
    print(f"        Projected added time for a 300s file: {rtf*300:.1f}s")
    print("=" * 60)
    if rtf < 0.2:
        print(
            "=> Comfortably sub-realtime. require_gpu: false looks SAFE for the shipped default."
        )
    elif rtf < 1.0:
        print(
            "=> Sub-realtime but with real overhead. Consider whether the added time "
            "is acceptable next to this pipeline's existing (diarization-dominated) runtime."
        )
    else:
        print(
            "=> AT OR ABOVE realtime on CPU. Do NOT ship require_gpu: false - default to "
            "require_gpu: true like target_voice_isolation instead."
        )


if __name__ == "__main__":
    main()
