# Lectra AI - Kaggle Demo

This folder contains a standalone Kaggle-ready demonstration of the custom DSP modules from the Lectra AI project.

## Contents

- `notebook.ipynb` - Interactive Jupyter notebook demonstrating all custom DSP features
- `src/` - Standalone copies of the 5 custom DSP modules
- `requirements.txt` - Python dependencies
- `README.md` - This file

## Quick Start on Kaggle

### Option 1: Upload as Dataset

1. Zip this entire folder:
   ```bash
   cd ..
   zip -r kaggle_demo.zip kaggle_demo/
   ```

2. Upload to Kaggle as a dataset:
   - Go to https://www.kaggle.com/datasets
   - Click "New Dataset"
   - Upload `kaggle_demo.zip`
   - Set title: "Lectra AI DSP Demo"

3. Create a new notebook and add the dataset

4. In the notebook, run:
   ```python
   import sys
   sys.path.insert(0, '/kaggle/input/voice-cleaning-dsp-demo/kaggle_demo')
   ```

5. Open and run `notebook.ipynb`

### Option 2: Direct Upload

1. Create a new Kaggle notebook

2. Upload files:
   - Click "Add Data" → "Upload"
   - Upload all files from `kaggle_demo/`

3. Install dependencies:
   ```python
   !pip install librosa pywt noisereduce numba matplotlib seaborn
   ```

4. Copy the notebook cells and run

## Local Usage

### Installation

```bash
cd kaggle_demo
pip install -r requirements.txt
```

### Run Notebook

```bash
jupyter notebook notebook.ipynb
```

## Features Demonstrated

The notebook demonstrates:

1. **Audio Quality Profiler** - Analyzes input audio characteristics
   - Wavelet-based noise estimation
   - SNR calculation
   - Spectral analysis
   - Processing recommendation

2. **Adaptive Router** - Selects optimal processing method
   - Spectral subtraction (light noise)
   - Wiener filter (medium noise)
   - DeepFilterNet recommendation (heavy noise)

3. **Spectral Restoration** - Restores lost frequencies
   - Pitch detection
   - Harmonic synthesis
   - Adaptive strength control

4. **Audio Quality Metrics** - Evaluates processing quality
   - 9 scientific metrics (SNR, PSNR, LSD, etc.)
   - Composite quality score (0-100)

5. **Optimized Utilities** - Performance benchmarks
   - Numba JIT compilation
   - 20-64x speedup demonstrations

## Module Documentation

### Audio Quality Profiler

```python
from src.audio_quality_profiler import AudioQualityProfiler

profiler = AudioQualityProfiler(sample_rate=16000)
profile = profiler.profile_audio(audio)
print(profile['snr_db'])  # Estimated SNR
print(profile['recommended_processing'])  # 'light', 'medium', or 'heavy'
```

### Adaptive Router

```python
from src.adaptive_router import AdaptiveRouter

router = AdaptiveRouter(sample_rate=16000)
cleaned, method = router.route_processing(audio, profile)
print(method)  # Processing method used
```

### Spectral Restoration

```python
from src.spectral_restoration import SpectralRestoration

restorer = SpectralRestoration(sample_rate=16000)
restored = restorer.adaptive_restoration(original, denoised, strength='auto')
```

### Audio Quality Metrics

```python
from src.audio_quality_metrics import AudioQualityMetrics

metrics = AudioQualityMetrics(sample_rate=16000)
results = metrics.comprehensive_evaluation(clean, processed)
print(results['overall_quality_score'])  # 0-100
```

### Optimized Utilities

```python
from src.optimized_utils import VectorizedAudioProcessor

processor = VectorizedAudioProcessor(sample_rate=16000)
benchmark = processor.benchmark_optimizations(audio)
print(benchmark['frame_energies']['speedup'])  # e.g., 64.2x
```

## Sample Audio

The notebook includes code to:
- Generate synthetic test audio
- Upload your own audio files
- Download sample audio from the internet

## Visualization

The notebook creates:
- Waveform plots (before/after)
- Spectrogram comparisons
- Metrics comparison tables
- Performance benchmark charts

## Notes

- **Numba**: Install for 20-64x speedups (optional but recommended)
- **PyWavelets**: Required for wavelet-based noise estimation
- **noisereduce**: Optional, provides alternative spectral subtraction
- **GPU**: Not required, all processing runs on CPU

## Troubleshooting

### Import Errors

If you get import errors, ensure the path is correct:

```python
import sys
sys.path.insert(0, './src')  # or '/kaggle/input/...'
```

### Missing Dependencies

Install missing packages:

```python
!pip install <package-name>
```

### Audio Upload Issues

On Kaggle, use the file upload widget:

```python
from google.colab import files  # For Colab
uploaded = files.upload()
```

Or use Kaggle's dataset feature to add audio files.

## License

MIT License - See main project LICENSE file

## Contact

For issues or questions, see the main project repository.

---

**Last Updated**: May 2026  
**Version**: 1.0.0
