import {
  Box,
  Typography,
  FormControl,
  FormControlLabel,
  Select,
  MenuItem,
  Switch,
  InputLabel,
  Grid,
  Tooltip,
  IconButton
} from '@mui/material'
import InfoIcon from '@mui/icons-material/Info'

export default function Settings({ settings, onSettingsChange }) {
  const handleChange = (field) => (event) => {
    const value = event.target.type === 'checkbox' ? event.target.checked : event.target.value
    onSettingsChange({ ...settings, [field]: value })
  }

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        ⚙️ Processing Settings
      </Typography>

      <Grid container spacing={3} sx={{ mt: 1 }}>
        {/* Whisper Model */}
        <Grid item xs={12} md={6}>
          <FormControl fullWidth>
            <InputLabel>Whisper Model</InputLabel>
            <Select
              value={settings.whisperModel}
              label="Whisper Model"
              onChange={handleChange('whisperModel')}
            >
              <MenuItem value="base">Base (74 MB) — Fast</MenuItem>
              <MenuItem value="small">Small (244 MB) — Better</MenuItem>
              <MenuItem value="medium">Medium (769 MB) — Good</MenuItem>
              <MenuItem value="large">Large (1.5 GB) — Best accuracy (slow)</MenuItem>
            </Select>
          </FormControl>
        </Grid>

        {/* Transcript Format */}
        <Grid item xs={12} md={6}>
          <FormControl fullWidth>
            <InputLabel>Transcript Format</InputLabel>
            <Select
              value={settings.transcriptFormat}
              label="Transcript Format"
              onChange={handleChange('transcriptFormat')}
            >
              <MenuItem value="txt">Plain Text (.txt)</MenuItem>
              <MenuItem value="srt">Subtitle (.srt)</MenuItem>
              <MenuItem value="vtt">WebVTT (.vtt)</MenuItem>
              <MenuItem value="json">JSON (.json)</MenuItem>
            </Select>
          </FormControl>
        </Grid>

        {/* Diarization */}
        <Grid item xs={12} md={6}>
          <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={settings.enableDiarization}
                  onChange={handleChange('enableDiarization')}
                  color="primary"
                />
              }
              label="Speaker Diarization"
            />
            <Tooltip title="Identify and separate different speakers in the audio. Requires HuggingFace token.">
              <IconButton size="small">
                <InfoIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>
        </Grid>
      </Grid>

      <Box sx={{ mt: 2, p: 2, backgroundColor: 'info.lighter', borderRadius: 1 }}>
        <Typography variant="caption" color="text.secondary">
          💡 <strong>Tip:</strong> Use <strong>Base</strong> for fast results, <strong>Large</strong> for best accuracy (needs ~3 GB RAM, takes longer).
          Enable diarization to identify different speakers (Teacher / Student etc).
        </Typography>
      </Box>
    </Box>
  )
}
