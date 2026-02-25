"""
Web Interface for Voice Cleaning Pipeline
Upload audio/video files and get cleaned results with transcripts
"""

import streamlit as st
import sys
import os
from pathlib import Path
import tempfile
import shutil

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from pipeline import VoiceCleaningPipeline
from utils import format_duration

# Page config
st.set_page_config(
    page_title="Voice Cleaning Pipeline",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #1E88E5;
        margin-bottom: 1rem;
    }
    .sub-header {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .result-box {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .success-msg {
        color: #28a745;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'processed' not in st.session_state:
    st.session_state.processed = False
if 'result' not in st.session_state:
    st.session_state.result = None

def initialize_pipeline(whisper_model, enable_diarization):
    """Initialize pipeline with selected settings"""
    with st.spinner("🔧 Initializing AI models... (First run downloads models ~500MB)"):
        try:
            pipeline = VoiceCleaningPipeline("config.yaml")
            
            # Update settings
            pipeline.config['asr']['model'] = whisper_model
            pipeline.config['diarization']['enabled'] = enable_diarization
            
            # Reinitialize ASR with selected model
            from asr_processor import ASRProcessor
            pipeline.asr = ASRProcessor(
                model_size=whisper_model,
                language=pipeline.config['asr'].get('language'),
                compute_type=pipeline.config['asr']['compute_type']
            )
            
            if not enable_diarization:
                pipeline.diarization = None
            
            return pipeline
        except Exception as e:
            st.error(f"❌ Error initializing pipeline: {e}")
            return None

def process_file(uploaded_file, pipeline, save_transcript, transcript_format):
    """Process uploaded file"""
    
    # Create temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Save uploaded file
        input_path = os.path.join(temp_dir, uploaded_file.name)
        with open(input_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        
        st.info(f"📁 File uploaded: {uploaded_file.name} ({uploaded_file.size / 1024 / 1024:.2f} MB)")
        
        # Create output directory
        output_dir = os.path.join(temp_dir, "outputs")
        os.makedirs(output_dir, exist_ok=True)
        
        # Process file
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("🎵 Loading audio...")
            progress_bar.progress(10)
            
            status_text.text("🔍 Detecting speech segments...")
            progress_bar.progress(20)
            
            status_text.text("🧹 Removing background noise (DeepFilterNet)...")
            progress_bar.progress(40)
            
            result = pipeline.process(
                input_path=input_path,
                output_dir=output_dir,
                save_transcript=save_transcript,
                transcript_format=transcript_format
            )
            
            progress_bar.progress(80)
            status_text.text("📝 Generating transcript...")
            
            progress_bar.progress(100)
            status_text.text("✅ Processing complete!")
            
            # Load output files
            audio_output_path = result['audio_output_path']
            with open(audio_output_path, 'rb') as f:
                audio_bytes = f.read()
            
            result['audio_bytes'] = audio_bytes
            result['audio_filename'] = os.path.basename(audio_output_path)
            
            # Load transcript if generated
            if save_transcript:
                input_name = Path(uploaded_file.name).stem
                transcript_path = os.path.join(output_dir, f"{input_name}_transcript.{transcript_format}")
                if os.path.exists(transcript_path):
                    with open(transcript_path, 'r', encoding='utf-8') as f:
                        result['transcript_file'] = f.read()
            
            # Load video if applicable
            if result.get('video_output_path') and os.path.exists(result['video_output_path']):
                with open(result['video_output_path'], 'rb') as f:
                    result['video_bytes'] = f.read()
                result['video_filename'] = os.path.basename(result['video_output_path'])
            
            return result
            
        except Exception as e:
            st.error(f"❌ Error processing file: {e}")
            import traceback
            st.code(traceback.format_exc())
            return None

# Header
st.markdown('<p class="main-header">🎙️ Voice Cleaning Pipeline</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Remove background noise from audio/video files with AI</p>', unsafe_allow_html=True)

# Sidebar - Settings
st.sidebar.header("⚙️ Settings")

st.sidebar.subheader("🎯 Whisper Model")
whisper_model = st.sidebar.selectbox(
    "Speech Recognition Model",
    ["tiny", "base", "small", "medium", "large"],
    index=1,  # Default to "base"
    help="Larger models are more accurate but slower"
)

model_info = {
    "tiny": "⚡ Fastest (~39M params, ~1GB RAM)",
    "base": "✅ Recommended (~74M params, ~1GB RAM)",
    "small": "🎯 Accurate (~244M params, ~2GB RAM)",
    "medium": "🔥 Very Accurate (~769M params, ~5GB RAM)",
    "large": "🌟 Best Quality (~1550M params, ~10GB RAM)"
}
st.sidebar.info(model_info[whisper_model])

st.sidebar.subheader("🗣️ Features")
enable_diarization = st.sidebar.checkbox(
    "Speaker Diarization",
    value=True,
    help="Identify different speakers (requires HuggingFace token)"
)

save_transcript = st.sidebar.checkbox(
    "Generate Transcript",
    value=True,
    help="Create text transcript of the audio"
)

transcript_format = st.sidebar.selectbox(
    "Transcript Format",
    ["txt", "srt", "vtt", "json"],
    help="Choose output format for transcript"
)

st.sidebar.markdown("---")
st.sidebar.subheader("📚 About")
st.sidebar.info("""
**Pipeline Steps:**
1. 🎵 Load audio/video
2. ✂️ Pre-VAD trim
3. 🧹 DeepFilterNet cleaning
4. 🔄 Silent-bed transplant
5. 🗣️ Speaker diarization
6. 📝 Speech recognition
""")

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📤 Upload File")
    uploaded_file = st.file_uploader(
        "Choose an audio or video file",
        type=['mp3', 'wav', 'flac', 'ogg', 'm4a', 'aac', 'mp4', 'avi', 'mkv', 'mov', 'webm'],
        help="Supported: Audio (MP3, WAV, FLAC) and Video (MP4, AVI, MKV)"
    )

with col2:
    st.subheader("⚡ Quick Stats")
    if uploaded_file:
        st.metric("File Size", f"{uploaded_file.size / 1024 / 1024:.2f} MB")
        st.metric("File Type", uploaded_file.type)

# Process button
if uploaded_file:
    if st.button("🚀 Start Processing", type="primary", use_container_width=True):
        # Initialize pipeline
        pipeline = initialize_pipeline(whisper_model, enable_diarization)
        
        if pipeline:
            # Process file
            result = process_file(uploaded_file, pipeline, save_transcript, transcript_format)
            
            if result:
                st.session_state.processed = True
                st.session_state.result = result
                st.balloons()

# Display results
if st.session_state.processed and st.session_state.result:
    result = st.session_state.result
    
    st.markdown("---")
    st.header("✨ Results")
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Original Duration", f"{result['duration_original']:.2f}s")
    with col2:
        st.metric("Processed Duration", f"{result['duration_processed']:.2f}s")
    with col3:
        st.metric("Speech Segments", result['speech_segments'])
    with col4:
        file_type = "Video" if result['is_video'] else "Audio"
        st.metric("Input Type", file_type)
    
    # Audio output
    st.subheader("🎵 Cleaned Audio")
    st.audio(result['audio_bytes'], format='audio/wav')
    st.download_button(
        label="⬇️ Download Cleaned Audio",
        data=result['audio_bytes'],
        file_name=result['audio_filename'],
        mime="audio/wav"
    )
    
    # Video output (if applicable)
    if result.get('video_bytes'):
        st.subheader("🎬 Cleaned Video")
        st.video(result['video_bytes'])
        st.download_button(
            label="⬇️ Download Cleaned Video",
            data=result['video_bytes'],
            file_name=result['video_filename'],
            mime="video/mp4"
        )
    
    # Transcript
    if save_transcript and result.get('transcript'):
        st.subheader("📝 Transcript")
        
        # Show speaker statistics if diarization enabled
        if enable_diarization and result.get('diarization'):
            st.info(f"🗣️ Detected {len(set(d['speaker'] for d in result['diarization']))} speakers")
        
        # Display transcript
        transcript_text = result['transcript'].get('text', '')
        st.text_area("Full Transcript", transcript_text, height=200)
        
        # Download transcript
        if result.get('transcript_file'):
            st.download_button(
                label=f"⬇️ Download Transcript (.{transcript_format})",
                data=result['transcript_file'],
                file_name=f"transcript.{transcript_format}",
                mime="text/plain"
            )
        
        # Show segments
        with st.expander("📊 View Detailed Segments"):
            segments = result['transcript'].get('segments', [])
            for i, seg in enumerate(segments[:10]):  # Show first 10
                st.markdown(f"**[{seg['start']:.2f}s - {seg['end']:.2f}s]** {seg['text']}")
            if len(segments) > 10:
                st.info(f"Showing 10 of {len(segments)} segments. Download full transcript for complete results.")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>🎙️ Voice Cleaning Pipeline | Powered by DeepFilterNet & Whisper</p>
    <p>Made with ❤️ using Streamlit</p>
</div>
""", unsafe_allow_html=True)
