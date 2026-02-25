# Models Folder

This folder stores downloaded AI models.

## 📦 Whisper Models (Auto-Downloaded)

Whisper speech recognition models will be automatically downloaded here on first use.

### Available Models:

| Model  | Size | Download Time* | Disk Space | Best For |
|--------|------|----------------|------------|----------|
| tiny   | 39 MB | ~10-30 sec | 75 MB | Quick tests |
| **base** | **74 MB** | **~20-60 sec** | **140 MB** | **Recommended** ✅ |
| small  | 244 MB | ~1-2 min | 460 MB | Better accuracy |
| medium | 769 MB | ~3-5 min | 1.5 GB | High quality |
| **large** | **1.5 GB** | **~5-10 min** | **2.9 GB** | **Best quality** 🌟 |

*Internet speed dependent

## 🗣️ Pyannote Models (Auto-Downloaded with Token)

Speaker diarization models from pyannote.audio will be stored in `models/pyannote/` subfolder.

### What Gets Downloaded:

| Model | Size | Purpose |
|-------|------|---------|
| Speaker Diarization | ~300 MB | Main diarization model |
| Speaker Embeddings | ~400 MB | Speaker recognition |
| **Total** | **~700 MB** | Auto-downloads on first use |

### 🔑 Token Required:

**pyannote.audio requires HuggingFace token** (free account):

1. Get token: https://huggingface.co/settings/tokens
2. Accept license: https://huggingface.co/pyannote/speaker-diarization-3.1
3. Set in PowerShell:
```powershell
$env:HUGGING_FACE_HUB_TOKEN="your_token_here"
```

### 🔓 No Tokens or Accounts Needed!

**For Whisper models:**
- ✅ **100% Open Source** - Whisper is free
- ✅ **No Registration** - Download directly
- ✅ **Local Storage** - Models stay here forever
- ✅ **One-Time Download** - Reused for all future processing

**For pyannote.audio:**
- ⚠️ **Requires HuggingFace token** (free account)
- ✅ **One-Time Setup** - Token saved in environment
- ✅ **Local Storage** - Models cached here forever

### 📁 What Gets Stored Here:

```
models/
├── tiny.pt           (Whisper tiny model)
├── base.pt           (Whisper base model)
├── small.pt          (Whisper small model)
├── medium.pt         (Whisper medium model)
├── large.pt          (Whisper large model)
└── pyannote/         (Diarization models folder)
    ├── models--pyannote--speaker-diarization-3.1/
    ├── models--pyannote--wespeaker-voxceleb-resnet34-LM/
    └── ... (various diarization models)
```

### 🚀 First Time Use:

When you select a model in the web interface:
1. Click "Start Processing"
2. Model downloads automatically (only once)
3. Shows "🔧 Initializing AI models..." message
4. Processing begins after download completes

**Only the first file takes time. All future files are instant!**

### 💡 Recommendations:

**Start with `base`:**
- Fast download (~1 minute)
- Good quality
- Low disk space (140 MB)
- Perfect for testing

**Upgrade to `large` for production:**
- Best transcription quality
- Worth the wait for important content
- Takes ~5-10 minutes to download first time
- Uses 2.9 GB disk space

### 🔧 Troubleshooting:

**Download too slow?**
- Check internet connection
- Downloads resume if interrupted
- Large model takes time (normal!)

**Out of disk space?**
- Delete unused models (e.g., delete `tiny.pt` if you don't use it)
- Each model is independent
- Keep only the models you use

**Download failed?**
- Try again - downloads resume automatically
- Check firewall settings
- Ensure ~3 GB free space for large model

---

**Note:** This folder is excluded from git (in `.gitignore`). Only you have these models locally. Anyone who clones your repo will download their own copy.
