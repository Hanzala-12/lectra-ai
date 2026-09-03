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
    <div className="max-w-2xl mx-auto px-8 sm:px-10 py-10 md:pl-6">
      <h1 className="font-serif text-4xl font-semibold tracking-tight text-text mb-2">{title}</h1>
      <p className="text-muted mb-9 text-sm">{subtitle}</p>

      {loading ? (
        <div className="flex items-center gap-2 text-muted justify-center py-16"><Loader2 className="w-5 h-5 animate-spin" /> Loading…</div>
      ) : lectures.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border2 bg-surface p-10 text-center">
          <div className="w-14 h-14 rounded-full bg-primary-light flex items-center justify-center mx-auto mb-4">
            <UploadCloud className="w-6 h-6 text-primary" />
          </div>
          <p className="text-muted mb-5">No lectures yet — upload one first.</p>
          <Link to="/app/upload" className="bg-primary hover:bg-primary-dark text-white px-6 py-3 rounded-lg font-semibold inline-flex items-center gap-2">
            <UploadCloud className="w-4 h-4" /> Upload a lecture
          </Link>
        </div>
      ) : (
        <div className="divide-y divide-border">
          {lectures.map((l) => (
            <Link key={l.id} to={`/app/lecture/${l.id}?tab=${tab}`}
              className="flex items-center justify-between gap-3 py-4 group">
              <div className="min-w-0">
                <p className="font-serif font-semibold text-text truncate group-hover:text-primary transition-colors">{l.title}</p>
                <p className="text-xs text-muted mt-0.5">{l.word_count.toLocaleString()} words · {new Date((l.created_at || 0) * 1000).toLocaleDateString()}</p>
              </div>
              <ChevronRight className="w-4 h-4 text-muted shrink-0" />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
