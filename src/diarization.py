"""
Speaker Diarization Module
Identifies who spoke when in the audio
"""

import numpy as np
import torch
import os
from typing import List, Dict, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class SpeakerDiarization:
    """Speaker diarization using pyannote.audio"""
    
    def __init__(self, 
                 min_speakers: int = 1,
                 max_speakers: int = 10,
                 device: str = None):
        """
        Args:
            min_speakers: Minimum number of speakers
            max_speakers: Maximum number of speakers
            device: torch device (cuda/cpu)
        """
        self.min_speakers = min_speakers
        self.max_speakers = max_speakers
        
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device
        
        logger.info(f"Initializing speaker diarization on {self.device}")
        self._load_model()
    
    def _load_model(self):
        """Load pyannote.audio pipeline"""
        try:
            # ----------------------------------------------------------------
            # Fix PyTorch 2.6+ weights_only=True default.  Pyannote checkpoints
            # contain many custom classes (TorchVersion, Specifications, etc.)
            # that are not in the safe-globals list.  Patching torch.load to
            # always use weights_only=False is the only reliable approach.
            # ----------------------------------------------------------------
            import torch as _torch
            import functools as _ft_load
            _orig_torch_load = _torch.load
            @_ft_load.wraps(_orig_torch_load)
            def _patched_torch_load(*args, **kwargs):
                kwargs['weights_only'] = False
                return _orig_torch_load(*args, **kwargs)
            _torch.load = _patched_torch_load

            # ----------------------------------------------------------------
            # Must patch BEFORE importing pyannote so its internal bindings
            # pick up the patched version of hf_hub_download.
            # ----------------------------------------------------------------
            import huggingface_hub as _hfhub
            import functools as _ft

            _orig_download = _hfhub.hf_hub_download
            @_ft.wraps(_orig_download)
            def _patched_download(*args, **kwargs):
                if 'use_auth_token' in kwargs:
                    kwargs.setdefault('token', kwargs.pop('use_auth_token'))
                return _orig_download(*args, **kwargs)
            _hfhub.hf_hub_download = _patched_download

            _orig_snapshot = _hfhub.snapshot_download
            @_ft.wraps(_orig_snapshot)
            def _patched_snapshot(*args, **kwargs):
                if 'use_auth_token' in kwargs:
                    kwargs.setdefault('token', kwargs.pop('use_auth_token'))
                return _orig_snapshot(*args, **kwargs)
            _hfhub.snapshot_download = _patched_snapshot

            # Also patch inside any already-imported pyannote modules
            import sys
            for mod_name, mod in list(sys.modules.items()):
                if 'pyannote' in mod_name and hasattr(mod, 'hf_hub_download'):
                    mod.hf_hub_download = _patched_download
                if 'pyannote' in mod_name and hasattr(mod, 'snapshot_download'):
                    mod.snapshot_download = _patched_snapshot
            # ----------------------------------------------------------------

            from pyannote.audio import Pipeline

            # Set local models directory
            project_root = Path(__file__).parent.parent
            models_dir = project_root / "models" / "pyannote"
            models_dir.mkdir(parents=True, exist_ok=True)

            # Set HuggingFace cache to local directory
            os.environ['HF_HOME'] = str(models_dir)
            os.environ['TORCH_HOME'] = str(models_dir)

            # Get HuggingFace token from environment
            hf_token = os.getenv('HF_TOKEN') or os.getenv('HUGGING_FACE_HUB_TOKEN')

            if not hf_token:
                logger.error("HuggingFace token not found! Set HF_TOKEN in .env file")
                self.pipeline = None
                return

            os.environ['HUGGING_FACE_HUB_TOKEN'] = hf_token
            os.environ['HF_TOKEN'] = hf_token

            logger.info(f"Using models directory: {models_dir}")
            logger.info("Loading speaker diarization model (downloads ~700MB on first use)...")

            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=hf_token,
                cache_dir=str(models_dir)
            )
            
            self.pipeline.to(torch.device(self.device))
            logger.info("Diarization pipeline loaded successfully")
            
        except Exception as e:
            logger.warning(f"Could not load diarization model: {e}")
            logger.warning("Diarization will be disabled. Set HUGGING_FACE_HUB_TOKEN to enable.")
            self.pipeline = None
    
    def diarize(self, audio_path: str) -> List[Dict]:
        """
        Perform speaker diarization
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            List of diarization segments with format:
            [{'start': float, 'end': float, 'speaker': str}, ...]
        """
        if self.pipeline is None:
            logger.warning("Diarization unavailable")
            return []
        
        try:
            # Load audio as a waveform tensor to bypass torchcodec/FFmpeg.
            # Pyannote accepts {"waveform": Tensor[C,T], "sample_rate": int}.
            import soundfile as sf
            import numpy as np
            audio_np, sr = sf.read(audio_path, dtype='float32', always_2d=True)
            # soundfile returns (T, C) — pyannote expects (C, T)
            waveform = torch.from_numpy(audio_np.T)
            audio_input = {"waveform": waveform, "sample_rate": sr}

            # Run diarization
            diarization = self.pipeline(
                audio_input,
                min_speakers=self.min_speakers,
                max_speakers=self.max_speakers
            )
            
            # Convert to list format
            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segments.append({
                    'start': turn.start,
                    'end': turn.end,
                    'speaker': speaker
                })
            
            n_speakers = len(set(seg['speaker'] for seg in segments))
            logger.info(f"Diarization complete: {n_speakers} speakers, {len(segments)} segments")
            
            return segments
            
        except Exception as e:
            logger.error(f"Diarization error: {e}")
            return []
    
    def get_speaker_statistics(self, segments: List[Dict]) -> Dict[str, float]:
        """
        Calculate speaking time for each speaker
        
        Args:
            segments: Diarization segments
            
        Returns:
            Dictionary of speaker: total_time_seconds
        """
        stats = {}
        for seg in segments:
            speaker = seg['speaker']
            duration = seg['end'] - seg['start']
            stats[speaker] = stats.get(speaker, 0) + duration
        
        return stats
