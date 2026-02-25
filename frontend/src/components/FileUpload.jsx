import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import {
  Box,
  Typography,
  Button,
  LinearProgress,
  Chip
} from '@mui/material'
import CloudUploadIcon from '@mui/icons-material/CloudUpload'
import AudioFileIcon from '@mui/icons-material/AudioFile'
import VideoFileIcon from '@mui/icons-material/VideoFile'

export default function FileUpload({ onFileSelect, onProcess, file, processing }) {
  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      onFileSelect(acceptedFiles[0])
    }
  }, [onFileSelect])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'audio/*': ['.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg'],
      'video/*': ['.mp4', '.avi', '.mkv', '.mov', '.webm']
    },
    multiple: false
  })

  const getFileIcon = () => {
    if (!file) return null
    const isVideo = file.type.startsWith('video/')
    return isVideo ? <VideoFileIcon fontSize="large" /> : <AudioFileIcon fontSize="large" />
  }

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        📁 Upload File
      </Typography>

      {/* Dropzone */}
      <Box
        {...getRootProps()}
        sx={{
          border: '2px dashed',
          borderColor: isDragActive ? 'primary.main' : 'grey.300',
          borderRadius: 2,
          p: 4,
          textAlign: 'center',
          cursor: 'pointer',
          backgroundColor: isDragActive ? 'action.hover' : 'background.paper',
          transition: 'all 0.3s',
          '&:hover': {
            borderColor: 'primary.main',
            backgroundColor: 'action.hover'
          }
        }}
      >
        <input {...getInputProps()} />
        <CloudUploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
        <Typography variant="h6" gutterBottom>
          {isDragActive ? 'Drop file here...' : 'Drag & drop file here'}
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          or click to browse
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Supported formats: MP3, WAV, M4A, FLAC, AAC, OGG, MP4, AVI, MKV, MOV, WEBM
        </Typography>
      </Box>

      {/* File Info */}
      {file && (
        <Box sx={{ mt: 3, p: 2, backgroundColor: 'grey.50', borderRadius: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            {getFileIcon()}
            <Box sx={{ flexGrow: 1 }}>
              <Typography variant="body1" fontWeight="bold">
                {file.name}
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                <Chip label={formatFileSize(file.size)} size="small" />
                <Chip label={file.type || 'Unknown type'} size="small" color="primary" />
              </Box>
            </Box>
          </Box>
        </Box>
      )}

      {/* Process Button */}
      <Box sx={{ mt: 3, display: 'flex', justifyContent: 'center' }}>
        <Button
          variant="contained"
          size="large"
          onClick={onProcess}
          disabled={!file || processing}
          startIcon={<CloudUploadIcon />}
          sx={{ minWidth: 200 }}
        >
          {processing ? 'Processing...' : 'Start Processing'}
        </Button>
      </Box>

      {/* Progress */}
      {processing && (
        <Box sx={{ mt: 3 }}>
          <LinearProgress />
          <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 1 }}>
            Processing your file... This may take a few minutes
          </Typography>
        </Box>
      )}
    </Box>
  )
}
