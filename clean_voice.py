#!/usr/bin/env python3
"""
Voice Cleaning CLI
Command-line interface for the voice cleaning pipeline
"""

import argparse
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from pipeline import VoiceCleaningPipeline
from utils import get_audio_files, create_directories

def main():
    parser = argparse.ArgumentParser(
        description='Voice Cleaning Pipeline - Remove background noise from audio/video files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process single audio file
  python clean_voice.py input.mp3
  
  # Process video file with transcript
  python clean_voice.py video.mp4 --transcript --transcript-format srt
  
  # Process all files in a directory
  python clean_voice.py --batch audio_folder/
  
  # Custom configuration
  python clean_voice.py input.wav --config custom_config.yaml
  
  # Multiple files
  python clean_voice.py file1.mp3 file2.wav file3.mp4
        """
    )
    
    # Input arguments
    parser.add_argument(
        'input',
        nargs='*',
        help='Input audio/video file(s) or directory (for batch mode)'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        default='outputs',
        help='Output directory (default: outputs/)'
    )
    
    parser.add_argument(
        '-c', '--config',
        default='config.yaml',
        help='Configuration file path (default: config.yaml)'
    )
    
    # Processing options
    parser.add_argument(
        '-b', '--batch',
        metavar='DIR',
        help='Process all audio/video files in directory'
    )
    
    parser.add_argument(
        '--recursive',
        action='store_true',
        help='Search recursively in batch mode'
    )
    
    # Transcript options
    parser.add_argument(
        '-t', '--transcript',
        action='store_true',
        help='Generate transcript'
    )
    
    parser.add_argument(
        '--transcript-format',
        choices=['txt', 'json', 'srt', 'vtt'],
        default='txt',
        help='Transcript format (default: txt)'
    )
    
    parser.add_argument(
        '--no-diarization',
        action='store_true',
        help='Disable speaker diarization'
    )
    
    # Output options
    parser.add_argument(
        '--format',
        choices=['wav', 'mp3', 'flac'],
        help='Output audio format (overrides config)'
    )
    
    parser.add_argument(
        '--no-video',
        action='store_true',
        help='Don\'t merge audio back to video'
    )
    
    # Utility options
    parser.add_argument(
        '--continue-on-error',
        action='store_true',
        help='Continue processing if a file fails (batch mode)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Validate input
    if not args.input and not args.batch:
        parser.error("Please provide input file(s) or use --batch mode")
    
    # Setup logging
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    # Create output directory
    create_directories(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Initialize pipeline
    try:
        print("Initializing voice cleaning pipeline...")
        pipeline = VoiceCleaningPipeline(args.config)
        
        # Apply command-line overrides
        if args.format:
            pipeline.config['output']['format'] = args.format
        if args.no_video:
            pipeline.config['output']['preserve_video'] = False
        if args.no_diarization:
            pipeline.config['diarization']['enabled'] = False
            pipeline.diarization = None
        
    except Exception as e:
        print(f"Error initializing pipeline: {e}", file=sys.stderr)
        return 1
    
    # Collect files to process
    input_files = []
    
    if args.batch:
        # Batch mode
        if not os.path.isdir(args.batch):
            print(f"Error: Directory not found: {args.batch}", file=sys.stderr)
            return 1
        
        input_files = get_audio_files(args.batch, recursive=args.recursive)
        
        if not input_files:
            print(f"No audio/video files found in {args.batch}", file=sys.stderr)
            return 1
        
        print(f"Found {len(input_files)} files to process")
    
    else:
        # Single or multiple file mode
        for file_path in args.input:
            if not os.path.exists(file_path):
                print(f"Warning: File not found: {file_path}", file=sys.stderr)
                if not args.continue_on_error:
                    return 1
            else:
                input_files.append(file_path)
    
    if not input_files:
        print("No valid input files to process", file=sys.stderr)
        return 1
    
    # Process files
    try:
        if len(input_files) > 1:
            # Batch processing
            results, failed = pipeline.process_batch(
                input_files,
                output_dir=args.output_dir,
                continue_on_error=args.continue_on_error
            )
            
            # Summary
            print("\n" + "="*70)
            print(f"Processing complete!")
            print(f"Successfully processed: {len(results)}/{len(input_files)} files")
            print(f"Output directory: {args.output_dir}")
            
            if failed:
                print(f"\nFailed files ({len(failed)}):")
                for file, error in failed:
                    print(f"  - {file}: {error}")
            
            return 0 if not failed or args.continue_on_error else 1
        
        else:
            # Single file processing
            result = pipeline.process(
                input_files[0],
                output_dir=args.output_dir,
                save_transcript=args.transcript,
                transcript_format=args.transcript_format
            )
            
            # Summary
            print("\n" + "="*70)
            print("Processing complete!")
            print(f"Input: {result['input_path']}")
            print(f"Audio output: {result['audio_output_path']}")
            if result['video_output_path']:
                print(f"Video output: {result['video_output_path']}")
            print(f"Duration: {result['duration_processed']:.2f}s")
            print(f"Speech segments detected: {result['speech_segments']}")
            print("="*70)
            
            return 0
    
    except KeyboardInterrupt:
        print("\n\nProcessing interrupted by user", file=sys.stderr)
        return 130
    
    except Exception as e:
        print(f"\nError during processing: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
