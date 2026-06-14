"""
Voice Beautify — post-cleaning master for the speech segments only.

Runs AFTER noise removal + diarization (it never touches those stages). It makes
the already-clean voice sound smooth/natural instead of "boxy / broken-speaker":

  1. Tone EQ        — gentle corrective curve (tame low-mid boom, add clarity,
                      de-harsh the presence bump). LINEAR → cannot change SNR.
  2. Leveler        — even out loudness (broadcast-consistent) with a noise gate
                      so the residual floor is never lifted.
  3. Air (optional) — harmonic high-band extension above 8 kHz, speech-gated and
                      subtle, output at a higher sample rate for "air"/brightness.
  4. Loudness + true-peak limit, then re-mask to guarantee silence between speech.

Bulletproof design: operates only on speech (silence stays zero), tone is linear,
the leveler gate sits above the residual floor, and a guard checks the noise floor
did not rise. Pure deterministic DSP — no learned model that can hallucinate.
"""

import logging
import numpy as np
import scipy.signal as sig

logger = logging.getLogger(__name__)


def _peaking(f0, gain_db, q, sr):
    """RBJ peaking-EQ biquad -> (b, a)."""
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * np.pi * f0 / sr
    alpha = np.sin(w0) / (2 * q)
    cw = np.cos(w0)
    b0 = 1 + alpha * A
    b1 = -2 * cw
    b2 = 1 - alpha * A
    a0 = 1 + alpha / A
    a1 = -2 * cw
    a2 = 1 - alpha / A
    return np.array([b0, b1, b2]) / a0, np.array([1.0, a1 / a0, a2 / a0])


def _shelf(f0, gain_db, sr, kind="high"):
    """RBJ shelving biquad -> (b, a)."""
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * np.pi * f0 / sr
    cw, sw = np.cos(w0), np.sin(w0)
    alpha = sw / 2 * np.sqrt((A + 1 / A) * (1 / 0.9 - 1) + 2)
    tsa = 2 * np.sqrt(A) * alpha
    if kind == "high":
        b0 = A * ((A + 1) + (A - 1) * cw + tsa)
        b1 = -2 * A * ((A - 1) + (A + 1) * cw)
        b2 = A * ((A + 1) + (A - 1) * cw - tsa)
        a0 = (A + 1) - (A - 1) * cw + tsa
        a1 = 2 * ((A - 1) - (A + 1) * cw)
        a2 = (A + 1) - (A - 1) * cw - tsa
    else:  # low shelf
        b0 = A * ((A + 1) - (A - 1) * cw + tsa)
        b1 = 2 * A * ((A - 1) - (A + 1) * cw)
        b2 = A * ((A + 1) - (A - 1) * cw - tsa)
        a0 = (A + 1) + (A - 1) * cw + tsa
        a1 = -2 * ((A - 1) + (A + 1) * cw)
        a2 = (A + 1) + (A - 1) * cw - tsa
    return np.array([b0, b1, b2]) / a0, np.array([1.0, a1 / a0, a2 / a0])


class VoiceBeautifier:
    def __init__(self, config: dict, sample_rate: int = 16000):
        b = config.get("beautify", {}) if config else {}
        self.enabled = bool(b.get("enabled", False))
        self.sr = sample_rate
        self.target_dbfs = float(b.get("target_loudness_dbfs", -19.0))
        self.tone_enabled = bool(b.get("tone", {}).get("enabled", True))
        lev = b.get("leveler", {})
        self.lev_enabled = bool(lev.get("enabled", True))
        self.lev_strength = float(lev.get("strength", 0.7))
        self.gate_dbfs = float(lev.get("gate_dbfs", -50.0))
        air = b.get("air", {})
        self.air_enabled = bool(air.get("enabled", True))
        self.air_out_sr = int(air.get("output_sr", 24000))
        self.air_amount_db = float(air.get("amount_db", -9.0))
        # Guard: how much the speech-to-noise ratio is allowed to drop (dB).
        self.max_snr_drop_db = float(b.get("max_snr_drop_db", 6.0))

    # ---- measurement helpers -------------------------------------------------
    def _env(self, y, frame=800, hop=160):
        return np.array(
            [
                np.sqrt(np.mean(y[i : i + frame] ** 2) + 1e-12)
                for i in range(0, max(1, len(y) - frame), hop)
            ]
        )

    def _noise_floor_db(self, y):
        """True noise floor = median of the quietest 10% of NON-ZERO frames.

        This targets the inter-word residual (the real noise), NOT quiet speech.
        Using a plain low percentile would conflate quiet syllables with noise and
        mis-read intended loudness leveling as 'added noise'.
        """
        e = self._env(y)
        nz = np.sort(e[e > 1e-5])
        if nz.size == 0:
            return -120.0
        return 20 * np.log10(np.median(nz[: max(1, len(nz) // 10)]) + 1e-12)

    def _snr_db(self, y):
        """Speech-to-noise: 70th-pct speech level minus the true noise floor."""
        e = self._env(y)
        nz = e[e > 1e-5]
        if nz.size == 0:
            return 120.0
        speech = 20 * np.log10(np.percentile(nz, 70) + 1e-12)
        return speech - self._noise_floor_db(y)

    def _loudness_spread_db(self, y):
        e = self._env(y)
        a = e[e > np.percentile(e, 40)]
        if a.size == 0:
            return 0.0
        d = 20 * np.log10(a + 1e-12)
        return float(np.percentile(d, 90) - np.percentile(d, 10))

    # ---- stages --------------------------------------------------------------
    def _tone(self, y):
        """Gentle corrective curve measured from the cleaned output's LTAS."""
        bands = [
            _peaking(420, -2.5, 1.0, self.sr),  # tame low-mid boom (boxy)
            _peaking(2600, +2.0, 0.8, self.sr),  # upper-mid clarity / presence
            _peaking(5200, -1.5, 1.2, self.sr),  # de-harsh the presence bump
            _shelf(180, +1.5, self.sr, "low"),  # restore a little warmth/body
        ]
        out = y.astype(np.float32)
        for b, a in bands:
            out = sig.lfilter(b, a, out).astype(np.float32)
        return out

    def _level(self, y):
        """Even out loudness by DOWNWARD compression only (tame the loud jumps).

        Gain is always <= 0 dB, applied only ABOVE the threshold, so quiet
        syllables and the residual noise floor are NEVER boosted. The lost level
        is restored later by a single linear makeup (the loudness stage), which
        preserves SNR exactly. This is what makes leveling safe re: noise.
        """
        frame = int(0.05 * self.sr)
        hop = int(0.010 * self.sr)
        env = np.array(
            [
                np.sqrt(np.mean(y[i : i + frame] ** 2) + 1e-12)
                for i in range(0, max(1, len(y) - frame), hop)
            ]
        )
        env_db = 20 * np.log10(env + 1e-12)
        active = env_db > self.gate_dbfs
        if active.sum() < 4:
            return y
        # Compress the loud excursions toward the 60th percentile of speech.
        threshold_db = np.percentile(env_db[active], 60)
        ratio = 3.0
        over = np.maximum(0.0, env_db - threshold_db)  # only loud frames
        gain_db = -over * (1.0 - 1.0 / ratio) * self.lev_strength  # always <= 0
        # smooth (fast attack on more reduction, slow release) — no pumping
        atk, rel = 0.010, 0.20
        a_a = 1 - np.exp(-hop / (atk * self.sr))
        a_r = 1 - np.exp(-hop / (rel * self.sr))
        sm = np.zeros_like(gain_db)
        for i in range(1, len(gain_db)):
            coef = a_a if gain_db[i] < sm[i - 1] else a_r  # more negative = attack
            sm[i] = sm[i - 1] + coef * (gain_db[i] - sm[i - 1])
        sm = np.minimum(sm, 0.0)  # guarantee downward-only after smoothing
        gain = 10 ** (sm / 20.0)
        g = np.interp(
            np.arange(len(y)), np.arange(len(gain)) * hop, gain, right=gain[-1]
        )
        return (y * g.astype(np.float32)).astype(np.float32)

    def _speech_mask(self, n, segments, sr):
        """1.0 inside speech (with 10 ms fades), 0.0 in gaps — at sample rate sr."""
        m = np.zeros(n, dtype=np.float32)
        fade = int(0.010 * sr)
        for s, e in segments:
            s2 = max(0, int(s * sr / self.sr))
            e2 = min(n, int(e * sr / self.sr))
            if e2 <= s2:
                continue
            m[s2:e2] = 1.0
            if e2 - s2 > 2 * fade:
                m[s2 : s2 + fade] = np.linspace(0, 1, fade)
                m[e2 - fade : e2] = np.linspace(1, 0, fade)
        return m

    def _add_air(self, y16, segments):
        """Extend the high band > 8 kHz as a NATURAL continuation of the existing
        speech HF — adaptive, smooth, and self-limiting.

        Key safety properties (learned from band-limited inputs like WhatsApp/Opus):
        - Air is scaled to the EXISTING top-octave energy (an "anchor"), NOT the
          whole-program level. A band-limited voice has a low anchor → it gets
          almost no air, so it can't grow a harsh synthetic shelf.
        - It uses single-sideband spectral translation (Hilbert) instead of
          rectification, so the band's natural downward slope is preserved (no
          top-heavy sizzle).
        - It is tilted down and capped to sit BELOW the anchor, and gated to speech.
        """
        out_sr = self.air_out_sr
        up = sig.resample_poly(y16, out_sr, self.sr).astype(np.float32)

        # Anchor: existing energy just below the 8 kHz edge (5-7 kHz).
        anchor = sig.sosfilt(
            sig.butter(4, [5000, 7000], btype="band", output="sos", fs=out_sr), up
        ).astype(np.float32)
        voiced = np.abs(up) > 1e-4
        anchor_rms = (
            float(np.sqrt(np.mean(anchor[voiced] ** 2) + 1e-12))
            if voiced.any()
            else 0.0
        )
        if anchor_rms < 1e-4:
            logger.info(
                "[beautify] air skipped — input has little HF to extend (band-limited)"
            )
            return up, out_sr

        # Source band to translate upward (preserves its natural shape/slope).
        src = sig.sosfilt(
            sig.butter(4, [3800, 7500], btype="band", output="sos", fs=out_sr), up
        ).astype(np.float32)
        # SSB up-shift by 4 kHz: 3.8-7.5k -> 7.8-11.5k, slope preserved.
        analytic = sig.hilbert(src)
        t = np.arange(len(src)) / out_sr
        shifted = np.real(analytic * np.exp(2j * np.pi * 4000.0 * t)).astype(np.float32)
        air = sig.sosfilt(
            sig.butter(
                4,
                [8000, min(12000, out_sr / 2 - 600)],
                btype="band",
                output="sos",
                fs=out_sr,
            ),
            shifted,
        ).astype(np.float32)
        # downward tilt so the very top rolls off (natural, not sizzly)
        air = sig.sosfilt(
            sig.butter(1, 9500, btype="low", output="sos", fs=out_sr), air
        ).astype(np.float32)

        # Scale so the air sits BELOW the anchor by |amount_db| (amount_db is negative).
        air_rms = float(np.sqrt(np.mean(air**2) + 1e-12))
        if air_rms > 1e-9:
            target = anchor_rms * 10 ** (self.air_amount_db / 20.0)
            air *= target / air_rms
        air *= self._speech_mask(len(air), segments, out_sr)  # speech only
        return (up + air).astype(np.float32), out_sr

    def _loudness_limit(self, y):
        a = y[np.abs(y) > 1e-4]
        if a.size:
            rms = np.sqrt(np.mean(a**2))
            if rms > 1e-6:
                y = y * np.clip(10 ** (self.target_dbfs / 20) / rms, 0.25, 8.0)
        peak = float(np.max(np.abs(y))) if y.size else 0.0
        if peak > 0.97:
            y = y * (0.97 / peak)
        return y.astype(np.float32)

    def _merge_segments(self, segments, gap_s=0.15):
        """Merge segments separated by less than gap_s (in 16 kHz sample units)."""
        if not segments:
            return []
        segs = sorted((int(s), int(e)) for s, e in segments if e > s)
        gap = int(gap_s * self.sr)
        merged = [list(segs[0])]
        for s, e in segs[1:]:
            if s <= merged[-1][1] + gap:
                merged[-1][1] = max(merged[-1][1], e)
            else:
                merged.append([s, e])
        return [tuple(m) for m in merged]

    def _remask(self, y, segments, sr):
        """Zero everything outside speech, 10 ms cosine fades (silence guarantee)."""
        fade = int(0.010 * sr)
        out = np.zeros(len(y), dtype=np.float32)
        for s, e in segments:
            s2, e2 = int(s * sr / self.sr), int(e * sr / self.sr)
            s2 = max(0, s2)
            e2 = min(len(y), e2)
            if e2 <= s2:
                continue
            seg = y[s2:e2].copy()
            if e2 - s2 > 2 * fade:
                seg[:fade] *= 0.5 * (1 - np.cos(np.linspace(0, np.pi, fade)))
                seg[-fade:] *= 0.5 * (1 + np.cos(np.linspace(0, np.pi, fade)))
            out[s2:e2] = seg
        return out

    # ---- entry point ---------------------------------------------------------
    def process(self, audio: np.ndarray, segments):
        """Returns (beautified_audio, output_sample_rate)."""
        if not self.enabled:
            return audio, self.sr
        audio = audio.astype(np.float32)
        segments = self._merge_segments(segments)  # robust to fragmented input
        snr_before = self._snr_db(audio)
        spread_before = self._loudness_spread_db(audio)

        def run(with_air):
            y = audio.copy()
            if self.tone_enabled:
                y = self._tone(y)
            if self.lev_enabled:
                y = self._level(y)
            out_sr = self.sr
            if with_air and self.air_enabled:
                y, out_sr = self._add_air(y, segments)
            y = self._loudness_limit(y)
            # Measure SNR BEFORE the re-mask: the re-mask only zeroes/fades samples,
            # so it can't add noise — measuring after it just pollutes the floor
            # metric with fade-transition frames. The air is already speech-gated.
            ymeas = sig.resample_poly(y, self.sr, out_sr) if out_sr != self.sr else y
            snr = self._snr_db(ymeas)
            spread = self._loudness_spread_db(ymeas)
            y = self._remask(y, segments, out_sr)
            return y, out_sr, snr, spread

        y, out_sr, snr_after, spread_after = run(with_air=True)
        logger.info(
            f"[beautify] loudness spread {spread_before:.1f}->{spread_after:.1f} dB | "
            f"SNR {snr_before:.1f}->{snr_after:.1f} dB (drop {snr_before - snr_after:+.1f}) | out_sr {out_sr}"
        )
        # --- safety guard: SNR must be preserved (no noise added) ---
        if snr_before - snr_after > self.max_snr_drop_db:
            logger.warning(
                f"[beautify] SNR dropped {snr_before - snr_after:.1f} dB "
                f"(> {self.max_snr_drop_db}); disabling air for safety"
            )
            y, out_sr, snr_after2, _ = run(with_air=False)
            if snr_before - snr_after2 > self.max_snr_drop_db:
                logger.warning(
                    "[beautify] SNR still degraded without air; returning input unchanged"
                )
                return audio, self.sr
        return y, out_sr
