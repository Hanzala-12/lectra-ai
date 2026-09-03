import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  CheckCircle2,
  FileText,
  HelpCircle,
  Library,
  Loader2,
  NotebookPen,
  UploadCloud,
} from 'lucide-react';
import { api, type LectureSummary } from '../lib/api';

function formatDate(ts?: number) {
  if (!ts) return 'Unknown date';
  return new Date(ts * 1000).toLocaleDateString();
}

function formatDuration(seconds?: number) {
  if (!seconds) return '0m';
  const mins = Math.max(1, Math.round(seconds / 60));
  return `${mins}m`;
}

export function Dashboard() {
  const [lectures, setLectures] = useState<LectureSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');

  useEffect(() => {
    api.library()
      .then((r) => setLectures(r.lectures))
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false));
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
        <Loader2 className="w-5 h-5 animate-spin" /> Loading dashboard...
      </div>
    );
  }

  if (err) {
    return (
      <div className="rounded-xl border border-error/30 bg-error-light p-5 text-error">
        {err}
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-12">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-8">
        <div>
          <h1 className="text-4xl font-bold tracking-tight mb-2">Student Dashboard</h1>
          <p className="text-muted">Live overview from your lecture repository.</p>
        </div>
        <Link
          to="/app/upload"
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-bold text-white shadow-sm hover:bg-primary-dark"
        >
          <UploadCloud className="w-5 h-5" /> Upload Lecture
        </Link>
      </div>

      <div className="grid md:grid-cols-4 gap-6 mb-12">
        <Stat icon={<Library className="w-5 h-5" />} label="Lectures" value={lectures.length} tone="text-primary" />
        <Stat icon={<NotebookPen className="w-5 h-5" />} label="Notes" value={stats.notes} tone="text-success" />
        <Stat icon={<HelpCircle className="w-5 h-5" />} label="Quizzes" value={stats.quizzes} tone="text-accent" />
        <Stat icon={<FileText className="w-5 h-5" />} label="Analyzed" value={stats.analyzed} tone="text-warning" />
      </div>

      {lectures.length === 0 ? (
        <div className="rounded-xl border border-border bg-surface p-10 text-center shadow-sm">
          <UploadCloud className="w-10 h-10 text-muted mx-auto mb-4" />
          <h2 className="text-xl font-bold mb-2">No lectures yet</h2>
          <p className="text-sm text-muted mb-5">Upload a recording to create your first transcript and study workspace.</p>
          <Link
            to="/app/upload"
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-bold text-white hover:bg-primary-dark"
          >
            <UploadCloud className="w-4 h-4" /> Upload now
          </Link>
        </div>
      ) : (
        <div className="grid md:grid-cols-3 gap-8">
          <div className="md:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-xl">Recent Lectures</h2>
              <Link to="/app/library" className="text-sm font-medium text-primary hover:text-primary-dark">
                View all
              </Link>
            </div>
            <div className="space-y-4">
              {lectures.slice(0, 5).map((lecture) => (
                <Link
                  key={lecture.id}
                  to={`/app/lecture/${lecture.id}`}
                  className="bg-surface border border-border rounded-xl p-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between shadow-sm hover:shadow-md hover:border-primary/40 transition"
                >
                  <div>
                    <h3 className="font-bold">{lecture.title}</h3>
                    <p className="text-sm text-muted">
                      {lecture.word_count} words | {formatDuration(lecture.duration)} audio | {formatDate(lecture.created_at)}
                    </p>
                  </div>
                  <ArtifactBadges lecture={lecture} />
                </Link>
              ))}
            </div>
          </div>

          <div>
            <h2 className="font-bold text-xl mb-4">Study Readiness</h2>
            <div className="bg-surface border border-border rounded-xl p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm font-medium text-muted">Generated artifacts</span>
                <span className="text-sm font-bold text-text">{stats.completion}%</span>
              </div>
              <div className="h-2 rounded-full bg-surface2 overflow-hidden border border-border mb-5">
                <div className="h-full bg-primary" style={{ width: `${stats.completion}%` }} />
              </div>
              <div className="space-y-3 text-sm">
                <ReadinessRow ok={stats.notes > 0} text={`${stats.notes} lectures have notes`} />
                <ReadinessRow ok={stats.quizzes > 0} text={`${stats.quizzes} lectures have quizzes`} />
                <ReadinessRow ok={stats.analyzed > 0} text={`${stats.analyzed} lectures have evaluations`} />
              </div>
              <div className="mt-6 rounded-lg bg-primary-light p-4 text-sm text-text">
                Total study material: <span className="font-bold">{stats.totalWords.toLocaleString()}</span> words across{' '}
                <span className="font-bold">{stats.totalMinutes}</span> recorded minutes.
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ icon, label, value, tone }: { icon: ReactNode; label: string; value: number; tone: string }) {
  return (
    <div className="bg-surface border border-border rounded-xl p-6 shadow-sm">
      <div className={`mb-3 ${tone}`}>{icon}</div>
      <div className="text-sm font-mono text-muted uppercase mb-2">{label}</div>
      <div className={`text-4xl font-bold tracking-tight ${tone}`}>{value}</div>
    </div>
  );
}

function ArtifactBadges({ lecture }: { lecture: LectureSummary }) {
  return (
    <div className="flex flex-wrap gap-2">
      <MiniBadge on={lecture.has_notes} label="Notes" />
      <MiniBadge on={lecture.has_quiz} label="Quiz" />
      <MiniBadge on={lecture.has_evaluation} label="Analysis" />
    </div>
  );
}

function MiniBadge({ on, label }: { on: boolean; label: string }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-1 text-[11px] ${on ? 'border-success/30 bg-success-light text-success' : 'border-border text-muted'}`}>
      {on ? <CheckCircle2 className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
      {label}
    </span>
  );
}

function ReadinessRow({ ok, text }: { ok: boolean; text: string }) {
  return (
    <div className="flex items-center gap-2">
      {ok ? <CheckCircle2 className="w-4 h-4 text-success" /> : <AlertTriangle className="w-4 h-4 text-warning" />}
      <span className="text-muted">{text}</span>
    </div>
  );
}
