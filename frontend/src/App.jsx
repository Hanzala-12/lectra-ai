import { useState } from 'react'
import {
  Container,
  Box,
  Typography,
  Paper,
  AppBar,
  Toolbar,
  Alert
} from '@mui/material'
import AudiotrackIcon from '@mui/icons-material/Audiotrack'
import FileUpload from './components/FileUpload'
import Settings from './components/Settings'
import Results from './components/Results'

function App() {
  const [file, setFile] = useState(null)
  const [processing, setProcessing] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [settings, setSettings] = useState({
    whisperModel: 'base',
    enableDiarization: true,
    transcriptFormat: 'txt'
  })

  const handleFileSelect = (selectedFile) => {
    setFile(selectedFile)
    setResult(null)
    setError(null)
  }

  const handleProcess = async () => {
    if (!file) return

    setProcessing(true)
    setError(null)

    const formData = new FormData()
    formData.append('file', file)
    formData.append('whisper_model', settings.whisperModel)
    formData.append('enable_diarization', settings.enableDiarization)
    formData.append('transcript_format', settings.transcriptFormat)

    try {
      const response = await fetch('/api/process', {
        method: 'POST',
        body: formData
      })

      const data = await response.json()

      if (data.success) {
        setResult(data)
      } else {
        setError(data.error || 'Processing failed')
      }
    } catch (err) {
      setError('Failed to connect to server: ' + err.message)
    } finally {
      setProcessing(false)
    }
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      {/* Header */}
      <AppBar position="static" elevation={0}>
        <Toolbar>
          <AudiotrackIcon sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Voice Cleaning Pipeline
          </Typography>
          <Typography variant="body2">
            Powered by DeepFilterNet & Whisper
          </Typography>
        </Toolbar>
      </AppBar>

      {/* Main Content */}
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4, flexGrow: 1 }}>
        <Typography variant="h4" gutterBottom align="center" sx={{ mb: 1 }}>
          🎙️ AI-Powered Voice Cleaning
        </Typography>
        <Typography variant="body1" align="center" color="text.secondary" sx={{ mb: 4 }}>
          Remove background noise from audio and video files with advanced AI
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
          <Settings settings={settings} onSettingsChange={setSettings} />
        </Paper>

        <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
          <FileUpload
            onFileSelect={handleFileSelect}
            onProcess={handleProcess}
            file={file}
            processing={processing}
          />
        </Paper>

        {result && (
          <Paper elevation={3} sx={{ p: 3 }}>
            <Results result={result} />
          </Paper>
        )}
      </Container>

      {/* Footer */}
      <Box component="footer" sx={{ py: 3, px: 2, mt: 'auto', backgroundColor: '#f5f5f5' }}>
        <Container maxWidth="lg">
          <Typography variant="body2" color="text.secondary" align="center">
            Voice Cleaning Pipeline © 2026 | Open Source
          </Typography>
        </Container>
      </Box>
    </Box>
  )
}

export default App
