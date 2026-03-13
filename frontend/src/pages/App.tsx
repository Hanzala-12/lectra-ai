import React, { useState, useRef } from 'react';
import { UploadCloud, Settings, FileAudio, Play, Download, CheckCircle2, AlertCircle, Loader2, ChevronDown, ChevronUp } from 'lucide-react';

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
  error?: string;
};

type TranscriptFormat = 'txt' | 'srt' | 'vtt' | 'json';

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').trim();

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

export function App() {
  const [state, setState] = useState<ProcessState>('idle');
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [result, setResult] = useState<ProcessResult | null>(null);
  const [whisperModel, setWhisperModel] = useState('base');
  const [enableDiarization, setEnableDiarization] = useState(true);
  const [transcriptFormat, setTranscriptFormat] = useState<TranscriptFormat>('txt');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      setFile(droppedFile);
      setResult(null);
      setErrorMessage('');
      setState('idle');
      setProgress(0);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setResult(null);
      setErrorMessage('');
      setState('idle');
      setProgress(0);
    }
  };

  const startProcessing = async () => {
    if (!file) return;

    setState('uploading');
    setProgress(5);
    setErrorMessage('');
    setResult(null);

    const progressTimer = window.setInterval(() => {
      setProgress((prev) => {
        if (prev >= 92) return prev;
        if (prev < 25) return prev + 8;
        if (prev < 60) return prev + 4;
        return prev + 2;
      });
    }, 400);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('whisper_model', whisperModel);
      formData.append('enable_diarization', String(enableDiarization));
      formData.append('transcript_format', transcriptFormat);

      setState('processing');

      const response = await fetch(buildUrl('/api/process'), {
        method: 'POST',
        body: formData,
      });

      const data = (await response.json()) as ProcessResult;
      if (!response.ok || !data.success) {
        throw new Error(data.error || `Request failed with status ${response.status}`);
      }

      setProgress(100);
      setResult(data);
      setState('done');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Processing failed';
      setErrorMessage(message);
      setState('error');
    } finally {
      window.clearInterval(progressTimer);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-6 py-12">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl mb-2">Upload Lecture</h1>
          <p className="text-sm text-muted">Upload a recording to get a transcript, AI explanations, and a practice quiz.</p>
        </div>
        
        <button 
          onClick={() => setSettingsOpen(!settingsOpen)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface border border-border text-sm font-medium hover:bg-surface2 transition-colors"
        >
          <Settings className="w-4 h-4" />
          Advanced Options
          {settingsOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {/* Settings Panel */}
      {settingsOpen && (
        <div className="mb-8 p-6 bg-surface border border-border rounded-xl shadow-lg animate-in slide-in-from-top-4 fade-in duration-200">
          <h3 className="font-bold mb-4 flex items-center gap-2">
            <Settings className="w-4 h-4 text-accent2" />
            Processing Settings
          </h3>
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium mb-2">Identify Speakers</label>
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="diarization"
                  className="w-4 h-4 accent-accent rounded"
                  checked={enableDiarization}
                  onChange={(e) => setEnableDiarization(e.target.checked)}
                />
                <label htmlFor="diarization" className="text-sm">Enable speaker diarization</label>
              </div>
              <p className="text-xs text-muted mt-2">Detects who spoke when and returns per-speaker segments/audio.</p>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Transcript Format</label>
              <select
                className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm focus:border-accent outline-none"
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
      )}

      {/* Main Area */}
      <div className="bg-surface border border-border rounded-2xl overflow-hidden shadow-2xl">
        
        {state === 'idle' && (
          <div 
            className={`p-12 text-center border-2 border-dashed m-6 rounded-xl transition-colors ${file ? 'border-accent bg-accent/5' : 'border-border hover:border-border2 bg-bg'}`}
            onDragOver={(e) => { e.preventDefault(); e.currentTarget.classList.add('border-accent', 'bg-accent/5'); }}
            onDragLeave={(e) => { e.currentTarget.classList.remove('border-accent', 'bg-accent/5'); }}
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
                <div className="w-16 h-16 rounded-full bg-surface2 flex items-center justify-center mx-auto mb-6">
                  <UploadCloud className="w-8 h-8 text-muted" />
                </div>
                <h3 className="text-xl font-bold mb-2">Drag & Drop your file here</h3>
                <p className="text-sm text-muted mb-6">or click to browse from your computer</p>
                <button 
                  onClick={() => fileInputRef.current?.click()}
                  className="bg-surface2 hover:bg-surface border border-border text-text px-6 py-2 rounded-lg text-sm font-medium transition-colors"
                >
                  Select File
                </button>
                <div className="mt-8 flex flex-wrap justify-center gap-2">
                  {['WAV', 'MP3', 'M4A', 'FLAC', 'MP4', 'MOV'].map(ext => (
                    <span key={ext} className="text-[10px] font-mono px-2 py-1 rounded bg-surface border border-border text-muted">{ext}</span>
                  ))}
                </div>
              </>
            ) : (
              <>
                <div className="w-16 h-16 rounded-full bg-accent/20 flex items-center justify-center mx-auto mb-6 border border-accent/30">
                  <FileAudio className="w-8 h-8 text-accent2" />
                </div>
                <h3 className="text-xl font-bold mb-2">{file.name}</h3>
                <p className="text-sm text-muted mb-8">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
                
                <div className="flex items-center justify-center gap-4">
                  <button 
                    onClick={() => setFile(null)}
                    className="bg-surface2 hover:bg-surface border border-border text-text px-6 py-3 rounded-xl text-sm font-medium transition-colors"
                  >
                    Cancel
                  </button>
                  <button 
                    onClick={startProcessing}
                    className="bg-accent hover:bg-accent/90 text-white px-8 py-3 rounded-xl text-sm font-bold transition-colors shadow-[0_0_20px_rgba(124,107,255,0.3)] flex items-center gap-2"
                  >
                    <Play className="w-4 h-4" /> Process File
                  </button>
                </div>
              </>
            )}
          </div>
        )}

        {(state === 'uploading' || state === 'processing') && (
          <div className="p-12 text-center">
            <div className="w-24 h-24 rounded-full bg-surface2 flex items-center justify-center mx-auto mb-8 relative">
              <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="48" fill="none" stroke="currentColor" strokeWidth="4" className="text-border" />
                <circle cx="50" cy="50" r="48" fill="none" stroke="currentColor" strokeWidth="4" className="text-accent transition-all duration-300" strokeDasharray={`${progress * 3.01} 301`} />
              </svg>
              <Loader2 className="w-8 h-8 text-accent2 animate-spin" />
            </div>
            
            <h3 className="text-xl font-bold mb-2">
              {state === 'uploading' ? 'Uploading...' : 'Processing Audio...'}
            </h3>
            <p className="text-sm text-muted mb-8">
                {progress < 30 ? 'Uploading file...' : 
                progress < 60 ? 'Cleaning background noise...' : 
                progress < 90 ? 'Running diarization/transcription...' : 
                'Finalizing output files...'}
            </p>
            
            <div className="max-w-md mx-auto bg-bg rounded-full h-2 overflow-hidden border border-border">
              <div className="h-full bg-accent transition-all duration-300" style={{ width: `${progress}%` }} />
            </div>
            <div className="mt-4 text-xs font-mono text-muted">{Math.round(progress)}% Complete</div>
          </div>
        )}

        {state === 'done' && (
          <div className="p-0">
            <div className="bg-teal/10 border-b border-teal/20 p-4 flex items-center justify-center gap-2 text-teal text-sm font-medium">
              <CheckCircle2 className="w-5 h-5" /> Processing complete! Results are ready.
            </div>
            
            <div className="grid md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-border">
              {/* Left: Audio Players */}
              <div className="p-8">
                <h3 className="font-bold mb-6">Audio Comparison</h3>
                
                <div className="space-y-6">
                  {/* Before */}
                  <div className="bg-bg rounded-xl p-4 border border-border">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs font-mono text-muted uppercase tracking-widest">Original</span>
                      {result?.original_audio_url && (
                        <a href={buildUrl(result.original_audio_url)} className="text-xs text-muted hover:text-text flex items-center gap-1" download>
                          <Download className="w-3 h-3" /> Download
                        </a>
                      )}
                    </div>
                    {result?.original_audio_url ? (
                      <audio controls className="w-full" src={buildUrl(result.original_audio_url)} />
                    ) : (
                      <p className="text-sm text-muted">Original audio unavailable.</p>
                    )}
                  </div>
                  
                  {/* After */}
                  <div className="bg-accent/5 rounded-xl p-4 border border-accent/20">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs font-mono text-accent2 uppercase tracking-widest">Cleaned</span>
                      {result?.audio_url && (
                        <a href={buildUrl(result.audio_url)} className="text-xs text-accent2 hover:text-white flex items-center gap-1" download>
                          <Download className="w-3 h-3" /> WAV
                        </a>
                      )}
                    </div>
                    {result?.audio_url ? (
                      <audio controls className="w-full" src={buildUrl(result.audio_url)} />
                    ) : (
                      <p className="text-sm text-muted">Cleaned audio unavailable.</p>
                    )}
                  </div>
                </div>

                <div className="mt-8 pt-8 border-t border-border">
                  <h3 className="font-bold mb-4">Speakers Detected</h3>
                  {(result?.speaker_audio && Object.keys(result.speaker_audio).length > 0) ? (
                    <div className="space-y-3">
                      {Object.entries(result.speaker_audio).map(([speaker, url], idx) => (
                        <div key={speaker} className="p-3 bg-surface2 rounded-lg border border-border">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-3">
                              <div className={`w-3 h-3 rounded-full ${idx % 2 === 0 ? 'bg-teal' : 'bg-amber'}`} />
                              <span className="text-sm font-medium">{speaker}</span>
                            </div>
                            <a href={buildUrl(url)} className="text-muted hover:text-text" download>
                              <Download className="w-4 h-4" />
                            </a>
                          </div>
                          <audio controls className="w-full" src={buildUrl(url)} />
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
                <div className="flex items-center justify-between mb-6">
                  <h3 className="font-bold">Transcript</h3>
                  <div className="flex gap-2">
                    {result?.transcript_url && (
                      <a href={buildUrl(result.transcript_url)} download className="px-2 py-1 text-[10px] font-mono rounded bg-surface2 border border-border text-muted hover:text-text">
                        DOWNLOAD
                      </a>
                    )}
                  </div>
                </div>
                
                <div className="flex-1 bg-bg rounded-xl border border-border p-4 overflow-y-auto max-h-[400px] space-y-4">
                  {(result?.transcript_segments && result.transcript_segments.length > 0) ? (
                    result.transcript_segments.map((seg, idx) => (
                      <div key={`${seg.start}-${idx}`}>
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`w-2 h-2 rounded-full ${idx % 2 === 0 ? 'bg-teal' : 'bg-amber'}`} />
                          <span className="text-xs font-bold">{seg.speaker || 'Speaker'}</span>
                          <span className="text-[10px] font-mono text-muted">
                            {formatTime(seg.start)} - {formatTime(seg.end)}
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
                    onClick={() => { setFile(null); setResult(null); setState('idle'); setProgress(0); setErrorMessage(''); }}
                    className="text-sm font-medium text-muted hover:text-text transition-colors"
                  >
                    Process Another File
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {state === 'error' && (
          <div className="p-8">
            <div className="bg-red-light border border-red/30 text-red p-4 rounded-xl flex items-start gap-3">
              <AlertCircle className="w-5 h-5 mt-0.5" />
              <div>
                <p className="font-semibold mb-1">Processing failed</p>
                <p className="text-sm">{errorMessage || 'Unknown error'}</p>
              </div>
            </div>
          </div>
        )}
      </div>
      
      <div className="mt-6 text-center">
        <p className="text-xs text-muted flex items-center justify-center gap-1">
          <AlertCircle className="w-3 h-3" /> Processed files are served from backend outputs.
        </p>
      </div>
    </div>
  );
}
