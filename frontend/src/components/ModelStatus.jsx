import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  LinearProgress,
  Chip,
  Collapse,
  Alert,
  List,
  ListItem,
  ListItemIcon,
  ListItemText
} from '@mui/material'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import DownloadingIcon from '@mui/icons-material/Downloading'
import PendingIcon from '@mui/icons-material/Pending'

export default function ModelStatus() {
  const [status, setStatus] = useState(null)
  const [visible, setVisible] = useState(true)

  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/model-status')
      const data = await res.json()
      setStatus(data)
      // Hide once all ready
      if (data.all_ready) {
        setTimeout(() => setVisible(false), 3000)
      }
    } catch (e) {
      // Backend not reachable yet
    }
  }

  useEffect(() => {
    fetchStatus()
    // Poll every 3 seconds
    const interval = setInterval(fetchStatus, 3000)
    return () => clearInterval(interval)
  }, [])

  if (!status || !visible) return null

  const models = Object.values(status.models)
  const allReady = status.all_ready

  return (
    <Collapse in={visible}>
      <Alert
        severity={allReady ? 'success' : 'info'}
        sx={{ mb: 3 }}
        onClose={() => setVisible(false)}
      >
        <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 'bold' }}>
          {allReady ? '✅ All models ready!' : '📥 Downloading required AI models (first time only)...'}
        </Typography>

        <List dense disablePadding>
          {models.map((model) => (
            <ListItem key={model.name} disablePadding sx={{ mb: 0.5 }}>
              <ListItemIcon sx={{ minWidth: 32 }}>
                {model.ready ? (
                  <CheckCircleIcon fontSize="small" color="success" />
                ) : model.progress > 0 ? (
                  <DownloadingIcon fontSize="small" color="info" />
                ) : (
                  <PendingIcon fontSize="small" color="disabled" />
                )}
              </ListItemIcon>
              <ListItemText
                primary={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      {model.name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {model.description}
                    </Typography>
                    <Chip
                      label={model.ready ? 'Ready' : model.progress > 0 ? `${model.progress}%` : 'Pending'}
                      size="small"
                      color={model.ready ? 'success' : model.progress > 0 ? 'info' : 'default'}
                      sx={{ ml: 'auto', height: 18, fontSize: '0.65rem' }}
                    />
                  </Box>
                }
                secondary={
                  !model.ready && (
                    <Box sx={{ mt: 0.5 }}>
                      <LinearProgress
                        variant={model.progress > 0 ? 'determinate' : 'indeterminate'}
                        value={model.progress}
                        sx={{ height: 4, borderRadius: 2 }}
                      />
                      {model.progress > 0 && (
                        <Typography variant="caption" color="text.secondary">
                          {model.downloaded} / {model.total}
                        </Typography>
                      )}
                    </Box>
                  )
                }
              />
            </ListItem>
          ))}
        </List>

        {!allReady && (
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            ⚡ Models download automatically to the models\ folder — never again after first time!
          </Typography>
        )}
      </Alert>
    </Collapse>
  )
}
