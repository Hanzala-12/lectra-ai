"""
Prometheus metrics for monitoring
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest
from functools import wraps
import time

# Define metrics
requests_total = Counter(
    'voice_cleaning_requests_total',
    'Total number of processing requests',
    ['status', 'model', 'format']
)

processing_duration = Histogram(
    'voice_cleaning_duration_seconds',
    'Time spent processing audio',
    buckets=(1, 5, 10, 30, 60, 120, 300, 600)
)

file_size_bytes = Histogram(
    'voice_cleaning_file_size_bytes',
    'Size of processed files',
    buckets=(1024*1024, 10*1024*1024, 50*1024*1024, 100*1024*1024, 500*1024*1024)
)

audio_length_seconds = Histogram(
    'voice_cleaning_audio_length_seconds',
    'Length of processed audio',
    buckets=(10, 30, 60, 120, 300, 600, 1800, 3600)
)

active_jobs = Gauge(
    'voice_cleaning_active_jobs',
    'Number of currently processing jobs'
)

model_load_time = Histogram(
    'model_load_time_seconds',
    'Time to load models',
    ['model_type']
)

errors_total = Counter(
    'voice_cleaning_errors_total',
    'Total number of errors',
    ['error_type']
)

def track_processing_time(func):
    """Decorator to track processing time"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        active_jobs.inc()
        
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start
            processing_duration.observe(duration)
            return result
        except Exception as e:
            errors_total.labels(error_type=type(e).__name__).inc()
            raise
        finally:
            active_jobs.dec()
    
    return wrapper

def track_request(status: str, model: str, format: str):
    """Track request metrics"""
    requests_total.labels(status=status, model=model, format=format).inc()

def track_file_metrics(size_bytes: int, length_seconds: float):
    """Track file size and length"""
    file_size_bytes.observe(size_bytes)
    audio_length_seconds.observe(length_seconds)
