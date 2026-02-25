# Web Interface Guide

## 🌐 Voice Cleaning Web Interface

A beautiful web interface for the voice cleaning pipeline with drag-and-drop file upload.

---

## 🚀 Quick Start

### 1. Install Dependencies (if not already done)
```powershell
.\setup.ps1
```

### 2. Start Web Interface
```powershell
.\start_web.ps1
```

The interface will open automatically at **http://localhost:8501**

---

## 🎯 Whisper Models Explained

### Models Download Automatically! ✅

**You don't need to manually download anything!**

On first use, Whisper will automatically download the selected model to:
- **Windows:** `C:\Users\YourName\.cache\whisper\`
- **Model files:** `.pt` format (PyTorch models)

### Model Comparison

| Model  | Size | Speed | Accuracy | RAM  | Best For |
|--------|------|-------|----------|------|----------|
| tiny   | 39M  | ⚡⚡⚡⚡⚡ | ⭐⭐     | 1GB  | Quick tests |
| **base**   | **74M**  | **⚡⚡⚡⚡**  | **⭐⭐⭐**   | **1GB**  | **Recommended** ✅ |
| small  | 244M | ⚡⚡⚡   | ⭐⭐⭐⭐   | 2GB  | Good balance |
| medium | 769M | ⚡⚡    | ⭐⭐⭐⭐⭐ | 5GB  | High accuracy |
| large  | 1.5G | ⚡     | ⭐⭐⭐⭐⭐ | 10GB | Best quality |

### 💡 Recommendations

**For Most Users:** Use **`base`** model
- Good accuracy
- Fast processing
- Low memory usage
- Best all-around choice

**For Short Audio (<5 min):** Use **`small`**
- Better accuracy
- Still reasonably fast

**For Critical Transcription:** Use **`medium`** or **`large`**
- Professional quality
- Slower but worth it for important content

---

## 🎨 Web Interface Features

### Upload Section
- ✅ Drag & drop file upload
- ✅ Supports audio (MP3, WAV, FLAC) and video (MP4, AVI, MKV)
- ✅ File size display

### Settings (Sidebar)
- 🎯 **Whisper Model Selection** - Choose quality vs speed
- 🗣️ **Speaker Diarization** - Identify different speakers
- 📝 **Transcript Options** - Enable/disable, choose format (TXT, SRT, VTT, JSON)

### Results
- 🎵 **Audio Player** - Listen to cleaned audio
- 🎬 **Video Player** - Watch cleaned video (if input was video)
- 📝 **Transcript Display** - Read full transcript
- ⬇️ **Download Buttons** - Download all processed files
- 📊 **Statistics** - Duration, segments, speakers

---

## 📁 File Storage

### Processed Files Location
Processed files are temporarily stored during web session but can be downloaded:
- Cleaned audio: `.wav` format
- Cleaned video: `.mp4` format
- Transcripts: `.txt`, `.srt`, `.vtt`, or `.json`

### Model Cache
Whisper models are permanently cached at:
```
C:\Users\YourName\.cache\whisper\
```

You only download each model once!

---

## 🔧 Advanced: Manual Model Download

If you want to pre-download models (optional):

```python
import whisper

# Download specific model
whisper.load_model("base")  # Downloads ~74MB

# Models available: tiny, base, small, medium, large
```

Or via CLI before starting:
```powershell
python -c "import whisper; whisper.load_model('base')"
```

---

## 🌟 Usage Tips

### For Best Results:
1. **Start with 'base' model** - Try it first
2. **Enable diarization** for multi-speaker content
3. **Choose SRT format** for video subtitles
4. **Use 'medium' model** for important transcriptions

### For Speed:
1. **Use 'tiny' or 'base'** models
2. **Disable diarization** if you don't need speaker labels
3. **Process shorter clips** (under 10 minutes)

### For Accuracy:
1. **Use 'medium' or 'large'** models
2. **Enable diarization** for speaker context
3. **High-quality input audio** = better results

---

## 🐛 Troubleshooting

### "Model download failed"
- Check internet connection
- Ensure ~1-10GB free disk space (depending on model)
- Try again - downloads resume automatically

### "Out of memory"
- Use smaller model (tiny or base)
- Close other applications
- Process shorter audio segments

### "Diarization not working"
- Set HuggingFace token: `$env:HUGGING_FACE_HUB_TOKEN="your_token"`
- Get token from: https://huggingface.co/settings/tokens

---

## 📊 Performance Guide

### CPU Processing Times (approximate):
- **tiny:** ~0.5x real-time (10 min audio = 5 min processing)
- **base:** ~1x real-time (10 min audio = 10 min processing)
- **small:** ~2x real-time
- **medium:** ~4x real-time
- **large:** ~8x real-time

### With GPU (CUDA):
- **5-10x faster** across all models
- Real-time or better for tiny/base models

---

## 🎓 Examples

### Example 1: Quick Podcast Cleanup
```
1. Upload: podcast.mp3
2. Model: base
3. Diarization: ✅ ON
4. Transcript: TXT
5. Process → Download cleaned audio + transcript
```

### Example 2: Interview Video with Subtitles
```
1. Upload: interview.mp4
2. Model: small
3. Diarization: ✅ ON
4. Transcript: SRT
5. Process → Download video with subtitles
```

### Example 3: High-Quality Transcription
```
1. Upload: lecture.wav
2. Model: medium
3. Diarization: ❌ OFF (single speaker)
4. Transcript: JSON
5. Process → Get detailed transcript with timestamps
```

---

## 💾 Model Sizes (Download Once)

| Model  | Download Size | Disk Space |
|--------|--------------|------------|
| tiny   | ~39 MB       | ~75 MB     |
| base   | ~74 MB       | ~140 MB    |
| small  | ~244 MB      | ~460 MB    |
| medium | ~769 MB      | ~1.5 GB    |
| large  | ~1.5 GB      | ~2.9 GB    |

**Total for all models:** ~3.3 GB (but you probably only need 1-2)

---

## 🎯 Summary

✅ **Models download automatically** - No manual download needed  
✅ **Start with 'base' model** - Best for most users  
✅ **Upgrade to 'medium'** when you need better accuracy  
✅ **One-time download** - Models are cached forever  
✅ **Easy web interface** - Just upload and click!  

---

**Ready to start?** Run `.\start_web.ps1` and open your browser! 🚀
