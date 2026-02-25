import {
  Box,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  Divider,
  Chip
} from '@mui/material'
import DownloadIcon from '@mui/icons-material/Download'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import AudioFileIcon from '@mui/icons-material/AudioFile'
import TranscriptIcon from '@mui/icons-material/Description'
import VideoFileIcon from '@mui/icons-material/VideoFile'

export default function Results({ result }) {
  const handleDownload = (filename) => {
    window.open(`/api/download/${filename}`, '_blank')
  }

  const formatDuration = (seconds) => {
    if (!seconds) return 'N/A'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}m ${secs}s`
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <CheckCircleIcon sx={{ fontSize: 40, color: 'success.main', mr: 2 }} />
        <Box>
          <Typography variant="h5" gutterBottom>
            ✅ Processing Complete!
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Processing time: {formatDuration(result.processing_time)}
          </Typography>
        </Box>
      </Box>

      <Divider sx={{ mb: 3 }} />

      <Grid container spacing={3}>
        {/* Cleaned Audio */}
        {result.cleaned_audio && (
          <Grid item xs={12} md={6}>
            <Card elevation={2}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <AudioFileIcon sx={{ fontSize: 32, color: 'primary.main', mr: 1 }} />
                  <Typography variant="h6">Cleaned Audio</Typography>
                </Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  High-quality audio with background noise removed
                </Typography>
                
                {/* Audio Player */}
                <Box sx={{ my: 2 }}>
                  <audio 
                    controls 
                    style={{ width: '100%' }}
                    src={`/api/download/${result.cleaned_audio.split('/').pop()}`}
                  >
                    Your browser does not support audio playback.
                  </audio>
                </Box>

                <Button
                  variant="contained"
                  startIcon={<DownloadIcon />}
                  onClick={() => handleDownload(result.cleaned_audio.split('/').pop())}
                  fullWidth
                >
                  Download Audio
                </Button>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Cleaned Video */}
        {result.cleaned_video && (
          <Grid item xs={12} md={6}>
            <Card elevation={2}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <VideoFileIcon sx={{ fontSize: 32, color: 'secondary.main', mr: 1 }} />
                  <Typography variant="h6">Cleaned Video</Typography>
                </Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Video with enhanced audio track
                </Typography>
                
                {/* Video Player */}
                <Box sx={{ my: 2 }}>
                  <video 
                    controls 
                    style={{ width: '100%', maxHeight: '300px' }}
                    src={`/api/download/${result.cleaned_video.split('/').pop()}`}
                  >
                    Your browser does not support video playback.
                  </video>
                </Box>

                <Button
                  variant="contained"
                  color="secondary"
                  startIcon={<DownloadIcon />}
                  onClick={() => handleDownload(result.cleaned_video.split('/').pop())}
                  fullWidth
                >
                  Download Video
                </Button>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Transcript */}
        {result.transcript && (
          <Grid item xs={12}>
            <Card elevation={2}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <TranscriptIcon sx={{ fontSize: 32, color: 'info.main', mr: 1 }} />
                  <Typography variant="h6">Transcript</Typography>
                  {result.diarization && (
                    <Chip 
                      label="With Speaker Diarization" 
                      size="small" 
                      color="success" 
                      sx={{ ml: 2 }}
                    />
                  )}
                </Box>

                {/* Transcript Preview */}
                <Box 
                  sx={{ 
                    p: 2, 
                    backgroundColor: 'grey.50', 
                    borderRadius: 1, 
                    maxHeight: 300, 
                    overflow: 'auto',
                    fontFamily: 'monospace',
                    fontSize: '0.9rem',
                    whiteSpace: 'pre-wrap',
                    mb: 2
                  }}
                >
                  {result.transcript_preview || 'Transcript available for download'}
                </Box>

                <Button
                  variant="outlined"
                  startIcon={<DownloadIcon />}
                  onClick={() => handleDownload(result.transcript.split('/').pop())}
                  fullWidth
                >
                  Download Full Transcript
                </Button>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>

      {/* Processing Info */}
      <Box sx={{ mt: 3, p: 2, backgroundColor: 'success.lighter', borderRadius: 1 }}>
        <Typography variant="body2">
          <strong>Pipeline Applied:</strong> Pre-VAD Trim → DeepFilterNet Enhancement → 
          Silent-Bed Transplant (20ms fades) → Whisper ASR
          {result.diarization && ' → Speaker Diarization'}
        </Typography>
      </Box>
    </Box>
  )
}
