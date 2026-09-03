import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, Send, Sparkles, UploadCloud } from 'lucide-react';
import { api, type ChatResponse, type LectureSummary } from '../lib/api';

type Msg = { role: 'user' | 'ai'; text: string };

export function Chat() {
  const [lectures, setLectures] = useState<LectureSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);

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
    const q = input.trim();
    if (!q || busy || !selectedId) return;
    setInput('');
    setMsgs((m) => [...m, { role: 'user', text: q }]);
    setBusy(true);
    try {
      const r: ChatResponse = await api.chat(selectedId, q);
      setMsgs((m) => [...m, { role: 'ai', text: r.answer }]);
    } catch (e: any) {
      setMsgs((m) => [...m, { role: 'ai', text: `⚠️ ${e.message}` }]);
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
          <div className="space-y-1 md:sticky md:top-6 md:self-start">
            {lectures.map((l) => (
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
            ))}
          </div>

          {/* Conversation */}
          <div className="rounded-lg bg-surface p-6 flex flex-col">
            {selected && (
              <div className="mb-5 pb-5 border-b border-border">
                <h2 className="font-serif text-xl font-semibold text-text">{selected.title}</h2>
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
              {busy && (
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
