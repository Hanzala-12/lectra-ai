"""
Example usage of the Voice Cleaning Pipeline
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from pipeline import VoiceCleaningPipeline

def example_basic():
    """Basic example: process a single file"""
    print("Example 1: Basic Processing")
    print("-" * 50)
    
    # Initialize pipeline
    pipeline = VoiceCleaningPipeline("config.yaml")
    
    # Process file
    result = pipeline.process(
        input_path="input.mp3",  # Replace with your file
        output_dir="outputs"
    )
    
    print(f"Output: {result['audio_output_path']}")
    print(f"Duration: {result['duration_processed']:.2f}s")
    print()

def example_with_transcript():
    """Example with transcript generation"""
    print("Example 2: Processing with Transcript")
    print("-" * 50)
    
    pipeline = VoiceCleaningPipeline("config.yaml")
    
    result = pipeline.process(
        input_path="interview.wav",
        output_dir="outputs",
        save_transcript=True,
        transcript_format="srt"
    )
    
    print("Transcript preview:")
    print(result['transcript']['text'][:200] + "...")
    print()

def example_video():
    """Example: process video file"""
    print("Example 3: Video Processing")
    print("-" * 50)
    
    pipeline = VoiceCleaningPipeline("config.yaml")
    
    result = pipeline.process(
        input_path="video.mp4",
        output_dir="outputs"
    )
    
    print(f"Cleaned audio: {result['audio_output_path']}")
    print(f"Cleaned video: {result['video_output_path']}")
    print()

def example_batch():
    """Example: batch processing"""
    print("Example 4: Batch Processing")
    print("-" * 50)
    
    pipeline = VoiceCleaningPipeline("config.yaml")
    
    input_files = [
        "audio1.mp3",
        "audio2.wav",
        "video1.mp4"
    ]
    
    results, failed = pipeline.process_batch(
        input_files=input_files,
        output_dir="outputs",
        continue_on_error=True
    )
    
    print(f"Successfully processed: {len(results)}/{len(input_files)}")
    print()

def example_custom_config():
    """Example: using custom configuration"""
    print("Example 5: Custom Configuration")
    print("-" * 50)
    
    pipeline = VoiceCleaningPipeline("config.yaml")
    
    # Modify configuration programmatically
    pipeline.config['vad']['aggressiveness'] = 2
    pipeline.config['asr']['model'] = 'small'
    
    # Reinitialize VAD with new settings
    from vad_processor import VADProcessor
    pipeline.vad_processor = VADProcessor(
        sample_rate=pipeline.sample_rate,
        aggressiveness=2
    )
    
    result = pipeline.process("input.mp3", "outputs")
    print(f"Processed with custom config: {result['audio_output_path']}")
    print()

def example_access_components():
    """Example: accessing individual components"""
    print("Example 6: Using Individual Components")
    print("-" * 50)
    
    from media_loader import MediaLoader
    from vad_processor import VADProcessor
    from deepfilter_processor import DeepFilterProcessor
    
    # Load audio
    loader = MediaLoader(target_sr=16000)
    audio, sr, is_video = loader.load_media("input.mp3")
    print(f"Loaded: {len(audio)/sr:.2f}s audio")
    
    # Apply VAD
    vad = VADProcessor(sample_rate=sr)
    trimmed_audio, segments = vad.trim_silence(audio)
    print(f"Detected {len(segments)} speech segments")
    
    # Apply noise reduction
    denoiser = DeepFilterProcessor()
    clean_audio = denoiser.process_audio(trimmed_audio, sr)
    print(f"Denoised audio: {len(clean_audio)/sr:.2f}s")
    
    # Save result
    loader.save_audio(clean_audio, sr, "outputs/manual_output.wav")
    print("Saved to: outputs/manual_output.wav")
    print()

if __name__ == "__main__":
    print("\n" + "="*70)
    print("Voice Cleaning Pipeline - Usage Examples")
    print("="*70 + "\n")
    
    print("NOTE: Replace file paths with your actual files before running!")
    print()
    
    # Uncomment the example you want to run:
    
    # example_basic()
    # example_with_transcript()
    # example_video()
    # example_batch()
    # example_custom_config()
    # example_access_components()
    
    print("See the source code for more examples!")
    print("Run: python examples.py")
