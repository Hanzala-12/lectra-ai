import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, Search, Send, Sparkles, UploadCloud } from 'lucide-react';
import { api, type LectureSummary } from '../lib/api';

type Msg = { role: 'user' | 'ai'; text: string };

export function Chat() {
  const [lectures, setLectures] = useState<LectureSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [q, setQ] = useState('');

  useEffect(() => {
    api.library().then((r) => {
      setLectures(r.lectures);
      if (r.lectures.length > 0) selectLecture(r.lectures[0].id);
    }).catch(() => {}).finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selectLecture = (id: string) => {
    setSelectedId(id);
    setMsgs([]);
    api.getLecture(id).then((lec) => {
      setMsgs(lec.chat_history.flatMap((h) => [
        { role: 'user' as const, text: h.question },
        { role: 'ai' as const, text: h.answer },
      ]));
    }).catch(() => {});
  };

  const send = async () => {
    const question = input.trim();
    if (!question || busy || !selectedId) return;
    setInput('');
    setMsgs((m) => [...m, { role: 'user', text: question }, { role: 'ai', text: '' }]);
    setBusy(true);
    try {
      await api.chatStream(selectedId, question, (delta) => {
        setMsgs((m) => {
          const next = [...m];
          next[next.length - 1] = { role: 'ai', text: next[next.length - 1].text + delta };
          return next;
        });
      });
    } catch (e: any) {
      setMsgs((m) => {
        const next = [...m];
        next[next.length - 1] = { role: 'ai', text: `⚠️ ${e.message}` };
        return next;
      });
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-20 text-muted">
        <Loader2 className="w-5 h-5 animate-spin" /> Loading…
      </div>
    );
  }

  const selected = lectures.find((l) => l.id === selectedId);
  const filtered = lectures.filter((l) => l.title.toLowerCase().includes(q.toLowerCase()));

  return (
    <div className="max-w-6xl mx-auto px-8 sm:px-10 py-10 md:pl-6">
      <div className="mb-8">
        <h1 className="font-serif text-4xl font-semibold tracking-tight text-text mb-2">Ask your lecture</h1>
        <p className="text-sm text-muted">Answers are grounded in the lecture's transcript.</p>
      </div>

      {lectures.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border2 bg-surface p-12 text-center">
          <div className="w-14 h-14 rounded-full bg-primary-light flex items-center justify-center mx-auto mb-5">
            <Sparkles className="w-6 h-6 text-primary" />
          </div>
          <p className="text-muted mb-5">No lectures yet — upload one first.</p>
          <Link to="/app/upload" className="bg-primary hover:bg-primary-dark text-white px-6 py-3 rounded-lg font-semibold inline-flex items-center gap-2">
            <UploadCloud className="w-4 h-4" /> Upload a lecture
          </Link>
        </div>
      ) : (
        <div className="grid md:grid-cols-[260px_1fr] gap-6">
          {/* Lecture list */}
          <div className="space-y-3 md:sticky md:top-6 md:self-start">
            {/* Always-visible entry point to add a new lecture without
                leaving Chat — processing still takes real minutes (the
                pipeline has to run), so this deep-links to the Upload flow
                rather than pretending to attach it instantly. */}
            <Link
              to="/app/upload"
              className="flex items-center gap-2 px-3.5 py-2.5 rounded-lg border border-dashed border-border2 text-sm font-medium text-muted hover:text-primary hover:border-primary/40 transition-colors"
            >
              <UploadCloud className="w-4 h-4 shrink-0" /> Upload a new lecture
            </Link>

            {lectures.length > 4 && (
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted w-3.5 h-3.5" />
                <input
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="Search lectures…"
                  className="w-full pl-9 pr-3 py-2 rounded-lg border border-border bg-surface text-sm outline-none focus:border-primary transition-colors"
                />
              </div>
            )}

            <div className="space-y-1">
              {filtered.length === 0 ? (
                <p className="text-xs text-muted px-3.5 py-2">No lectures match "{q}".</p>
              ) : (
                filtered.map((l) => (
                  <button
                    key={l.id}
                    onClick={() => selectLecture(l.id)}
                    className={`w-full text-left px-3.5 py-3 rounded-lg transition-colors ${
                      l.id === selectedId ? 'bg-primary-light' : 'hover:bg-surface2'
                    }`}
                  >
                    <p className={`text-sm font-serif font-semibold truncate ${l.id === selectedId ? 'text-primary-dark' : 'text-text'}`}>{l.title}</p>
                    <p className="text-xs text-muted mt-0.5">
                      {l.word_count.toLocaleString()} words · {new Date((l.created_at || 0) * 1000).toLocaleDateString()}
                    </p>
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Conversation */}
          <div className="rounded-lg bg-surface p-6 flex flex-col">
            {selected && (
              <div className="mb-5 pb-5 border-b border-border flex items-center justify-between gap-3">
                <h2 className="font-serif text-xl font-semibold text-text truncate">{selected.title}</h2>
                <Link to={`/app/lecture/${selected.id}`} className="text-xs font-medium text-primary hover:text-primary-dark shrink-0">
                  Open full workspace →
                </Link>
              </div>
            )}

            <div className="flex-1 min-h-[45vh] max-h-[55vh] overflow-y-auto space-y-5 mb-5">
              {msgs.length === 0 && (
                <div className="text-center py-12">
                  <p className="text-muted text-sm">Ask a question to get started.</p>
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
              {busy && msgs[msgs.length - 1]?.text === '' && (
                <div className="flex items-center gap-2 text-muted text-sm">
                  <Loader2 className="w-4 h-4 animate-spin" /> Thinking…
                </div>
              )}
            </div>

            <div className="flex gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && send()}
                placeholder="Ask a question about this lecture…"
                className="flex-1 px-4 py-2.5 rounded-lg border border-border bg-bg text-text text-sm outline-none focus:border-primary transition-colors"
              />
              <button
                onClick={send}
                disabled={busy || !selectedId}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-primary text-white text-sm font-semibold hover:bg-primary-dark disabled:opacity-50 transition-colors"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
