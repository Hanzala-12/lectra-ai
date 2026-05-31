# Custom DSP Modules Documentation

## Overview

This document provides detailed API reference, formulas, and usage examples for the five custom DSP modules in Lectra AI.

**Status**: Experimental (disabled by default)  
**Total Lines of Code**: ~2,400 lines  
**Language**: Python 3.10+  
**Dependencies**: NumPy, SciPy, PyWavelets (optional), Numba (optional)

---

## Table of Contents

1. [Audio Quality Metrics](#1-audio-quality-metrics)
2. [Audio Quality Profiler](#2-audio-quality-profiler)
3. [Spectral Restoration](#3-spectral-restoration)
4. [Adaptive Router](#4-adaptive-router)
5. [Optimized Utilities](#5-optimized-utilities)
6. [Integration Guide](#integration-guide)
7. [Configuration](#configuration)
8. [Troubleshooting](#troubleshooting)

---

## 1. Audio Quality Metrics

**File**: `src/audio_quality_metrics.py`  
**Lines**: ~550  
**Purpose**: Evaluate audio processing quality using 9 scientific metrics

### Class: `AudioQualityMetrics`

```python
from src.audio_quality_metrics import AudioQualityMetrics

metrics = AudioQualityMetrics(sample_rate=16000)
```

### Methods

#### `comprehensive_evaluation(clean_audio, processed_audio, sample_rate=None)`

Compute all 9 quality metrics between clean and processed audio.

**Parameters**:
- `clean_audio` (np.ndarray): Reference clean audio (1D, float32)
- `processed_audio` (np.ndarray): Processed/enhanced audio (1D, float32)
- `sample_rate` (int, optional): Sample rate in Hz

**Returns**: Dictionary with keys:
- `snr_db` (float): Signal-to-Noise Ratio in dB
- `psnr_db` (float): Peak Signal-to-Noise Ratio in dB
- `segmental_snr_db` (float): Frame-by-frame SNR average
- `log_spectral_distance` (float): Frequency-domain distortion
- `itakura_saito_distance` (float): Perceptual distance measure
- `correlation_coefficient` (float): Waveform similarity [-1, 1]
- `cepstral_distance` (float): Voice characteristic preservation
- `envelope_distance` (float): Amplitude contour matching
- `overall_quality_score` (float): Composite score [0, 100]

**Example**:
```python
results = metrics.comprehensive_evaluation(clean, processed, 16000)
print(f"Quality Score: {results['overall_quality_score']:.1f}/100")
print(f"SNR: {results['snr_db']:.2f} dB")
```

### Metric Formulas

#### 1. SNR (Signal-to-Noise Ratio)

$$
\text{SNR} = 10 \log_{10} \left( \frac{P_{\text{signal}}}{P_{\text{noise}}} \right)
$$

Where:
- $P_{\text{signal}} = \frac{1}{N} \sum_{n=1}^{N} x_{\text{clean}}^2[n]$
- $P_{\text{noise}} = \frac{1}{N} \sum_{n=1}^{N} (x_{\text{processed}}[n] - x_{\text{clean}}[n])^2$

**Range**: -∞ to +∞ dB (higher is better)

#### 2. PSNR (Peak Signal-to-Noise Ratio)

$$
\text{PSNR} = 10 \log_{10} \left( \frac{\max(|x_{\text{clean}}|)^2}{\text{MSE}} \right)
$$

**Range**: 0 to +∞ dB (higher is better)

#### 3. Segmental SNR

$$
\text{SegSNR} = \frac{1}{M} \sum_{m=1}^{M} \text{SNR}_m
$$

Computed frame-by-frame, more robust to local variations.

#### 4. Log-Spectral Distance (LSD)

$$
\text{LSD} = \sqrt{\frac{1}{KM} \sum_{k,m} \left( \log_{10} |X_{\text{clean}}[k,m]| - \log_{10} |X_{\text{proc}}[k,m]| \right)^2}
$$

**Range**: 0 to +∞ (lower is better)

#### 5. Itakura-Saito Distance

$$
\text{IS} = \frac{1}{KM} \sum_{k,m} \left( \frac{P_{\text{clean}}[k,m]}{P_{\text{proc}}[k,m]} - \log \frac{P_{\text{clean}}[k,m]}{P_{\text{proc}}[k,m]} - 1 \right)
$$

Perceptual distance based on spectral envelopes.

#### 6. Correlation Coefficient

$$
\rho = \frac{\text{cov}(x_{\text{clean}}, x_{\text{proc}})}{\sigma_{\text{clean}} \sigma_{\text{proc}}}
$$

**Range**: -1 to +1 (higher is better)

#### 7. Cepstral Distance

$$
\text{CepDist} = \sqrt{\sum_{q=1}^{Q} (c_{\text{clean}}[q] - c_{\text{proc}}[q])^2}
$$

Where $c[q]$ are cepstral coefficients.

#### 8. Envelope Distance

$$
\text{EnvDist} = \sqrt{\frac{1}{N} \sum_{n=1}^{N} (|H(x_{\text{clean}})[n]| - |H(x_{\text{proc}})[n]|)^2}
$$

Where $H(\cdot)$ is the Hilbert transform.

#### 9. Composite Quality Score

Weighted combination of all metrics, normalized to 0-100 scale:

$$
\text{Score} = 100 \times \sum_{i} w_i \cdot \text{normalize}(\text{metric}_i)
$$

Weights: SNR (20%), PSNR (15%), SegSNR (15%), LSD (10%), IS (10%), Corr (15%), Cep (8%), Env (7%)

---

## 2. Audio Quality Profiler

**File**: `src/audio_quality_profiler.py`  
**Lines**: ~400  
**Purpose**: Analyze input audio characteristics before processing

### Class: `AudioQualityProfiler`

```python
from src.audio_quality_profiler import AudioQualityProfiler

profiler = AudioQualityProfiler(sample_rate=16000, wavelet='db8')
```

### Methods

#### `profile_audio(audio, sample_rate=None)`

Analyze audio and return quality profile.

**Parameters**:
- `audio` (np.ndarray): Input audio (1D, mono)
- `sample_rate` (int, optional): Sample rate in Hz

**Returns**: Dictionary with keys:
- `snr_db` (float): Estimated SNR
- `noise_floor_db` (float): Estimated noise floor level
- `spectral_flatness` (float): Tonality measure [0, 1]
- `spectral_rolloff` (float): Frequency below which 85% of energy
- `zero_crossing_rate` (float): Signal irregularity measure
- `dominant_frequency` (float): Peak frequency in Hz
- `recommended_processing` (str): 'light', 'medium', or 'heavy'

**Example**:
```python
profile = profiler.profile_audio(audio, 16000)
print(f"SNR: {profile['snr_db']:.1f} dB")
print(f"Recommendation: {profile['recommended_processing']}")
```

### Feature Descriptions

#### Wavelet-Based Noise Estimation

Uses PyWavelets for multi-resolution analysis:

$$
\sigma_{\text{noise}} = \frac{\text{median}(|d_3|)}{0.6745}
$$

Where $d_3$ are the highest-frequency detail coefficients from wavelet decomposition.

#### Spectral Flatness (Wiener Entropy)

$$
\text{SF} = \frac{\exp\left(\frac{1}{K} \sum_{k=1}^{K} \log P[k]\right)}{\frac{1}{K} \sum_{k=1}^{K} P[k]}
$$

- SF ≈ 0: Tonal (speech-like)
- SF ≈ 1: Noisy (white noise-like)

#### Spectral Rolloff

Frequency $f_r$ where:

$$
\sum_{k=1}^{k_r} P[k] = 0.85 \sum_{k=1}^{K} P[k]
$$

#### Zero-Crossing Rate

$$
\text{ZCR} = \frac{1}{N-1} \sum_{n=1}^{N-1} \mathbb{1}[\text{sign}(x[n]) \neq \text{sign}(x[n-1])]
$$

Higher ZCR indicates more irregular/noisy signal.

### Processing Recommendation Logic

```
if SNR > 15 dB:
    return 'light'
elif SNR > 5 dB:
    return 'medium'
else:
    return 'heavy'
```

---

## 3. Spectral Restoration

**File**: `src/spectral_restoration.py`  
**Lines**: ~450  
**Purpose**: Restore high-frequency content lost during aggressive noise removal

### Class: `SpectralRestoration`

```python
from src.spectral_restoration import SpectralRestoration

restorer = SpectralRestoration(sample_rate=16000)
```

### Methods

#### `adaptive_restoration(original_audio, denoised_audio, strength='auto')`

Apply adaptive spectral restoration.

**Parameters**:
- `original_audio` (np.ndarray): Original noisy audio
- `denoised_audio` (np.ndarray): Denoised audio (may have lost high frequencies)
- `strength` (str): 'auto', 'light', 'medium', or 'heavy'

**Returns**: Enhanced audio (np.ndarray, float32)

**Example**:
```python
restored = restorer.adaptive_restoration(original, denoised, strength='auto')
```

### Algorithms

#### Pitch Detection (Autocorrelation)

$$
R[\tau] = \sum_{n=0}^{N-\tau-1} x[n] \cdot x[n+\tau]
$$

Pitch frequency:

$$
f_0 = \frac{f_s}{\arg\max_{\tau \in [\tau_{\min}, \tau_{\max}]} R[\tau]}
$$

Search range: 50-500 Hz (typical voice range)

#### Harmonic Synthesis

For detected pitch $f_0$, synthesize harmonics:

$$
x_{\text{synth}}[n] = \sum_{h=1}^{H} a_h \sin(2\pi h f_0 n / f_s)
$$

Where $a_h = 1/h$ (amplitude decreases with harmonic number).

#### Cepstral Envelope Extraction

1. Compute log-magnitude spectrum: $\log |X[k]|$
2. Apply inverse FFT to get cepstrum: $c[q] = \text{IFFT}(\log |X[k]|)$
3. Lifter (keep low quefrency): $c[q] = 0$ for $q > Q_{\max}$
4. Transform back: $\text{envelope} = \exp(\text{FFT}(c[q]))$

#### Adaptive Strength

Automatically estimated based on high-frequency energy loss:

$$
\text{strength} = 0.2 + 0.6 \times \left(1 - \frac{E_{\text{high}}^{\text{denoised}}}{E_{\text{high}}^{\text{original}}}\right)
$$

Where $E_{\text{high}}$ is energy above 2 kHz.

---

## 4. Adaptive Router

**File**: `src/adaptive_router.py`  
**Lines**: ~450  
**Purpose**: Intelligently select processing method based on noise level

### Class: `AdaptiveRouter`

```python
from src.adaptive_router import AdaptiveRouter

router = AdaptiveRouter(sample_rate=16000)
```

### Methods

#### `route_processing(audio, profile, config=None)`

Route audio to appropriate processing method.

**Parameters**:
- `audio` (np.ndarray): Input audio
- `profile` (dict): Audio quality profile from AudioQualityProfiler
- `config` (dict, optional): Configuration dict

**Returns**: Tuple of (processed_audio, method_name)

**Example**:
```python
cleaned, method = router.route_processing(audio, profile)
print(f"Used method: {method}")
```

### Routing Logic

```
SNR > 15 dB  → Spectral Subtraction (fast, light noise)
SNR 5-15 dB  → Wiener Filter (moderate, medium noise)
SNR < 5 dB   → DeepFilterNet required (heavy noise)
```

### Processing Methods

#### Spectral Subtraction

$$
|\hat{X}[k,m]| = \max(|Y[k,m]| - \alpha |\hat{N}[k]|, \beta |Y[k,m]|)
$$

Where:
- $Y[k,m]$: Noisy STFT
- $\hat{N}[k]$: Estimated noise spectrum
- $\alpha = 2.0$: Over-subtraction factor
- $\beta = 0.01$: Spectral floor

#### Wiener Filter

$$
G[k,m] = \frac{\text{SNR}_{\text{prior}}[k,m]}{\text{SNR}_{\text{prior}}[k,m] + 1}
$$

Where:

$$
\text{SNR}_{\text{prior}}[k,m] = \max\left(\frac{|Y[k,m]|^2}{|\hat{N}[k]|^2} - 1, 0\right)
$$

Enhanced spectrum:

$$
\hat{X}[k,m] = G[k,m] \cdot Y[k,m]
$$

---

## 5. Optimized Utilities

**File**: `src/optimized_utils.py`  
**Lines**: ~550  
**Purpose**: CPU-level optimizations using Numba JIT compilation

### Class: `VectorizedAudioProcessor`

```python
from src.optimized_utils import VectorizedAudioProcessor

processor = VectorizedAudioProcessor(sample_rate=16000)
```

### Methods

#### `compute_frame_energies_vectorized(audio, frame_len=512, hop_len=256)`

Compute frame energies using optimized implementation.

**Returns**: Array of frame energies

**Speedup**: 20-64x with Numba

#### `estimate_snr_numba(clean, noisy)`

Estimate SNR using optimized implementation.

**Returns**: SNR in dB

**Speedup**: 10-24x with Numba

#### `fast_rms(audio, frame_len=512)`

Fast RMS calculation using vectorized operations.

**Returns**: Array of RMS values per frame

**Speedup**: 15-30x with Numba

#### `benchmark_optimizations(audio=None, n_iterations=100)`

Benchmark optimized vs original implementations.

**Returns**: Dictionary with benchmark results

**Example**:
```python
results = processor.benchmark_optimizations(audio, n_iterations=50)
print(f"Frame energy speedup: {results['frame_energies']['speedup']:.1f}x")
```

### Optimization Techniques

#### Numba JIT Compilation

```python
@jit(nopython=True, parallel=True, cache=True)
def _compute_frame_energies_numba(audio, frame_len, hop_len):
    n_frames = (len(audio) - frame_len) // hop_len + 1
    energies = np.zeros(n_frames)
    
    for i in prange(n_frames):  # Parallel loop
        start = i * hop_len
        end = start + frame_len
        frame = audio[start:end]
        energies[i] = np.sqrt(np.mean(frame ** 2))
    
    return energies
```

**Benefits**:
- LLVM machine code generation
- SIMD vectorization (AVX/SSE)
- Multi-core parallelization
- Cache-friendly memory access

#### Performance Results

| Operation | NumPy Time | Numba Time | Speedup |
|-----------|------------|------------|---------|
| Frame Energy | 38.5 ms | 0.6 ms | 64.2x |
| SNR Estimation | 18.7 ms | 0.8 ms | 23.4x |
| RMS Calculation | 25.3 ms | 1.2 ms | 21.1x |

**Accuracy**: < 0.001% error (near-perfect)

---

## Integration Guide

### Enable Custom Modules in Pipeline

Edit `config.yaml`:

```yaml
profiler:
  enabled: true
  wavelet: 'db8'

adaptive_router:
  enabled: true
  fallback_to_deepfilter: true

spectral_restoration:
  enabled: true
  strength: 'auto'

quality_metrics:
  enabled: true
  compute_composite_score: true
```

### Programmatic Usage

```python
from src.pipeline import LectraAIPipeline

# Initialize with custom modules enabled
pipeline = LectraAIPipeline('config.yaml')

# Process audio
result = pipeline.process('input.wav', output_dir='outputs')

# Access custom module results
if 'audio_profile' in result:
    print(f"SNR: {result['audio_profile']['snr_db']:.1f} dB")

if 'processing_method' in result:
    print(f"Method: {result['processing_method']}")

if 'quality_metrics' in result:
    print(f"Quality: {result['quality_metrics']['overall_quality_score']:.1f}/100")
```

### Standalone Usage

```python
# Use modules independently
from src.audio_quality_profiler import AudioQualityProfiler
from src.adaptive_router import AdaptiveRouter
import soundfile as sf

# Load audio
audio, sr = sf.read('input.wav')

# Profile
profiler = AudioQualityProfiler(sample_rate=sr)
profile = profiler.profile_audio(audio)

# Route
router = AdaptiveRouter(sample_rate=sr)
cleaned, method = router.route_processing(audio, profile)

# Save
sf.write('output.wav', cleaned, sr)
```

---

## Configuration

### Default Settings

```yaml
profiler:
  enabled: false  # Disabled by default
  wavelet: 'db8'  # Daubechies 8 wavelet

adaptive_router:
  enabled: false
  fallback_to_deepfilter: true  # Use DeepFilterNet if router fails

spectral_restoration:
  enabled: false
  strength: 'auto'  # Options: 'auto', 'light', 'medium', 'heavy'

quality_metrics:
  enabled: false
  compute_composite_score: true
```

### Wavelet Options

- `'db4'`, `'db8'`, `'db16'`: Daubechies wavelets (recommended)
- `'sym4'`, `'sym8'`: Symlet wavelets
- `'coif1'`, `'coif2'`: Coiflet wavelets

### Restoration Strength

- `'auto'`: Automatically estimated (recommended)
- `'light'`: 0.3 (minimal restoration)
- `'medium'`: 0.5 (moderate restoration)
- `'heavy'`: 0.7 (aggressive restoration)

---

## Troubleshooting

### Import Errors

**Problem**: `ImportError: No module named 'audio_quality_profiler'`

**Solution**:
```python
import sys
sys.path.insert(0, 'path/to/src')
```

### PyWavelets Not Available

**Problem**: `PyWavelets not available - wavelet analysis disabled`

**Solution**:
```bash
pip install PyWavelets
```

**Fallback**: Profiler uses simple noise estimation if PyWavelets unavailable.

### Numba Not Available

**Problem**: `Numba not available - using NumPy fallbacks`

**Solution**:
```bash
pip install numba
```

**Impact**: No performance optimizations, but functionality preserved.

### noisereduce Not Available

**Problem**: `noisereduce not available - using custom implementations`

**Solution**:
```bash
pip install noisereduce
```

**Fallback**: Router uses custom spectral subtraction implementation.

### Low Quality Scores

**Problem**: Quality metrics show low scores after processing

**Possible Causes**:
1. Over-aggressive noise removal (try lighter processing)
2. Spectral restoration strength too high (reduce to 'light')
3. Input audio quality very poor (SNR < 0 dB)

**Solutions**:
- Disable adaptive router, use DeepFilterNet directly
- Reduce restoration strength
- Check input audio quality with profiler

### Slow Performance

**Problem**: Processing takes too long

**Solutions**:
1. Install Numba for 20-64x speedup
2. Disable quality metrics (computationally expensive)
3. Use lighter processing methods (spectral subtraction instead of Wiener)
4. Reduce audio sample rate (if acceptable)

---

## References

### Academic Papers

1. **Spectral Subtraction**: Boll, S. F. (1979). "Suppression of acoustic noise in speech using spectral subtraction." IEEE Transactions on Acoustics, Speech, and Signal Processing.

2. **Wiener Filtering**: Scalart, P., & Filho, J. V. (1996). "Speech enhancement based on a priori signal to noise estimation." IEEE ICASSP.

3. **Itakura-Saito Distance**: Itakura, F., & Saito, S. (1968). "Analysis synthesis telephony based on the maximum likelihood method." 6th International Congress on Acoustics.

4. **Cepstral Analysis**: Oppenheim, A. V., & Schafer, R. W. (2009). "Discrete-Time Signal Processing" (3rd ed.). Prentice Hall.

5. **Wavelet Denoising**: Donoho, D. L. (1995). "De-noising by soft-thresholding." IEEE Transactions on Information Theory.

### Software Libraries

- **NumPy**: Harris, C. R., et al. (2020). "Array programming with NumPy." Nature.
- **SciPy**: Virtanen, P., et al. (2020). "SciPy 1.0: fundamental algorithms for scientific computing in Python." Nature Methods.
- **Numba**: Lam, S. K., et al. (2015). "Numba: A LLVM-based Python JIT compiler." LLVM-HPC Workshop.

---

**Last Updated**: May 2026  
**Version**: 1.0.0  
**Maintainer**: Lectra AI Project
