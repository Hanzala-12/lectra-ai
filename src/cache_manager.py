"""
Simple file-based caching for processing results
Optimized for CPU laptops - avoids reprocessing same files
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
import logging
import shutil

logger = logging.getLogger(__name__)

class FileCache:
    """File-based cache for audio processing results"""
    
    def __init__(self, cache_dir: str = "./cache"):
        """
        Initialize file cache
        
        Args:
            cache_dir: Directory to store cached results
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized file cache at {self.cache_dir}")
    
    def _generate_key(self, file_path: str, config: Dict[str, Any]) -> str:
        """
        Generate cache key from file content and config
        
        Args:
            file_path: Path to input file
            config: Processing configuration
            
        Returns:
            Cache key (hash string)
        """
        # Hash file content
        hasher = hashlib.md5()
        
        with open(file_path, 'rb') as f:
            # Read file in chunks to handle large files
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        
        file_hash = hasher.hexdigest()
        
        # Hash config (only relevant parts)
        config_str = json.dumps({
            'model': config.get('asr', {}).get('model'),
            'compute_type': config.get('asr', {}).get('compute_type'),
            'diarization': config.get('diarization', {}).get('enabled'),
            'sample_rate': config.get('audio', {}).get('sample_rate'),
        }, sort_keys=True)
        
        config_hash = hashlib.md5(config_str.encode()).hexdigest()
        
        # Combine hashes
        cache_key = f"{file_hash}_{config_hash}"
        return cache_key
    
    def get(self, file_path: str, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached result
        
        Args:
            file_path: Path to input file
            config: Processing configuration
            
        Returns:
            Cached result or None if not found
        """
        try:
            cache_key = self._generate_key(file_path, config)
            cache_path = self.cache_dir / cache_key
            
            if not cache_path.exists():
                logger.debug(f"Cache miss for key {cache_key}")
                return None
            
            # Load metadata
            metadata_path = cache_path / "metadata.json"
            if not metadata_path.exists():
                logger.warning(f"Cache corrupted for key {cache_key}")
                return None
            
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Check if output files exist
            audio_path = cache_path / "cleaned_audio.wav"
            if not audio_path.exists():
                logger.warning(f"Cache corrupted for key {cache_key}")
                return None
            
            logger.info(f"Cache HIT for key {cache_key}")
            
            return {
                'cache_key': cache_key,
                'cache_path': str(cache_path),
                'audio_path': str(audio_path),
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Error retrieving from cache: {e}")
            return None
    
    def set(self, 
            file_path: str, 
            config: Dict[str, Any], 
            result: Dict[str, Any],
            output_audio: str,
            transcript_path: Optional[str] = None) -> None:
        """
        Store result in cache
        
        Args:
            file_path: Path to input file
            config: Processing configuration
            result: Processing result metadata
            output_audio: Path to processed audio file
            transcript_path: Path to transcript file (optional)
        """
        try:
            cache_key = self._generate_key(file_path, config)
            cache_path = self.cache_dir / cache_key
            cache_path.mkdir(parents=True, exist_ok=True)
            
            # Copy output audio
            shutil.copy2(output_audio, cache_path / "cleaned_audio.wav")
            
            # Copy transcript if available
            if transcript_path and os.path.exists(transcript_path):
                shutil.copy2(transcript_path, cache_path / "transcript.txt")
            
            # Save metadata
            metadata = {
                'input_file': os.path.basename(file_path),
                'config': config,
                'result': result,
                'cached_at': str(Path(output_audio).stat().st_mtime)
            }
            
            with open(cache_path / "metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Cached result with key {cache_key}")
            
        except Exception as e:
            logger.error(f"Error storing in cache: {e}")
    
    def clear(self) -> None:
        """Clear all cached files"""
        try:
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Cache cleared")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            cache_items = list(self.cache_dir.glob("*/metadata.json"))
            total_size = sum(
                sum(f.stat().st_size for f in item.parent.glob("*"))
                for item in cache_items
            )
            
            return {
                'items': len(cache_items),
                'size_mb': total_size / 1024 / 1024,
                'path': str(self.cache_dir)
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {'items': 0, 'size_mb': 0}
