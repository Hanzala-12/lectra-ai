import { useState, useRef } from 'react'
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Divider,
  Chip,
  Stack,
  Tooltip,
  Avatar
} from '@mui/material'
import DownloadIcon from '@mui/icons-material/Download'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import GraphicEqIcon from '@mui/icons-material/GraphicEq'
import RecordVoiceOverIcon from '@mui/icons-material/RecordVoiceOver'
import AccessTimeIcon from '@mui/icons-material/AccessTime'
import VolumeUpIcon from '@mui/icons-material/VolumeUp'
import PeopleIcon from '@mui/icons-material/People'

// Soft colour palette for up to 6 distinct speakers
const SPEAKER_COLORS = [
  { bg: '#e3f2fd', border: '#1565c0', avatar: '#1565c0', label: '#0d47a1' }, // blue   â€“ Speaker 1
  { bg: '#fce4ec', border: '#c62828', avatar: '#c62828', label: '#b71c1c' }, // red    â€“ Speaker 2
  { bg: '#e8f5e9', border: '#2e7d32', avatar: '#2e7d32', label: '#1b5e20' }, // green  â€“ Speaker 3
  { bg: '#fff8e1', border: '#f57f17', avatar: '#f57f17', label: '#e65100' }, // amber  â€“ Speaker 4
  { bg: '#f3e5f5', border: '#6a1b9a', avatar: '#6a1b9a', label: '#4a148c' }, // purple â€“ Speaker 5
  { bg: '#e0f7fa', border: '#00695c', avatar: '#00695c', label: '#004d40' }, // teal   â€“ Speaker 6
]

function formatTime(seconds) {
  if (seconds == null) return ''
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

function formatDuration(seconds) {
  if (!seconds) return 'N/A'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return m > 0 ? `${m}m ${s}s` : `${s}s`
}

// Human-friendly speaker label (SPEAKER_00 â†’ Speaker 1, etc.)
function speakerLabel(rawId, indexMap) {
  if (!rawId) return 'Unknown'
  const idx = indexMap[rawId]
  return `Speaker ${(idx ?? 0) + 1}`
}

export default function Results({ result }) {
  const cleanedAudioRef = useRef(null)

  // Seek cleaned audio when user clicks a transcript segment
  const seekTo = (seconds) => {
    if (cleanedAudioRef.current) {
      cleanedAudioRef.current.currentTime = seconds
      cleanedAudioRef.current.play()
    }
  }

  // Assign a stable colour index to each unique speaker id
  const speakerIndexMap = {}
  ;(result.transcript_segments || []).forEach(seg => {
    if (seg.speaker && speakerIndexMap[seg.speaker] === undefined) {
      speakerIndexMap[seg.speaker] = Object.keys(speakerIndexMap).length
    }
  })
  // also include speakers that only appear in diarization (no transcript)
  ;(result.diarization || []).forEach(seg => {
    if (seg.speaker && speakerIndexMap[seg.speaker] === undefined) {
      speakerIndexMap[seg.speaker] = Object.keys(speakerIndexMap).length
    }
  })

  const hasDiarization = result.diarization && result.diarization.length > 0
  const hasSegments = result.transcript_segments && result.transcript_segments.length > 0
  const speakerAudio = result.speaker_audio || {}
  const hasSpeakerAudio = Object.keys(speakerAudio).length > 0

  // Group diarization segments per speaker for the sidebar
  const segsBySpk = {}
  ;(result.diarization || []).forEach(seg => {
    const spk = seg.speaker || 'Unknown'
    if (!segsBySpk[spk]) segsBySpk[spk] = []
    segsBySpk[spk].push(seg)
  })

  return (
    <Box>
      {/* â”€â”€ Header â”€â”€ */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <CheckCircleIcon sx={{ fontSize: 40, color: 'success.main', mr: 2 }} />
        <Box>
          <Typography variant="h5" fontWeight={700}>Processing Complete!</Typography>
          <Typography variant="body2" color="text.secondary">
            {formatDuration(result.duration_original)} original â†’ {formatDuration(result.duration_processed)} cleaned
            &nbsp;Â·&nbsp; {result.speech_segments} speech segments detected
          </Typography>
        </Box>
      </Box>

      <Divider sx={{ mb: 3 }} />

      {/* â”€â”€ Original Audio Player â”€â”€ */}
      {result.original_audio_url && (
        <Card elevation={2} sx={{ mb: 2, borderLeft: '5px solid', borderColor: 'grey.400' }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5 }}>
              <VolumeUpIcon sx={{ color: 'grey.600', mr: 1 }} />
              <Typography variant="h6" fontWeight={600}>Original Audio</Typography>
              <Chip label="Unprocessed" size="small" sx={{ ml: 1.5, bgcolor: 'grey.200' }} />
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
              Raw upload before any noise removal
            </Typography>
            <audio controls style={{ width: '100%', borderRadius: 8 }} src={result.original_audio_url} />
          </CardContent>
        </Card>
      )}

      {/* â”€â”€ Cleaned Audio Player â”€â”€ */}
      {result.audio_url && (
        <Card elevation={3} sx={{ mb: 3, borderLeft: '5px solid', borderColor: 'primary.main' }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5 }}>
              <GraphicEqIcon sx={{ color: 'primary.main', mr: 1 }} />
              <Typography variant="h6" fontWeight={600}>Cleaned Audio</Typography>
              <Chip label="Noise Removed" size="small" color="success" sx={{ ml: 1.5 }} />
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
              Background noise removed with DeepFilterNet3 Â· Click any transcript line to jump to that moment
            </Typography>
            <audio
              ref={cleanedAudioRef}
              controls
              style={{ width: '100%', borderRadius: 8 }}
              src={result.audio_url}
            />
            <Button
              variant="contained"
              startIcon={<DownloadIcon />}
              href={result.audio_url}
              download
              sx={{ mt: 1.5 }}
            >
              Download Cleaned Audio (.wav)
            </Button>
          </CardContent>
        </Card>
      )}

      {/* â”€â”€ Per-Speaker Diarization Audio â”€â”€ */}
      {(hasSpeakerAudio || hasDiarization) && (
        <Card elevation={3} sx={{ mb: 3, borderLeft: '5px solid', borderColor: 'secondary.main' }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <PeopleIcon sx={{ color: 'secondary.main', mr: 1 }} />
              <Typography variant="h6" fontWeight={600}>Speaker Diarization</Typography>
              <Chip
                label={`${Object.keys(speakerIndexMap).length} Speaker${Object.keys(speakerIndexMap).length !== 1 ? 's' : ''}`}
                size="small"
                color="secondary"
                sx={{ ml: 1.5 }}
              />
            </Box>

            <Stack spacing={2}>
              {Object.entries(speakerIndexMap).map(([rawId, idx]) => {
                const color = SPEAKER_COLORS[idx % SPEAKER_COLORS.length]
                const label = speakerLabel(rawId, speakerIndexMap)
                const audioUrl = speakerAudio[rawId]
                const segs = segsBySpk[rawId] || []

                return (
                  <Box
                    key={rawId}
                    sx={{
                      p: 2,
                      borderRadius: 2,
                      bgcolor: color.bg,
                      border: `1px solid ${color.border}44`,
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1, gap: 1.5 }}>
                      <Avatar sx={{ bgcolor: color.avatar, width: 36, height: 36, fontSize: '0.8rem' }}>
                        {label.slice(0, 2).toUpperCase()}
                      </Avatar>
                      <Typography fontWeight={700} sx={{ color: color.label }}>{label}</Typography>
                      <Chip
                        label={`${segs.length} segment${segs.length !== 1 ? 's' : ''}`}
                        size="small"
                        sx={{ bgcolor: `${color.border}22`, color: color.label }}
                      />
                      <Typography variant="caption" color="text.secondary">
                        {formatDuration(segs.reduce((acc, s) => acc + (s.end - s.start), 0))} total
                      </Typography>
                    </Box>

                    {/* Speaker-only audio player */}
                    {audioUrl ? (
                      <audio controls style={{ width: '100%', borderRadius: 6, marginBottom: 8 }} src={audioUrl} />
                    ) : (
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                        (speaker audio not available yet â€” available after diarization)
                      </Typography>
                    )}

                    {/* Timestamp list for this speaker */}
                    {segs.length > 0 && (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.8 }}>
                        {segs.map((s, i) => (
                          <Chip
                            key={i}
                            icon={<AccessTimeIcon style={{ fontSize: 12 }} />}
                            label={`${formatTime(s.start)} â€“ ${formatTime(s.end)}`}
                            size="small"
                            onClick={() => seekTo(s.start)}
                            sx={{
                              cursor: 'pointer',
                              bgcolor: 'white',
                              border: `1px solid ${color.border}44`,
                              fontSize: '0.7rem',
                              '&:hover': { bgcolor: color.bg, boxShadow: 1 },
                            }}
                          />
                        ))}
                      </Box>
                    )}
                  </Box>
                )
              })}
            </Stack>
          </CardContent>
        </Card>
      )}

      {/* â”€â”€ Transcript â”€â”€ */}
      {(result.transcript || hasSegments) && (
        <Card elevation={3} sx={{ mb: 3, borderLeft: '5px solid', borderColor: 'info.main' }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <RecordVoiceOverIcon sx={{ color: 'info.main', mr: 1 }} />
              <Typography variant="h6" fontWeight={600}>Transcript</Typography>
              {hasDiarization ? (
                <Chip label="Speaker Diarization" size="small" color="success" sx={{ ml: 1.5 }} />
              ) : (
                <Chip label="No Diarization" size="small" color="default" sx={{ ml: 1.5 }} />
              )}
            </Box>

            {/* Segment bubbles */}
            {hasSegments ? (
              <Stack spacing={1.5} sx={{ mb: 2 }}>
                {result.transcript_segments.map((seg, idx) => {
                  const rawId = seg.speaker || null
                  const colorIdx = rawId != null
                    ? (speakerIndexMap[rawId] % SPEAKER_COLORS.length)
                    : idx % SPEAKER_COLORS.length
                  const color = SPEAKER_COLORS[colorIdx]
                  const label = rawId
                    ? speakerLabel(rawId, speakerIndexMap)
                    : `Speaker ${idx + 1}`

                  return (
                    <Box key={idx} sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5 }}>
                      <Tooltip title={label}>
                        <Avatar
                          sx={{
                            bgcolor: color.avatar,
                            width: 36, height: 36,
                            fontSize: '0.75rem',
                            flexShrink: 0,
                            mt: 0.5,
                          }}
                        >
                          {label.slice(0, 2).toUpperCase()}
                        </Avatar>
                      </Tooltip>

                      <Box
                        onClick={() => seekTo(seg.start)}
                        sx={{
                          flex: 1,
                          p: '10px 14px',
                          borderRadius: 2,
                          bgcolor: color.bg,
                          border: `1px solid ${color.border}33`,
                          cursor: 'pointer',
                          transition: 'box-shadow 0.15s',
                          '&:hover': { boxShadow: `0 2px 8px ${color.border}55` },
                        }}
                      >
                        <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5, gap: 1 }}>
                          <Typography variant="caption" fontWeight={700} sx={{ color: color.label }}>
                            {label}
                          </Typography>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.4 }}>
                            <AccessTimeIcon sx={{ fontSize: 11, color: 'text.disabled' }} />
                            <Typography variant="caption" color="text.disabled">
                              {formatTime(seg.start)} â€“ {formatTime(seg.end)}
                            </Typography>
                          </Box>
                        </Box>
                        <Typography variant="body2" sx={{ lineHeight: 1.6 }}>
                          {seg.text}
                        </Typography>
                      </Box>
                    </Box>
                  )
                })}
              </Stack>
            ) : (
              <Box
                sx={{
                  p: 2, bgcolor: 'grey.50', borderRadius: 1,
                  fontFamily: 'monospace', fontSize: '0.9rem',
                  whiteSpace: 'pre-wrap', maxHeight: 300, overflow: 'auto', mb: 2,
                }}
              >
                {result.transcript || 'No transcript available.'}
              </Box>
            )}

            {result.transcript_url && (
              <Button variant="outlined" startIcon={<DownloadIcon />} href={result.transcript_url} download>
                Download Transcript (.txt)
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {/* â”€â”€ Pipeline summary â”€â”€ */}
      <Box sx={{ p: 2, bgcolor: '#f1f8e9', border: '1px solid #c5e1a5', borderRadius: 1 }}>
        <Typography variant="body2" color="text.secondary">
          <strong>Pipeline applied:</strong>&nbsp;
          Pre-VAD Trim â†’ DeepFilterNet3 Enhancement â†’ Silent-Bed Transplant (20 ms fades)
          {hasDiarization && ' â†’ Speaker Diarization (Pyannote)'}
          {result.transcript && ' â†’ Whisper ASR'}
        </Typography>
      </Box>
    </Box>
  )
}
