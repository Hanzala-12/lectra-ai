"""Utility functions for the voice cleaning pipeline"""

import os
import numpy as np
from pathlib import Path
from typing import List

def get_audio_files(directory: str, recursive: bool = True) -> List[str]:
    """
    Get all audio/video files in a directory
    
    Args:
        directory: Directory path
        recursive: Search recursively
        
    Returns:
        List of file paths
    """
    extensions = {
        '.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aac',
        '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'
    }
    
    files = []
    path = Path(directory)
    
    if recursive:
        for ext in extensions:
            files.extend(path.rglob(f"*{ext}"))
    else:
        for ext in extensions:
            files.extend(path.glob(f"*{ext}"))
    
    return [str(f) for f in sorted(files)]

def format_duration(seconds: float) -> str:
    """Format duration in seconds to HH:MM:SS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"

def calculate_snr(signal: np.ndarray, noise: np.ndarray) -> float:
    """
    Calculate Signal-to-Noise Ratio
    
    Args:
        signal: Clean signal
        noise: Noise signal
        
    Returns:
        SNR in dB
    """
    signal_power = np.mean(signal ** 2)
    noise_power = np.mean(noise ** 2)
    
    if noise_power == 0:
        return float('inf')
    
    snr = 10 * np.log10(signal_power / noise_power)
    return snr

def create_directories(base_dir: str):
    """Create necessary directories for the project"""
    dirs = [
        'uploads',
        'outputs',
        'temp',
        'models'
    ]
    
    for d in dirs:
        path = Path(base_dir) / d
        path.mkdir(parents=True, exist_ok=True)
