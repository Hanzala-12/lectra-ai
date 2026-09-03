import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock,
  HelpCircle,
  Library,
  Loader2,
  NotebookPen,
  Sparkles,
  UploadCloud,
} from 'lucide-react';
import { api, getToken, type LectureSummary, type Student } from '../lib/api';

function formatDate(ts?: number) {
  if (!ts) return 'Unknown date';
  const d = new Date(ts * 1000);
  const today = new Date();
  const isToday = d.toDateString() === today.toDateString();
  return isToday ? `Today, ${d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}` : d.toLocaleDateString();
}

function formatDuration(seconds?: number) {
  if (!seconds) return '0m';
  const mins = Math.max(1, Math.round(seconds / 60));
  return `${mins}m`;
}

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 18) return 'Good afternoon';
  return 'Good evening';
}

const heroLine = (lectureCount: number, completion: number) => {
  if (lectureCount === 0) return "Upload your first lecture and let's get you studying.";
  if (completion >= 80) return "You're in great shape — your study material is fully prepped.";
  if (completion >= 40) return 'Solid progress. A few more lectures could use notes or a quiz.';
  return 'Plenty of lectures waiting on notes and quizzes — pick one up?';
};

export function Dashboard() {
  const [lectures, setLectures] = useState<LectureSummary[]>([]);
  const [student, setStudent] = useState<Student | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');

  useEffect(() => {
    api.library()
      .then((r) => setLectures(r.lectures))
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false));
    if (getToken()) api.me().then(setStudent).catch(() => {});
  }, []);

  const stats = useMemo(() => {
    const totalWords = lectures.reduce((sum, l) => sum + (l.word_count || 0), 0);
    const totalMinutes = lectures.reduce((sum, l) => sum + Math.round((l.duration || 0) / 60), 0);
    const notes = lectures.filter((l) => l.has_notes).length;
    const quizzes = lectures.filter((l) => l.has_quiz).length;
    const analyzed = lectures.filter((l) => l.has_evaluation).length;
    const completedArtifacts = notes + quizzes + analyzed;
    const possibleArtifacts = Math.max(lectures.length * 3, 1);
    return {
      totalWords,
      totalMinutes,
      notes,
      quizzes,
      analyzed,
      completion: Math.round((completedArtifacts / possibleArtifacts) * 100),
    };
  }, [lectures]);

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-20 text-muted">
        <Loader2 className="w-5 h-5 animate-spin" /> Loading dashboard…
      </div>
    );
  }

  if (err) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-12 md:pl-2">
        <div className="rounded-2xl border border-error/30 bg-error-light p-5 text-error">{err}</div>
      </div>
    );
  }

  const firstName = (student?.name || student?.username || '').split(' ')[0];

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 md:pl-2">
      {/* Hero */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-primary via-primary to-accent2 p-8 sm:p-10 mb-8 shadow-soft-lg">
        <div className="absolute -top-16 -right-16 w-64 h-64 rounded-full bg-white/10 blur-2xl" />
        <div className="absolute -bottom-20 left-1/3 w-72 h-72 rounded-full bg-accent/30 blur-3xl" />
        <div className="relative">
          <p className="text-sm font-medium text-white/80 mb-2">
            {greeting()}{firstName ? `, ${firstName}` : ''} 👋
          </p>
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-white mb-3 max-w-xl">
            {heroLine(lectures.length, stats.completion)}
          </h1>
          <div className="flex flex-wrap items-center gap-3 mt-6">
            <Link
              to="/app/upload"
              className="inline-flex items-center gap-2 rounded-xl bg-white px-5 py-2.5 text-sm font-bold text-primary shadow-soft hover:shadow-soft-lg hover:-translate-y-0.5 transition-all"
            >
              <UploadCloud className="w-4 h-4" /> Upload lecture
            </Link>
            {lectures.length > 0 && (
              <Link
                to="/app/library"
                className="inline-flex items-center gap-2 rounded-xl bg-white/15 backdrop-blur px-5 py-2.5 text-sm font-semibold text-white hover:bg-white/25 transition-all"
              >
                <Library className="w-4 h-4" /> Browse library
              </Link>
            )}
          </div>
        </div>
      </div>

      <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-4 mb-10">
        <Stat icon={<Library className="w-5 h-5" />} label="Lectures" value={lectures.length} tone="primary" />
        <Stat icon={<NotebookPen className="w-5 h-5" />} label="Notes ready" value={stats.notes} tone="success" />
        <Stat icon={<HelpCircle className="w-5 h-5" />} label="Quizzes ready" value={stats.quizzes} tone="accent" />
        <Stat icon={<Sparkles className="w-5 h-5" />} label="Analyzed" value={stats.analyzed} tone="warning" />
      </div>

      {lectures.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border2 bg-surface p-12 text-center shadow-soft">
          <div className="w-16 h-16 rounded-2xl bg-primary-light flex items-center justify-center mx-auto mb-5">
            <UploadCloud className="w-7 h-7 text-primary" />
          </div>
          <h2 className="text-xl font-bold text-text mb-2">Upload your first lecture</h2>
          <p className="text-sm text-muted mb-6 max-w-sm mx-auto">
            Drop in a recording and Lectra will clean the audio, transcribe it, and get notes and a quiz ready for you.
          </p>
          <Link
            to="/app/upload"
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-6 py-3 text-sm font-semibold text-white shadow-soft hover:bg-primary-dark"
          >
            <UploadCloud className="w-4 h-4" /> Upload a lecture
          </Link>
        </div>
      ) : (
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-lg text-text">Recent lectures</h2>
              <Link to="/app/library" className="text-sm font-medium text-primary hover:text-primary-dark inline-flex items-center gap-1 group">
                View all <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
              </Link>
            </div>
            <div className="space-y-3">
              {lectures.slice(0, 5).map((lecture) => (
                <Link
                  key={lecture.id}
                  to={`/app/lecture/${lecture.id}`}
                  className="bg-surface border border-border rounded-2xl p-4 flex items-center gap-4 shadow-soft hover:shadow-soft-lg hover:border-primary/30 hover:-translate-y-0.5 transition-all"
                >
                  <div className="w-11 h-11 rounded-xl bg-primary-light flex items-center justify-center shrink-0">
                    <NotebookPen className="w-5 h-5 text-primary" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="font-semibold text-text truncate">{lecture.title}</h3>
                    <p className="text-xs text-muted flex items-center gap-1.5 mt-0.5">
                      <Clock className="w-3 h-3" /> {formatDuration(lecture.duration)} · {lecture.word_count} words · {formatDate(lecture.created_at)}
                    </p>
                  </div>
                  <ArtifactBadges lecture={lecture} />
                </Link>
              ))}
            </div>
          </div>

          <div>
            <h2 className="font-bold text-lg text-text mb-4">Study readiness</h2>
            <div className="bg-surface border border-border rounded-2xl p-6 shadow-soft">
              <div className="relative w-28 h-28 mx-auto mb-5">
                <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="42" fill="none" stroke="var(--color-surface2)" strokeWidth="10" />
                  <circle
                    cx="50" cy="50" r="42" fill="none" stroke="url(#readinessGradient)" strokeWidth="10"
                    strokeLinecap="round" strokeDasharray={`${stats.completion * 2.64} 264`}
                    className="transition-all duration-700"
                  />
                  <defs>
                    <linearGradient id="readinessGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="var(--color-primary)" />
                      <stop offset="100%" stopColor="var(--color-accent)" />
                    </linearGradient>
                  </defs>
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-2xl font-bold text-text">{stats.completion}%</span>
                </div>
              </div>
              <div className="space-y-2.5 text-sm mb-5">
                <ReadinessRow ok={stats.notes > 0} text={`${stats.notes} lecture${stats.notes === 1 ? '' : 's'} with notes`} />
                <ReadinessRow ok={stats.quizzes > 0} text={`${stats.quizzes} lecture${stats.quizzes === 1 ? '' : 's'} with quizzes`} />
                <ReadinessRow ok={stats.analyzed > 0} text={`${stats.analyzed} lecture${stats.analyzed === 1 ? '' : 's'} analyzed`} />
              </div>
              <div className="rounded-xl bg-gradient-to-br from-primary-light to-accent-light p-4 text-sm text-text">
                <span className="font-bold">{stats.totalWords.toLocaleString()}</span> words across{' '}
                <span className="font-bold">{stats.totalMinutes}</span> recorded minutes.
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const TONE_CLASSES: Record<string, string> = {
  primary: 'bg-primary-light text-primary',
  success: 'bg-success-light text-success',
  accent: 'bg-accent-light text-accent',
  warning: 'bg-warning-light text-warning',
};

function Stat({ icon, label, value, tone }: { icon: ReactNode; label: string; value: number; tone: string }) {
  return (
    <div className="bg-surface border border-border rounded-2xl p-5 shadow-soft hover:shadow-soft-lg hover:-translate-y-0.5 transition-all">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-4 ${TONE_CLASSES[tone]}`}>{icon}</div>
      <div className="text-3xl font-bold tracking-tight text-text mb-1">{value}</div>
      <div className="text-sm text-muted">{label}</div>
    </div>
  );
}

function ArtifactBadges({ lecture }: { lecture: LectureSummary }) {
  return (
    <div className="hidden sm:flex flex-wrap gap-1.5 shrink-0">
      <MiniBadge on={lecture.has_notes} label="Notes" />
      <MiniBadge on={lecture.has_quiz} label="Quiz" />
      <MiniBadge on={lecture.has_evaluation} label="Analysis" />
    </div>
  );
}

function MiniBadge({ on, label }: { on: boolean; label: string }) {
  if (!on) return null;
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-success-light text-success px-2.5 py-1 text-[11px] font-medium">
      <CheckCircle2 className="w-3 h-3" />
      {label}
    </span>
  );
}

function ReadinessRow({ ok, text }: { ok: boolean; text: string }) {
  return (
    <div className="flex items-center gap-2.5">
      {ok ? <CheckCircle2 className="w-4 h-4 text-success shrink-0" /> : <AlertTriangle className="w-4 h-4 text-muted shrink-0" />}
      <span className={ok ? 'text-text' : 'text-muted'}>{text}</span>
    </div>
  );
}
