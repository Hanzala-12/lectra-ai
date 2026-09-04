import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock,
  UploadCloud,
} from 'lucide-react';
import { api, getToken, type LectureSummary, type Student } from '../lib/api';
import { Reveal, StaggerGroup, StaggerItem } from '../components/Reveal';
import { NumberTicker } from '../components/ui/number-ticker';
import { ActivityHeatmap } from '../components/ActivityHeatmap';

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
    // Rough, clearly-labeled estimate, not a tracked metric: the marketing
    // copy's own claim is that re-watching to take notes costs ~3x a
    // lecture's length, so Lectra's own notes/quiz generation saves roughly
    // the other 2x. Same order-of-magnitude logic as any "time saved"
    // callout — a fun, honest approximation, not a precise measurement.
    const hoursSaved = Math.round((totalMinutes * 2) / 60);
    return {
      totalWords,
      totalMinutes,
      notes,
      quizzes,
      analyzed,
      notReady,
      hoursSaved,
      completion: Math.round((completedArtifacts / possibleArtifacts) * 100),
    };
  }, [lectures]);

  if (loading) {
    return <DashboardSkeleton />;
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
      <Reveal className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between mb-10">
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
      </Reveal>

      <StaggerGroup className="grid grid-cols-2 sm:grid-cols-4 gap-8 mb-12 pb-10 border-b border-border">
        <StaggerItem><Stat label="Lectures" value={lectures.length} /></StaggerItem>
        <StaggerItem><Stat label="Notes ready" value={stats.notes} /></StaggerItem>
        <StaggerItem><Stat label="Quizzes ready" value={stats.quizzes} /></StaggerItem>
        <StaggerItem><Stat label="Analyzed" value={stats.analyzed} /></StaggerItem>
      </StaggerGroup>

      {lectures.length > 0 && (
        <Reveal delay={0.05} className="bg-surface rounded-lg p-6 mb-12">
          <div className="flex items-center justify-between mb-5 gap-4 flex-wrap">
            <h2 className="font-serif text-xl font-semibold text-text">Study activity</h2>
            {stats.hoursSaved > 0 && (
              <p className="text-sm text-muted">
                Estimated <span className="font-semibold text-primary-dark">~{stats.hoursSaved}h</span> saved not re-watching lectures
              </p>
            )}
          </div>
          <ActivityHeatmap lectures={lectures} />
        </Reveal>
      )}

      {lectures.length === 0 ? (
        <Reveal delay={0.1} className="rounded-lg border border-dashed border-border2 bg-surface p-12 text-center">
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
        </Reveal>
      ) : (
        <div className="grid lg:grid-cols-[1fr_320px] gap-14">
          <div>
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-serif text-2xl font-semibold text-text">Recent lectures</h2>
              <Link to="/app/library" className="text-sm font-medium text-primary hover:text-primary-dark inline-flex items-center gap-1 group">
                View all <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
              </Link>
            </div>
            <StaggerGroup className="divide-y divide-border">
              {lectures.slice(0, 5).map((lecture) => (
                <StaggerItem key={lecture.id}>
                  <Link
                    to={`/app/lecture/${lecture.id}`}
                    className="flex items-center justify-between gap-4 py-4 px-3 -mx-3 rounded-lg group hover:bg-surface transition-colors"
                  >
                    <div className="min-w-0">
                      <h3 className="font-serif font-semibold text-text truncate group-hover:text-primary transition-colors">{lecture.title}</h3>
                      <p className="text-xs text-muted flex items-center gap-1.5 mt-1">
                        <Clock className="w-3 h-3" /> {formatDuration(lecture.duration)} · {lecture.word_count.toLocaleString()} words · {formatDate(lecture.created_at)}
                      </p>
                    </div>
                    <ArtifactBadges lecture={lecture} />
                  </Link>
                </StaggerItem>
              ))}
            </StaggerGroup>
          </div>

          <Reveal delay={0.15} direction="right">
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
                  <span className="font-serif text-3xl font-semibold text-text">
                    <NumberTicker value={stats.completion} className="font-serif text-3xl font-semibold text-text tabular-nums" />%
                  </span>
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
          </Reveal>
        </div>
      )}
    </div>
  );
}

// Content-shaped placeholder instead of a spinner — mirrors the real page's
// hero/stats/two-column layout so nothing visually jumps when data arrives.
const bar = 'animate-pulse rounded bg-surface2';
function DashboardSkeleton() {
  return (
    <div className="max-w-6xl mx-auto px-8 sm:px-10 py-10 md:pl-6">
      <div className="flex flex-col gap-4 mb-10">
        <div className={`${bar} h-3 w-32`} />
        <div className={`${bar} h-10 w-3/4 max-w-xl`} />
        <div className={`${bar} h-4 w-64 mt-1`} />
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-8 mb-12 pb-10 border-b border-border">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="space-y-2.5">
            <div className={`${bar} h-3 w-16`} />
            <div className={`${bar} h-9 w-10`} />
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-[1fr_320px] gap-14">
        <div className="space-y-5">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex items-center justify-between gap-4 py-4 border-b border-border">
              <div className="space-y-2 flex-1 min-w-0">
                <div className={`${bar} h-4 w-2/3`} />
                <div className={`${bar} h-3 w-1/2`} />
              </div>
            </div>
          ))}
        </div>
        <div className="bg-surface rounded-lg p-6 space-y-5">
          <div className={`${bar} w-32 h-32 rounded-full mx-auto`} />
          <div className="space-y-2.5">
            <div className={`${bar} h-4 w-full`} />
            <div className={`${bar} h-4 w-5/6`} />
            <div className={`${bar} h-4 w-4/6`} />
          </div>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="label-caps text-muted mb-2">{label}</p>
      <p className="font-serif text-4xl font-semibold text-text">
        <NumberTicker value={value} className="font-serif text-4xl font-semibold text-text tabular-nums" />
      </p>
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
