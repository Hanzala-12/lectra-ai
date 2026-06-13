"""
MetricGAN+ Speech Enhancement Module
A light, fast (faster-than-realtime on CPU) neural denoiser that isolates voice
from noise via a bounded spectral mask. Used as the final neural polish after
DeepFilterNet to drive the noise floor toward inaudible without artifacts.

Model: speechbrain/metricgan-plus-voicebank (16 kHz).
"""

import os
import shutil
import logging
import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Windows / huggingface_hub compatibility patches. Applied at import so any
# SpeechBrain model download works without admin/developer-mode symlinks and
# regardless of huggingface_hub version (use_auth_token -> token rename).
# ---------------------------------------------------------------------------
def _install_compat_patches():
    # os.symlink -> copy fallback (Windows blocks symlink without privilege)
    _orig_symlink = os.symlink

    def _symlink_or_copy(src, dst, *a, **k):
        try:
            _orig_symlink(src, dst, *a, **k)
        except OSError:
            try:
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy(src, dst)
            except shutil.SameFileError:
                pass

    os.symlink = _symlink_or_copy
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")

    try:
        import huggingface_hub as _hf
        import functools as _ft

        for _name in ("hf_hub_download", "snapshot_download"):
            _orig = getattr(_hf, _name, None)
            if _orig is None:
                continue

            def _make(o):
                @_ft.wraps(o)
                def _wrapped(*a, **k):
                    k.pop("use_auth_token", None)
                    return o(*a, **k)

                return _wrapped

            setattr(_hf, _name, _make(_orig))
    except Exception:
        pass


class MetricGANProcessor:
    """SpeechBrain MetricGAN+ enhancement wrapper."""

    REPO = "speechbrain/metricgan-plus-voicebank"

    def __init__(
        self, model_dir: str = None, device: str = "cpu", chunk_seconds: float = 30.0
    ):
        _install_compat_patches()
        import torch

        self.device = device
        self.sample_rate = 16000
        self.chunk_seconds = chunk_seconds
        self._torch = torch

        if model_dir is None:
            model_dir = os.path.join(
                os.path.dirname(__file__), "..", "models", "metricgan"
            )
        model_dir = os.path.abspath(model_dir)
        os.makedirs(model_dir, exist_ok=True)

        # Download (into local dir, no cache symlinks) if not already present.
        if not os.path.exists(os.path.join(model_dir, "hyperparams.yaml")):
            from huggingface_hub import snapshot_download

            logger.info("Downloading MetricGAN+ model (first use)...")
            snapshot_download(
                self.REPO,
                allow_patterns=["*.yaml", "*.ckpt", "*.bin", "*.txt", "*.py"],
                local_dir=model_dir,
            )

        # Force COPY instead of symlink when SpeechBrain populates savedir.
        import speechbrain.utils.fetching as _fetch

        _ls = _fetch.LocalStrategy
        _orig_link = _fetch.link_with_strategy
        _fetch.link_with_strategy = lambda s, d, st: _orig_link(s, d, _ls.COPY)

        from speechbrain.inference.enhancement import SpectralMaskEnhancement

        logger.info(f"Loading MetricGAN+ on {device}")
        self.model = SpectralMaskEnhancement.from_hparams(
            source=model_dir, savedir=model_dir, run_opts={"device": device}
        )
        logger.info("MetricGAN+ loaded successfully")

    def enhance(self, audio: np.ndarray) -> np.ndarray:
        """Enhance a mono 16 kHz float32 waveform. Chunked to bound memory."""
        torch = self._torch
        audio = audio.astype(np.float32)
        n = len(audio)
        if n == 0:
            return audio

        chunk = int(self.chunk_seconds * self.sample_rate)
        overlap = int(0.5 * self.sample_rate)
        if n <= chunk:
            return self._enhance_one(audio)

        out = np.zeros(n, dtype=np.float32)
        wsum = np.zeros(n, dtype=np.float32)
        step = max(1, chunk - overlap)
        s = 0
        while s < n:
            e = min(n, s + chunk)
            seg = audio[s:e]
            est = self._enhance_one(seg)
            w = np.ones(len(seg), dtype=np.float32)
            if s > 0:
                w[:overlap] = np.linspace(0, 1, overlap, dtype=np.float32)
            if e < n:
                w[-overlap:] = np.minimum(
                    w[-overlap:], np.linspace(1, 0, overlap, dtype=np.float32)
                )
            out[s:e] += est * w
            wsum[s:e] += w
            if e >= n:
                break
            s += step
        nz = wsum > 0
        out[nz] /= wsum[nz]
        return out

    def _enhance_one(self, seg: np.ndarray) -> np.ndarray:
        torch = self._torch
        with torch.no_grad():
            est = self.model.enhance_batch(
                torch.from_numpy(seg).unsqueeze(0), lengths=torch.tensor([1.0])
            )
        return est.squeeze(0).cpu().numpy().astype(np.float32)[: len(seg)]
