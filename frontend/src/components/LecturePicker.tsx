import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, Search, UploadCloud, ChevronRight } from 'lucide-react';
import { api, type LectureSummary } from '../lib/api';
import { Reveal, StaggerGroup, StaggerItem } from './Reveal';

/** Lists lectures and routes the user into the lecture hub at a specific tab. */
export function LecturePicker({ title, subtitle, tab }: { title: string; subtitle: string; tab: string }) {
  const [lectures, setLectures] = useState<LectureSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState('');

  useEffect(() => {
    api.library().then((r) => setLectures(r.lectures)).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const filtered = lectures.filter((l) => l.title.toLowerCase().includes(q.toLowerCase()));

  return (
    <div className="max-w-2xl mx-auto px-8 sm:px-10 py-10 md:pl-6">
      <Reveal className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between mb-9">
        <div>
          <h1 className="font-serif text-4xl font-semibold tracking-tight text-text mb-2">{title}</h1>
          <p className="text-muted text-sm">{subtitle}</p>
        </div>
        <Link
          to="/app/upload"
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary-dark transition-colors shrink-0"
        >
          <UploadCloud className="w-4 h-4" /> Upload new
        </Link>
      </Reveal>

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
        <>
          {lectures.length > 4 && (
            <div className="relative mb-4">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted w-4 h-4" />
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search lectures…"
                className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-border bg-surface text-sm outline-none focus:border-primary transition-colors"
              />
            </div>
          )}
          {filtered.length === 0 ? (
            <p className="text-muted text-sm py-8 text-center">No lectures match "{q}".</p>
          ) : (
            <StaggerGroup className="divide-y divide-border">
              {filtered.map((l) => (
                <StaggerItem key={l.id}>
                  <Link to={`/app/lecture/${l.id}?tab=${tab}`}
                    className="flex items-center justify-between gap-3 py-4 px-3 -mx-3 rounded-lg group hover:bg-surface transition-colors">
                    <div className="min-w-0">
                      <p className="font-serif font-semibold text-text truncate group-hover:text-primary transition-colors">{l.title}</p>
                      <p className="text-xs text-muted mt-0.5">{l.word_count.toLocaleString()} words · {new Date((l.created_at || 0) * 1000).toLocaleDateString()}</p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-muted shrink-0 transition-transform group-hover:translate-x-0.5" />
                  </Link>
                </StaggerItem>
              ))}
            </StaggerGroup>
          )}
        </>
      )}
    </div>
  );
}
