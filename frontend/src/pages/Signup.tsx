import React, { useState } from 'react';
import { Lock, User, AtSign, Mail, ArrowRight, Loader2, AlertCircle, GraduationCap } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../lib/api';

export function Signup() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError('Username and password are required.');
      return;
    }
    if (password.length < 4) {
      setError('Password should be at least 4 characters.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await api.signup(username.trim(), password, name.trim() || undefined, email.trim() || undefined);
      navigate('/app/dashboard');
    } catch (err: any) {
      setError(err.message || 'Sign up failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center px-8 py-16">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center text-center mb-9">
          <Link to="/" className="flex items-center gap-2.5 mb-8">
            <div className="w-9 h-9 rounded-lg bg-primary flex items-center justify-center text-white">
              <GraduationCap className="w-[18px] h-[18px]" />
            </div>
            <span className="font-serif font-semibold text-xl tracking-tight text-text">Lectra</span>
          </Link>
          <h1 className="font-serif text-3xl font-semibold tracking-tight text-text mb-2">Create your account</h1>
          <p className="text-muted text-sm">Join Lectra AI and transform how you learn</p>
        </div>

        <form className="space-y-5" onSubmit={handleSubmit}>
          {error && (
            <div className="flex items-start gap-2 rounded-lg bg-error-light px-4 py-3 text-sm text-error">
              <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="space-y-1.5">
            <label className="text-sm font-medium text-text">Full name</label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-muted">
                <User className="w-4 h-4" />
              </div>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoComplete="name"
                className="w-full bg-surface border border-border rounded-lg py-3 pl-10 pr-4 text-text placeholder:text-muted/60 focus:border-primary outline-none transition-colors text-sm"
                placeholder="John Doe"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium text-text">Email <span className="text-muted font-normal">(optional)</span></label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-muted">
                <Mail className="w-4 h-4" />
              </div>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                className="w-full bg-surface border border-border rounded-lg py-3 pl-10 pr-4 text-text placeholder:text-muted/60 focus:border-primary outline-none transition-colors text-sm"
                placeholder="john@nuces.edu.pk"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium text-text">Username</label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-muted">
                <AtSign className="w-4 h-4" />
              </div>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                className="w-full bg-surface border border-border rounded-lg py-3 pl-10 pr-4 text-text placeholder:text-muted/60 focus:border-primary outline-none transition-colors text-sm"
                placeholder="hanzala"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium text-text">Password</label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-muted">
                <Lock className="w-4 h-4" />
              </div>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password"
                className="w-full bg-surface border border-border rounded-lg py-3 pl-10 pr-4 text-text placeholder:text-muted/60 focus:border-primary outline-none transition-colors text-sm"
                placeholder="••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 bg-primary hover:bg-primary-dark text-white font-semibold py-3 rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-60"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <span>Sign Up</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>

          <div className="text-center text-sm text-muted">
            Already have an account?{' '}
            <Link to="/login" className="font-semibold text-primary hover:text-primary-dark transition-colors">
              Sign in
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
