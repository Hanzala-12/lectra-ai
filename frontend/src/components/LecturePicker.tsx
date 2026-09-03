import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, UploadCloud, ChevronRight, Mic } from 'lucide-react';
import { api, type LectureSummary } from '../lib/api';

/** Lists lectures and routes the user into the lecture hub at a specific tab. */
export function LecturePicker({ title, subtitle, tab }: { title: string; subtitle: string; tab: string }) {
  const [lectures, setLectures] = useState<LectureSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.library().then((r) => setLectures(r.lectures)).catch(() => {}).finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-2xl mx-auto px-6 py-12 md:pl-2">
      <h1 className="text-3xl font-bold tracking-tight text-text mb-1.5">{title}</h1>
      <p className="text-muted mb-8">{subtitle}</p>

      {loading ? (
        <div className="flex items-center gap-2 text-muted justify-center py-16"><Loader2 className="w-5 h-5 animate-spin" /> Loading…</div>
      ) : lectures.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border2 bg-surface p-10 text-center shadow-soft">
          <div className="w-14 h-14 rounded-2xl bg-primary-light flex items-center justify-center mx-auto mb-4">
            <Mic className="w-6 h-6 text-primary" />
          </div>
          <p className="text-muted mb-5">No lectures yet — upload one first.</p>
          <Link to="/app/upload" className="bg-primary hover:bg-primary-dark text-white px-6 py-3 rounded-xl font-semibold inline-flex items-center gap-2 shadow-soft">
            <UploadCloud className="w-4 h-4" /> Upload a lecture
          </Link>
        </div>
      ) : (
        <div className="space-y-2.5">
          {lectures.map((l) => (
            <Link key={l.id} to={`/app/lecture/${l.id}?tab=${tab}`}
              className="flex items-center justify-between gap-3 rounded-2xl border border-border bg-surface p-4 shadow-soft hover:border-primary/30 hover:shadow-soft-lg hover:-translate-y-0.5 transition-all">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-10 h-10 rounded-xl bg-primary-light flex items-center justify-center shrink-0">
                  <Mic className="w-4 h-4 text-primary" />
                </div>
                <div className="min-w-0">
                  <p className="font-medium text-text truncate">{l.title}</p>
                  <p className="text-xs text-muted">{l.word_count} words · {new Date((l.created_at || 0) * 1000).toLocaleDateString()}</p>
                </div>
              </div>
              <ChevronRight className="w-5 h-5 text-muted shrink-0" />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
