import { Link } from 'react-router-dom';
import { Play, UploadCloud, FileAudio, CheckCircle2, ArrowRight, BookOpen, Brain, Languages, Target, MessageSquare, LineChart, Library, GraduationCap } from 'lucide-react';

export function Home() {
  return (
    <div className="flex flex-col min-h-screen">
      {/* Hero Section */}
      <section className="relative pt-32 pb-24 overflow-hidden">
        <div className="absolute top-[-200px] right-[-200px] w-[700px] h-[700px] bg-[radial-gradient(circle,rgba(26,92,143,0.15)_0%,transparent_70%)] pointer-events-none" />
        <div className="absolute bottom-[-100px] left-[-100px] w-[500px] h-[500px] bg-[radial-gradient(circle,rgba(14,138,110,0.08)_0%,transparent_70%)] pointer-events-none" />
        
        <div className="max-w-7xl mx-auto px-6 grid lg:grid-cols-2 gap-16 items-center">
          <div className="z-10">
            <h1 className="font-display text-5xl md:text-7xl leading-[1.1] tracking-tight mb-6">
              Your lecture.<br />
              <em className="text-accent2 not-italic">Transcribed, explained, quizzed.</em>
            </h1>
            
            <p className="text-lg text-muted mb-10 max-w-xl leading-relaxed">
              Upload your lecture recording → get a clean transcript, AI explanations in English or Urdu, and a personalized quiz — in minutes.
            </p>
            
            <div className="flex flex-col sm:flex-row items-center gap-4 mb-8">
              <Link
                to="/app/upload"
                className="w-full sm:w-auto flex items-center justify-center gap-2 bg-accent hover:bg-accent2 text-white px-8 py-4 rounded-xl font-bold transition-all shadow-sm hover:-translate-y-0.5"
              >
                <UploadCloud className="w-5 h-5" />
                Upload a Lecture
              </Link>
              <a
                href="#demo"
                className="w-full sm:w-auto flex items-center justify-center gap-2 bg-surface2 hover:bg-surface border border-border hover:border-border2 text-text px-8 py-4 rounded-xl font-medium transition-all"
              >
                See How It Works
              </a>
            </div>
            
            <div className="flex items-center gap-6 text-sm text-muted font-mono">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-teal" />
                <span>No signup required</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-teal" />
                <span>Urdu & Roman Urdu</span>
              </div>
            </div>
          </div>
          
          {/* Animated Mockup */}
          <div className="relative z-10 bg-surface border border-border rounded-2xl p-6 shadow-xl">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-red animate-pulse" />
                <span className="text-xs font-mono uppercase tracking-widest text-muted">Processing Lecture</span>
              </div>
            </div>
            
            <div className="space-y-4">
              <div className="bg-bg rounded-xl p-4 border border-border">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-surface2 flex items-center justify-center text-text">
                    <FileAudio className="w-5 h-5" />
                  </div>
                  <div className="flex-1">
                    <div className="h-2 bg-border rounded-full w-3/4 mb-2" />
                    <div className="h-2 bg-border rounded-full w-1/2" />
                  </div>
                </div>
              </div>
              
              <div className="bg-accent-light/50 rounded-xl p-4 border border-accent/20">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-bold text-accent">Teacher</span>
                  <span className="text-[10px] font-mono text-muted">14:32</span>
                </div>
                <p className="text-sm text-text/80">So, the key concept in gradient descent is the learning rate...</p>
              </div>
              
              <div className="bg-teal-light/50 rounded-xl p-4 border border-teal/20">
                <div className="flex items-center gap-2 mb-2">
                  <Brain className="w-4 h-4 text-teal" />
                  <span className="text-xs font-bold text-teal">AI Explanation (Urdu)</span>
                </div>
                <p className="text-sm text-text/80">Gradient descent mein learning rate aapke qadam (steps) ka size hai...</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Trust Strip */}
      <section className="border-y border-border bg-surface py-8">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-center gap-12">
          <span className="text-xs font-mono uppercase tracking-widest text-muted">Powered By</span>
          <div className="flex items-center gap-8 opacity-60 grayscale">
            <div className="font-bold text-lg">Whisper</div>
            <div className="font-bold text-lg">pyannote</div>
            <div className="font-bold text-lg">DeepFilterNet</div>
            <div className="font-bold text-lg">RAG</div>
          </div>
          <div className="hidden md:block w-px h-8 bg-border" />
          <div className="flex items-center gap-2 opacity-80">
            <GraduationCap className="w-5 h-5 text-accent" />
            <span className="font-bold text-sm">NUCES CFD</span>
          </div>
        </div>
      </section>

      {/* Problem Section */}
      <section className="py-24 bg-surface">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="font-display text-4xl md:text-5xl mb-4">Studying from recordings is <em className="text-red not-italic">broken.</em></h2>
          </div>
          
          <div className="grid md:grid-cols-3 gap-12">
            <div className="text-center">
              <div className="w-16 h-16 mx-auto bg-red-light rounded-2xl flex items-center justify-center mb-6">
                <FileAudio className="w-8 h-8 text-red" />
              </div>
              <h3 className="text-xl font-bold mb-3">Noisy recordings</h3>
              <p className="text-muted">AC hum, background chatter, and poor mics make it impossible to hear what the teacher actually said.</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 mx-auto bg-amber-light rounded-2xl flex items-center justify-center mb-6">
                <BookOpen className="w-8 h-8 text-amber" />
              </div>
              <h3 className="text-xl font-bold mb-3">Hours wasted re-watching</h3>
              <p className="text-muted">Spending 3 hours to take notes on a 1-hour lecture because you keep pausing and rewinding.</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 mx-auto bg-purple-light rounded-2xl flex items-center justify-center mb-6">
                <Target className="w-8 h-8 text-purple" />
              </div>
              <h3 className="text-xl font-bold mb-3">Illusion of competence</h3>
              <p className="text-muted">You think you understood the lecture, but you have no way to test yourself until the midterm.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Demo Section */}
      <section id="demo" className="py-24 border-t border-border">
        <div className="max-w-5xl mx-auto px-6">
          <div className="text-center mb-12">
            <h2 className="font-display text-4xl mb-4">Hear the difference. <em className="text-accent2 not-italic">See the result.</em></h2>
          </div>
          
          <div className="bg-surface border border-border rounded-2xl p-8 shadow-sm">
            <div className="grid md:grid-cols-2 gap-8 mb-8">
              {/* Before */}
              <div className="bg-bg rounded-xl p-4 border border-border">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-mono text-muted uppercase tracking-widest">Original Recording</span>
                </div>
                <div className="flex items-center gap-4">
                  <button className="w-10 h-10 rounded-full bg-surface2 flex items-center justify-center text-text hover:bg-surface transition-colors shrink-0">
                    <Play className="w-4 h-4 ml-0.5" />
                  </button>
                  <div className="flex-1 h-8 bg-surface2 rounded relative overflow-hidden">
                    <div className="absolute inset-0 flex items-center px-2 gap-[2px]">
                      {Array.from({length: 30}).map((_, i) => (
                        <div key={i} className="w-1 bg-muted/40 rounded-full" style={{ height: `${Math.max(20, Math.random() * 100)}%` }} />
                      ))}
                    </div>
                  </div>
                </div>
              </div>
              
              {/* After */}
              <div className="bg-teal-light/30 rounded-xl p-4 border border-teal/20">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-mono text-teal uppercase tracking-widest">After LECTRA-AI</span>
                </div>
                <div className="flex items-center gap-4">
                  <button className="w-10 h-10 rounded-full bg-teal flex items-center justify-center text-white hover:bg-teal/90 transition-colors shrink-0">
                    <Play className="w-4 h-4 ml-0.5" />
                  </button>
                  <div className="flex-1 h-8 bg-teal/10 rounded relative overflow-hidden">
                    <div className="absolute inset-0 flex items-center px-2 gap-[2px]">
                      {Array.from({length: 30}).map((_, i) => (
                        <div key={i} className="w-1 bg-teal/60 rounded-full" style={{ height: `${Math.max(10, Math.random() * 60)}%` }} />
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="bg-bg rounded-xl p-6 border border-border mb-8">
              <div className="flex items-center gap-2 mb-4">
                <span className="text-xs font-bold text-accent">Teacher</span>
                <span className="text-[10px] font-mono text-muted">00:12</span>
              </div>
              <p className="text-sm leading-relaxed mb-4">So, the key concept in gradient descent is the learning rate. If it's too high, you overshoot. Too low, and it takes forever to converge.</p>
              
              <div className="bg-surface2 p-4 rounded-lg border border-border">
                <div className="flex items-center gap-2 mb-2">
                  <Brain className="w-4 h-4 text-accent" />
                  <span className="text-xs font-bold text-accent">AI Explanation</span>
                </div>
                <p className="text-sm text-muted">Gradient descent is like walking down a mountain blindfolded. The learning rate is the size of your steps. Big steps = you might miss the bottom. Small steps = it takes too long.</p>
              </div>
            </div>
            
            <div className="text-center">
              <Link to="/app/upload" className="inline-flex items-center gap-2 bg-accent hover:bg-accent2 text-white px-6 py-3 rounded-lg font-bold transition-colors">
                Upload Your Own Lecture <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-24 bg-surface border-t border-border">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="font-display text-4xl md:text-5xl mb-4">How it <em className="text-accent2 not-italic">works</em></h2>
          </div>
          
          <div className="grid md:grid-cols-3 gap-12 relative">
            <div className="hidden md:block absolute top-12 left-[15%] right-[15%] h-px bg-border border-dashed border-t" />
            
            {[
              {
                step: "01",
                title: "Upload your lecture",
                desc: "Drop any audio or video file (MP3, MP4, WAV). No signup required to start.",
                icon: <UploadCloud className="w-6 h-6 text-accent" />
              },
              {
                step: "02",
                title: "LECTRA-AI processes it",
                desc: "We remove noise, transcribe speech, and generate AI explanations and quizzes.",
                icon: <Brain className="w-6 h-6 text-accent" />
              },
              {
                step: "03",
                title: "Ace your exam",
                desc: "Get a clean transcript, study notes, a practice quiz, and a personalized study plan.",
                icon: <Target className="w-6 h-6 text-accent" />
              }
            ].map((step, i) => (
              <div key={i} className="relative z-10 flex flex-col items-center text-center">
                <div className="w-24 h-24 rounded-full bg-surface border border-border flex items-center justify-center mb-6 shadow-sm relative">
                  <div className="absolute -top-2 -right-2 w-8 h-8 rounded-full bg-accent-light border border-accent/20 flex items-center justify-center text-xs font-mono text-accent">
                    {step.step}
                  </div>
                  {step.icon}
                </div>
                <h3 className="text-xl font-bold mb-3">{step.title}</h3>
                <p className="text-sm text-muted max-w-xs">{step.desc}</p>
              </div>
            ))}
          </div>
          
          <p className="text-center text-sm text-muted mt-12 font-mono">Processing takes 2–5 minutes for a 1-hour lecture.</p>
        </div>
      </section>

      {/* Modules */}
      <section className="py-24">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="font-display text-4xl md:text-5xl mb-4">Everything you need to <em className="text-accent2 not-italic">understand.</em></h2>
          </div>
          
          <div className="grid md:grid-cols-3 gap-6 mb-12">
            {[
              { icon: <FileAudio className="text-accent" />, title: "Noise Removal & Speaker ID", desc: "Crystal clear audio, separated by who is speaking." },
              { icon: <BookOpen className="text-teal" />, title: "Smart Transcription", desc: "Highly accurate, timestamped transcripts fine-tuned for academics." },
              { icon: <Brain className="text-purple" />, title: "AI Explanations", desc: "Complex topics explained at Beginner, Intermediate, or Advanced levels." },
              { icon: <Target className="text-amber" />, title: "Quiz Generation", desc: "Auto-generated MCQs and short answers to test your knowledge." },
              { icon: <LineChart className="text-red" />, title: "Weakness Detection", desc: "Analytics that show exactly which topics you need to review." },
              { icon: <Library className="text-accent2" />, title: "Smart Library", desc: "Search across all your lectures instantly." }
            ].map((mod, i) => (
              <div key={i} className="bg-surface border border-border rounded-xl p-6 hover:border-accent2 transition-colors">
                <div className="w-10 h-10 rounded-lg bg-bg flex items-center justify-center mb-4">
                  {mod.icon}
                </div>
                <h3 className="font-bold mb-2">{mod.title}</h3>
                <p className="text-sm text-muted mb-4">{mod.desc}</p>
                <Link to="/features" className="text-xs font-mono text-accent hover:underline">Learn more →</Link>
              </div>
            ))}
          </div>
          
          <div className="bg-surface2 rounded-xl p-6 border border-border">
            <h4 className="text-sm font-bold mb-4">Plus advanced features:</h4>
            <div className="flex flex-wrap gap-3">
              {["Ask Your Lecture Chatbot", "Concept Timeline", "Exam-Relevance Highlighting", "Personalized Study Plan", "Emphasis Detection"].map((feat, i) => (
                <span key={i} className="text-xs font-mono bg-surface border border-border px-3 py-1.5 rounded-full text-muted">{feat}</span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Multilingual */}
      <section className="py-24 bg-accent text-white">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid md:grid-cols-2 gap-16 items-center">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 border border-white/20 text-xs font-mono uppercase tracking-widest mb-6">
                <Languages className="w-4 h-4" /> Built for Pakistan
              </div>
              <h2 className="font-display text-4xl md:text-5xl mb-6">Understand any concept in <em className="text-teal-light not-italic">Urdu.</em></h2>
              <p className="text-lg text-white/80 mb-8">
                Not just translated — explained clearly in Urdu and Roman Urdu, so nothing gets lost in translation.
              </p>
              <p className="text-sm text-white/60">
                Transcription is in English; explanations available in English, Urdu, and Roman Urdu.
              </p>
            </div>
            
            <div className="bg-white text-text rounded-2xl p-6 shadow-2xl">
              <div className="flex gap-4 mb-6 border-b border-border pb-4">
                <button className="text-sm font-bold text-accent border-b-2 border-accent pb-1">English</button>
                <button className="text-sm font-medium text-muted hover:text-text">Urdu</button>
                <button className="text-sm font-medium text-muted hover:text-text">Roman Urdu</button>
              </div>
              <div className="space-y-4">
                <p className="text-sm"><strong>Concept:</strong> Backpropagation</p>
                <p className="text-sm text-muted">Backpropagation is the algorithm used to calculate the gradient of the loss function with respect to the weights in a neural network...</p>
                <div className="p-4 bg-teal-light/30 rounded-lg border border-teal/20 mt-4">
                  <p className="text-sm font-medium text-teal mb-2">Roman Urdu Explanation</p>
                  <p className="text-sm text-muted">Backpropagation ek tareeqa hai jisse neural network apni ghaltiyon (errors) se seekhta hai. Yeh dekhta hai ke output mein kitni ghalti hai aur phir peechay ki taraf ja kar weights ko adjust karta hai...</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-24 bg-surface border-t border-border text-center">
        <div className="max-w-3xl mx-auto px-6">
          <h2 className="font-display text-4xl md:text-5xl mb-6">Your next exam starts with one upload.</h2>
          <p className="text-lg text-muted mb-10">No signup required. Upload a lecture and get your first transcript free.</p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/app/upload"
              className="w-full sm:w-auto bg-accent hover:bg-accent2 text-white px-8 py-4 rounded-xl font-bold transition-all shadow-sm"
            >
              Upload Now
            </Link>
            <Link
              to="/app/dashboard"
              className="w-full sm:w-auto bg-surface2 hover:bg-surface border border-border text-text px-8 py-4 rounded-xl font-medium transition-all"
            >
              Create Free Account
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
