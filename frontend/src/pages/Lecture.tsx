import React, { useEffect, useState } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import {
  FileText, NotebookPen, HelpCircle, CalendarDays, BarChart3, MessageSquare,
  Loader2, AlertCircle, RefreshCw, Send, CheckCircle2, XCircle, ArrowLeft,
} from 'lucide-react';
import {
  api, buildUrl, type Lecture as LectureT, type QuizQuestion, type GradeResult,
  type Schedule, type Evaluation, type ChatResponse,
} from '../lib/api';

type Tab = 'transcript' | 'notes' | 'quiz' | 'schedule' | 'evaluation' | 'chat';
const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: 'transcript', label: 'Transcript', icon: <FileText className="w-4 h-4" /> },
  { id: 'notes', label: 'Notes', icon: <NotebookPen className="w-4 h-4" /> },
  { id: 'quiz', label: 'Quiz', icon: <HelpCircle className="w-4 h-4" /> },
  { id: 'schedule', label: 'Schedule', icon: <CalendarDays className="w-4 h-4" /> },
  { id: 'evaluation', label: 'Evaluation', icon: <BarChart3 className="w-4 h-4" /> },
  { id: 'chat', label: 'Chat', icon: <MessageSquare className="w-4 h-4" /> },
];

const card = 'rounded-xl border border-border bg-surface p-5';
const btn = 'inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-dark disabled:opacity-50';

function Spinner({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 text-muted text-sm py-8 justify-center">
      <Loader2 className="w-4 h-4 animate-spin" /> {label}
    </div>
  );
}

function ErrorBox({ msg }: { msg: string }) {
  const isLLM = /not configured|credits|402|503/i.test(msg);
  return (
    <div className="flex items-start gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 p-4 text-sm">
      <AlertCircle className="w-5 h-5 text-amber-500 shrink-0" />
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

  if (loading) return <div className="p-8"><Spinner label="Loading lecture…" /></div>;
  if (err || !lecture) return <div className="p-8"><ErrorBox msg={err || 'Lecture not found'} /></div>;

  return (
    <div className="max-w-4xl mx-auto p-6">
      <Link to="/app/library" className="inline-flex items-center gap-1 text-sm text-muted hover:text-text mb-4">
        <ArrowLeft className="w-4 h-4" /> Library
      </Link>
      <h1 className="text-2xl font-bold text-text mb-1">{lecture.title}</h1>
      <p className="text-sm text-muted mb-5">
        {lecture.transcript_text.split(/\s+/).length} words
        {lecture.metadata?.duration_processed ? ` · ${Math.round(lecture.metadata.duration_processed)}s audio` : ''}
      </p>

      <div className="flex flex-wrap gap-1 border-b border-border mb-5">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => selectTab(t.id)}
            className={`flex items-center gap-1.5 px-3 py-2 text-sm border-b-2 -mb-px transition ${
              tab === t.id ? 'border-primary text-primary font-medium' : 'border-transparent text-muted hover:text-text'
            }`}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {tab === 'transcript' && <TranscriptTab lecture={lecture} />}
      {tab === 'notes' && <NotesTab id={id} initial={lecture.notes} />}
      {tab === 'quiz' && <QuizTab id={id} initial={lecture.quiz} />}
      {tab === 'schedule' && <ScheduleTab id={id} initial={lecture.schedule} />}
      {tab === 'evaluation' && <EvaluationTab id={id} initial={lecture.evaluation} />}
      {tab === 'chat' && <ChatTab id={id} history={lecture.chat_history} />}
    </div>
  );
}

// ----------------------------------------------------------------- Transcript
function TranscriptTab({ lecture }: { lecture: LectureT }) {
  const audio = lecture.metadata?.audio_url;
  return (
    <div className="space-y-4">
      {audio && (
        <div className={card}>
          <p className="text-sm font-medium text-text mb-2">Cleaned audio</p>
          <audio controls className="w-full" src={buildUrl(audio)} />
        </div>
      )}
      <div className={card}>
        {lecture.transcript_segments?.length ? (
          <div className="space-y-2 max-h-[60vh] overflow-y-auto">
            {lecture.transcript_segments.map((s, i) => (
              <p key={i} className="text-sm text-text">
                {s.speaker && <span className="text-primary font-medium mr-2">{s.speaker}</span>}
                <span className="text-muted font-mono text-xs mr-2">{Math.floor(s.start)}s</span>
                {s.text}
              </p>
            ))}
          </div>
        ) : (
          <p className="text-sm text-text whitespace-pre-wrap">{lecture.transcript_text}</p>
        )}
      </div>
    </div>
  );
}

// ----------------------------------------------------------------- Notes
function NotesTab({ id, initial }: { id: string; initial: string | null }) {
  const [notes, setNotes] = useState(initial);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');
  const gen = (refresh = false) => {
    setLoading(true); setErr('');
    api.notes(id, refresh).then((r) => setNotes(r.notes)).catch((e) => setErr(e.message)).finally(() => setLoading(false));
  };
  useEffect(() => { if (!initial) gen(); }, []); // auto-generate first time
  if (loading) return <Spinner label="Generating study notes…" />;
  if (err) return <div className="space-y-3"><ErrorBox msg={err} /><button className={btn} onClick={() => gen()}>Retry</button></div>;
  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <button className="text-sm text-muted hover:text-text inline-flex items-center gap-1" onClick={() => gen(true)}>
          <RefreshCw className="w-4 h-4" /> Regenerate
        </button>
      </div>
      <div className={card}><pre className="whitespace-pre-wrap font-sans text-sm text-text leading-relaxed">{notes}</pre></div>
    </div>
  );
}

// ----------------------------------------------------------------- Quiz
function QuizTab({ id, initial }: { id: string; initial: QuizQuestion[] | null }) {
  const [quiz, setQuiz] = useState<QuizQuestion[] | null>(initial);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [result, setResult] = useState<GradeResult | null>(null);
  const gen = (refresh = false) => {
    setLoading(true); setErr(''); setResult(null); setAnswers({});
    api.quiz(id, 5, refresh).then((r) => setQuiz(r.quiz)).catch((e) => setErr(e.message)).finally(() => setLoading(false));
  };
  useEffect(() => { if (!initial) gen(); }, []);
  const submit = () => {
    const arr = (quiz || []).map((_, i) => (answers[i] ?? -1));
    api.gradeQuiz(id, arr).then(setResult).catch((e) => setErr(e.message));
  };
  if (loading) return <Spinner label="Generating quiz…" />;
  if (err) return <div className="space-y-3"><ErrorBox msg={err} /><button className={btn} onClick={() => gen()}>Retry</button></div>;
  if (!quiz?.length) return <p className="text-muted text-sm">No quiz available.</p>;
  return (
    <div className="space-y-4">
      {quiz.map((q, qi) => {
        const correct = result?.breakdown[qi];
        return (
          <div key={qi} className={card}>
            <p className="font-medium text-text mb-3">{qi + 1}. {q.question}</p>
            <div className="space-y-2">
              {q.options.map((opt, oi) => {
                const picked = answers[qi] === oi;
                let cls = 'border-border hover:border-primary/50';
                if (result) {
                  if (oi === q.answer_index) cls = 'border-green-500 bg-green-500/10';
                  else if (picked) cls = 'border-red-500 bg-red-500/10';
                }
                return (
                  <button key={oi} disabled={!!result} onClick={() => setAnswers({ ...answers, [qi]: oi })}
                    className={`w-full text-left px-3 py-2 rounded-lg border text-sm transition ${picked && !result ? 'border-primary bg-primary/10' : cls}`}>
                    {opt}
                  </button>
                );
              })}
            </div>
            {result && <p className="text-xs text-muted mt-2">{q.explanation}</p>}
          </div>
        );
      })}
      {!result ? (
        <button className={btn} onClick={submit} disabled={Object.keys(answers).length < quiz.length}>Submit answers</button>
      ) : (
        <div className={`${card} flex items-center justify-between`}>
          <p className="text-lg font-bold text-text">Score: {result.score}% ({result.correct}/{result.total})</p>
          <button className="text-sm text-muted hover:text-text inline-flex items-center gap-1" onClick={() => gen(true)}>
            <RefreshCw className="w-4 h-4" /> New quiz
          </button>
        </div>
      )}
    </div>
  );
}

// ----------------------------------------------------------------- Schedule
function ScheduleTab({ id, initial }: { id: string; initial: Schedule | null }) {
  const [sch, setSch] = useState<Schedule | null>(initial);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');
  const gen = (refresh = false) => {
    setLoading(true); setErr('');
    api.schedule(id, 7, refresh).then((r) => setSch(r.schedule)).catch((e) => setErr(e.message)).finally(() => setLoading(false));
  };
  useEffect(() => { if (!initial) gen(); }, []);
  if (loading) return <Spinner label="Building study plan…" />;
  if (err) return <div className="space-y-3"><ErrorBox msg={err} /><button className={btn} onClick={() => gen()}>Retry</button></div>;
  if (!sch?.plan) return <p className="text-muted text-sm">No schedule.</p>;
  return (
    <div className="space-y-3">
      {sch.plan.map((d) => (
        <div key={d.day} className={card}>
          <div className="flex justify-between items-center mb-2">
            <p className="font-medium text-text">Day {d.day} — {d.focus}</p>
            <span className="text-xs text-muted">{d.est_minutes} min</span>
          </div>
          <ul className="list-disc list-inside text-sm text-muted space-y-1">
            {d.tasks?.map((t, i) => <li key={i}>{t}</li>)}
          </ul>
        </div>
      ))}
      {sch.tips?.length > 0 && (
        <div className={card}>
          <p className="font-medium text-text mb-2">Tips</p>
          <ul className="list-disc list-inside text-sm text-muted space-y-1">{sch.tips.map((t, i) => <li key={i}>{t}</li>)}</ul>
        </div>
      )}
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
  if (loading) return <Spinner label="Analyzing lecture…" />;
  if (err) return <div className="space-y-3"><ErrorBox msg={err} /><button className={btn} onClick={() => gen()}>Retry</button></div>;
  if (!ev) return <p className="text-muted text-sm">No analysis.</p>;
  return (
    <div className="space-y-3">
      <div className={`${card} grid grid-cols-2 gap-4`}>
        <div><p className="text-xs text-muted">Difficulty</p><p className="text-text font-medium capitalize">{ev.difficulty}</p></div>
        <div><p className="text-xs text-muted">Est. study time</p><p className="text-text font-medium">{ev.estimated_study_minutes} min</p></div>
      </div>
      <div className={card}><p className="font-medium text-text mb-2">Summary</p><p className="text-sm text-muted">{ev.summary}</p></div>
      <div className={card}>
        <p className="font-medium text-text mb-2">Main topics</p>
        <div className="flex flex-wrap gap-2">{ev.main_topics?.map((t, i) => <span key={i} className="text-xs px-2 py-1 rounded-full bg-surface2 text-text border border-border">{t}</span>)}</div>
      </div>
      {ev.comprehension_questions?.length > 0 && (
        <div className={card}>
          <p className="font-medium text-text mb-2">Check your understanding</p>
          <ul className="list-disc list-inside text-sm text-muted space-y-1">{ev.comprehension_questions.map((q, i) => <li key={i}>{q}</li>)}</ul>
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
  const send = async () => {
    const q = input.trim();
    if (!q || busy) return;
    setInput(''); setMsgs((m) => [...m, { role: 'user', text: q }]); setBusy(true);
    try {
      const r: ChatResponse = await api.chat(id, q);
      setMsgs((m) => [...m, { role: 'ai', text: r.answer }]);
    } catch (e: any) {
      setMsgs((m) => [...m, { role: 'ai', text: `⚠️ ${e.message}` }]);
    } finally { setBusy(false); }
  };
  return (
    <div className="space-y-3">
      <div className={`${card} min-h-[40vh] max-h-[55vh] overflow-y-auto space-y-3`}>
        {msgs.length === 0 && <p className="text-muted text-sm text-center py-8">Ask anything about this lecture.</p>}
        {msgs.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] px-3 py-2 rounded-lg text-sm ${m.role === 'user' ? 'bg-primary text-white' : 'bg-surface2 text-text border border-border'}`}>
              {m.text}
            </div>
          </div>
        ))}
        {busy && <Spinner label="Thinking…" />}
      </div>
      <div className="flex gap-2">
        <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder="Ask a question…" className="flex-1 px-3 py-2 rounded-lg border border-border bg-surface text-text text-sm outline-none focus:border-primary" />
        <button className={btn} onClick={send} disabled={busy}><Send className="w-4 h-4" /></button>
      </div>
    </div>
  );
}
