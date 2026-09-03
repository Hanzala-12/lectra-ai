import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock,
  Loader2,
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

const heroLine = (lectureCount: number, ready: number) => {
  if (lectureCount === 0) return "Upload your first lecture and let's get you studying.";
  if (ready === 0) return `${lectureCount} lecture${lectureCount === 1 ? '' : 's'} in your library — pick one up.`;
  return `${ready} lecture${ready === 1 ? '' : 's'} still waiting on notes or a quiz.`;
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
    const notReady = lectures.filter((l) => !(l.has_notes && l.has_quiz)).length;
    return {
      totalWords,
      totalMinutes,
      notes,
      quizzes,
      analyzed,
      notReady,
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
      <div className="max-w-6xl mx-auto px-10 py-12 md:pl-6">
        <div className="rounded-lg border border-error/30 bg-error-light p-5 text-error">{err}</div>
      </div>
    );
  }

  const firstName = (student?.name || student?.username || '').split(' ')[0];

  return (
    <div className="max-w-6xl mx-auto px-8 sm:px-10 py-10 md:pl-6">
      <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between mb-10">
        <div>
          <p className="label-caps text-primary mb-3">
            {greeting()}{firstName ? `, ${firstName}` : ''}
          </p>
          <h1 className="font-serif text-4xl sm:text-[2.75rem] leading-[1.1] font-semibold tracking-tight text-text max-w-xl">
            {heroLine(lectures.length, stats.notReady)}
          </h1>
          <p className="text-muted mt-3 text-[15px]">Pick up where you left off, or bring in something new.</p>
        </div>
        <div className="flex items-center gap-5 shrink-0">
          <Link
            to="/app/upload"
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-white hover:bg-primary-dark transition-colors"
          >
            <UploadCloud className="w-4 h-4" /> Upload lecture
          </Link>
          {lectures.length > 0 && (
            <Link to="/app/library" className="text-sm font-medium text-primary hover:text-primary-dark inline-flex items-center gap-1 group">
              Browse library <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
            </Link>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-8 mb-12 pb-10 border-b border-border">
        <Stat label="Lectures" value={lectures.length} />
        <Stat label="Notes ready" value={stats.notes} />
        <Stat label="Quizzes ready" value={stats.quizzes} />
        <Stat label="Analyzed" value={stats.analyzed} />
      </div>

      {lectures.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border2 bg-surface p-12 text-center">
          <div className="w-14 h-14 rounded-full bg-primary-light flex items-center justify-center mx-auto mb-5">
            <UploadCloud className="w-6 h-6 text-primary" />
          </div>
          <h2 className="font-serif text-xl font-semibold text-text mb-2">Upload your first lecture</h2>
          <p className="text-sm text-muted mb-6 max-w-sm mx-auto">
            Drop in a recording and Lectra will clean the audio, transcribe it, and get notes and a quiz ready for you.
          </p>
          <Link
            to="/app/upload"
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-6 py-3 text-sm font-semibold text-white hover:bg-primary-dark"
          >
            <UploadCloud className="w-4 h-4" /> Upload a lecture
          </Link>
        </div>
      ) : (
        <div className="grid lg:grid-cols-[1fr_320px] gap-14">
          <div>
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-serif text-2xl font-semibold text-text">Recent lectures</h2>
              <Link to="/app/library" className="text-sm font-medium text-primary hover:text-primary-dark inline-flex items-center gap-1 group">
                View all <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
              </Link>
            </div>
            <div className="divide-y divide-border">
              {lectures.slice(0, 5).map((lecture) => (
                <Link
                  key={lecture.id}
                  to={`/app/lecture/${lecture.id}`}
                  className="flex items-center justify-between gap-4 py-4 group"
                >
                  <div className="min-w-0">
                    <h3 className="font-serif font-semibold text-text truncate group-hover:text-primary transition-colors">{lecture.title}</h3>
                    <p className="text-xs text-muted flex items-center gap-1.5 mt-1">
                      <Clock className="w-3 h-3" /> {formatDuration(lecture.duration)} · {lecture.word_count.toLocaleString()} words · {formatDate(lecture.created_at)}
                    </p>
                  </div>
                  <ArtifactBadges lecture={lecture} />
                </Link>
              ))}
            </div>
          </div>

          <div>
            <h2 className="font-serif text-2xl font-semibold text-text mb-5">Study readiness</h2>
            <div className="bg-surface rounded-lg p-6">
              <div className="relative w-32 h-32 mx-auto mb-6">
                <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="42" fill="none" stroke="var(--color-surface2)" strokeWidth="9" />
                  <circle
                    cx="50" cy="50" r="42" fill="none" stroke="var(--color-primary)" strokeWidth="9"
                    strokeDasharray={`${stats.completion * 2.64} 264`}
                    className="transition-all duration-700"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="font-serif text-3xl font-semibold text-text">{stats.completion}%</span>
                </div>
              </div>
              <div className="space-y-2.5 text-sm mb-6">
                <ReadinessRow ok={stats.notes > 0} text={`${stats.notes} of ${lectures.length} lectures have notes`} />
                <ReadinessRow ok={stats.quizzes > 0} text={`${stats.quizzes} of ${lectures.length} lectures have quizzes`} />
                <ReadinessRow ok={stats.analyzed > 0} text={`${stats.analyzed} of ${lectures.length} lectures analyzed`} />
              </div>
              <p className="text-sm text-muted pt-5 border-t border-border">
                <span className="font-semibold text-text">{stats.totalWords.toLocaleString()}</span> words across{' '}
                <span className="font-semibold text-text">{Math.floor(stats.totalMinutes / 60)}h {stats.totalMinutes % 60}m</span> recorded.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="label-caps text-muted mb-2">{label}</p>
      <p className="font-serif text-4xl font-semibold text-text">{value}</p>
    </div>
  );
}

function ArtifactBadges({ lecture }: { lecture: LectureSummary }) {
  return (
    <div className="hidden sm:flex flex-wrap gap-1.5 shrink-0">
      <Badge on={lecture.has_notes} label="Notes" tone="accent" />
      <Badge on={lecture.has_quiz} label="Quiz" tone="primary" />
      {lecture.best_score != null && (
        <span className="inline-flex items-center text-[11px] px-2.5 py-1 rounded-full bg-accent-light text-accent2 font-medium">
          Best {Math.round(lecture.best_score)}%
        </span>
      )}
    </div>
  );
}

function Badge({ on, label, tone }: { on: boolean; label: string; tone: 'primary' | 'accent' }) {
  if (!on) return null;
  const cls = tone === 'primary' ? 'bg-primary-light text-primary-dark' : 'bg-accent-light text-accent2';
  return <span className={`inline-flex items-center text-[11px] px-2.5 py-1 rounded-full font-medium ${cls}`}>{label}</span>;
}

function ReadinessRow({ ok, text }: { ok: boolean; text: string }) {
  return (
    <div className="flex items-center gap-2.5">
      {ok ? <CheckCircle2 className="w-4 h-4 text-primary shrink-0" /> : <AlertTriangle className="w-4 h-4 text-muted shrink-0" />}
      <span className={ok ? 'text-text' : 'text-muted'}>{text}</span>
    </div>
  );
}
