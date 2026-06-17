import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, UploadCloud, ChevronRight } from 'lucide-react';
import { api, type LectureSummary } from '../lib/api';

/** Lists lectures and routes the user into the lecture hub at a specific tab. */
export function LecturePicker({ title, subtitle, tab }: { title: string; subtitle: string; tab: string }) {
  const [lectures, setLectures] = useState<LectureSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.library().then((r) => setLectures(r.lectures)).catch(() => {}).finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-3xl mx-auto px-6 py-12">
      <h1 className="text-3xl font-bold tracking-tight mb-1">{title}</h1>
      <p className="text-muted mb-8">{subtitle}</p>

      {loading ? (
        <div className="flex items-center gap-2 text-muted justify-center py-16"><Loader2 className="w-5 h-5 animate-spin" /> Loading…</div>
      ) : lectures.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-muted mb-4">No lectures yet — upload one first.</p>
          <Link to="/app/upload" className="bg-primary hover:bg-primary-dark text-white px-6 py-3 rounded-lg font-bold inline-flex items-center gap-2">
            <UploadCloud className="w-5 h-5" /> Upload a lecture
          </Link>
        </div>
      ) : (
        <div className="space-y-2">
          {lectures.map((l) => (
            <Link key={l.id} to={`/app/lecture/${l.id}?tab=${tab}`}
              className="flex items-center justify-between rounded-xl border border-border bg-surface p-4 hover:border-primary/50 hover:shadow-md transition">
              <div>
                <p className="font-medium text-text">{l.title}</p>
                <p className="text-xs text-muted">{l.word_count} words · {new Date((l.created_at || 0) * 1000).toLocaleDateString()}</p>
              </div>
              <ChevronRight className="w-5 h-5 text-muted" />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
