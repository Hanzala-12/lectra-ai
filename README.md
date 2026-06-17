# Lectra AI with Custom DSP Enhancements

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A production-ready noise removal pipeline for speech audio with optional custom digital signal processing (DSP) modules for academic research and deployment.

## Overview

This project combines state-of-the-art deep learning models with custom algorithmic implementations to remove background noise from audio/video files and generate accurate transcripts with speaker diarization.

### Key Features

- **Two-stage neural noise removal**: **DeepFilterNet3 → MetricGAN+** — DFN removes the bulk, MetricGAN+ polishes the residual to a near-silent floor (~39 dB speech-to-noise) without artifacts. See **[Noise Removal & Diarization pipeline](docs/NOISE_REMOVAL_AND_DIARIZATION.md)**.
- **Speaker Diarization**: Automatic speaker identification using Pyannote 3.1 (drives both speech detection and per-speaker transcription)
- **Speech Recognition**: faster-whisper turbo model for transcription
- **CPU-friendly**: the full denoise chain runs faster-than-realtime on CPU (no GPU required)
- **Custom DSP Algorithms**: hand-written signal processing (adaptive thresholds, gain-riding, clarity EQ, loudness normalization) plus optional experimental modules
- **Voice Beautify (optional)**: post-cleaning master applied to speech only — adaptive tone, loudness leveling, and high-band "air" — SNR-guarded so it never adds noise back. Off by default; see [`beautify`](config.yaml) in config.
- **Study Assistant (NLP/LLM + RAG)**: turns a transcript into **study notes, quizzes, a personalized schedule, an evaluation/analysis**, and a **RAG-grounded chatbot**, stored in a lecture repository. Provider-agnostic (OpenRouter by default). See **[Study Assistant docs](docs/STUDY_ASSISTANT.md)**.
- **Web Interface**: React frontend + FastAPI backend
- **Docker Support**: One-command deployment

---

## Quick Start

### Prerequisites

- Python 3.10 or higher
- 8GB RAM minimum (16GB recommended)
- ffmpeg (automatically bundled)

### Installation

```bash
# Clone repository
git clone https://github.com/Hanzala-12/lectra-ai.git
cd lectra-ai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download models (automatic on first run)
python clean_voice.py --help
```

### Usage

#### Command Line Interface

```bash
# Process single audio file
python clean_voice.py input.mp3

# Process with transcription
python clean_voice.py audio.wav --transcript --transcript-format srt

# Process video file
python clean_voice.py video.mp4 --transcript

# Process directory
python clean_voice.py ./audio_folder/
```

#### Web Interface

```bash
# Start backend server
python backend.py

# Start frontend (in another terminal)
cd frontend && npm install && npm run dev

# Open browser: http://localhost:3000
```

#### Docker Deployment

```bash
# Build and run with docker-compose
docker-compose up --build

# Access at http://localhost:3000
```

---

## Project Structure

```
.
├── backend.py                  # FastAPI web server
├── clean_voice.py             # Command-line interface
├── config.yaml                # Configuration settings
├── src/                       # Core modules
│   ├── pipeline.py           # Main processing pipeline
│   ├── deepfilter_processor.py          # DeepFilterNet3 noise suppression
│   ├── metricgan_processor.py           # MetricGAN+ neural enhancement (final polish)
│   ├── voice_beautify.py                # Optional post-cleaning master (tone/leveler/air)
│   ├── vad_processor.py
│   ├── diarization.py
│   ├── asr_processor.py
│   ├── audio_quality_profiler.py     # [CUSTOM] Input analysis
│   ├── spectral_restoration.py        # [CUSTOM] Post-processing
│   ├── audio_quality_metrics.py       # [CUSTOM] Quality evaluation
│   ├── adaptive_router.py             # [CUSTOM] Smart routing
│   └── optimized_utils.py             # [CUSTOM] Benchmark/helper utilities
├── tests/                     # Test suite
├── examples/                  # Demo scripts
├── notebooks/                 # Jupyter notebooks
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md       # System design
│   ├── OPTIMIZATION.md       # Performance details
│   └── INTEGRATION.md        # Integration guide
└── frontend/                  # React web UI
```

---

## Custom DSP Modules

This project includes **four custom DSP stages plus one benchmark/helper module** for research and experimentation:

Four modules are lazily loaded inside `src/pipeline.py` behind config flags. `optimized_utils` remains a support module for benchmarks and tests rather than a live processing stage.

### [Experimental] Custom Modules (Disabled by Default)

**Status**: ✅ Implemented | ⚠️ Experimental | 🔒 Disabled by Default

The following modules are available but disabled by default to preserve the stable production pipeline:

### 1. Audio Quality Profiler (`src/audio_quality_profiler.py`)
**~400 lines of code** | **Status**: ✅ Implemented

Analyzes input audio characteristics before processing:
- Wavelet-based noise estimation
- SNR (Signal-to-Noise Ratio) calculation
- Spectral flatness and rolloff analysis
- Zero-crossing rate detection
- Dominant frequency identification

```python
from src.audio_quality_profiler import AudioQualityProfiler

profiler = AudioQualityProfiler(sample_rate=16000)
metrics = profiler.profile_audio(audio)
print(f"SNR: {metrics['snr_db']:.1f} dB")
print(f"Recommended processing: {metrics['recommended_processing']}")
```

### 2. Spectral Restoration (`src/spectral_restoration.py`)
**~450 lines of code** | **Status**: ✅ Implemented

Restores high-frequency content lost during aggressive noise removal:
- Cepstral analysis for voice/noise separation
- Autocorrelation-based pitch detection
- Harmonic synthesis for frequency regeneration
- Adaptive restoration strength control

```python
from src.spectral_restoration import SpectralRestoration

restorer = SpectralRestoration(sample_rate=16000)
enhanced = restorer.adaptive_restoration(original, denoised)
```

### 3. Audio Quality Metrics (`src/audio_quality_metrics.py`)
**~550 lines of code** | **Status**: ✅ Implemented

Nine scientific metrics for quality evaluation:
1. SNR (Signal-to-Noise Ratio)
2. PSNR (Peak Signal-to-Noise Ratio)
3. Segmental SNR
4. Log-Spectral Distance
5. Itakura-Saito Distance
6. Correlation Coefficient
7. Cepstral Distance
8. Envelope Distance
9. Composite Quality Score

```python
from src.audio_quality_metrics import AudioQualityMetrics

metrics_calc = AudioQualityMetrics(sample_rate=16000)
results = metrics_calc.comprehensive_evaluation(clean, noisy, processed)
print(f"Quality Score: {results['overall_quality_score']:.1f}/100")
```

### 4. Adaptive Router (`src/adaptive_router.py`)
**~450 lines of code** | **Status**: ✅ Implemented

Intelligent processing method selection based on noise level:
- **Light noise** (SNR > 15 dB): Spectral Subtraction
- **Medium noise** (5-15 dB): Wiener Filter
- **Heavy noise** (SNR < 5 dB): DeepFilterNet (DNN)

```python
from src.adaptive_router import AdaptiveRouter

router = AdaptiveRouter(sample_rate=16000)
cleaned, decision = router.route_processing(audio, profile)
print(f"Processing method: {decision}")
```

### 5. Performance Optimization (`src/optimized_utils.py`)
**~550 lines of code** | **Status**: ✅ Implemented

CPU-level optimizations achieving 3-64x speedup:
- Numba JIT compilation (LLVM machine code)
- SIMD vectorization (AVX/SSE instructions)
- Multi-core parallelization
- Cache-friendly algorithms

**Benchmark Results**:
- Frame Energy: **64x faster** (38.5ms → 0.6ms)
- SNR Estimation: **24x faster** (18.7ms → 0.8ms)
- Accuracy: **<0.001% error** (near-perfect)

```python
from src.optimized_utils import VectorizedAudioProcessor

processor = VectorizedAudioProcessor(sample_rate=16000)
energies = processor.compute_frame_energies_vectorized(audio)  # 64x faster!
```

### Enabling Custom Modules

**Important**: Custom modules are **disabled by default** to preserve the stable production pipeline.

To enable them, edit `config.yaml`:

```yaml
profiler:
  enabled: true  # Enable audio quality profiling
  
adaptive_router:
  enabled: true  # Enable intelligent method selection
  
spectral_restoration:
  enabled: true  # Enable post-processing enhancement
  
quality_metrics:
  enabled: true  # Enable quality evaluation
```

**Note**: These modules are experimental and may affect processing time and quality. Use with caution in production.

For detailed documentation, see [docs/CUSTOM_DSP.md](docs/CUSTOM_DSP.md).

---

## Roadmap

Study-assistant features — **backend implemented** ([docs](docs/STUDY_ASSISTANT.md)); frontend wiring in progress:

- **Quiz Generation** - Generate & auto-grade MCQ quizzes from transcripts. *(✅ backend: `POST /api/lecture/{id}/quiz`; UI wiring pending)*
- **AI-Powered Study Notes** - Markdown summary, key points & definitions. *(✅ backend: `POST /api/lecture/{id}/notes`; UI wiring pending)*
- **RAG Chatbot** - Ask questions answered from the lecture transcript. *(✅ backend: `POST /api/lecture/{id}/chat`; UI wiring pending)*
- **Personalized Schedule & Evaluation** - Spaced-repetition study plan + lecture analysis. *(✅ backend: `/schedule`, `/evaluate`)*

Next: point the React pages (Library / Quiz / Chat / Dashboard / Analytics) at these endpoints, and an optional 48 kHz audio path.

---

## Documentation

- **[Noise Removal & Diarization Pipeline](docs/NOISE_REMOVAL_AND_DIARIZATION.md)**: Full end-to-end signal chain, how each stage works, and the measured engineering decisions behind the clean result ⭐
- **[Pipeline Explained (plain language)](docs/PIPELINE_EXPLAINED.md)**: point-by-point walkthrough for explaining the noise-removal process to others
- **[Study Assistant (NLP/LLM + RAG)](docs/STUDY_ASSISTANT.md)**: notes, quiz, schedule, evaluation & chatbot — API reference and how to enable the LLM ⭐
- **[Architecture](docs/ARCHITECTURE.md)**: System design and component overview
- **[Custom DSP Modules](docs/CUSTOM_DSP.md)**: API reference and usage guide for experimental modules
- **[Performance Optimization](docs/OPTIMIZATION.md)**: CPU optimization techniques and benchmarks
- **[Integration Guide](docs/INTEGRATION.md)**: How to integrate custom modules into the pipeline

---

## Examples and Demos

### Run Performance Benchmarks

```bash
python examples/performance_benchmark.py
```

**Expected output** (with Numba installed):
```
RESULTS - Frame Energy Calculation
  Original (NumPy):  38.50 ms
  Optimized (Numba):  0.60 ms
  Speedup:           64.2x faster

RESULTS - SNR Estimation
  Original (NumPy):  18.70 ms
  Optimized (Numba):  0.80 ms
  Speedup:           23.4x faster

All accuracy tests: PASSED
```

### Custom Integration Demo

```bash
python examples/custom_integration.py [input_audio.wav]
```

Shows complete workflow with all custom modules integrated. If no audio file provided, uses synthetic test audio.

### Interactive Jupyter Notebook

```bash
cd kaggle_demo
jupyter notebook notebook.ipynb
```

Contains:
- Live performance benchmarks
- Visual comparison charts (waveforms, spectrograms)
- Accuracy validation
- Quality metrics evaluation
- Step-by-step demonstrations of all 5 custom modules

**Kaggle Ready**: The `kaggle_demo/` folder can be zipped and uploaded to Kaggle as a standalone dataset.

---

## API Reference

### REST API Endpoints

#### POST `/api/process`

Process audio/video file with optional transcription.

**Request**:
```json
{
  "file": "audio.mp3",
  "enable_diarization": true,
  "enable_transcript": true
}
```

**Response**:
```json
{
  "audio_output_path": "outputs/cleaned_audio.wav",
  "transcript": "Hello world...",
  "speakers": ["SPEAKER_00", "SPEAKER_01"],
  "duration": 60.5,
  "quality_metrics": {
    "snr_db": 18.4,
    "overall_quality_score": 76.3
  }
}
```

See [API Documentation](docs/ARCHITECTURE.md#deployment-architecture) for full details.

---

## Testing

### Run All Tests

```bash
# Full suite (requires complete runtime deps, including soundfile)
pytest tests/

# Custom module tests
pytest tests/test_custom_modules.py -v

# Cleanup tool tests
pytest tests/test_cleanup_tool.py tests/test_cleanup_tool_properties.py -q

# Integration tests
pytest tests/test_pipeline.py

# API tests
pytest tests/test_api.py
```

### Verified Test Status (May 17, 2026)

```
cleanup_tool tests: 78 passed
pytest tests -q: blocked in current environment by missing dependency `soundfile`
```

---

## Performance

### Processing Speed

| Audio Duration | Processing Time | Real-time Factor |
|----------------|-----------------|------------------|
| 60 seconds | 8-12 seconds | 5-7.5x faster |
| 5 minutes | 40-60 seconds | 5-7.5x faster |
| 30 minutes | 4-6 minutes | 5-7.5x faster |

**With Optimizations**: Up to 64x faster on CPU-intensive operations.

### Resource Usage

- **RAM**: 2-4GB (models loaded)
- **CPU**: 4+ cores recommended
- **GPU**: Optional (CUDA for faster DeepFilterNet)
- **Disk**: ~3GB (models + cache)

---

## Technology Stack

### Core Technologies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend** | FastAPI | REST API server |
| **Frontend** | React 19 + TypeScript | Web interface |
| **Noise Removal (stage 1)** | DeepFilterNet3 | Deep learning noise reduction |
| **Noise Removal (stage 2)** | MetricGAN+ (SpeechBrain) | Neural enhancement / final polish |
| **Speech Recognition** | faster-whisper Turbo | Transcription |
| **Speaker Diarization** | Pyannote 3.1 | Speaker identification |
| **DSP** | NumPy, SciPy | Signal processing |
| **Optimization** | Numba | JIT compilation |

### Custom Libraries

- **PyWavelets**: Wavelet analysis
- **librosa**: Audio feature extraction
- **noisereduce**: Spectral subtraction
- **soundfile**: Audio I/O

---

## Configuration

### config.yaml

The key noise-removal and diarization settings (see
[the pipeline doc](docs/NOISE_REMOVAL_AND_DIARIZATION.md#6-configuration-reference)
for the full reference):

```yaml
audio:
  sample_rate: 16000

deepfilternet:            # stage 1 — DeepFilterNet3
  atten_lim_db: 30        # suppression strength
  post_filter: false      # off → preserves quiet consonants
  dry_wet_mix: 0.0        # original blended back (off; MetricGAN+ handles restoration)

neural_enhancer:          # stage 2 — MetricGAN+ final polish
  enabled: true           # set false for DeepFilterNet-only (faster, slightly noisier)
  model: "metricgan-plus-voicebank"

beautify:                 # optional post-cleaning master (speech only)
  enabled: false          # off by default; true → adaptive tone + leveler + 24kHz "air"
  air:
    amount_db: -9         # high-band extension level, relative to the input's own HF

diarization:
  enabled: true
  min_speakers: 1
  max_speakers: 10

asr:
  model: "turbo"          # turbo, large-v3, large, medium, small, base, tiny
  language: null          # auto-detect

output:
  format: "wav"
  bit_depth: 16
```

---

## Deployment

### Production Deployment

```bash
# Using Docker Compose (recommended)
docker-compose up -d

# Manual deployment
gunicorn backend:app --workers 4 --bind 0.0.0.0:8000
```

### Environment Variables

```bash
# .env file
HUGGINGFACE_TOKEN=your_token_here
MAX_FILE_SIZE_MB=200
OUTPUTS_DIR=./outputs
CACHE_DIR=./cache
LOG_LEVEL=INFO
```

---

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- Follow PEP 8 guidelines
- Use type hints for function signatures
- Add docstrings to all public functions
- Run `black` formatter before committing

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- **DeepFilterNet**: Schröter et al. for the excellent noise removal model
- **MetricGAN+ / SpeechBrain**: Fu et al. and the SpeechBrain team for the neural speech enhancement model
- **faster-whisper**: Systran for the optimized Whisper implementation using CTranslate2
- **Whisper**: OpenAI for the robust speech recognition model
- **Pyannote**: Hervé Bredin for the speaker diarization toolkit
- **NumPy/SciPy**: Community for foundational numerical computing libraries

---

## Citation

If you use this project in your research, please cite:

```bibtex
@software{lectra_ai,
  title = {Lectra AI with Custom DSP Enhancements},
  year = {2026},
  author = {Hanzala-12 and contributors},
  url = {https://github.com/Hanzala-12/lectra-ai}
}
```

---

## Support

- **Documentation**: See [docs/](docs/) folder
- **Issues**: [GitHub Issues](https://github.com/Hanzala-12/lectra-ai/issues)

---

## Roadmap

### Upcoming Features
- [ ] Real-time streaming support (WebRTC)
- [ ] Multi-language transcription
- [ ] Custom model fine-tuning
- [ ] Mobile app (iOS/Android)
- [ ] Cloud deployment templates (AWS, GCP, Azure)

### Research Extensions
- [ ] Hybrid classical/DL noise removal
- [ ] Perceptual quality metrics
- [ ] Speaker-adapted restoration
- [ ] Edge device optimization (Raspberry Pi, mobile)

---

**Status**: Production Ready — DeepFilterNet3 → MetricGAN+ noise removal + Pyannote diarization  
**Last Updated**: June 2026  
**Maintainer**: Hanzala-12

---

## Star History

If you find this project useful, please consider giving it a star on GitHub.

[![Star History Chart](https://api.star-history.com/svg?repos=Hanzala-12/lectra-ai&type=Date)](https://star-history.com/#Hanzala-12/lectra-ai&Date)
