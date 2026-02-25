# Voice Cleaning Pipeline - React Frontend

Modern web interface for the Voice Cleaning Pipeline built with React 18 and Material-UI.

## Features

- 🎨 Modern, responsive UI with Material-UI components
- 📁 Drag & drop file upload with react-dropzone
- ⚙️ Configurable processing settings (Whisper model, diarization, transcript format)
- 🎧 Live audio/video preview of processed files
- 📥 One-click download of cleaned files and transcripts
- 📊 Real-time processing progress feedback

## Prerequisites

- **Node.js 18.x or higher** (LTS recommended)
  - Download from: https://nodejs.org/
- Backend server running on port 8000

## Installation

1. **Install dependencies:**
   ```bash
   npm install
   ```

## Development

1. **Start development server:**
   ```bash
   npm run dev
   ```
   
   The app will open at http://localhost:3000

2. **Build for production:**
   ```bash
   npm run build
   ```

3. **Preview production build:**
   ```bash
   npm run preview
   ```

## Configuration

The frontend is configured to proxy API requests to `http://localhost:8000`. This is set in `vite.config.js`.

If you need to change the backend URL, edit the proxy configuration:

```javascript
// vite.config.js
export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://your-backend-url:8000'
    }
  }
})
```

## Project Structure

```
frontend/
├── src/
│   ├── main.jsx              # App entry point
│   ├── App.jsx               # Root component
│   └── components/
│       ├── FileUpload.jsx    # Drag & drop file upload
│       ├── Settings.jsx      # Processing configuration
│       └── Results.jsx       # Results display & download
├── public/                   # Static assets
├── index.html               # HTML template
├── vite.config.js          # Vite configuration
└── package.json            # Dependencies

```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Lint code (if ESLint configured)

## Tech Stack

- **React 18** - UI framework
- **Vite** - Build tool & dev server
- **Material-UI (MUI)** - Component library
- **react-dropzone** - File upload
- **axios** - HTTP client

## API Integration

The frontend communicates with the FastAPI backend through these endpoints:

- `POST /api/process` - Upload and process audio/video files
- `GET /api/download/{filename}` - Download processed files
- `WebSocket /ws/process` - Real-time progress updates (planned)

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## Troubleshooting

### Port already in use

If port 3000 is already in use, Vite will prompt you to use a different port or kill the existing process.

### Cannot connect to backend

Make sure the backend server is running on port 8000. Check the console for error messages.

### Module not found errors

Try deleting `node_modules` and reinstalling:
```bash
rm -rf node_modules
npm install
```
