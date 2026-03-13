import React, { useState, MouseEvent } from 'react';
import { Mail, Lock, User, ArrowRight, BookOpen, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';

export function Signup() {
  const [rotation, setRotation] = useState({ x: 0, y: 0 });
  const [isHovered, setIsHovered] = useState(false);

  const handleMouseMove = (e: MouseEvent<HTMLDivElement>) => {
    if (!e.currentTarget) return;
    const rect = e.currentTarget.getBoundingClientRect();
    
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    
    // Subtle tilt for a more natural feel. Reduced further to 3 to match the visual feel of the shorter Login box.
    const rotateX = ((y - centerY) / centerY) * -3; 
    const rotateY = ((x - centerX) / centerX) * 3;
    
    setRotation({ x: rotateX, y: rotateY });
  };

  const handleMouseLeave = () => {
    setRotation({ x: 0, y: 0 });
    setIsHovered(false);
  };

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center relative overflow-hidden font-sans perspective-1000 py-12">
      {/* Animated 3D Background Elements */}
      <div className="absolute inset-0 z-0">
        <div className="absolute top-[20%] right-[20%] w-96 h-96 bg-accent/20 rounded-full mix-blend-screen filter blur-[100px] animate-pulse" />
        <div className="absolute bottom-[20%] left-[20%] w-[500px] h-[500px] bg-accent2/20 rounded-full mix-blend-screen filter blur-[120px] animate-pulse" style={{ animationDelay: '2s' }} />
        <div className="absolute top-[40%] left-[40%] w-72 h-72 bg-blue-500/20 rounded-full mix-blend-screen filter blur-[80px] animate-pulse" style={{ animationDelay: '4s' }} />
      </div>

      <div className="w-full max-w-6xl mx-auto px-6 grid md:grid-cols-2 gap-12 items-center z-10">
        {/* Left Side: 3D Interactive Card */}
        <div className="flex justify-center perspective-1000 order-2 md:order-1">
          <div
            onMouseMove={handleMouseMove}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={handleMouseLeave}
            className="w-full max-w-md relative transition-transform duration-200 ease-out preserve-3d"
            style={{
              transform: isHovered 
                ? `rotateX(${rotation.x}deg) rotateY(${rotation.y}deg) translateZ(30px)` 
                : 'rotateX(0deg) rotateY(0deg) translateZ(0px)',
              transformStyle: 'preserve-3d'
            }}
          >
            {/* Glossy Card */}
            <div className="bg-surface/60 backdrop-blur-xl border border-white/10 p-10 rounded-3xl shadow-[0_0_50px_rgba(0,0,0,0.3)] relative overflow-hidden">
              
              {/* Inner Glow */}
              <div className="absolute inset-0 bg-gradient-to-bl from-white/10 to-transparent opacity-50 pointer-events-none" />

              <div className="relative z-10" style={{ transform: 'translateZ(40px)' }}>
                <div className="mb-8 text-center">
                  <h2 className="text-3xl font-bold mb-2">Create Account</h2>
                  <p className="text-muted text-sm">Join Lectra-AI and transform how you learn</p>
                </div>

                <form className="space-y-6" onSubmit={(e) => e.preventDefault()}>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-muted ml-1">Full Name</label>
                    <div className="relative group">
                      <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-muted group-focus-within:text-accent transition-colors">
                        <User className="w-5 h-5" />
                      </div>
                      <input
                        type="text"
                        className="w-full bg-bg/50 border border-border rounded-xl py-3 pl-12 pr-4 text-text placeholder:text-muted/50 focus:border-accent focus:ring-1 focus:ring-accent outline-none transition-all"
                        placeholder="John Doe"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium text-muted ml-1">Email Address</label>
                    <div className="relative group">
                      <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-muted group-focus-within:text-accent transition-colors">
                        <Mail className="w-5 h-5" />
                      </div>
                      <input
                        type="email"
                        className="w-full bg-bg/50 border border-border rounded-xl py-3 pl-12 pr-4 text-text placeholder:text-muted/50 focus:border-accent focus:ring-1 focus:ring-accent outline-none transition-all"
                        placeholder="john@nuces.edu.pk"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium text-muted ml-1">Password</label>
                    <div className="relative group">
                      <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-muted group-focus-within:text-accent transition-colors">
                        <Lock className="w-5 h-5" />
                      </div>
                      <input
                        type="password"
                        className="w-full bg-bg/50 border border-border rounded-xl py-3 pl-12 pr-4 text-text placeholder:text-muted/50 focus:border-accent focus:ring-1 focus:ring-accent outline-none transition-all"
                        placeholder="••••••••"
                      />
                    </div>
                  </div>

                  <Link to="/app/dashboard">
                    <button className="w-full mt-8 bg-text hover:bg-white text-bg font-bold py-4 rounded-xl flex items-center justify-center gap-2 transition-all duration-300 hover:shadow-[0_0_30px_rgba(255,255,255,0.4)] group overflow-hidden relative">
                      <div className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-black/10 to-transparent -translate-x-full group-hover:animate-[shimmer_1.5s_infinite]" />
                      <span>Sign Up</span>
                      <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                    </button>
                  </Link>

                  <div className="mt-8 text-center text-sm text-muted">
                    Already have an account?{' '}
                    <Link to="/login" className="font-bold text-accent hover:text-accent2 transition-colors">
                      Sign in
                    </Link>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side: Marketing text */}
        <div className="hidden md:flex flex-col gap-6 animate-in slide-in-from-right-8 fade-in duration-1000 order-1 md:order-2">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-surface border border-white/10 w-fit backdrop-blur-md">
            <Sparkles className="w-4 h-4 text-accent2" />
            <span className="text-sm font-medium tracking-wide">Start Your Journey</span>
          </div>
          <h1 className="text-5xl lg:text-7xl font-display font-bold leading-tight drop-shadow-2xl">
            Never miss <br />
            a detail <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent to-accent2">
              again.
            </span>
          </h1>
          <p className="text-lg text-muted max-w-md leading-relaxed">
            Create your free account today and get full access to AI transcription, smart quizzes, and noise-free audio perfectly tailored to your lectures.
          </p>
        </div>
      </div>

      <style>{`
        .perspective-1000 { perspective: 1000px; }
        .preserve-3d { transform-style: preserve-3d; }
        @keyframes shimmer {
          100% { transform: translateX(100%); }
        }
      `}</style>
    </div>
  );
}
