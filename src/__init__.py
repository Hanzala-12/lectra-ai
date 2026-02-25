"""Package initialization"""

from .pipeline import VoiceCleaningPipeline
from .media_loader import MediaLoader
from .vad_processor import VADProcessor
from .deepfilter_processor import DeepFilterProcessor
from .silent_bed import SilentBedTransplant
from .diarization import SpeakerDiarization
from .asr_processor import ASRProcessor

__version__ = "1.0.0"
__all__ = [
    'VoiceCleaningPipeline',
    'MediaLoader',
    'VADProcessor',
    'DeepFilterProcessor',
    'SilentBedTransplant',
    'SpeakerDiarization',
    'ASRProcessor',
]
