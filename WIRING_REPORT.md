# Wiring Report

## What Was Missing

- `src/pipeline.py` used eager optional imports for the custom DSP modules instead of loading them only when the matching config flag was enabled.
- `src.pipeline` could not be imported cleanly as a package module because the internal pipeline dependencies were imported with flat module paths.
- The benchmark helper in `src/optimized_utils.py` could divide by zero when the measured Numba time rounded to zero.

## What Was Added

- Package-safe imports in `src/pipeline.py` so `from src.pipeline import LectraAIPipeline` works.
- Lazy loading for the optional DSP modules inside the processing path, guarded by the existing config flags.
- A safe benchmark speedup calculation in `src/optimized_utils.py` that no longer crashes on a zero Numba timing result.

## Wiring Status

- `audio_quality_profiler` is now wired into Step 1.5 of the pipeline.
- `adaptive_router` is wired before the DeepFilterNet stage.
- `spectral_restoration` is wired after noise removal.
- `audio_quality_metrics` is wired at the end of processing and included in the result payload.
- `clean_voice.py` and `backend.py` continue to use the same pipeline entry point, so they inherit the custom DSP behavior without duplicating it.

## Verification

- `python -c "from src.pipeline import LectraAIPipeline; print('OK')"`
- `python -m pytest tests/test_custom_modules.py -v`
- `python -m pytest tests/test_pipeline.py -v`
- `python -m pytest tests/test_custom_modules.py -k test_optimized_benchmark -v`

All of the above passed after the patch.
