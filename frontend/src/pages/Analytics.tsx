import { useEffect, useMemo, useState } from 'react';
import { motion } from 'motion/react';
import {
  AlertTriangle,
  BarChart2,
  CheckCircle2,
  Download,
  XCircle,
} from 'lucide-react';
import { api, type Lecture, type LectureSummary } from '../lib/api';
import { Reveal, StaggerGroup, StaggerItem } from '../components/Reveal';
import { NumberTicker } from '../components/ui/number-ticker';

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
      total, notes, quizzes, schedules, evaluations, totalWords, totalMinutes,
      avgStudyMinutes, avgDifficulty, topics, artifactBars,
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
    return <AnalyticsSkeleton />;
  }

  if (err) {
    return (
      <div className="max-w-6xl mx-auto px-8 sm:px-10 py-10 md:pl-6">
        <div className="rounded-lg border border-error/30 bg-error-light p-5 text-error">{err}</div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-8 sm:px-10 py-10 md:pl-6">
      <Reveal className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between mb-10">
        <div>
          <h1 className="font-serif text-4xl font-semibold tracking-tight text-text mb-2">Learning analytics</h1>
          <p className="text-sm text-muted">Computed from saved lectures and generated study artifacts.</p>
        </div>
        <button
          onClick={exportReport}
          className="flex items-center gap-2 px-5 py-2.5 rounded-lg border border-border text-sm font-medium hover:bg-surface2 transition-colors shrink-0"
        >
          <Download className="w-4 h-4" /> Export report
        </button>
      </Reveal>

      {analytics.total === 0 ? (
        <div className="rounded-lg border border-dashed border-border2 bg-surface p-12 text-center">
          <div className="w-14 h-14 rounded-full bg-primary-light flex items-center justify-center mx-auto mb-5">
            <BarChart2 className="w-6 h-6 text-primary" />
          </div>
          <h2 className="font-serif text-xl font-semibold text-text mb-2">No analytics yet</h2>
          <p className="text-sm text-muted">Upload and process lectures to build your learning analytics.</p>
        </div>
      ) : (
        <>
          <StaggerGroup className="grid grid-cols-3 gap-8 mb-12 pb-10 border-b border-border">
            <StaggerItem>
              <p className="label-caps text-muted mb-2">Repository coverage</p>
              <p className="font-serif text-4xl font-semibold text-text mb-1">
                <NumberTicker value={pct(analytics.notes + analytics.quizzes + analytics.evaluations, analytics.total * 3)} className="font-serif text-4xl font-semibold text-text tabular-nums" />%
              </p>
              <p className="text-sm text-muted">{analytics.total} lectures tracked</p>
            </StaggerItem>
            <StaggerItem>
              <p className="label-caps text-muted mb-2">Study load</p>
              <p className="font-serif text-4xl font-semibold text-text mb-1">
                <NumberTicker value={analytics.avgStudyMinutes || 0} className="font-serif text-4xl font-semibold text-text tabular-nums" />m
              </p>
              <p className="text-sm text-muted">Average estimated study time</p>
            </StaggerItem>
            <StaggerItem>
              <p className="label-caps text-muted mb-2">Difficulty</p>
              <p className="font-serif text-4xl font-semibold text-text mb-1">
                {analytics.avgDifficulty >= 2.6 ? 'Hard' : analytics.avgDifficulty >= 1.6 ? 'Moderate' : 'Easy'}
              </p>
              <p className="text-sm text-muted">{analytics.evaluations} evaluated lectures</p>
            </StaggerItem>
          </StaggerGroup>

          <div className="grid md:grid-cols-2 gap-14 mb-12">
            <Reveal delay={0.1}>
              <h3 className="font-serif text-xl font-semibold text-text mb-6">Generated artifact coverage</h3>
              <div className="space-y-5">
                {analytics.artifactBars.map((bar) => (
                  <div key={bar.label} className="flex items-center gap-4">
                    <span className="w-20 shrink-0 text-sm text-muted">{bar.label}</span>
                    <div className="h-1.5 flex-1 rounded-full bg-surface2 overflow-hidden">
                      <motion.div
                        className="h-full bg-primary rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: `${bar.value}%` }}
                        transition={{ duration: 0.7, ease: [0.21, 0.47, 0.32, 0.98] }}
                      />
                    </div>
                    <span className="w-10 text-right text-sm font-semibold text-text">{bar.value}%</span>
                  </div>
                ))}
              </div>
            </Reveal>

            <Reveal delay={0.15}>
              <h3 className="font-serif text-xl font-semibold text-text mb-6">Top evaluated topics</h3>
              {analytics.topics.length === 0 ? (
                <div className="rounded-lg bg-warning-light p-4 text-sm text-text">
                  Generate lecture evaluations to populate topic analytics.
                </div>
              ) : (
                <div className="space-y-5">
                  {analytics.topics.slice(0, 3).map((topic) => (
                    <div key={topic.topic} className="flex items-center gap-4">
                      <span className="w-36 shrink-0 truncate text-sm text-muted">{topic.topic}</span>
                      <div className="h-1.5 flex-1 rounded-full bg-surface2 overflow-hidden">
                        <motion.div
                          className="h-full bg-accent rounded-full"
                          initial={{ width: 0 }}
                          animate={{ width: `${pct(topic.count, analytics.topics[0]?.count || 1)}%` }}
                          transition={{ duration: 0.7, ease: [0.21, 0.47, 0.32, 0.98] }}
                        />
                      </div>
                      <span className="w-10 text-right text-sm font-semibold text-text">{pct(topic.count, analytics.total)}%</span>
                    </div>
                  ))}
                </div>
              )}
            </Reveal>
          </div>

          <Reveal delay={0.2}>
            <h3 className="font-serif text-xl font-semibold text-text mb-5">Lecture detail matrix</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left">
                    <th className="py-3 pr-4 label-caps text-muted font-semibold">Lecture</th>
                    <th className="py-3 px-4 label-caps text-muted font-semibold">Words</th>
                    <th className="py-3 px-4 label-caps text-muted font-semibold">Notes</th>
                    <th className="py-3 px-4 label-caps text-muted font-semibold">Quiz</th>
                    <th className="py-3 px-4 label-caps text-muted font-semibold">Schedule</th>
                    <th className="py-3 px-4 label-caps text-muted font-semibold">Evaluation</th>
                  </tr>
                </thead>
                <tbody>
                  {lectures.map((lecture) => (
                    <tr key={lecture.id} className="border-b border-border/70 last:border-0">
                      <td className="py-3.5 pr-4 font-serif font-semibold text-text">{lecture.title}</td>
                      <td className="py-3.5 px-4 text-muted">{lecture.word_count.toLocaleString()}</td>
                      <td className="py-3.5 px-4"><StatusDot on={lecture.has_notes} /></td>
                      <td className="py-3.5 px-4"><StatusDot on={lecture.has_quiz} /></td>
                      <td className="py-3.5 px-4"><StatusDot on={lecture.has_schedule} /></td>
                      <td className="py-3.5 px-4"><StatusDot on={lecture.has_evaluation} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Reveal>
        </>
      )}
    </div>
  );
}

// Content-shaped placeholder instead of a spinner — mirrors the real page's
// stat row / bar-chart columns / table so nothing visually jumps when data
// arrives.
const bar = 'animate-pulse rounded bg-surface2';
function AnalyticsSkeleton() {
  return (
    <div className="max-w-6xl mx-auto px-8 sm:px-10 py-10 md:pl-6">
      <div className="flex flex-col gap-2 mb-10">
        <div className={`${bar} h-10 w-72`} />
        <div className={`${bar} h-4 w-96 max-w-full`} />
      </div>

      <div className="grid grid-cols-3 gap-8 mb-12 pb-10 border-b border-border">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="space-y-2">
            <div className={`${bar} h-3 w-24`} />
            <div className={`${bar} h-9 w-16`} />
            <div className={`${bar} h-3 w-32`} />
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-14 mb-12">
        {Array.from({ length: 2 }).map((_, col) => (
          <div key={col} className="space-y-5">
            <div className={`${bar} h-5 w-48`} />
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4">
                <div className={`${bar} h-3 w-20 shrink-0`} />
                <div className={`${bar} h-1.5 flex-1 rounded-full`} />
                <div className={`${bar} h-3 w-8 shrink-0`} />
              </div>
            ))}
          </div>
        ))}
      </div>

      <div className="space-y-4">
        <div className={`${bar} h-5 w-56`} />
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className={`${bar} h-8 w-full`} />
        ))}
      </div>
    </div>
  );
}

function StatusDot({ on }: { on: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${on ? 'text-primary' : 'text-muted'}`}>
      {on ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
      {on ? 'Ready' : 'Missing'}
    </span>
  );
}
