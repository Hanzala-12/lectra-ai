# Wiring Audit

| Module | `src/pipeline.py` | `clean_voice.py` | `backend.py` | Config-controlled |
| --- | --- | --- | --- | --- |
| `audio_quality_profiler` | Imported lazily and called during Step 1.5 when `profiler.enabled` is true | Not imported directly; reaches the pipeline through `LectraAIPipeline` | Not imported directly; reaches the pipeline through `LectraAIPipeline` | Yes, `profiler.enabled` |
| `spectral_restoration` | Imported lazily and called after noise reduction when `spectral_restoration.enabled` is true | Not imported directly; reaches the pipeline through `LectraAIPipeline` | Not imported directly; reaches the pipeline through `LectraAIPipeline` | Yes, `spectral_restoration.enabled` |
| `audio_quality_metrics` | Imported lazily and called at the end of processing when `quality_metrics.enabled` is true | Not imported directly; reaches the pipeline through `LectraAIPipeline` | Not imported directly; reaches the pipeline through `LectraAIPipeline` | Yes, `quality_metrics.enabled` |
| `adaptive_router` | Imported lazily and called before the DeepFilterNet stage when `adaptive_router.enabled` is true | Not imported directly; reaches the pipeline through `LectraAIPipeline` | Not imported directly; reaches the pipeline through `LectraAIPipeline` | Yes, `adaptive_router.enabled` |
| `optimized_utils` | Not part of the main pipeline flow; used by the benchmark and helper tests | Not imported directly | Not imported directly | No dedicated runtime flag |

## Notes

- `clean_voice.py` and `backend.py` both enter the same processing pipeline, so the custom DSP wiring lives in `src/pipeline.py`.
- The pipeline now loads optional DSP modules only when the matching config section is enabled, so disabled features do not pay the import/initialization cost.
- `optimized_utils` remains a support module rather than a live processing stage in the main pipeline.
