import React, { useState, MouseEvent } from 'react';
import {
  Lock, User, AtSign, Mail, ArrowRight, Sparkles, Loader2, AlertCircle,
  Eye, EyeOff, Check, X, ShieldCheck,
} from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import {
  validateUsername, validateName, validateEmail, validatePassword, validateConfirm,
  passwordChecks, passwordStrength,
} from '../lib/validation';

const INPUT_BASE =
  'w-full bg-bg/50 border rounded-xl py-3 pl-12 text-text placeholder:text-muted/50 focus:ring-1 outline-none transition-all shadow-sm';
const inputClass = (hasError: boolean, extraRight = 'pr-4') =>
  `${INPUT_BASE} ${extraRight} ${
    hasError ? 'border-error focus:border-error focus:ring-error' : 'border-border focus:border-primary focus:ring-primary'
  }`;

const STRENGTH_COLORS = ['bg-border', 'bg-error', 'bg-amber-500', 'bg-lime-500', 'bg-emerald-500'];

type FieldName = 'name' | 'email' | 'username' | 'password' | 'confirm';

function FieldShell({
  label, optional, icon, error, children,
}: {
  label: string;
  optional?: boolean;
  icon: React.ReactNode;
  error: string | null;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-muted ml-1">
        {label} {optional && <span className="text-muted/60 font-normal">(optional)</span>}
      </label>
      <div className="relative group">
        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-muted group-focus-within:text-primary transition-colors">
          {icon}
        </div>
        {children}
      </div>
      {error && (
        <p className="text-xs text-error ml-1 flex items-center gap-1" role="alert">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" /> {error}
        </p>
      )}
    </div>
  );
}

export function Signup() {
  const [rotation, setRotation] = useState({ x: 0, y: 0 });
  const [isHovered, setIsHovered] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [touched, setTouched] = useState<Partial<Record<FieldName, boolean>>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const errors: Record<FieldName, string | null> = {
    name: validateName(name),
    email: validateEmail(email),
    username: validateUsername(username),
    password: validatePassword(password, username),
    confirm: validateConfirm(password, confirm),
  };
  const isValid = Object.values(errors).every((e) => e === null);
  // Show a field's error once the user has left it (or tried to submit).
  const shown = (f: FieldName) => (touched[f] ? errors[f] : null);
  const touch = (f: FieldName) => setTouched((t) => ({ ...t, [f]: true }));

  const checks = passwordChecks(password, username);
  const strength = passwordStrength(password, username);

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setTouched({ name: true, email: true, username: true, password: true, confirm: true });
    if (!isValid) {
      setError('Please fix the highlighted fields.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await api.signup(username.trim(), password, confirm, name.trim() || undefined, email.trim() || undefined);
      navigate('/app/dashboard', { replace: true });
    } catch (err: any) {
      setError(err.message || 'Sign up failed');
    } finally {
      setLoading(false);
    }
  };

  const eyeButton = (visible: boolean, toggle: () => void, label: string) => (
    <button
      type="button"
      onClick={toggle}
      aria-label={label}
      className="absolute inset-y-0 right-0 pr-4 flex items-center text-muted hover:text-primary transition-colors"
      tabIndex={-1}
    >
      {visible ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
    </button>
  );

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center relative overflow-hidden font-sans perspective-1000 py-12">
      {/* Animated 3D Background Elements */}
      <div className="absolute inset-0 z-0">
        <div className="absolute top-[20%] right-[20%] w-96 h-96 bg-primary/20 rounded-full mix-blend-screen filter blur-[100px] animate-pulse" />
        <div className="absolute bottom-[20%] left-[20%] w-[500px] h-[500px] bg-accent/20 rounded-full mix-blend-screen filter blur-[120px] animate-pulse" style={{ animationDelay: '2s' }} />
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
            <div className="bg-surface/60 backdrop-blur-xl border border-white/10 p-10 rounded-3xl shadow-xl relative overflow-hidden">

              {/* Inner Glow */}
              <div className="absolute inset-0 bg-gradient-to-bl from-white/10 to-transparent opacity-50 pointer-events-none" />

              <div className="relative z-10" style={{ transform: 'translateZ(40px)' }}>
                <div className="mb-8 text-center">
                  <h2 className="text-3xl font-bold tracking-tight mb-2">Create Account</h2>
                  <p className="text-muted text-sm">Join Lectra-AI and transform how you learn</p>
                </div>

                <form className="space-y-5" onSubmit={handleSubmit} noValidate>
                  {error && (
                    <div className="flex items-start gap-2 rounded-xl border border-error/30 bg-error-light px-4 py-3 text-sm text-error" role="alert">
                      <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                      <span>{error}</span>
                    </div>
                  )}

                  <FieldShell label="Full Name" optional icon={<User className="w-5 h-5" />} error={shown('name')}>
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      onBlur={() => touch('name')}
                      autoComplete="name"
                      maxLength={60}
                      className={inputClass(!!shown('name'))}
                      placeholder="John Doe"
                    />
                  </FieldShell>

                  <FieldShell label="Email" optional icon={<Mail className="w-5 h-5" />} error={shown('email')}>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      onBlur={() => touch('email')}
                      autoComplete="email"
                      maxLength={254}
                      className={inputClass(!!shown('email'))}
                      placeholder="john@nuces.edu.pk"
                    />
                  </FieldShell>

                  <FieldShell label="Username" icon={<AtSign className="w-5 h-5" />} error={shown('username')}>
                    <input
                      type="text"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      onBlur={() => touch('username')}
                      autoComplete="username"
                      maxLength={20}
                      className={inputClass(!!shown('username'))}
                      placeholder="hanzala"
                    />
                  </FieldShell>
                  <p className="-mt-3 text-xs text-muted/70 ml-1">
                    3-20 characters, starts with a letter. Letters, numbers, _ and . only.
                  </p>

                  <FieldShell label="Password" icon={<Lock className="w-5 h-5" />} error={shown('password')}>
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      onBlur={() => touch('password')}
                      autoComplete="new-password"
                      maxLength={128}
                      className={inputClass(!!shown('password'), 'pr-12')}
                      placeholder="••••••••"
                    />
                    {eyeButton(showPassword, () => setShowPassword((v) => !v), showPassword ? 'Hide password' : 'Show password')}
                  </FieldShell>

                  {password && (
                    <div className="-mt-2 space-y-3" aria-live="polite">
                      <div className="flex items-center gap-3">
                        <div className="flex flex-1 gap-1.5">
                          {[1, 2, 3, 4].map((i) => (
                            <div
                              key={i}
                              className={`h-1.5 flex-1 rounded-full transition-colors ${
                                i <= strength.score ? STRENGTH_COLORS[strength.score] : 'bg-border'
                              }`}
                            />
                          ))}
                        </div>
                        <span className="text-xs font-medium text-muted w-20 text-right">{strength.label}</span>
                      </div>
                      <ul className="grid grid-cols-1 gap-1">
                        {checks.map((c) => (
                          <li
                            key={c.id}
                            className={`flex items-center gap-2 text-xs transition-colors ${
                              c.ok ? 'text-emerald-600' : 'text-muted'
                            }`}
                          >
                            {c.ok ? <Check className="w-3.5 h-3.5 shrink-0" /> : <X className="w-3.5 h-3.5 shrink-0 opacity-50" />}
                            {c.label}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <FieldShell label="Confirm Password" icon={<ShieldCheck className="w-5 h-5" />} error={shown('confirm')}>
                    <input
                      type={showConfirm ? 'text' : 'password'}
                      value={confirm}
                      onChange={(e) => setConfirm(e.target.value)}
                      onBlur={() => touch('confirm')}
                      autoComplete="new-password"
                      maxLength={128}
                      className={inputClass(!!shown('confirm'), 'pr-12')}
                      placeholder="••••••••"
                    />
                    {eyeButton(showConfirm, () => setShowConfirm((v) => !v), showConfirm ? 'Hide confirmation' : 'Show confirmation')}
                  </FieldShell>
                  {confirm && !errors.confirm && (
                    <p className="-mt-3 text-xs text-emerald-600 ml-1 flex items-center gap-1">
                      <Check className="w-3.5 h-3.5" /> Passwords match
                    </p>
                  )}

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full mt-8 bg-accent hover:bg-accent2 text-white font-bold py-4 rounded-xl flex items-center justify-center gap-2 transition-all duration-300 shadow-md hover:shadow-lg group overflow-hidden relative disabled:opacity-60"
                  >
                    <div className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:animate-[shimmer_1.5s_infinite]" />
                    {loading ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <>
                        <span>Sign Up</span>
                        <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                      </>
                    )}
                  </button>

                  <div className="mt-8 text-center text-sm text-muted">
                    Already have an account?{' '}
                    <Link to="/login" className="font-bold text-primary hover:text-primary-dark transition-colors">
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
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-surface border border-white/10 w-fit backdrop-blur-md shadow-sm">
            <Sparkles className="w-4 h-4 text-primary" />
            <span className="text-sm font-medium tracking-wide">Start Your Journey</span>
          </div>
          <h1 className="text-5xl lg:text-7xl font-bold tracking-tight leading-tight drop-shadow-2xl">
            Never miss <br />
            a detail <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-accent">
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
