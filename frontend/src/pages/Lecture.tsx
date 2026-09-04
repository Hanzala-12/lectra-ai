import React, { useEffect, useState } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import {
  FileText, NotebookPen, HelpCircle, CalendarDays, BarChart3, MessageSquare,
  Loader2, AlertCircle, RefreshCw, Send, CheckCircle2, XCircle, ArrowLeft,
  Music, Sparkles, Users, Clock, Sparkle, Pencil, X, Download, Headphones,
} from 'lucide-react';
import {
  api, buildUrl, type Lecture as LectureT, type QuizQuestion, type GradeResult,
  type Schedule, type Evaluation, type AudioFile, type ReviewState,
} from '../lib/api';

type Tab = 'transcript' | 'notes' | 'recap' | 'quiz' | 'schedule' | 'evaluation' | 'chat';
const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: 'transcript', label: 'Transcript', icon: <FileText className="w-4 h-4" /> },
  { id: 'notes', label: 'Notes', icon: <NotebookPen className="w-4 h-4" /> },
  { id: 'recap', label: 'Recap', icon: <Headphones className="w-4 h-4" /> },
  { id: 'quiz', label: 'Quiz', icon: <HelpCircle className="w-4 h-4" /> },
  { id: 'schedule', label: 'Schedule', icon: <CalendarDays className="w-4 h-4" /> },
  { id: 'evaluation', label: 'Evaluation', icon: <BarChart3 className="w-4 h-4" /> },
  { id: 'chat', label: 'Chat', icon: <MessageSquare className="w-4 h-4" /> },
];

const card = 'rounded-lg bg-surface p-5';
const btn = 'inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-primary text-white text-sm font-semibold hover:bg-primary-dark disabled:opacity-50 disabled:pointer-events-none transition-colors';
const btnGhost = 'text-sm text-muted hover:text-text inline-flex items-center gap-1.5 font-medium transition-colors';

function Spinner({ label }: { label: string }) {
  return (
    <div className="flex flex-col items-center gap-3 text-muted text-sm py-16 justify-center">
      <Loader2 className="w-6 h-6 animate-spin text-primary" /> {label}
    </div>
  );
}

function ErrorBox({ msg }: { msg: string }) {
  const isLLM = /not configured|credits|402|503/i.test(msg);
  return (
    <div className="flex items-start gap-3 rounded-lg bg-warning-light p-4 text-sm">
      <AlertCircle className="w-5 h-5 text-warning shrink-0 mt-0.5" />
      <div>
        <p className="text-text">{msg}</p>
        {isLLM && (
          <p className="text-muted mt-1">
            Add <code>OPENROUTER_API_KEY</code> to the backend <code>.env</code> (or set a
            free <code>OPENROUTER_MODEL</code>) to enable AI features.
          </p>
        )}
      </div>
    </div>
  );
}

// ----------------------------------------------------------------- Export
// One consolidated Markdown file of everything generated for this lecture so
// far (notes/quiz/schedule/evaluation are skipped individually if not yet
// generated — never a placeholder), plus the transcript as reference
// material at the end. Pure client-side Blob download, no backend route.
function buildExportMarkdown(lecture: LectureT): string {
  const speaker = (label: string) => lecture.speaker_names?.[label] || label.replace('SPEAKER_', 'Speaker ');
  const lines: string[] = [
    `# ${lecture.title}`,
    '',
    `*Exported from Lectra AI — ${new Date().toLocaleString()}*`,
  ];

  if (lecture.notes) {
    lines.push('', '## Notes', '', lecture.notes);
  }

  if (lecture.quiz?.length) {
    lines.push('', '## Quiz', '');
    lecture.quiz.forEach((q, i) => {
      lines.push(`**${i + 1}. ${q.question}**`, '');
      q.answers.forEach((a) => lines.push(`- ${a.is_correct ? '[x]' : '[ ]'} ${a.text}`));
      lines.push('', `*${q.explanation}*`, '');
    });
  }

  if (lecture.schedule?.plan?.length) {
    lines.push('', '## Study schedule', '');
    if (lecture.schedule.available_time) lines.push(`**Available time:** ${lecture.schedule.available_time}  `);
    if (lecture.schedule.learning_goals) lines.push(`**Learning goals:** ${lecture.schedule.learning_goals}`);
    lines.push('');
    lecture.schedule.plan.forEach((d) => {
      lines.push(`### Day ${d.day} — ${d.focus} (${d.est_minutes} min)`, '');
      (d.tasks || []).forEach((t) => lines.push(`- ${t}`));
      lines.push('');
    });
    if (lecture.schedule.tips?.length) {
      lines.push('**Tips**', '');
      lecture.schedule.tips.forEach((t) => lines.push(`- ${t}`));
    }
  }

  if (lecture.evaluation) {
    const ev = lecture.evaluation;
    lines.push(
      '', '## Evaluation', '',
      `**Difficulty:** ${ev.difficulty}  `,
      `**Estimated study time:** ${ev.estimated_study_minutes} min`,
      '', ev.summary, '',
    );
    if (ev.main_topics?.length) lines.push(`**Main topics:** ${ev.main_topics.join(', ')}`, '');
    if (ev.comprehension_questions?.length) {
      lines.push('**Check your understanding:**', '');
      ev.comprehension_questions.forEach((q) => lines.push(`- ${q}`));
    }
  }

  if (lecture.transcript_text) {
    lines.push('', '## Transcript', '');
    if (lecture.transcript_segments?.length) {
      lecture.transcript_segments.forEach((s) => {
        lines.push(`${s.speaker ? `**${speaker(s.speaker)}:** ` : ''}${s.text}`, '');
      });
    } else {
      lines.push(lecture.transcript_text);
    }
  }

  return lines.join('\n');
}

function downloadLectureMarkdown(lecture: LectureT) {
  const md = buildExportMarkdown(lecture);
  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  const safeTitle = lecture.title.trim().replace(/[^\w\- ]+/g, '').replace(/\s+/g, '-').toLowerCase() || 'lecture';
  a.download = `${safeTitle}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

export function Lecture() {
  const { id = '' } = useParams();
  const [params, setParams] = useSearchParams();
  const initial = (params.get('tab') as Tab) || 'transcript';
  const [tab, setTab] = useState<Tab>(initial);
  const [lecture, setLecture] = useState<LectureT | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');

  useEffect(() => {
    api.getLecture(id).then(setLecture).catch((e) => setErr(e.message)).finally(() => setLoading(false));
  }, [id]);

  const selectTab = (t: Tab) => { setTab(t); setParams({ tab: t }, { replace: true }); };

  if (loading) return <div className="max-w-5xl mx-auto px-8 sm:px-10 py-10 md:pl-6"><Spinner label="Loading lecture…" /></div>;
  if (err || !lecture) return <div className="max-w-5xl mx-auto px-8 sm:px-10 py-10 md:pl-6"><ErrorBox msg={err || 'Lecture not found'} /></div>;

  const durationMin = lecture.metadata?.duration_processed ? Math.round(lecture.metadata.duration_processed / 60) : null;

  return (
    <div className="max-w-5xl mx-auto px-8 sm:px-10 py-8 md:pl-6">
      <Link to="/app/library" className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-text mb-5 font-medium transition-colors">
        <ArrowLeft className="w-4 h-4" /> Back to Library
      </Link>

      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          {durationMin != null && <p className="label-caps text-primary mb-2">{durationMin} min audio</p>}
          <h1 className="font-serif text-3xl sm:text-4xl font-semibold text-text mb-2 tracking-tight">{lecture.title}</h1>
          <p className="text-sm text-muted">{lecture.transcript_text.split(/\s+/).filter(Boolean).length.toLocaleString()} words</p>
        </div>
        <button onClick={() => downloadLectureMarkdown(lecture)} className={`${btnGhost} shrink-0`}>
          <Download className="w-3.5 h-3.5" /> Export as Markdown
        </button>
      </div>

      <div className="flex flex-wrap gap-1 border-b border-border mb-6">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => selectTab(t.id)}
            className={`flex items-center gap-1.5 px-3.5 py-2.5 text-sm border-b-2 -mb-px font-medium transition-colors whitespace-nowrap ${
              tab === t.id ? 'border-primary text-primary' : 'border-transparent text-muted hover:text-text'
            }`}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {tab === 'transcript' && <TranscriptTab lecture={lecture} />}
      {tab === 'notes' && <NotesTab id={id} initial={lecture.notes} />}
      {tab === 'recap' && <RecapTab id={id} initialScript={lecture.recap_script} initialAudioUrl={lecture.recap_audio_url} />}
      {tab === 'quiz' && <QuizTab id={id} initial={lecture.quiz} initialQuizId={lecture.quiz_id} />}
      {tab === 'schedule' && <ScheduleTab id={id} initial={lecture.schedule} initialReviewState={lecture.review_state} />}
      {tab === 'evaluation' && <EvaluationTab id={id} initial={lecture.evaluation} />}
      {tab === 'chat' && <ChatTab id={id} history={lecture.chat_history} />}
    </div>
  );
}

// ----------------------------------------------------------------- Transcript
const AUDIO_KIND_LABEL: Record<string, string> = { original: 'Original recording', cleaned: 'Cleaned audio' };

// Resolves a raw diarization label ("SPEAKER_00") to whatever the student
// renamed it to, falling back to an auto-formatted default ("Speaker 00").
function speakerName(rawLabel: string, names: Record<string, string>) {
  return names[rawLabel] || rawLabel.replace('SPEAKER_', 'Speaker ');
}

function audioLabel(kind: string, names: Record<string, string> = {}) {
  if (AUDIO_KIND_LABEL[kind]) return AUDIO_KIND_LABEL[kind];
  if (kind.startsWith('speaker:')) return speakerName(kind.replace('speaker:', ''), names);
  return kind;
}

// Not a component (called inline, wrapped in a keyed element by the caller)
// — this project has no @types/react anywhere, so `key` isn't recognized as
// a reserved prop on a locally-declared function component.
function audioCardContent(a: AudioFile, names: Record<string, string>) {
  const isSpeaker = a.kind.startsWith('speaker:');
  return (
    <div className="rounded-lg bg-surface2 p-4">
      <div className="flex items-center gap-2 mb-2.5">
        {isSpeaker ? <Users className="w-3.5 h-3.5 text-primary" /> : <Music className="w-3.5 h-3.5 text-primary" />}
        <span className="text-sm font-medium text-text">{audioLabel(a.kind, names)}</span>
        {a.duration != null && <span className="text-xs text-muted ml-auto">{Math.round(a.duration)}s</span>}
      </div>
      <audio controls className="w-full h-9" src={buildUrl(a.file_path)} />
    </div>
  );
}

// Compact inline editor for renaming diarization labels ("SPEAKER_00" ->
// "Professor"). Scoped to TranscriptTab's own state since speaker names are
// only rendered here today; lift to the Lecture page if that changes.
function SpeakerRenameForm({
  rawLabels, names, onSave, onCancel,
}: {
  rawLabels: string[];
  names: Record<string, string>;
  onSave: (next: Record<string, string>) => void;
  onCancel: () => void;
}) {
  const [drafts, setDrafts] = useState<Record<string, string>>(
    Object.fromEntries(rawLabels.map((l) => [l, names[l] || ''])),
  );
  const [saving, setSaving] = useState(false);
  const save = async () => {
    setSaving(true);
    try {
      await onSave(drafts);
    } finally {
      setSaving(false);
    }
  };
  return (
    <div className={`${card} space-y-3`}>
      <p className="label-caps text-muted">Rename speakers</p>
      <div className="space-y-2">
        {rawLabels.map((label) => (
          <div key={label} className="flex items-center gap-2">
            <span className="text-xs text-muted w-20 shrink-0">{label.replace('SPEAKER_', 'Speaker ')}</span>
            <input
              value={drafts[label] ?? ''}
              onChange={(e) => setDrafts({ ...drafts, [label]: e.target.value })}
              placeholder="e.g. Professor"
              className="flex-1 min-w-0 px-2.5 py-1.5 rounded-md border border-border bg-surface text-sm outline-none focus:border-primary transition-colors"
            />
          </div>
        ))}
      </div>
      <div className="flex items-center gap-2 justify-end">
        <button onClick={onCancel} className={btnGhost}><X className="w-3.5 h-3.5" /> Cancel</button>
        <button onClick={save} disabled={saving} className={`${btn} px-3.5 py-1.5 text-xs`}>
          {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />} Save
        </button>
      </div>
    </div>
  );
}

function TranscriptTab({ lecture }: { lecture: LectureT }) {
  const audioFiles = lecture.audio_files || [];
  const legacyAudio = lecture.metadata?.audio_url;
  const segments = lecture.transcript_segments || [];

  const [names, setNames] = useState<Record<string, string>>(lecture.speaker_names || {});
  const [renaming, setRenaming] = useState(false);
  const rawLabels = Array.from(new Set(segments.map((s) => s.speaker).filter((s): s is string => !!s)));

  const saveNames = async (next: Record<string, string>) => {
    const r = await api.renameSpeakers(lecture.id, next);
    setNames(r.speaker_names);
    setRenaming(false);
  };

  // The one audio file transcript clicks control — prefer "cleaned" (what a
  // listener actually wants), else whatever's first, else the legacy
  // single-file field on old records. Every other file (original, per-speaker
  // splits) still plays independently below, just not synced.
  const primary = audioFiles.find((a) => a.kind === 'cleaned') || audioFiles[0] || null;
  const primaryUrl = primary ? buildUrl(primary.file_path) : legacyAudio ? buildUrl(legacyAudio) : null;
  const otherFiles = primary ? audioFiles.filter((a) => a.audio_id !== primary.audio_id) : audioFiles;

  const audioRef = React.useRef<HTMLAudioElement>(null);
  const lineRefs = React.useRef<(HTMLButtonElement | null)[]>([]);
  const [currentTime, setCurrentTime] = useState(0);
  const [playing, setPlaying] = useState(false);

  const activeIndex = primaryUrl
    ? segments.findIndex((s) => currentTime >= s.start && currentTime < s.end)
    : -1;

  useEffect(() => {
    if (activeIndex >= 0) lineRefs.current[activeIndex]?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [activeIndex]);

  const seekTo = (start: number) => {
    const el = audioRef.current;
    if (!el) return;
    el.currentTime = start;
    el.play();
  };

  return (
    <div className="grid md:grid-cols-[260px_1fr] gap-6">
      <div className="space-y-3 md:sticky md:top-6 md:self-start">
        {primaryUrl && (
          <div className={`${card} space-y-2.5`}>
            <div className="flex items-center gap-2">
              <Music className="w-3.5 h-3.5 text-primary" />
              <span className="text-sm font-medium text-text">{primary ? audioLabel(primary.kind, names) : 'Cleaned audio'}</span>
              {playing && (
                <span className="ml-auto flex items-center gap-1 text-[10px] text-primary font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" /> Playing
                </span>
              )}
            </div>
            <audio
              ref={audioRef}
              controls
              className="w-full h-9"
              src={primaryUrl}
              onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
              onPlay={() => setPlaying(true)}
              onPause={() => setPlaying(false)}
            />
            {segments.length > 0 && <p className="text-xs text-muted">Click any line to jump there.</p>}
          </div>
        )}
        {otherFiles.length > 0 && (
          <div className={`${card} space-y-3`}>
            <p className="label-caps text-muted">{primaryUrl ? 'Other audio' : 'Audio'}</p>
            {otherFiles.map((a) => <div key={a.audio_id}>{audioCardContent(a, names)}</div>)}
          </div>
        )}
        {!primaryUrl && legacyAudio && (
          <div className={card}>
            <p className="text-sm font-medium text-text mb-2">Cleaned audio</p>
            <audio controls className="w-full" src={buildUrl(legacyAudio)} />
          </div>
        )}
        {rawLabels.length > 0 && (
          renaming ? (
            <SpeakerRenameForm rawLabels={rawLabels} names={names} onSave={saveNames} onCancel={() => setRenaming(false)} />
          ) : (
            <button onClick={() => setRenaming(true)} className={`${btnGhost} ${card}`}>
              <Pencil className="w-3.5 h-3.5" /> Rename speakers
            </button>
          )
        )}
      </div>
      <div className={card}>
        {segments.length ? (
          <div className="space-y-1 max-h-[65vh] overflow-y-auto pr-1">
            {segments.map((s, i) => {
              const isActive = i === activeIndex;
              return (
                <button
                  key={i}
                  ref={(el) => { lineRefs.current[i] = el; }}
                  onClick={() => seekTo(s.start)}
                  disabled={!primaryUrl}
                  className={`block w-full text-left text-[15px] leading-relaxed px-2.5 py-1.5 rounded-md transition-colors ${
                    isActive ? 'bg-primary-light text-primary-dark' : 'text-text'
                  } ${primaryUrl ? 'hover:bg-surface2 cursor-pointer' : 'cursor-default'}`}
                >
                  {s.speaker && (
                    <span className={`font-semibold mr-2 ${isActive ? 'text-primary-dark' : 'text-primary'}`}>
                      {speakerName(s.speaker, names)}
                    </span>
                  )}
                  <span className={`text-xs mr-2 tabular-nums ${isActive ? 'text-primary-dark/70' : 'text-muted'}`}>
                    {Math.floor(s.start / 60)}:{String(Math.floor(s.start % 60)).padStart(2, '0')}
                  </span>
                  {s.text}
                </button>
              );
            })}
          </div>
        ) : (
          <p className="text-[15px] text-text whitespace-pre-wrap leading-relaxed">{lecture.transcript_text}</p>
        )}
      </div>
    </div>
  );
}

// ----------------------------------------------------------------- Notes
function NotesTab({ id, initial }: { id: string; initial: string | null }) {
  const [notes, setNotes] = useState(initial ?? '');
  const [streaming, setStreaming] = useState(false);
  const [err, setErr] = useState('');
  const gen = (refresh = false) => {
    setStreaming(true); setErr(''); setNotes('');
    api.notesStream(id, (delta) => setNotes((n) => n + delta), refresh)
      .catch((e) => setErr(e.message))
      .finally(() => setStreaming(false));
  };
  useEffect(() => { if (!initial) gen(); }, []); // auto-generate first time
  if (streaming && !notes) return <Spinner label="Generating study notes…" />;
  if (err) return <div className="space-y-3"><ErrorBox msg={err} /><button className={btn} onClick={() => gen()}>Retry</button></div>;
  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <button className={btnGhost} onClick={() => gen(true)} disabled={streaming}>
          <RefreshCw className="w-3.5 h-3.5" /> Regenerate
        </button>
      </div>
      <div className={card}><pre className="whitespace-pre-wrap font-sans text-[15px] text-text leading-relaxed">{notes}</pre></div>
    </div>
  );
}

// ----------------------------------------------------------------- Recap
function RecapTab({ id, initialScript, initialAudioUrl }: { id: string; initialScript: string | null; initialAudioUrl: string | null }) {
  const [script, setScript] = useState(initialScript);
  const [audioUrl, setAudioUrl] = useState(initialAudioUrl);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');

  const gen = (refresh = false) => {
    setLoading(true); setErr('');
    api.recap(id, refresh)
      .then((r) => { setScript(r.script); setAudioUrl(r.audio_url); })
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false));
  };

  if (loading) return <Spinner label="Writing and narrating your recap…" />;
  if (err) return <div className="space-y-3"><ErrorBox msg={err} /><button className={btn} onClick={() => gen()}>Retry</button></div>;

  if (!script || !audioUrl) {
    return (
      <div className={`${card} max-w-md text-center space-y-4 py-10 mx-auto`}>
        <div className="w-12 h-12 rounded-full bg-primary-light flex items-center justify-center mx-auto">
          <Headphones className="w-5 h-5 text-primary" />
        </div>
        <div>
          <p className="font-serif font-semibold text-text text-lg mb-1">Listen to a recap</p>
          <p className="text-sm text-muted">A short, spoken-style summary of this lecture — about a minute of narrated audio.</p>
        </div>
        <button className={btn} onClick={() => gen()}>
          <Headphones className="w-4 h-4" /> Generate audio recap
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className={`${card} space-y-3`}>
        <div className="flex items-center gap-2">
          <Headphones className="w-3.5 h-3.5 text-primary" />
          <span className="text-sm font-medium text-text">Audio recap</span>
        </div>
        <audio controls className="w-full" src={buildUrl(audioUrl)} />
      </div>
      <div className={card}>
        <p className="text-[15px] text-text leading-relaxed">{script}</p>
      </div>
      <div className="flex justify-end">
        <button className={btnGhost} onClick={() => gen(true)}>
          <RefreshCw className="w-3.5 h-3.5" /> Regenerate
        </button>
      </div>
    </div>
  );
}

// ----------------------------------------------------------------- Quiz
function QuizTab({ id, initial, initialQuizId }: { id: string; initial: QuizQuestion[] | null; initialQuizId: string | null }) {
  const [quiz, setQuiz] = useState<QuizQuestion[] | null>(initial);
  // Quiz is a real, versioned entity now (quiz_repository.py) — track which
  // version is on screen so grading targets it exactly, even if a newer quiz
  // gets generated (e.g. in another tab) before this one is submitted.
  const [quizId, setQuizId] = useState<string | null>(initialQuizId);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');
  // question_id -> selected answer_id
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<GradeResult | null>(null);
  const gen = (refresh = false) => {
    setLoading(true); setErr(''); setResult(null); setAnswers({});
    api.quiz(id, 5, refresh).then((r) => { setQuiz(r.quiz); setQuizId(r.quiz_id); }).catch((e) => setErr(e.message)).finally(() => setLoading(false));
  };
  useEffect(() => { if (!initial) gen(); }, []);
  const submit = () => {
    const arr = (quiz || []).map((q) => answers[q.question_id] ?? null);
    api.gradeQuiz(id, arr, quizId ?? undefined).then(setResult).catch((e) => setErr(e.message));
  };
  if (loading) return <Spinner label="Writing a quiz from this lecture…" />;
  if (err) return <div className="space-y-3"><ErrorBox msg={err} /><button className={btn} onClick={() => gen()}>Retry</button></div>;
  if (!quiz?.length) return <p className="text-muted text-sm">No quiz available.</p>;
  const answeredCount = Object.keys(answers).length;
  return (
    <div className="space-y-4">
      {result && (
        <div className={`${card} flex items-center gap-5`}>
          <div className="relative w-16 h-16 shrink-0">
            <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="42" fill="none" stroke="var(--color-surface2)" strokeWidth="10" />
              <circle cx="50" cy="50" r="42" fill="none" stroke={result.score >= 70 ? 'var(--color-primary)' : 'var(--color-accent)'} strokeWidth="10" strokeDasharray={`${result.score * 2.64} 264`} />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center text-sm font-bold text-text">{Math.round(result.score)}%</div>
          </div>
          <div className="flex-1">
            <p className="font-serif font-semibold text-lg text-text">{result.correct} of {result.total} correct</p>
            <p className="text-sm text-muted">{result.score >= 70 ? 'Nice work — you know this material.' : 'Review the explanations below, then try a new quiz.'}</p>
          </div>
          <button className={btnGhost} onClick={() => gen(true)}>
            <RefreshCw className="w-3.5 h-3.5" /> New quiz
          </button>
        </div>
      )}
      {quiz.map((q, qi) => {
        return (
          <div key={q.question_id} className={card}>
            <p className="font-medium text-text mb-3.5">{qi + 1}. {q.question}</p>
            <div className="space-y-2">
              {q.answers.map((a) => {
                const picked = answers[q.question_id] === a.answer_id;
                let cls = 'bg-surface2 hover:bg-primary-light/60';
                if (result) {
                  if (a.is_correct) cls = 'bg-primary-light text-primary-dark';
                  else if (picked) cls = 'bg-accent-light text-accent2';
                  else cls = 'bg-surface2 opacity-50';
                }
                return (
                  <button key={a.answer_id} disabled={!!result}
                    onClick={() => setAnswers({ ...answers, [q.question_id]: a.answer_id })}
                    className={`w-full text-left px-4 py-2.5 rounded-lg text-sm transition-colors flex items-center justify-between gap-2 ${picked && !result ? 'bg-primary text-white font-medium' : cls}`}>
                    {a.text}
                    {result && a.is_correct && <CheckCircle2 className="w-4 h-4 shrink-0" />}
                    {result && picked && !a.is_correct && <XCircle className="w-4 h-4 shrink-0" />}
                  </button>
                );
              })}
            </div>
            {result && <p className="text-xs text-muted mt-3 leading-relaxed">{q.explanation}</p>}
          </div>
        );
      })}
      {!result && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-muted">{answeredCount} of {quiz.length} answered</p>
          <button className={btn} onClick={submit} disabled={answeredCount < quiz.length}>Submit answers</button>
        </div>
      )}
    </div>
  );
}

// ----------------------------------------------------------------- Schedule (StudyPlan)
function ScheduleTab({ id, initial, initialReviewState }: { id: string; initial: Schedule | null; initialReviewState: ReviewState | null }) {
  const [sch, setSch] = useState<Schedule | null>(initial);
  const [reviewState, setReviewState] = useState<ReviewState | null>(initialReviewState);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');
  const [availableTime, setAvailableTime] = useState(initial?.available_time || '');
  const [learningGoals, setLearningGoals] = useState(initial?.learning_goals || '');

  const gen = (refresh = false) => {
    setLoading(true); setErr('');
    api.schedule(id, 7, refresh, availableTime || undefined, learningGoals || undefined)
      .then((r) => { setSch(r.schedule); setReviewState(r.review_state); })
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false));
  };

  if (loading) return <Spinner label="Building your study plan…" />;
  if (err) return <div className="space-y-3"><ErrorBox msg={err} /><button className={btn} onClick={() => gen()}>Retry</button></div>;

  // No plan yet — collect the real inputs the plan should be built around
  // (StudyPlan.available_time / StudyPlan.learning_goals) before generating.
  if (!sch?.plan) {
    return (
      <div className={`${card} max-w-lg space-y-5`}>
        <div className="flex items-center gap-2 text-text font-serif font-semibold text-lg">
          <Sparkle className="w-4 h-4 text-primary" /> Personalize your plan
        </div>
        <div>
          <label className="text-sm font-medium text-text block mb-1.5">How much time do you have?</label>
          <input
            value={availableTime}
            onChange={(e) => setAvailableTime(e.target.value)}
            placeholder="e.g. 1 hour per day"
            className="w-full px-3.5 py-2.5 rounded-lg border border-border bg-surface text-sm outline-none focus:border-primary transition-colors"
          />
        </div>
        <div>
          <label className="text-sm font-medium text-text block mb-1.5">What are your learning goals?</label>
          <textarea
            value={learningGoals}
            onChange={(e) => setLearningGoals(e.target.value)}
            placeholder="e.g. understand this well enough for my midterm"
            rows={2}
            className="w-full px-3.5 py-2.5 rounded-lg border border-border bg-surface text-sm outline-none focus:border-primary resize-none transition-colors"
          />
        </div>
        <button className={btn} onClick={() => gen()}>Build my study plan</button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {(sch.available_time || sch.learning_goals) && (
        <div className={`${card} text-sm text-muted flex flex-wrap gap-x-5 gap-y-1`}>
          {sch.available_time && <span className="inline-flex items-center gap-1.5"><Clock className="w-3.5 h-3.5" /> {sch.available_time}</span>}
          {sch.learning_goals && <span className="inline-flex items-center gap-1.5"><Sparkle className="w-3.5 h-3.5" /> {sch.learning_goals}</span>}
        </div>
      )}
      {reviewState && reviewState.attempts_considered > 0 && reviewState.next_review_at != null && (
        <div className={`${card} text-sm text-muted flex items-center gap-1.5`}>
          <CalendarDays className="w-3.5 h-3.5 text-primary shrink-0" />
          <span>
            <span className="text-text font-medium">
              Next review: {new Date(reviewState.next_review_at * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
            </span>
            {' '}— spaced repetition suggests {reviewState.interval_days} day{reviewState.interval_days === 1 ? '' : 's'} after
            your last quiz ({reviewState.repetition_count} good review{reviewState.repetition_count === 1 ? '' : 's'} in a row).
          </span>
        </div>
      )}
      <div className="grid sm:grid-cols-2 gap-3">
        {sch.plan.map((d) => (
          <div key={d.day} className={card}>
            <div className="flex justify-between items-baseline mb-2.5">
              <p className="font-serif font-semibold text-text">Day {d.day} · {d.focus}</p>
              <span className="text-xs text-muted shrink-0 ml-2">{d.est_minutes} min</span>
            </div>
            <ul className="space-y-1.5">
              {d.tasks?.map((t, i) => (
                <li key={i} className="text-sm text-muted flex items-start gap-2">
                  <span className="w-1 h-1 rounded-full bg-primary mt-2 shrink-0" /> {t}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      {sch.tips?.length > 0 && (
        <div className={card}>
          <p className="font-serif font-semibold text-text mb-2.5 flex items-center gap-1.5"><Sparkle className="w-4 h-4 text-primary" /> Tips</p>
          <ul className="space-y-1.5">
            {sch.tips.map((t, i) => (
              <li key={i} className="text-sm text-muted flex items-start gap-2">
                <span className="w-1 h-1 rounded-full bg-primary mt-2 shrink-0" /> {t}
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="flex justify-end">
        <button className={btnGhost} onClick={() => gen(true)}>
          <RefreshCw className="w-3.5 h-3.5" /> Rebuild plan
        </button>
      </div>
    </div>
  );
}

// ----------------------------------------------------------------- Evaluation
function EvaluationTab({ id, initial }: { id: string; initial: Evaluation | null }) {
  const [ev, setEv] = useState<Evaluation | null>(initial);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');
  const gen = (refresh = false) => {
    setLoading(true); setErr('');
    api.evaluate(id, refresh).then((r) => setEv(r.evaluation)).catch((e) => setErr(e.message)).finally(() => setLoading(false));
  };
  useEffect(() => { if (!initial) gen(); }, []);
  if (loading) return <Spinner label="Analyzing lecture difficulty and topics…" />;
  if (err) return <div className="space-y-3"><ErrorBox msg={err} /><button className={btn} onClick={() => gen()}>Retry</button></div>;
  if (!ev) return <p className="text-muted text-sm">No analysis.</p>;
  return (
    <div className="space-y-3">
      <div className="grid sm:grid-cols-2 gap-6 pb-6 border-b border-border">
        <div>
          <p className="label-caps text-muted mb-1.5">Difficulty</p>
          <p className="font-serif text-text font-semibold text-2xl capitalize">{ev.difficulty}</p>
        </div>
        <div>
          <p className="label-caps text-muted mb-1.5">Est. study time</p>
          <p className="font-serif text-text font-semibold text-2xl">{ev.estimated_study_minutes} min</p>
        </div>
      </div>
      <div className={card}><p className="font-serif font-semibold text-lg text-text mb-2">Summary</p><p className="text-[15px] text-muted leading-relaxed">{ev.summary}</p></div>
      <div className={card}>
        <p className="font-serif font-semibold text-lg text-text mb-2.5">Main topics</p>
        <div className="flex flex-wrap gap-2">{ev.main_topics?.map((t, i) => <span key={i} className="text-xs px-2.5 py-1.5 rounded-full bg-primary-light text-primary-dark font-medium">{t}</span>)}</div>
      </div>
      {ev.comprehension_questions?.length > 0 && (
        <div className={card}>
          <p className="font-serif font-semibold text-lg text-text mb-2.5">Check your understanding</p>
          <ul className="space-y-1.5">
            {ev.comprehension_questions.map((q, i) => (
              <li key={i} className="text-sm text-muted flex items-start gap-2">
                <span className="w-1 h-1 rounded-full bg-primary mt-2 shrink-0" /> {q}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ----------------------------------------------------------------- Chat
function ChatTab({ id, history }: { id: string; history: { question: string; answer: string }[] }) {
  const [msgs, setMsgs] = useState<{ role: 'user' | 'ai'; text: string }[]>(
    history.flatMap((h) => [{ role: 'user' as const, text: h.question }, { role: 'ai' as const, text: h.answer }]),
  );
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const appendToLastMsg = (delta: string) => {
    setMsgs((m) => {
      const next = [...m];
      next[next.length - 1] = { role: 'ai', text: next[next.length - 1].text + delta };
      return next;
    });
  };
  const send = async () => {
    const q = input.trim();
    if (!q || busy) return;
    setInput('');
    setMsgs((m) => [...m, { role: 'user', text: q }, { role: 'ai', text: '' }]);
    setBusy(true);
    try {
      await api.chatStream(id, q, appendToLastMsg);
    } catch (e: any) {
      setMsgs((m) => {
        const next = [...m];
        next[next.length - 1] = { role: 'ai', text: `⚠️ ${e.message}` };
        return next;
      });
    } finally { setBusy(false); }
  };
  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <Link to="/app/chat" className={btnGhost}>
          <MessageSquare className="w-3.5 h-3.5" /> Chat with a different lecture
        </Link>
      </div>
      <div className={`${card} min-h-[40vh] max-h-[55vh] overflow-y-auto space-y-4`}>
        {msgs.length === 0 && (
          <div className="text-center py-12">
            <div className="w-11 h-11 rounded-full bg-primary-light flex items-center justify-center mx-auto mb-3">
              <Sparkles className="w-5 h-5 text-primary" />
            </div>
            <p className="text-muted text-sm">Ask anything about this lecture — answers are grounded in the transcript.</p>
          </div>
        )}
        {msgs.map((m, i) =>
          m.role === 'user' ? (
            <p key={i} className="label-caps text-muted">{m.text}</p>
          ) : (
            <div key={i}>
              <p className="label-caps text-primary mb-1.5">Lectra</p>
              <p className="text-[15px] text-text leading-relaxed">{m.text}</p>
            </div>
          ),
        )}
        {busy && msgs[msgs.length - 1]?.text === '' && <Spinner label="Thinking…" />}
      </div>
      <div className="flex gap-2">
        <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder="Ask a question…" className="flex-1 px-4 py-2.5 rounded-lg border border-border bg-surface text-text text-sm outline-none focus:border-primary transition-colors" />
        <button className={`${btn} px-4`} onClick={send} disabled={busy}><Send className="w-4 h-4" /></button>
      </div>
    </div>
  );
}
