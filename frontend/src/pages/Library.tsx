import { useEffect, useState, type ReactNode, type MouseEvent } from 'react';
import { Link } from 'react-router-dom';
import { Search, UploadCloud, FileText, HelpCircle, NotebookPen, Loader2, Trash2 } from 'lucide-react';
import { api, type LectureSummary } from '../lib/api';

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
    <div className="max-w-7xl mx-auto px-6 py-12">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-4xl font-bold tracking-tight">Smart Lecture Library</h1>
        <Link to="/app/upload" className="bg-primary hover:bg-primary-dark text-white px-6 py-2 rounded-lg font-bold transition-colors shadow-sm inline-flex items-center gap-2">
          <UploadCloud className="w-5 h-5" /> Upload New
        </Link>
      </div>

      <div className="relative mb-8">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-muted w-5 h-5" />
        <input value={q} onChange={(e) => setQ(e.target.value)} type="text" placeholder="Search lectures…"
          className="w-full pl-12 pr-4 py-3 rounded-xl border border-border bg-surface focus:border-primary outline-none shadow-sm transition-colors" />
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-muted justify-center py-16"><Loader2 className="w-5 h-5 animate-spin" /> Loading…</div>
      ) : err ? (
        <p className="text-center text-muted py-16">{err}</p>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-muted mb-4">No lectures yet. Upload one to get started.</p>
          <Link to="/app/upload" className="bg-primary hover:bg-primary-dark text-white px-6 py-3 rounded-lg font-bold inline-flex items-center gap-2">
            <UploadCloud className="w-5 h-5" /> Upload a lecture
          </Link>
        </div>
      ) : (
        <div className="grid md:grid-cols-3 gap-6">
          {filtered.map((l) => (
            <Link key={l.id} to={`/app/lecture/${l.id}`}
              className="group rounded-xl border border-border bg-surface p-5 hover:border-primary/50 hover:shadow-md transition relative">
              <button onClick={(e) => remove(l.id, e)} title="Delete"
                className="absolute top-3 right-3 text-muted hover:text-red-500 opacity-0 group-hover:opacity-100 transition">
                <Trash2 className="w-4 h-4" />
              </button>
              <h3 className="font-bold text-text mb-1 pr-6 line-clamp-2">{l.title}</h3>
              <p className="text-xs text-muted mb-4">
                {l.word_count} words · {new Date((l.created_at || 0) * 1000).toLocaleDateString()}
              </p>
              <div className="flex flex-wrap gap-2">
                <Badge on={l.has_notes} icon={<NotebookPen className="w-3 h-3" />} label="Notes" />
                <Badge on={l.has_quiz} icon={<HelpCircle className="w-3 h-3" />} label="Quiz" />
                <Badge on={l.has_evaluation} icon={<FileText className="w-3 h-3" />} label="Analysis" />
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
    <span className={`inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-full border ${on ? 'border-primary/40 text-primary bg-primary/10' : 'border-border text-muted'}`}>
      {icon} {label}
    </span>
  );
}
