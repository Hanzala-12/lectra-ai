import { useEffect, useState, type ReactNode, type MouseEvent } from 'react';
import { Link } from 'react-router-dom';
import { Search, UploadCloud, HelpCircle, NotebookPen, Loader2, Trash2, Mic, Clock } from 'lucide-react';
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
    <div className="max-w-7xl mx-auto px-6 py-10 md:pl-2">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-text">Lecture Library</h1>
          <p className="text-sm text-muted mt-1">{lectures.length} lecture{lectures.length === 1 ? '' : 's'} in your workspace</p>
        </div>
        <Link
          to="/app/upload"
          className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-white shadow-soft hover:bg-primary-dark hover:shadow-soft-lg transition-all shrink-0"
        >
          <UploadCloud className="w-4 h-4" /> Upload new
        </Link>
      </div>

      <div className="relative mb-8">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-muted w-4 h-4" />
        <input value={q} onChange={(e) => setQ(e.target.value)} type="text" placeholder="Search lectures…"
          className="w-full pl-11 pr-4 py-3 rounded-xl border border-border bg-surface focus:border-primary focus:ring-4 focus:ring-primary/10 outline-none shadow-soft transition-all" />
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
        <div className="rounded-2xl border border-dashed border-border2 bg-surface p-12 text-center shadow-soft">
          <div className="w-16 h-16 rounded-2xl bg-primary-light flex items-center justify-center mx-auto mb-5">
            <Mic className="w-7 h-7 text-primary" />
          </div>
          <p className="text-muted mb-5">No lectures yet. Upload one to get started.</p>
          <Link to="/app/upload" className="bg-primary hover:bg-primary-dark text-white px-6 py-3 rounded-xl font-semibold inline-flex items-center gap-2 shadow-soft">
            <UploadCloud className="w-4 h-4" /> Upload a lecture
          </Link>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {filtered.map((l) => (
            <Link key={l.id} to={`/app/lecture/${l.id}`}
              className="group rounded-2xl border border-border bg-surface p-5 hover:border-primary/30 hover:shadow-soft-lg hover:-translate-y-0.5 transition-all relative shadow-soft flex flex-col">
              <div className="flex items-start justify-between mb-4">
                <div className="w-10 h-10 rounded-xl bg-primary-light flex items-center justify-center shrink-0">
                  <Mic className="w-5 h-5 text-primary" />
                </div>
                <button onClick={(e) => remove(l.id, e)} title="Delete"
                  className="text-muted hover:text-error opacity-0 group-hover:opacity-100 transition p-1.5 -m-1.5 rounded-lg hover:bg-error-light">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
              <h3 className="font-semibold text-text mb-1.5 line-clamp-2 flex-1">{l.title}</h3>
              <p className="text-xs text-muted mb-4 flex items-center gap-1.5 flex-wrap">
                {formatDuration(l.duration) && (
                  <span className="inline-flex items-center gap-1"><Clock className="w-3 h-3" /> {formatDuration(l.duration)}</span>
                )}
                <span>· {l.word_count} words</span>
                <span>· {new Date((l.created_at || 0) * 1000).toLocaleDateString()}</span>
              </p>
              <div className="flex flex-wrap gap-1.5">
                <Badge on={l.has_notes} icon={<NotebookPen className="w-3 h-3" />} label="Notes" />
                <Badge on={l.has_quiz} icon={<HelpCircle className="w-3 h-3" />} label="Quiz" />
                {l.best_score != null && (
                  <span className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-full bg-success-light text-success font-medium">
                    Best {Math.round(l.best_score)}%
                  </span>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function Badge({ on, icon, label }: { on: boolean; icon: ReactNode; label: string }) {
  return (
    <span className={`inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-full font-medium ${on ? 'text-primary bg-primary-light' : 'text-muted bg-surface2'}`}>
      {icon} {label}
    </span>
  );
}
