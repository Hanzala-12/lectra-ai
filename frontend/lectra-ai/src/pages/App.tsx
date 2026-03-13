import React, { useState, useRef } from 'react';
import { UploadCloud, Settings, FileAudio, Play, Pause, Download, CheckCircle2, AlertCircle, Loader2, ChevronDown, ChevronUp } from 'lucide-react';

type ProcessState = 'idle' | 'uploading' | 'processing' | 'done' | 'error';

export function App() {
  const [state, setState] = useState<ProcessState>('idle');
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      setFile(droppedFile);
      setState('idle');
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setState('idle');
    }
  };

  const startProcessing = () => {
    if (!file) return;
    setState('uploading');
    
    // Mock processing pipeline
    let p = 0;
    const interval = setInterval(() => {
      p += Math.random() * 15;
      if (p >= 100) {
        clearInterval(interval);
        setProgress(100);
        setState('done');
      } else {
        setProgress(p);
        if (p > 20 && state === 'uploading') setState('processing');
      }
    }, 500);
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
          <div className="grid md:grid-cols-3 gap-6">
            <div>
              <label className="block text-sm font-medium mb-2">Whisper Model</label>
              <select className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm focus:border-accent outline-none">
                <option value="base">Base (Fast, Good accuracy)</option>
                <option value="small">Small (Slower, Better accuracy)</option>
                <option value="medium">Medium (Slowest, Best accuracy)</option>
              </select>
              <p className="text-xs text-muted mt-2">Larger models take longer but produce fewer errors.</p>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">AI Explanations</label>
              <div className="flex items-center gap-3">
                <input type="checkbox" id="explain" className="w-4 h-4 accent-accent rounded" defaultChecked />
                <label htmlFor="explain" className="text-sm">Generate explanations</label>
              </div>
              <p className="text-xs text-muted mt-2">Creates summaries and concept breakdowns in English and Urdu.</p>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Practice Quiz</label>
              <div className="flex items-center gap-3">
                <input type="checkbox" id="quiz" className="w-4 h-4 accent-accent rounded" defaultChecked />
                <label htmlFor="quiz" className="text-sm">Generate quiz</label>
              </div>
              <p className="text-xs text-muted mt-2">Creates MCQs based on the lecture content.</p>
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
              {progress < 30 ? 'Loading audio and transcribing...' : 
               progress < 60 ? 'Generating AI explanations...' : 
               progress < 90 ? 'Creating practice quiz...' : 
               'Assembling final study materials...'}
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
                      <a href="#" className="text-xs text-muted hover:text-text flex items-center gap-1"><Download className="w-3 h-3" /> WAV</a>
                    </div>
                    <div className="flex items-center gap-4">
                      <button className="w-10 h-10 rounded-full bg-surface2 flex items-center justify-center text-text hover:bg-surface transition-colors shrink-0">
                        <Play className="w-4 h-4 ml-0.5" />
                      </button>
                      <div className="flex-1 h-10 bg-surface2 rounded relative overflow-hidden">
                        {/* Mock Waveform */}
                        <div className="absolute inset-0 flex items-center px-2 gap-[2px]">
                          {Array.from({length: 30}).map((_, i) => (
                            <div key={i} className="w-1.5 bg-muted/40 rounded-full" style={{ height: `${Math.max(20, Math.random() * 100)}%` }} />
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {/* After */}
                  <div className="bg-accent/5 rounded-xl p-4 border border-accent/20">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs font-mono text-accent2 uppercase tracking-widest">Cleaned</span>
                      <a href="#" className="text-xs text-accent2 hover:text-white flex items-center gap-1"><Download className="w-3 h-3" /> WAV</a>
                    </div>
                    <div className="flex items-center gap-4">
                      <button className="w-10 h-10 rounded-full bg-accent flex items-center justify-center text-white hover:bg-accent/90 transition-colors shadow-[0_0_15px_rgba(124,107,255,0.4)] shrink-0">
                        <Play className="w-4 h-4 ml-0.5" />
                      </button>
                      <div className="flex-1 h-10 bg-accent/10 rounded relative overflow-hidden">
                        {/* Mock Waveform */}
                        <div className="absolute inset-0 flex items-center px-2 gap-[2px]">
                          {Array.from({length: 30}).map((_, i) => (
                            <div key={i} className="w-1.5 bg-accent/60 rounded-full" style={{ height: `${Math.max(10, Math.random() * 60)}%` }} />
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-8 pt-8 border-t border-border">
                  <h3 className="font-bold mb-4">Speakers Detected</h3>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 bg-surface2 rounded-lg border border-border">
                      <div className="flex items-center gap-3">
                        <div className="w-3 h-3 rounded-full bg-teal" />
                        <span className="text-sm font-medium">Speaker 1</span>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="text-xs font-mono text-muted">0:45</span>
                        <button className="text-muted hover:text-text"><Download className="w-4 h-4" /></button>
                      </div>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-surface2 rounded-lg border border-border">
                      <div className="flex items-center gap-3">
                        <div className="w-3 h-3 rounded-full bg-amber" />
                        <span className="text-sm font-medium">Speaker 2</span>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="text-xs font-mono text-muted">1:12</span>
                        <button className="text-muted hover:text-text"><Download className="w-4 h-4" /></button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right: Transcript */}
              <div className="p-8 flex flex-col h-full">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="font-bold">Transcript</h3>
                  <div className="flex gap-2">
                    <button className="px-2 py-1 text-[10px] font-mono rounded bg-surface2 border border-border text-muted hover:text-text">TXT</button>
                    <button className="px-2 py-1 text-[10px] font-mono rounded bg-surface2 border border-border text-muted hover:text-text">SRT</button>
                    <button className="px-2 py-1 text-[10px] font-mono rounded bg-surface2 border border-border text-muted hover:text-text">VTT</button>
                  </div>
                </div>
                
                <div className="flex-1 bg-bg rounded-xl border border-border p-4 overflow-y-auto max-h-[400px] space-y-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="w-2 h-2 rounded-full bg-teal" />
                      <span className="text-xs font-bold">Speaker 1</span>
                      <span className="text-[10px] font-mono text-muted cursor-pointer hover:text-accent2">00:00:00</span>
                    </div>
                    <p className="text-sm text-muted leading-relaxed">So, I was thinking about the new architecture for the backend. We need to make sure it scales properly.</p>
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="w-2 h-2 rounded-full bg-amber" />
                      <span className="text-xs font-bold">Speaker 2</span>
                      <span className="text-[10px] font-mono text-muted cursor-pointer hover:text-accent2">00:00:08</span>
                    </div>
                    <p className="text-sm text-muted leading-relaxed">Yeah, absolutely. If we use a message queue, we can decouple the processing workers from the API layer. That should handle the load spikes.</p>
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="w-2 h-2 rounded-full bg-teal" />
                      <span className="text-xs font-bold">Speaker 1</span>
                      <span className="text-[10px] font-mono text-muted cursor-pointer hover:text-accent2">00:00:15</span>
                    </div>
                    <p className="text-sm text-muted leading-relaxed">Exactly. I'll draft a proposal for that this afternoon.</p>
                  </div>
                </div>
                
                <div className="mt-6 pt-6 border-t border-border flex justify-center">
                  <button 
                    onClick={() => { setFile(null); setState('idle'); }}
                    className="text-sm font-medium text-muted hover:text-text transition-colors"
                  >
                    Process Another File
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
      
      <div className="mt-6 text-center">
        <p className="text-xs text-muted flex items-center justify-center gap-1">
          <AlertCircle className="w-3 h-3" /> Files are deleted automatically after 1 hour.
        </p>
      </div>
    </div>
  );
}
