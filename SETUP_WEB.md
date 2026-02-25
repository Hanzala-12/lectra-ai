# Voice Cleaning Pipeline - Web Interface Setup Guide

Welcome! This guide will help you set up and run the React + FastAPI web interface.

## 🎯 Quick Start (3 Steps)

### Step 1: Install Node.js (if not already installed)

**Download Node.js:**
1. Go to https://nodejs.org/
2. Download the **LTS version** (20.x or higher recommended)
3. Run the installer with default settings
4. Restart your PowerShell/Terminal after installation

**Verify installation:**
```powershell
node --version
npm --version
```

### Step 2: Install Frontend Dependencies

```powershell
cd d:\fyp\frontend
npm install
```

This will take 1-2 minutes. Wait for it to complete.

### Step 3: Start Both Servers

```powershell
cd d:\fyp
.\start_servers.ps1
```

This will open two PowerShell windows:
- **Backend**: http://localhost:8000 (FastAPI)
- **Frontend**: http://localhost:3000 (React)

Then open your browser to: **http://localhost:3000**

---

## 📋 What You Need

### Already Installed ✅
- Python 3.10.11 with virtual environment
- All Python dependencies (PyTorch, Whisper, DeepFilterNet, etc.)
- FastAPI backend

### Need to Install 📦
- **Node.js** (for React frontend)

---

## 🚀 Starting the Application

### Option 1: Start Both Servers (Recommended)

```powershell
.\start_servers.ps1
```

This opens two windows for backend and frontend.

### Option 2: Start Manually

**Terminal 1 - Backend:**
```powershell
.\start_backend.ps1
```

**Terminal 2 - Frontend:**
```powershell
.\start_frontend.ps1
```

---

## 🎨 Using the Web Interface

1. **Upload File**
   - Drag & drop your audio/video file
   - Or click to browse
   - Supported: MP3, WAV, MP4, MKV, etc.

2. **Configure Settings**
   - Choose Whisper model (base recommended)
   - Select transcript format (txt, srt, vtt, json)
   - Enable speaker diarization (optional, needs HF token)

3. **Process**
   - Click "Start Processing"
   - Wait for completion (1-5 minutes depending on file size)

4. **Download Results**
   - Listen to cleaned audio
   - Watch cleaned video (if video input)
   - Download transcript with timestamps

---

## 🔧 Troubleshooting

### "npm is not recognized"
**Solution:** Node.js is not installed or not in PATH
1. Install Node.js from https://nodejs.org/
2. Restart PowerShell
3. Verify: `node --version`

### Port 3000 already in use
**Solution:** Another app is using port 3000
- Vite will ask if you want to use a different port
- Or stop the other application using port 3000

### Port 8000 already in use
**Solution:** Backend port conflict
- Edit `backend.py` and change port to 8001
- Edit `frontend/vite.config.js` proxy to match

### Cannot connect to backend
**Solution:** Backend not running
1. Check if backend terminal shows: "Application startup complete"
2. Test: Open http://localhost:8000/docs in browser
3. If not working, restart backend

### npm install fails
**Solution:** Clear cache and retry
```powershell
cd frontend
npm cache clean --force
rm -rf node_modules
npm install
```

### Processing fails with "No transcript"
**Solution:** Transcript feature requires Whisper installation
- Check if `openai-whisper` is installed: `pip list | findstr whisper`
- If not: `pip install openai-whisper`

### Speaker diarization not working
**Solution:** Requires HuggingFace token
1. Get free token from https://huggingface.co/settings/tokens
2. Accept pyannote/speaker-diarization terms
3. Set token in config or disable diarization

---

## 📁 Architecture

```
d:\fyp\
├── backend.py              # FastAPI server (port 8000)
├── frontend/               # React app (port 3000)
│   ├── src/
│   │   ├── App.jsx        # Main component
│   │   ├── main.jsx       # Entry point
│   │   └── components/    # UI components
│   └── package.json       # Dependencies
├── src/                    # Python pipeline modules
├── models/                 # AI models (auto-downloaded)
├── outputs/                # Processed files
└── start_servers.ps1       # Start script
```

**Flow:**
1. User uploads file via React frontend (port 3000)
2. Frontend sends file to FastAPI backend (port 8000)
3. Backend runs pipeline: VAD → DeepFilterNet → Silent-bed → ASR
4. Results saved to `outputs/` folder
5. Frontend displays results with audio player + download buttons

---

## 🎯 Next Steps After Setup

### Test with Sample Files
1. Upload a short audio clip (30 seconds)
2. Use "base" Whisper model
3. Disable diarization for first test
4. Verify cleaned audio sounds better

### Production Use
- For large files, use "small" or "medium" Whisper model
- Enable diarization for multi-speaker content
- Use SRT format for subtitles
- Use JSON format for programmatic processing

---

## 📞 Need Help?

**Common Issues:**
- Check both terminal windows for error messages
- Verify all ports are available (3000, 8000)
- Ensure Python virtual environment is activated in backend
- Check browser console (F12) for frontend errors

**Test Backend Directly:**
```powershell
curl http://localhost:8000/health
```

**Test Frontend Build:**
```powershell
cd frontend
npm run build
```

---

## 🌟 Features

### Backend (FastAPI)
- ✅ RESTful API endpoints
- ✅ File upload with multipart/form-data
- ✅ Automatic audio extraction from video
- ✅ Progress tracking (WebSocket ready)
- ✅ CORS enabled for local development
- ✅ Swagger docs at /docs

### Frontend (React)
- ✅ Modern Material-UI design
- ✅ Drag & drop file upload
- ✅ Real-time progress indicator
- ✅ Audio/video preview
- ✅ Configurable settings
- ✅ One-click downloads
- ✅ Responsive design

---

**Ready to go? Run `.\start_servers.ps1` and open http://localhost:3000!** 🚀
