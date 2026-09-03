import { Link } from 'react-router-dom';
import { Play, UploadCloud, FileAudio, CheckCircle2, ArrowRight, BookOpen, Brain, Languages, Target, LineChart, Library, GraduationCap } from 'lucide-react';

export function Home() {
  return (
    <div className="flex flex-col min-h-screen">
      {/* Hero Section */}
      <section className="relative pt-28 pb-24">
        <div className="max-w-4xl mx-auto px-8 sm:px-10 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface text-sm font-medium text-muted mb-8">
            <span className="flex h-1.5 w-1.5 rounded-full bg-primary"></span>
            Lectra AI is now in public beta
          </div>

          <h1 className="font-serif text-5xl md:text-7xl font-semibold tracking-tight mb-8 text-text leading-[1.05]">
            Your lecture.<br />
            <span className="text-primary">Transcribed, explained,</span>{' '}
            <span className="text-accent">quizzed.</span>
          </h1>

          <p className="text-lg text-muted mb-10 max-w-2xl mx-auto leading-relaxed">
            Upload your lecture recording and get a clean transcript, AI explanations in English or Urdu, and a personalized quiz — in minutes.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mb-12">
            <Link
              to="/app/upload"
              className="w-full sm:w-auto flex items-center justify-center gap-2 bg-primary hover:bg-primary-dark text-white px-7 py-3.5 rounded-lg font-semibold transition-colors"
            >
              <UploadCloud className="w-4 h-4" />
              Upload a Lecture
            </Link>
            <a
              href="#how-it-works"
              className="w-full sm:w-auto flex items-center justify-center gap-2 border border-border hover:bg-surface2 text-text px-7 py-3.5 rounded-lg font-medium transition-colors"
            >
              See How It Works
            </a>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-muted">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-primary" />
              <span>No signup required</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-primary" />
              <span>Urdu &amp; Roman Urdu Support</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-primary" />
              <span>Free during beta</span>
            </div>
          </div>
        </div>
      </section>

      {/* Mockup Section */}
      <section className="py-12 px-8 sm:px-10">
        <div className="max-w-4xl mx-auto">
          <div className="bg-surface rounded-lg overflow-hidden">
            {/* Mockup Header */}
            <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
              <div className="flex gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-error/60" />
                <div className="w-2.5 h-2.5 rounded-full bg-warning/60" />
                <div className="w-2.5 h-2.5 rounded-full bg-primary/60" />
              </div>
              <div className="mx-auto label-caps text-muted flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                Processing Lecture
              </div>
            </div>

            {/* Mockup Content */}
            <div className="p-6 md:p-10 grid md:grid-cols-2 gap-6">
              <div className="bg-surface2 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-semibold text-text">Teacher</span>
                  <span className="text-[11px] text-muted">14:32</span>
                </div>
                <p className="text-sm text-muted leading-relaxed">So, the key concept in gradient descent is the learning rate. If it's too high, you overshoot. Too low, and it takes forever to converge.</p>
              </div>

              <div className="bg-primary-light rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Brain className="w-3.5 h-3.5 text-primary-dark" />
                  <span className="text-xs font-semibold text-primary-dark">AI Explanation (Urdu)</span>
                </div>
                <p className="text-sm text-text leading-relaxed">Gradient descent mein learning rate aapke qadam (steps) ka size hai. Agar step zyada bada hoga toh aap manzil miss kar denge, aur agar chota hoga toh bohot waqt lag jayega.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Trust Strip */}
      <section className="border-y border-border py-8">
        <div className="max-w-6xl mx-auto px-8 sm:px-10 flex flex-col md:flex-row items-center justify-center gap-10">
          <span className="label-caps text-muted">A NUCES CFD Project</span>
          <div className="flex items-center gap-8 text-sm text-muted font-medium">
            <div>AI Audio Processing</div>
            <div>Smart Diarization</div>
            <div>Noise Suppression</div>
          </div>
          <div className="hidden md:block w-px h-6 bg-border" />
          <div className="flex items-center gap-2 text-sm font-medium text-text">
            <GraduationCap className="w-4 h-4 text-primary" />
            <span>University Grade</span>
          </div>
        </div>
      </section>

      {/* Problem Section */}
      <section className="py-24">
        <div className="max-w-5xl mx-auto px-8 sm:px-10">
          <div className="text-center mb-16">
            <h2 className="font-serif text-4xl md:text-5xl font-semibold tracking-tight">Studying from recordings is <span className="text-accent">broken.</span></h2>
          </div>

          <div className="grid md:grid-cols-3 gap-12">
            <div className="text-center">
              <div className="w-14 h-14 mx-auto bg-error-light rounded-full flex items-center justify-center mb-6">
                <FileAudio className="w-6 h-6 text-error" />
              </div>
              <h3 className="font-serif text-xl font-semibold mb-3">Noisy recordings</h3>
              <p className="text-muted text-[15px] leading-relaxed">AC hum, background chatter, and poor mics make it impossible to hear what the teacher actually said.</p>
            </div>
            <div className="text-center">
              <div className="w-14 h-14 mx-auto bg-warning-light rounded-full flex items-center justify-center mb-6">
                <BookOpen className="w-6 h-6 text-warning" />
              </div>
              <h3 className="font-serif text-xl font-semibold mb-3">Hours wasted re-watching</h3>
              <p className="text-muted text-[15px] leading-relaxed">Spending 3 hours to take notes on a 1-hour lecture because you keep pausing and rewinding.</p>
            </div>
            <div className="text-center">
              <div className="w-14 h-14 mx-auto bg-primary-light rounded-full flex items-center justify-center mb-6">
                <Target className="w-6 h-6 text-primary" />
              </div>
              <h3 className="font-serif text-xl font-semibold mb-3">Illusion of competence</h3>
              <p className="text-muted text-[15px] leading-relaxed">You think you understood the lecture, but you have no way to test yourself until the midterm.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Demo Section */}
      <section id="demo" className="py-24 border-t border-border">
        <div className="max-w-4xl mx-auto px-8 sm:px-10">
          <div className="text-center mb-12">
            <h2 className="font-serif text-4xl font-semibold tracking-tight">Hear the difference. <span className="text-primary">See the result.</span></h2>
          </div>

          <div className="bg-surface rounded-lg p-8">
            <div className="grid md:grid-cols-2 gap-6 mb-8">
              {/* Before */}
              <div className="bg-surface2 rounded-lg p-4">
                <p className="label-caps text-muted mb-3">Original Recording</p>
                <div className="flex items-center gap-4">
                  <button className="w-9 h-9 rounded-full bg-surface flex items-center justify-center text-text shrink-0">
                    <Play className="w-3.5 h-3.5 ml-0.5" />
                  </button>
                  <div className="flex-1 h-7 rounded relative overflow-hidden">
                    <div className="absolute inset-0 flex items-center px-2 gap-[2px]">
                      {Array.from({length: 30}).map((_, i) => (
                        <div key={i} className="w-1 bg-muted/40 rounded-full" style={{ height: `${Math.max(20, ((i * 37) % 100))}%` }} />
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* After */}
              <div className="bg-primary-light rounded-lg p-4">
                <p className="label-caps text-primary-dark mb-3">After Lectra AI</p>
                <div className="flex items-center gap-4">
                  <button className="w-9 h-9 rounded-full bg-primary flex items-center justify-center text-white shrink-0">
                    <Play className="w-3.5 h-3.5 ml-0.5" />
                  </button>
                  <div className="flex-1 h-7 rounded relative overflow-hidden">
                    <div className="absolute inset-0 flex items-center px-2 gap-[2px]">
                      {Array.from({length: 30}).map((_, i) => (
                        <div key={i} className="w-1 bg-primary/50 rounded-full" style={{ height: `${Math.max(10, ((i * 23) % 60))}%` }} />
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-surface2 rounded-lg p-6 mb-8">
              <div className="flex items-center gap-2 mb-4">
                <span className="text-xs font-semibold text-text">Teacher</span>
                <span className="text-[11px] text-muted">00:12</span>
              </div>
              <p className="text-sm leading-relaxed mb-4 text-muted">So, the key concept in gradient descent is the learning rate. If it's too high, you overshoot. Too low, and it takes forever to converge.</p>

              <div className="bg-surface p-4 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Brain className="w-3.5 h-3.5 text-primary" />
                  <span className="text-xs font-semibold text-primary">AI Explanation</span>
                </div>
                <p className="text-sm text-muted leading-relaxed">Gradient descent is like walking down a mountain blindfolded. The learning rate is the size of your steps. Big steps = you might miss the bottom. Small steps = it takes too long.</p>
              </div>
            </div>

            <div className="text-center">
              <Link to="/app/upload" className="inline-flex items-center gap-2 bg-primary hover:bg-primary-dark text-white px-6 py-3 rounded-lg font-semibold transition-colors">
                Upload Your Own Lecture <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="py-24 border-t border-border">
        <div className="max-w-5xl mx-auto px-8 sm:px-10">
          <div className="text-center mb-16">
            <h2 className="font-serif text-4xl md:text-5xl font-semibold tracking-tight">How it <span className="text-primary">works</span></h2>
          </div>

          <div className="grid md:grid-cols-3 gap-12 relative">
            <div className="hidden md:block absolute top-11 left-[15%] right-[15%] h-px bg-border" />

            {[
              {
                step: '01',
                title: 'Upload your lecture',
                desc: 'Drop any audio or video file (MP3, MP4, WAV). No signup required to start.',
                icon: <UploadCloud className="w-5 h-5 text-primary" />,
              },
              {
                step: '02',
                title: 'Lectra AI processes it',
                desc: 'We remove noise, transcribe speech, and generate AI explanations and quizzes.',
                icon: <Brain className="w-5 h-5 text-primary" />,
              },
              {
                step: '03',
                title: 'Ace your exam',
                desc: 'Get a clean transcript, study notes, a practice quiz, and a personalized study plan.',
                icon: <Target className="w-5 h-5 text-primary" />,
              },
            ].map((step, i) => (
              <div key={i} className="relative z-10 flex flex-col items-center text-center">
                <div className="w-20 h-20 rounded-full bg-surface flex items-center justify-center mb-6 relative">
                  <div className="absolute -top-1.5 -right-1.5 w-7 h-7 rounded-full bg-primary-light flex items-center justify-center text-[11px] font-semibold text-primary-dark">
                    {step.step}
                  </div>
                  {step.icon}
                </div>
                <h3 className="font-serif text-xl font-semibold mb-3">{step.title}</h3>
                <p className="text-sm text-muted max-w-xs leading-relaxed">{step.desc}</p>
              </div>
            ))}
          </div>

          <p className="text-center text-sm text-muted mt-14">Processing takes 2–5 minutes for a 1-hour lecture.</p>
        </div>
      </section>

      {/* Modules */}
      <section className="py-24">
        <div className="max-w-6xl mx-auto px-8 sm:px-10">
          <div className="text-center mb-16">
            <h2 className="font-serif text-4xl md:text-5xl font-semibold tracking-tight">Everything you need to <span className="text-accent">understand.</span></h2>
          </div>

          <div className="grid md:grid-cols-3 gap-5 mb-10">
            {[
              { icon: <FileAudio className="w-5 h-5 text-primary" />, title: 'Noise Removal & Speaker ID', desc: 'Crystal clear audio, separated by who is speaking.' },
              { icon: <BookOpen className="w-5 h-5 text-primary" />, title: 'Smart Transcription', desc: 'Highly accurate, timestamped transcripts fine-tuned for academics.' },
              { icon: <Brain className="w-5 h-5 text-primary" />, title: 'AI Explanations', desc: 'Complex topics explained at Beginner, Intermediate, or Advanced levels.' },
              { icon: <Target className="w-5 h-5 text-primary" />, title: 'Quiz Generation', desc: 'Auto-generated MCQs and short answers to test your knowledge.' },
              { icon: <LineChart className="w-5 h-5 text-primary" />, title: 'Weakness Detection', desc: 'Analytics that show exactly which topics you need to review.' },
              { icon: <Library className="w-5 h-5 text-primary" />, title: 'Smart Library', desc: 'Search across all your lectures instantly.' },
            ].map((mod, i) => (
              <div key={i} className="bg-surface rounded-lg p-6">
                <div className="w-10 h-10 rounded-lg bg-primary-light flex items-center justify-center mb-4">
                  {mod.icon}
                </div>
                <h3 className="font-serif font-semibold mb-2">{mod.title}</h3>
                <p className="text-sm text-muted mb-4 leading-relaxed">{mod.desc}</p>
                <Link to="/features" className="text-xs font-semibold text-accent hover:underline">Learn more →</Link>
              </div>
            ))}
          </div>

          <div className="bg-surface rounded-lg p-6">
            <h4 className="text-sm font-semibold mb-4 text-text">Plus advanced features:</h4>
            <div className="flex flex-wrap gap-2">
              {['Ask Your Lecture Chatbot', 'Concept Timeline', 'Exam-Relevance Highlighting', 'Personalized Study Plan', 'Emphasis Detection'].map((feat, i) => (
                <span key={i} className="text-xs bg-surface2 px-3 py-1.5 rounded-full text-muted">{feat}</span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Multilingual */}
      <section className="py-24 bg-primary text-white">
        <div className="max-w-6xl mx-auto px-8 sm:px-10">
          <div className="grid md:grid-cols-2 gap-16 items-center">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 text-xs font-semibold uppercase tracking-wide mb-6">
                <Languages className="w-3.5 h-3.5" /> Built for Pakistan
              </div>
              <h2 className="font-serif text-4xl md:text-5xl font-semibold mb-6 leading-tight">Understand any concept in <span className="text-accent2">Urdu.</span></h2>
              <p className="text-lg text-white/80 mb-8 leading-relaxed">
                Not just translated — explained clearly in Urdu and Roman Urdu, so nothing gets lost in translation.
              </p>
              <p className="text-sm text-white/60">
                Transcription is in English; explanations available in English, Urdu, and Roman Urdu.
              </p>
            </div>

            <div className="bg-surface text-text rounded-lg p-6">
              <div className="flex gap-4 mb-6 border-b border-border pb-4">
                <button className="text-sm font-semibold text-primary border-b-2 border-primary pb-1">English</button>
                <button className="text-sm font-medium text-muted hover:text-text">Urdu</button>
                <button className="text-sm font-medium text-muted hover:text-text">Roman Urdu</button>
              </div>
              <div className="space-y-4">
                <p className="text-sm"><strong>Concept:</strong> Backpropagation</p>
                <p className="text-sm text-muted leading-relaxed">Backpropagation is the algorithm used to calculate the gradient of the loss function with respect to the weights in a neural network...</p>
                <div className="p-4 bg-primary-light rounded-lg mt-4">
                  <p className="text-sm font-medium text-primary-dark mb-2">Roman Urdu Explanation</p>
                  <p className="text-sm text-muted leading-relaxed">Backpropagation ek tareeqa hai jisse neural network apni ghaltiyon (errors) se seekhta hai. Yeh dekhta hai ke output mein kitni ghalti hai aur phir peechay ki taraf ja kar weights ko adjust karta hai...</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-24 border-t border-border text-center">
        <div className="max-w-2xl mx-auto px-8 sm:px-10">
          <h2 className="font-serif text-4xl md:text-5xl font-semibold tracking-tight mb-6">Your next exam starts with one upload.</h2>
          <p className="text-lg text-muted mb-10">No signup required. Upload a lecture and get your first transcript free.</p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              to="/app/upload"
              className="w-full sm:w-auto bg-primary hover:bg-primary-dark text-white px-8 py-3.5 rounded-lg font-semibold transition-colors"
            >
              Upload Now
            </Link>
            <Link
              to="/app/dashboard"
              className="w-full sm:w-auto border border-border hover:bg-surface2 text-text px-8 py-3.5 rounded-lg font-medium transition-colors"
            >
              Create Free Account
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
