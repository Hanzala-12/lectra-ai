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

### 🔓 No Tokens or Accounts Needed!

- ✅ **100% Open Source** - Whisper is free
- ✅ **No Registration** - Download directly
- ✅ **Local Storage** - Models stay here forever
- ✅ **One-Time Download** - Reused for all future processing

### 📁 What Gets Stored Here:

```
models/
├── tiny.pt       (if you use tiny model)
├── base.pt       (if you use base model)
├── small.pt      (if you use small model)
├── medium.pt     (if you use medium model)
└── large.pt      (if you use large model)
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
