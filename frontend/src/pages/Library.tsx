import { useEffect, useState, type MouseEvent } from 'react';
import { Link } from 'react-router-dom';
import { Search, UploadCloud, Loader2, Trash2, Mic } from 'lucide-react';
import { api, type LectureSummary } from '../lib/api';

function formatDuration(seconds?: number) {
  if (!seconds) return null;
  const mins = Math.max(1, Math.round(seconds / 60));
  return `${mins}m`;
}

export function Library() {
  const [lectures, setLectures] = useState<LectureSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');
  const [q, setQ] = useState('');

  const load = () => {
    setLoading(true);
    api.library().then((r) => setLectures(r.lectures)).catch((e) => setErr(e.message)).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const remove = async (id: string, e: MouseEvent) => {
    e.preventDefault();
    if (!confirm('Delete this lecture?')) return;
    await api.deleteLecture(id).catch(() => {});
    load();
  };

  const filtered = lectures.filter((l) => l.title.toLowerCase().includes(q.toLowerCase()));

  return (
    <div className="max-w-6xl mx-auto px-8 sm:px-10 py-10 md:pl-6">
      <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between mb-8">
        <div>
          <h1 className="font-serif text-4xl font-semibold tracking-tight text-text mb-2">Lecture library</h1>
          <p className="text-sm text-muted">{lectures.length} lecture{lectures.length === 1 ? '' : 's'} in your workspace</p>
        </div>
        <Link
          to="/app/upload"
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-white hover:bg-primary-dark transition-colors shrink-0"
        >
          <UploadCloud className="w-4 h-4" /> Upload new
        </Link>
      </div>

      <div className="relative mb-9 max-w-sm">
        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted w-4 h-4" />
        <input value={q} onChange={(e) => setQ(e.target.value)} type="text" placeholder="Search lectures…"
          className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-border bg-surface focus:border-primary outline-none transition-colors text-sm" />
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-muted justify-center py-16"><Loader2 className="w-5 h-5 animate-spin" /> Loading…</div>
      ) : err ? (
        <p className="text-center text-muted py-16">{err}</p>
      ) : filtered.length === 0 && q ? (
        <div className="text-center py-16">
          <p className="text-muted">No lectures match "{q}".</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border2 bg-surface p-12 text-center">
          <div className="w-14 h-14 rounded-full bg-primary-light flex items-center justify-center mx-auto mb-5">
            <Mic className="w-6 h-6 text-primary" />
          </div>
          <p className="text-muted mb-5">No lectures yet. Upload one to get started.</p>
          <Link to="/app/upload" className="bg-primary hover:bg-primary-dark text-white px-6 py-3 rounded-lg font-semibold inline-flex items-center gap-2">
            <UploadCloud className="w-4 h-4" /> Upload a lecture
          </Link>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {filtered.map((l) => (
            <Link key={l.id} to={`/app/lecture/${l.id}`}
              className="group rounded-lg bg-surface p-5 hover:bg-primary-light/40 transition-colors relative flex flex-col">
              <button onClick={(e) => remove(l.id, e)} title="Delete"
                className="absolute top-4 right-4 text-muted hover:text-error opacity-0 group-hover:opacity-100 transition p-1 rounded">
                <Trash2 className="w-4 h-4" />
              </button>
              <p className="label-caps text-primary mb-2 pr-6">
                {formatDuration(l.duration) ? `${formatDuration(l.duration)} audio` : 'Lecture'}
              </p>
              <h3 className="font-serif font-semibold text-lg text-text mb-2 line-clamp-2 flex-1 pr-2">{l.title}</h3>
              <p className="text-xs text-muted mb-4">
                {l.word_count.toLocaleString()} words · {new Date((l.created_at || 0) * 1000).toLocaleDateString()}
              </p>
              <div className="flex flex-wrap gap-1.5">
                <Badge on={l.has_notes} label="Notes" tone="accent" />
                <Badge on={l.has_quiz} label="Quiz" tone="primary" />
                {l.best_score != null && <Badge on label={`Best ${Math.round(l.best_score)}%`} tone="accent" />}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function Badge({ on, label, tone }: { on: boolean; label: string; tone: 'primary' | 'accent' }) {
  if (!on) return null;
  const cls = tone === 'primary' ? 'bg-primary-light text-primary-dark' : 'bg-accent-light text-accent2';
  return <span className={`inline-flex items-center text-[11px] px-2.5 py-1 rounded-full font-medium ${cls}`}>{label}</span>;
}
