import { Link, Outlet } from 'react-router-dom';
import { Menu, X, Github, GraduationCap } from 'lucide-react';
import { useState, useEffect } from 'react';

export function Layout() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="min-h-screen flex flex-col">
      {/* Navigation */}
      <header
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          isScrolled
            ? 'bg-bg/80 backdrop-blur-md border-b border-border py-4'
            : 'bg-transparent py-6'
        }`}
      >
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center border border-accent/20 group-hover:bg-accent/20 transition-colors">
              <GraduationCap className="w-4 h-4 text-accent2" />
            </div>
            <span className="font-display text-xl tracking-tight font-bold">
              LECTRA-AI
            </span>
          </Link>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-8">
            <Link to="/features" className="text-sm font-medium text-muted hover:text-accent transition-colors duration-300">Features</Link>
            <Link to="/app/dashboard" className="text-sm font-medium text-muted hover:text-accent transition-colors duration-300">How It Works</Link>
            <Link to="/about" className="text-sm font-medium text-muted hover:text-accent transition-colors duration-300">About Us</Link>
          </nav>

          <div className="hidden md:flex items-center gap-4">
            <Link
              to="/app/dashboard"
              className="text-sm font-medium text-muted hover:text-accent transition-colors duration-300 px-4 py-2"
            >
              Sign In
            </Link>
            <Link
              to="/app/upload"
              className="text-sm font-bold bg-accent hover:bg-accent2 text-white px-5 py-2.5 rounded-lg transition-all duration-300 shadow-sm hover:shadow-md transform hover:-translate-y-0.5"
            >
              Try Free
            </Link>
          </div>

          {/* Mobile Menu Toggle */}
          <button
            className="md:hidden p-2 text-muted hover:text-text"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {/* Mobile Nav */}
        {mobileMenuOpen && (
          <div className="md:hidden absolute top-full left-0 right-0 bg-surface border-b border-border p-6 flex flex-col gap-4 shadow-xl transition-all duration-300">
            <Link to="/features" className="text-lg font-medium hover:text-accent transition-colors" onClick={() => setMobileMenuOpen(false)}>Features</Link>
            <Link to="/app/dashboard" className="text-lg font-medium hover:text-accent transition-colors" onClick={() => setMobileMenuOpen(false)}>How It Works</Link>
            <Link to="/about" className="text-lg font-medium hover:text-accent transition-colors" onClick={() => setMobileMenuOpen(false)}>About Us</Link>
            <div className="h-px bg-border my-2" />
            <Link
              to="/app/dashboard"
              className="text-center font-medium text-text px-5 py-3 rounded-lg border border-border"
              onClick={() => setMobileMenuOpen(false)}
            >
              Sign In
            </Link>
            <Link
              to="/app/upload"
              className="text-center font-bold bg-accent text-white px-5 py-3 rounded-lg"
              onClick={() => setMobileMenuOpen(false)}
            >
              Try Free
            </Link>
          </div>
        )}
      </header>

      {/* Main Content */}
      <main className="flex-1 pt-24">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="bg-text text-white/40 mt-24">
        <div className="max-w-7xl mx-auto px-6 py-16">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-12 mb-16">
            <div className="col-span-1 md:col-span-2">
              <Link to="/" className="flex items-center gap-2 mb-4">
                <div className="w-6 h-6 rounded bg-white/10 flex items-center justify-center border border-white/20">
                  <GraduationCap className="w-3 h-3 text-white" />
                </div>
                <span className="font-display text-lg tracking-tight font-bold text-white">
                  LECTRA-AI
                </span>
              </Link>
              <p className="text-sm text-white/60 mb-6 max-w-xs">
                AI-powered lecture intelligence platform that transforms raw classroom recordings into personalized, interactive learning resources.
              </p>
              <p className="text-xs font-mono text-white/40 uppercase tracking-widest">
                NUCES Department of Artificial Intelligence
              </p>
            </div>
            
            <div>
              <h4 className="font-mono text-xs uppercase tracking-widest text-white/60 mb-6">Product</h4>
              <ul className="flex flex-col gap-3">
                <li><Link to="/app/upload" className="text-sm hover:text-white transition-colors">Upload</Link></li>
                <li><Link to="/app/library" className="text-sm hover:text-white transition-colors">Library</Link></li>
                <li><Link to="/app/quiz" className="text-sm hover:text-white transition-colors">Quiz</Link></li>
                <li><Link to="/app/analytics" className="text-sm hover:text-white transition-colors">Analytics</Link></li>
                <li><Link to="/app/chat" className="text-sm hover:text-white transition-colors">Chatbot</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="font-mono text-xs uppercase tracking-widest text-white/60 mb-6">Features</h4>
              <ul className="flex flex-col gap-3">
                <li><Link to="/features" className="text-sm hover:text-white transition-colors">All Modules</Link></li>
                <li><Link to="/features" className="text-sm hover:text-white transition-colors">Noise Removal</Link></li>
                <li><Link to="/features" className="text-sm hover:text-white transition-colors">Smart Transcripts</Link></li>
                <li><Link to="/features" className="text-sm hover:text-white transition-colors">AI Explanations</Link></li>
                <li><Link to="/features" className="text-sm hover:text-white transition-colors">Multilingual Support</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="font-mono text-xs uppercase tracking-widest text-white/60 mb-6">Company</h4>
              <ul className="flex flex-col gap-3">
                <li><Link to="/about" className="text-sm hover:text-white transition-colors">Team</Link></li>
                <li><Link to="/about" className="text-sm hover:text-white transition-colors">About Us</Link></li>
                <li><Link to="/privacy" className="text-sm hover:text-white transition-colors">Privacy</Link></li>
                <li><Link to="/terms" className="text-sm hover:text-white transition-colors">Terms</Link></li>
              </ul>
            </div>
          </div>
          
          <div className="flex flex-col md:flex-row items-center justify-between pt-8 border-t border-white/10">
            <p className="text-xs font-mono">© {new Date().getFullYear()} LECTRA-AI. Hassan Raza · M Hanzala Yaqoob · Muhammad Zohair Hassnain · NUCES CFD 2026</p>
            <div className="flex items-center gap-4 mt-4 md:mt-0">
              <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">
                <Github className="w-4 h-4" />
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
