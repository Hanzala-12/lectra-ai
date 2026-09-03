import { useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  AlertTriangle,
  BarChart2,
  CheckCircle2,
  Download,
  Loader2,
  NotebookPen,
  TrendingUp,
  XCircle,
} from 'lucide-react';
import { api, type Lecture, type LectureSummary } from '../lib/api';

type LoadedLecture = LectureSummary & { detail?: Lecture };

function pct(value: number, total: number) {
  if (total === 0) return 0;
  return Math.round((value / total) * 100);
}

function difficultyScore(level?: string) {
  const normalized = (level || '').toLowerCase();
  if (normalized.includes('easy') || normalized.includes('beginner')) return 1;
  if (normalized.includes('hard') || normalized.includes('advanced')) return 3;
  return 2;
}

export function Analytics() {
  const [lectures, setLectures] = useState<LoadedLecture[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');

  useEffect(() => {
    async function load() {
      try {
        const library = await api.library();
        const details = await Promise.allSettled(
          library.lectures.map((lecture) => api.getLecture(lecture.id)),
        );
        setLectures(
          library.lectures.map((lecture, index) => ({
            ...lecture,
            detail: details[index].status === 'fulfilled' ? details[index].value : undefined,
          })),
        );
      } catch (e: any) {
        setErr(e.message || 'Could not load analytics');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const analytics = useMemo(() => {
    const total = lectures.length;
    const notes = lectures.filter((l) => l.has_notes).length;
    const quizzes = lectures.filter((l) => l.has_quiz).length;
    const schedules = lectures.filter((l) => l.has_schedule).length;
    const evaluations = lectures.filter((l) => l.has_evaluation).length;
    const totalWords = lectures.reduce((sum, l) => sum + (l.word_count || 0), 0);
    const totalMinutes = lectures.reduce((sum, l) => sum + Math.round((l.duration || 0) / 60), 0);
    const evaluated = lectures.map((l) => l.detail?.evaluation).filter(Boolean);
    const avgStudyMinutes = evaluated.length
      ? Math.round(evaluated.reduce((sum, ev) => sum + (ev?.estimated_study_minutes || 0), 0) / evaluated.length)
      : 0;
    const avgDifficulty = evaluated.length
      ? evaluated.reduce((sum, ev) => sum + difficultyScore(ev?.difficulty), 0) / evaluated.length
      : 0;

    const topicCounts = new Map<string, number>();
    for (const lecture of lectures) {
      for (const topic of lecture.detail?.evaluation?.main_topics || []) {
        topicCounts.set(topic, (topicCounts.get(topic) || 0) + 1);
      }
    }
    const topics = [...topicCounts.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8)
      .map(([topic, count]) => ({ topic, count }));

    const artifactBars = [
      { label: 'Notes', value: pct(notes, total), count: notes },
      { label: 'Quizzes', value: pct(quizzes, total), count: quizzes },
      { label: 'Schedules', value: pct(schedules, total), count: schedules },
      { label: 'Analysis', value: pct(evaluations, total), count: evaluations },
    ];

    return {
      total,
      notes,
      quizzes,
      schedules,
      evaluations,
      totalWords,
      totalMinutes,
      avgStudyMinutes,
      avgDifficulty,
      topics,
      artifactBars,
    };
  }, [lectures]);

  const exportReport = () => {
    const lines = [
      'Lectra AI Analytics Report',
      `Generated: ${new Date().toLocaleString()}`,
      '',
      `Lectures: ${analytics.total}`,
      `Words: ${analytics.totalWords}`,
      `Recorded minutes: ${analytics.totalMinutes}`,
      `Notes generated: ${analytics.notes}`,
      `Quizzes generated: ${analytics.quizzes}`,
      `Schedules generated: ${analytics.schedules}`,
      `Evaluations generated: ${analytics.evaluations}`,
      '',
      'Top topics:',
      ...(analytics.topics.length ? analytics.topics.map((t) => `- ${t.topic}: ${t.count}`) : ['- No evaluated topics yet']),
    ];
    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'lectra-analytics-report.txt';
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-20 text-muted">
        <Loader2 className="w-5 h-5 animate-spin" /> Loading analytics…
      </div>
    );
  }

  if (err) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-10 md:pl-2">
        <div className="rounded-2xl border border-error/30 bg-error-light p-5 text-error">{err}</div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-10 md:pl-2">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-text">Learning analytics</h1>
          <p className="text-muted mt-1 text-sm">Computed from saved lectures and generated study artifacts.</p>
        </div>
        <button
          onClick={exportReport}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-surface border border-border text-sm font-medium hover:bg-surface2 transition-colors shadow-soft"
        >
          <Download className="w-4 h-4" /> Export report
        </button>
      </div>

      {analytics.total === 0 ? (
        <div className="rounded-2xl border border-dashed border-border2 bg-surface p-12 text-center shadow-soft">
          <div className="w-16 h-16 rounded-2xl bg-primary-light flex items-center justify-center mx-auto mb-5">
            <BarChart2 className="w-7 h-7 text-primary" />
          </div>
          <h2 className="text-xl font-bold text-text mb-2">No analytics yet</h2>
          <p className="text-sm text-muted">Upload and process lectures to build your learning analytics.</p>
        </div>
      ) : (
        <>
          <div className="grid sm:grid-cols-3 gap-5 mb-8">
            <SummaryCard
              title="Repository coverage"
              value={`${pct(analytics.notes + analytics.quizzes + analytics.evaluations, analytics.total * 3)}%`}
              subtitle={`${analytics.total} lectures tracked`}
              icon={<TrendingUp className="w-5 h-5" />}
              tone="primary"
            />
            <SummaryCard
              title="Study load"
              value={`${analytics.avgStudyMinutes || 0}m`}
              subtitle="Average estimated study time"
              icon={<NotebookPen className="w-5 h-5" />}
              tone="accent"
            />
            <SummaryCard
              title="Difficulty"
              value={analytics.avgDifficulty >= 2.6 ? 'Hard' : analytics.avgDifficulty >= 1.6 ? 'Medium' : 'Easy'}
              subtitle={`${analytics.evaluations} evaluated lectures`}
              icon={<AlertTriangle className="w-5 h-5" />}
              tone="warning"
            />
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-surface border border-border rounded-2xl p-6 shadow-soft">
              <h3 className="font-bold text-lg text-text mb-5">Generated artifact coverage</h3>
              <div className="space-y-4">
                {analytics.artifactBars.map((bar) => (
                  <div key={bar.label}>
                    <div className="flex items-center justify-between mb-1.5 text-sm">
                      <span className="font-medium text-text">{bar.label}</span>
                      <span className="text-muted">{bar.count}/{analytics.total}</span>
                    </div>
                    <div className="h-2.5 rounded-full bg-surface2 overflow-hidden">
                      <div className="h-full bg-primary rounded-full transition-all duration-500" style={{ width: `${bar.value}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-surface border border-border rounded-2xl p-6 shadow-soft">
              <h3 className="font-bold text-lg text-text mb-5">Top evaluated topics</h3>
              {analytics.topics.length === 0 ? (
                <div className="rounded-xl bg-warning-light p-4 text-sm text-text">
                  Generate lecture evaluations to populate topic analytics.
                </div>
              ) : (
                <div className="space-y-3">
                  {analytics.topics.map((topic) => (
                    <div key={topic.topic} className="flex items-center gap-3">
                      <div className="w-32 shrink-0 truncate text-sm font-medium text-text">{topic.topic}</div>
                      <div className="h-2.5 flex-1 rounded-full bg-surface2 overflow-hidden">
                        <div
                          className="h-full bg-accent rounded-full transition-all duration-500"
                          style={{ width: `${pct(topic.count, analytics.topics[0]?.count || 1)}%` }}
                        />
                      </div>
                      <span className="w-8 text-right text-xs text-muted">{topic.count}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="bg-surface border border-border rounded-2xl p-6 shadow-soft md:col-span-2">
              <h3 className="font-bold text-lg text-text mb-5">Lecture detail matrix</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-muted">
                      <th className="py-3 pr-4 font-medium">Lecture</th>
                      <th className="py-3 px-4 font-medium">Words</th>
                      <th className="py-3 px-4 font-medium">Notes</th>
                      <th className="py-3 px-4 font-medium">Quiz</th>
                      <th className="py-3 px-4 font-medium">Schedule</th>
                      <th className="py-3 px-4 font-medium">Evaluation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lectures.map((lecture) => (
                      <tr key={lecture.id} className="border-b border-border/70 last:border-0">
                        <td className="py-3 pr-4 font-medium text-text">{lecture.title}</td>
                        <td className="py-3 px-4 text-muted">{lecture.word_count}</td>
                        <td className="py-3 px-4"><StatusDot on={lecture.has_notes} /></td>
                        <td className="py-3 px-4"><StatusDot on={lecture.has_quiz} /></td>
                        <td className="py-3 px-4"><StatusDot on={lecture.has_schedule} /></td>
                        <td className="py-3 px-4"><StatusDot on={lecture.has_evaluation} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </>
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

function SummaryCard({
  title,
  value,
  subtitle,
  icon,
  tone,
}: {
  title: string;
  value: string;
  subtitle: string;
  icon: ReactNode;
  tone: string;
}) {
  return (
    <div className="bg-surface border border-border rounded-2xl p-6 shadow-soft">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-text">{title}</h3>
        <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${TONE_CLASSES[tone]}`}>{icon}</div>
      </div>
      <div className="text-4xl font-bold tracking-tight text-text mb-1.5">{value}</div>
      <p className="text-sm text-muted">{subtitle}</p>
    </div>
  );
}

function StatusDot({ on }: { on: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${on ? 'text-success' : 'text-muted'}`}>
      {on ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
      {on ? 'Ready' : 'Missing'}
    </span>
  );
}
