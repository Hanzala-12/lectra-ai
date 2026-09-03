import React, { useState, useRef, useEffect } from 'react';
import { UploadCloud, Settings, FileAudio, Play, Download, CheckCircle2, AlertCircle, Loader2, ChevronDown, ChevronUp, X, Sparkles, Wind, Users2, Mic2 } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { Link } from 'react-router-dom';
import { getToken } from '../lib/api';

type ProcessState = 'idle' | 'uploading' | 'processing' | 'done' | 'error';

type TranscriptSegment = {
  start: number;
  end: number;
  text: string;
  speaker?: string | null;
};

type ProcessResult = {
  success: boolean;
  original_audio_url?: string;
  audio_url?: string;
  transcript?: string;
  transcript_url?: string;
  transcript_segments?: TranscriptSegment[];
  duration_original?: number;
  duration_processed?: number;
  speech_segments?: number;
  diarization?: Array<{ start: number; end: number; speaker?: string }>;
  speaker_audio?: Record<string, string>;
  lecture_id?: string;
  title?: string;
  error?: string;
};

type TranscriptFormat = 'txt' | 'srt' | 'vtt' | 'json';

const API_BASE = ((import.meta as any).env?.VITE_API_BASE_URL || '').trim();

function buildUrl(path: string): string {
  if (!path) return path;
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  if (API_BASE) {
    return `${API_BASE.replace(/\/$/, '')}${path}`;
  }
  return path;
}

function formatDuration(seconds?: number): string {
  if (seconds == null) return 'N/A';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${String(secs).padStart(2, '0')}`;
}

// Real, measured per-stage cost of the pipeline (this session's performance
// investigation, clean/uncontended runs): media load + diarization ~43% of
// total time, DeepFilterNet3 + MetricGAN+ noise removal ~4%, transcription
// ~53%. Used to (a) drive the step checklist below in real proportion
// instead of guessed evenly-spaced steps, and (b) estimate a realistic wait
// time from the file's own duration (measured ratio: ~4.7x the audio's own
// length on this CPU-only setup) so "why is this taking so long" never has
// to be asked.
const STEPS = [
  { key: 'upload', label: 'Uploading recording', icon: UploadCloud, at: 4 },
  { key: 'diarize', label: 'Cleaning audio & finding speakers', icon: Users2, at: 8 },
  { key: 'denoise', label: 'Removing background noise', icon: Wind, at: 48 },
  { key: 'transcribe', label: 'Transcribing speech', icon: Mic2, at: 53 },
  { key: 'done', label: 'Wrapping up', icon: Sparkles, at: 98 },
] as const;
const PROCESSING_TO_REALTIME_RATIO = 4.7;

export function App() {
  const [state, setState] = useState<ProcessState>('idle');
  const [file, setFile] = useState<File | null>(null);
  const [audioSeconds, setAudioSeconds] = useState<number | null>(null);
  const [progress, setProgress] = useState(0);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [result, setResult] = useState<ProcessResult | null>(null);
  const [whisperModel, setWhisperModel] = useState('base');
  const [enableDiarization, setEnableDiarization] = useState(true);
  const [transcriptFormat, setTranscriptFormat] = useState<TranscriptFormat>('txt');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [toast, setToast] = useState<{ message: string; type: 'error' | 'success' } | null>(null);

  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  const inspectDuration = (f: File) => {
    setAudioSeconds(null);
    const el = document.createElement('audio');
    el.preload = 'metadata';
    el.onloadedmetadata = () => {
      if (Number.isFinite(el.duration)) setAudioSeconds(el.duration);
      URL.revokeObjectURL(el.src);
    };
    el.onerror = () => URL.revokeObjectURL(el.src);
    el.src = URL.createObjectURL(f);
  };

  const pickFile = (f: File) => {
    setFile(f);
    setResult(null);
    setErrorMessage('');
    setState('idle');
    setProgress(0);
    inspectDuration(f);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) pickFile(droppedFile);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) pickFile(selectedFile);
  };

  const estimatedMinutes = audioSeconds != null ? Math.max(1, Math.round((audioSeconds * PROCESSING_TO_REALTIME_RATIO) / 60)) : null;

  const currentStep = STEPS.reduce((acc, s) => (progress >= s.at ? s : acc), STEPS[0]);

  const startProcessing = async () => {
    if (!file) return;

    setState('uploading');
    setProgress(2);
    setErrorMessage('');
    setResult(null);

    // Paced against the estimated real duration (from the file's own audio
    // length) instead of a generic timer, so the bar's speed roughly tracks
    // reality for both a 2-minute clip and a 40-minute one.
    const estTotalMs = Math.max(20000, (audioSeconds || 120) * PROCESSING_TO_REALTIME_RATIO * 1000);
    const startedAt = Date.now();
    const progressTimer = window.setInterval(() => {
      const elapsed = Date.now() - startedAt;
      const pct = Math.min(96, (elapsed / estTotalMs) * 100);
      setProgress((prev) => Math.max(prev, pct));
    }, 500);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('whisper_model', whisperModel);
      formData.append('enable_diarization', String(enableDiarization));
      formData.append('transcript_format', transcriptFormat);

      setState('processing');

      const token = getToken();
      const response = await fetch(buildUrl('/api/process-lecture'), {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        body: formData,
      });

      const data = (await response.json()) as ProcessResult & { detail?: string };
      if (!response.ok || !data.success) {
        throw new Error(
          data.error || data.detail || `Request failed with status ${response.status}`,
        );
      }

      setProgress(100);
      setResult(data);
      setState('done');
      setToast({ message: 'Processing completed successfully!', type: 'success' });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Processing failed';
      setErrorMessage(message);
      setState('error');
      setToast({ message, type: 'error' });
    } finally {
      window.clearInterval(progressTimer);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-8 sm:px-10 py-10 md:pl-6 relative">
      {/* Toast Notification */}
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: -20, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.9 }}
            className={`fixed top-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-lg shadow-soft-lg ${
              toast.type === 'error' ? 'bg-error-light text-error' : 'bg-success-light text-success'
            }`}
          >
            {toast.type === 'error' ? <AlertCircle className="w-5 h-5" /> : <CheckCircle2 className="w-5 h-5" />}
            <span className="text-sm font-medium">{toast.message}</span>
            <button onClick={() => setToast(null)} className="ml-2 hover:opacity-70 transition-opacity">
              <X className="w-4 h-4" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="font-serif text-4xl font-semibold tracking-tight text-text mb-2">Upload lecture</h1>
          <p className="text-sm text-muted">Get a clean transcript, notes, and a practice quiz.</p>
        </div>

        <button
          onClick={() => setSettingsOpen(!settingsOpen)}
          className="hidden sm:flex items-center gap-2 px-4 py-2 rounded-lg border border-border text-sm font-medium hover:bg-surface2 transition-colors shrink-0"
        >
          <Settings className="w-4 h-4" />
          Advanced
          {settingsOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {/* Settings Panel */}
      <AnimatePresence>
        {settingsOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden mb-6"
          >
            <div className="p-6 bg-surface rounded-lg">
              <h3 className="font-serif font-semibold text-lg mb-4 flex items-center gap-2 text-text">
                <Settings className="w-4 h-4 text-primary" />
                Processing settings
              </h3>
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium mb-2 text-text">Identify speakers</label>
                  <div className="flex items-center gap-2.5">
                    <input
                      type="checkbox"
                      id="diarization"
                      className="w-4 h-4 accent-primary rounded"
                      checked={enableDiarization}
                      onChange={(e) => setEnableDiarization(e.target.checked)}
                    />
                    <label htmlFor="diarization" className="text-sm text-text">Enable speaker diarization</label>
                  </div>
                  <p className="text-xs text-muted mt-2">Detects who spoke when and returns per-speaker segments/audio.</p>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2 text-text">Transcript format</label>
                  <select
                    className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none"
                    value={transcriptFormat}
                    onChange={(e) => setTranscriptFormat(e.target.value as TranscriptFormat)}
                  >
                    <option value="txt">TXT</option>
                    <option value="srt">SRT</option>
                    <option value="vtt">VTT</option>
                    <option value="json">JSON</option>
                  </select>
                  <p className="text-xs text-muted mt-2">Format used for downloadable transcript output.</p>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Area */}
      <motion.div
        layout
        className="bg-surface rounded-lg overflow-hidden"
      >

        {state === 'idle' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className={`p-12 text-center border-2 border-dashed m-5 rounded-lg transition-colors ${file ? 'border-primary bg-primary-light/30' : 'border-border2 hover:border-primary/40'}`}
            onDragOver={(e) => { e.preventDefault(); e.currentTarget.classList.add('border-primary'); }}
            onDragLeave={(e) => { e.currentTarget.classList.remove('border-primary'); }}
            onDrop={handleDrop}
          >
            <input
              type="file"
              ref={fileInputRef}
              className="hidden"
              accept=".wav,.mp3,.m4a,.flac,.aac,.ogg,.mp4,.avi,.mkv,.mov,.webm"
              onChange={handleFileSelect}
            />

            {!file ? (
              <>
                <div className="w-14 h-14 rounded-full bg-primary-light flex items-center justify-center mx-auto mb-6">
                  <UploadCloud className="w-7 h-7 text-primary" />
                </div>
                <h3 className="font-serif text-xl font-semibold mb-2 text-text">Drag & drop your recording here</h3>
                <p className="text-sm text-muted mb-6">or click to browse from your computer</p>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="bg-primary hover:bg-primary-dark text-white px-6 py-2.5 rounded-lg text-sm font-semibold transition-colors"
                >
                  Select file
                </button>
                <div className="mt-8 flex flex-wrap justify-center gap-2">
                  {['WAV', 'MP3', 'M4A', 'FLAC', 'MP4', 'MOV'].map(ext => (
                    <span key={ext} className="text-[11px] font-medium px-2.5 py-1 rounded-full bg-surface2 text-muted">{ext}</span>
                  ))}
                </div>
              </>
            ) : (
              <motion.div initial={{ scale: 0.95 }} animate={{ scale: 1 }}>
                <div className="w-14 h-14 rounded-full bg-primary-light flex items-center justify-center mx-auto mb-6">
                  <FileAudio className="w-7 h-7 text-primary" />
                </div>
                <h3 className="font-serif text-xl font-semibold mb-1.5 text-text truncate max-w-md mx-auto">{file.name}</h3>
                <p className="text-sm text-muted mb-1">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
                <p className="text-xs text-muted mb-8">
                  {estimatedMinutes != null
                    ? `~${estimatedMinutes} min to process on this machine (no GPU) — grab a coffee, this runs in the background.`
                    : 'Reading duration…'}
                </p>

                <div className="flex items-center justify-center gap-3">
                  <button
                    onClick={() => setFile(null)}
                    className="bg-surface2 hover:bg-border text-text px-6 py-3 rounded-lg text-sm font-medium transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={startProcessing}
                    className="bg-primary hover:bg-primary-dark text-white px-8 py-3 rounded-lg text-sm font-semibold transition-colors flex items-center gap-2"
                  >
                    <Play className="w-4 h-4" /> Process file
                  </button>
                </div>
              </motion.div>
            )}
          </motion.div>
        )}

        {(state === 'uploading' || state === 'processing') && (
          <motion.div
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            className="p-10 sm:p-12"
          >
            <div className="max-w-sm mx-auto text-center mb-8">
              <div className="w-20 h-20 rounded-full bg-primary-light flex items-center justify-center mx-auto mb-6 relative">
                <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="46" fill="none" stroke="var(--color-surface2)" strokeWidth="5" />
                  <circle cx="50" cy="50" r="46" fill="none" stroke="var(--color-primary)" strokeWidth="5" strokeLinecap="round" strokeDasharray={`${progress * 2.89} 289`} className="transition-all duration-500" />
                </svg>
                <Loader2 className="w-7 h-7 text-primary animate-spin" />
              </div>
              <h3 className="font-serif text-lg font-semibold text-text mb-1">{currentStep.label}…</h3>
              <p className="text-sm text-muted">
                {estimatedMinutes != null ? `Estimated ~${estimatedMinutes} min total — ` : ''}{Math.round(progress)}% complete
              </p>
            </div>

            <div className="max-w-sm mx-auto space-y-1">
              {STEPS.filter((s) => s.key !== 'done').map((s) => {
                const Icon = s.icon;
                const done = progress > s.at + 4 || (progress >= 96 && s.key !== currentStep.key);
                const active = s.key === currentStep.key;
                return (
                  <div key={s.key} className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${active ? 'bg-primary-light' : ''}`}>
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${done ? 'bg-primary text-white' : active ? 'bg-primary text-white' : 'bg-surface2 text-muted'}`}>
                      {done ? <CheckCircle2 className="w-3.5 h-3.5" /> : <Icon className="w-3.5 h-3.5" />}
                    </div>
                    <span className={`text-sm ${active ? 'text-text font-medium' : done ? 'text-muted' : 'text-muted/60'}`}>{s.label}</span>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}

        {state === 'done' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-0"
          >
            <div className="bg-success-light p-4 flex items-center justify-center gap-2 text-success text-sm font-medium">
              <CheckCircle2 className="w-5 h-5" /> Processing complete! Results are ready.
            </div>

            {result?.lecture_id && (
              <div className="bg-primary-light/50 p-4 flex flex-col sm:flex-row items-center justify-between gap-3">
                <p className="text-sm text-text">
                  Your lecture is saved. Generate <span className="font-medium">notes, quizzes, a study schedule</span> or <span className="font-medium">chat</span> with it.
                </p>
                <Link to={`/app/lecture/${result.lecture_id}`}
                  className="shrink-0 inline-flex items-center gap-2 bg-primary hover:bg-primary-dark text-white px-5 py-2.5 rounded-lg font-semibold">
                  <Sparkles className="w-4 h-4" /> Open study tools
                </Link>
              </div>
            )}

            <div className="grid md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-border">
              {/* Left: Audio Players */}
              <div className="p-8">
                <h3 className="font-serif font-semibold text-lg mb-5 text-text">Audio comparison</h3>

                <div className="space-y-4">
                  {/* Before */}
                  <div className="bg-surface2 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2.5">
                      <span className="label-caps text-muted">Original</span>
                      {result?.original_audio_url && (
                        <a href={buildUrl(result.original_audio_url)} className="text-xs text-muted hover:text-text flex items-center gap-1" download>
                          <Download className="w-3 h-3" /> Download
                        </a>
                      )}
                    </div>
                    {result?.original_audio_url ? (
                      <audio controls className="w-full h-9" src={buildUrl(result.original_audio_url)} />
                    ) : (
                      <p className="text-sm text-muted">Original audio unavailable.</p>
                    )}
                  </div>

                  {/* After */}
                  <div className="bg-primary-light rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2.5">
                      <span className="label-caps text-primary-dark">Cleaned</span>
                      {result?.audio_url && (
                        <a href={buildUrl(result.audio_url)} className="text-xs text-primary-dark hover:opacity-70 flex items-center gap-1" download>
                          <Download className="w-3 h-3" /> WAV
                        </a>
                      )}
                    </div>
                    {result?.audio_url ? (
                      <audio controls className="w-full h-9" src={buildUrl(result.audio_url)} />
                    ) : (
                      <p className="text-sm text-muted">Cleaned audio unavailable.</p>
                    )}
                  </div>
                </div>

                <div className="mt-7 pt-7 border-t border-border">
                  <h3 className="font-serif font-semibold text-lg mb-4 text-text">Speakers detected</h3>
                  {(result?.speaker_audio && Object.keys(result.speaker_audio).length > 0) ? (
                    <div className="space-y-3">
                      {Object.entries(result.speaker_audio).map(([speaker, url]) => (
                        <div key={speaker} className="p-3.5 bg-surface2 rounded-lg">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2.5">
                              <Users2 className="w-4 h-4 text-primary" />
                              <span className="text-sm font-medium text-text">{speaker.replace('SPEAKER_', 'Speaker ')}</span>
                            </div>
                            <a href={buildUrl(url as string)} className="text-muted hover:text-text" download>
                              <Download className="w-4 h-4" />
                            </a>
                          </div>
                          <audio controls className="w-full h-9" src={buildUrl(url as string)} />
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted">No speaker tracks available.</p>
                  )}
                </div>
              </div>

              {/* Right: Transcript */}
              <div className="p-8 flex flex-col h-full">
                <div className="flex items-center justify-between mb-5">
                  <h3 className="font-serif font-semibold text-lg text-text">Transcript</h3>
                  {result?.transcript_url && (
                    <a href={buildUrl(result.transcript_url)} download className="px-3 py-1.5 text-xs font-medium rounded-full bg-surface2 text-muted hover:text-text">
                      Download
                    </a>
                  )}
                </div>

                <div className="flex-1 bg-surface2 rounded-lg p-4 overflow-y-auto max-h-[400px] space-y-4">
                  {(result?.transcript_segments && result.transcript_segments.length > 0) ? (
                    result.transcript_segments.map((seg, idx) => (
                      <div key={`${seg.start}-${idx}`}>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-semibold text-primary">{(seg.speaker || 'Speaker').replace('SPEAKER_', 'Speaker ')}</span>
                          <span className="text-[11px] text-muted tabular-nums">
                            {formatTime(seg.start)} – {formatTime(seg.end)}
                          </span>
                        </div>
                        <p className="text-sm text-muted leading-relaxed">{seg.text}</p>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-muted leading-relaxed">{result?.transcript || 'No transcript available (ASR may be disabled in backend config).'}</p>
                  )}
                </div>

                <div className="mt-4 text-xs text-muted">
                  Duration: {formatDuration(result?.duration_original)} → {formatDuration(result?.duration_processed)}
                  {' · '}
                  Segments: {result?.speech_segments ?? 0}
                </div>

                <div className="mt-6 pt-6 border-t border-border flex justify-center">
                  <button
                    onClick={() => { setFile(null); setResult(null); setState('idle'); setProgress(0); setErrorMessage(''); setAudioSeconds(null); }}
                    className="text-sm font-medium text-muted hover:text-text transition-colors"
                  >
                    Process another file
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {state === 'error' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="p-8"
          >
            <div className="bg-error-light text-error p-4 rounded-lg flex items-start gap-3">
              <AlertCircle className="w-5 h-5 mt-0.5 shrink-0" />
              <div>
                <p className="font-semibold mb-1">Processing failed</p>
                <p className="text-sm">{errorMessage || 'Unknown error'}</p>
              </div>
            </div>
            <div className="mt-5 flex justify-center">
              <button
                onClick={() => { setState('idle'); setErrorMessage(''); setProgress(0); }}
                className="text-sm font-medium text-primary hover:text-primary-dark"
              >
                Try again
              </button>
            </div>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
}
