import { Link, Outlet, useLocation } from 'react-router-dom';
import { Menu, X, Github, GraduationCap } from 'lucide-react';
import { useState, useEffect } from 'react';
import { AnimatePresence, motion } from 'motion/react';

export function Layout() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();

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
            ? 'bg-surface/80 backdrop-blur-md border-b border-border py-4 shadow-sm'
            : 'bg-transparent py-6'
        }`}
      >
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-white transition-transform group-hover:scale-105 shadow-sm">
              <GraduationCap className="w-4 h-4" />
            </div>
            <span className="font-bold text-xl tracking-tight text-primary">
              Lectra
            </span>
          </Link>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-8">
            <Link to="/features" className="text-sm font-medium text-muted hover:text-primary transition-colors duration-300">Features</Link>
            <a href="/#how-it-works" className="text-sm font-medium text-muted hover:text-primary transition-colors duration-300">How It Works</a>
            <Link to="/about" className="text-sm font-medium text-muted hover:text-primary transition-colors duration-300">About Us</Link>
          </nav>

          <div className="hidden md:flex items-center gap-4">
            <Link
              to="/login"
              className="text-sm font-medium text-muted hover:text-primary transition-colors duration-300 px-4 py-2"
            >
              Sign In
            </Link>
            <Link
              to="/app/upload"
              className="text-sm font-medium bg-primary hover:bg-primary-dark text-white px-5 py-2.5 rounded-full transition-all duration-300 shadow-sm hover:shadow-md transform hover:-translate-y-0.5"
            >
              Get Started
            </Link>
          </div>

          {/* Mobile Menu Toggle */}
          <button
            className="md:hidden p-2 text-muted hover:text-primary transition-colors"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {/* Mobile Nav */}
        {mobileMenuOpen && (
          <div className="md:hidden absolute top-full left-0 right-0 bg-surface border-b border-border p-6 flex flex-col gap-4 shadow-xl transition-all duration-300">
            <Link to="/features" className="text-lg font-medium hover:text-primary transition-colors" onClick={() => setMobileMenuOpen(false)}>Features</Link>
            <a href="/#how-it-works" className="text-lg font-medium hover:text-primary transition-colors" onClick={() => setMobileMenuOpen(false)}>How It Works</a>
            <Link to="/about" className="text-lg font-medium hover:text-primary transition-colors" onClick={() => setMobileMenuOpen(false)}>About Us</Link>
            <div className="h-px bg-border my-2" />
            <Link
              to="/login"
              className="text-center font-medium text-primary px-5 py-3 rounded-lg border border-border hover:bg-surface2 transition-colors"
              onClick={() => setMobileMenuOpen(false)}
            >
              Sign In
            </Link>
            <Link
              to="/app/upload"
              className="text-center font-medium bg-primary text-white px-5 py-3 rounded-lg hover:bg-primary-dark transition-colors shadow-sm"
              onClick={() => setMobileMenuOpen(false)}
            >
              Get Started
            </Link>
          </div>
        )}
      </header>

      {/* Main Content */}
      <main className="flex-1 pt-24">
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
            className="w-full h-full"
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
      </main>

      {/* Footer */}
      <footer className="bg-surface border-t border-border mt-24">
        <div className="max-w-7xl mx-auto px-6 py-16">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-12 mb-16">
            <div className="col-span-1 md:col-span-2">
              <Link to="/" className="flex items-center gap-2 mb-4">
                <div className="w-6 h-6 rounded bg-primary flex items-center justify-center text-white shadow-sm">
                  <GraduationCap className="w-3 h-3" />
                </div>
                <span className="font-bold text-lg tracking-tight text-primary">
                  Lectra
                </span>
              </Link>
              <p className="text-sm text-muted mb-6 max-w-xs">
                AI-powered lecture intelligence platform that transforms raw classroom recordings into personalized, interactive learning resources.
              </p>
              <p className="text-xs font-mono text-muted uppercase tracking-widest">
                NUCES Department of Artificial Intelligence
              </p>
            </div>
            
            <div>
              <h4 className="font-mono text-xs uppercase tracking-widest text-muted mb-6">Product</h4>
              <ul className="flex flex-col gap-3">
                <li><Link to="/app/upload" className="text-sm text-text hover:text-primary transition-colors">Upload</Link></li>
                <li><Link to="/app/library" className="text-sm text-text hover:text-primary transition-colors">Library</Link></li>
                <li><Link to="/app/quiz" className="text-sm text-text hover:text-primary transition-colors">Quiz</Link></li>
                <li><Link to="/app/analytics" className="text-sm text-text hover:text-primary transition-colors">Analytics</Link></li>
                <li><Link to="/app/chat" className="text-sm text-text hover:text-primary transition-colors">Chatbot</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="font-mono text-xs uppercase tracking-widest text-muted mb-6">Features</h4>
              <ul className="flex flex-col gap-3">
                <li><Link to="/features" className="text-sm text-text hover:text-primary transition-colors">All Modules</Link></li>
                <li><Link to="/features" className="text-sm text-text hover:text-primary transition-colors">Noise Removal</Link></li>
                <li><Link to="/features" className="text-sm text-text hover:text-primary transition-colors">Smart Transcripts</Link></li>
                <li><Link to="/features" className="text-sm text-text hover:text-primary transition-colors">AI Explanations</Link></li>
                <li><Link to="/features" className="text-sm text-text hover:text-primary transition-colors">Multilingual Support</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="font-mono text-xs uppercase tracking-widest text-muted mb-6">Company</h4>
              <ul className="flex flex-col gap-3">
                <li><Link to="/about" className="text-sm text-text hover:text-primary transition-colors">Team</Link></li>
                <li><Link to="/about" className="text-sm text-text hover:text-primary transition-colors">About Us</Link></li>
                <li><Link to="/privacy" className="text-sm text-text hover:text-primary transition-colors">Privacy</Link></li>
                <li><Link to="/terms" className="text-sm text-text hover:text-primary transition-colors">Terms</Link></li>
              </ul>
            </div>
          </div>
          
          <div className="flex flex-col md:flex-row items-center justify-between pt-8 border-t border-border">
            <p className="text-xs font-mono text-muted">© {new Date().getFullYear()} Lectra AI. Hassan Raza · M Hanzala Yaqoob · Muhammad Zohair Hassnain · NUCES CFD 2026</p>
            <div className="flex items-center gap-4 mt-4 md:mt-0">
              <a href="https://github.com/Hanzala-12/voice-cleaning-pipeline" target="_blank" rel="noopener noreferrer" className="text-muted hover:text-primary transition-colors">
                <Github className="w-4 h-4" />
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
