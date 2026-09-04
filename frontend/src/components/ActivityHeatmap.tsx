import type { LectureSummary } from '../lib/api';

/**
 * GitHub-style contribution heatmap, scoped honestly to what the dashboard
 * actually knows: lecture upload days (LectureSummary.created_at). It does
 * NOT claim to track quiz attempts or chat usage — LectureSummary only
 * carries a lifetime quiz_attempts count, not per-attempt dates, so folding
 * those in would mean guessing. If per-day quiz/chat activity becomes
 * available from the API later, extend `countsByDay` to merge those sources
 * too rather than widening the label without the data behind it.
 *
 * For a study app this isn't just decoration — spaced repetition (see
 * src/spaced_repetition.py) is built on the premise that consistency beats
 * cramming, so surfacing the pattern reinforces the behavior the app is
 * actually trying to encourage.
 */

const DAY_MS = 86_400_000;
const WEEKS = 12;

function dateKey(d: Date) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

interface Cell {
  key: string;
  date: Date;
  count: number;
  future: boolean;
}

function buildWeeks(lectures: LectureSummary[]): Cell[][] {
  const counts = new Map<string, number>();
  for (const l of lectures) {
    const d = new Date(l.created_at * 1000);
    const key = dateKey(d);
    counts.set(key, (counts.get(key) || 0) + 1);
  }

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const todayTime = today.getTime();

  // Anchor the grid so the last column is the calendar week containing
  // today (Sun start), then walk back WEEKS-1 more full weeks.
  const currentWeekStart = new Date(todayTime - today.getDay() * DAY_MS);
  const gridStart = new Date(currentWeekStart.getTime() - (WEEKS - 1) * 7 * DAY_MS);

  const cells: Cell[] = [];
  for (let i = 0; i < WEEKS * 7; i++) {
    const date = new Date(gridStart.getTime() + i * DAY_MS);
    const future = date.getTime() > todayTime;
    const key = dateKey(date);
    cells.push({ key, date, count: future ? 0 : counts.get(key) || 0, future });
  }

  const weeks: Cell[][] = [];
  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));
  return weeks;
}

function intensityClass(cell: Cell) {
  if (cell.future) return 'opacity-0';
  if (cell.count === 0) return 'bg-surface2';
  if (cell.count === 1) return 'bg-primary/40';
  if (cell.count === 2) return 'bg-primary/70';
  return 'bg-primary';
}

export function ActivityHeatmap({ lectures }: { lectures: LectureSummary[] }) {
  const weeks = buildWeeks(lectures);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-1 overflow-x-auto pb-1">
        {weeks.map((week, wi) => (
          <div key={wi} className="flex flex-col gap-1 shrink-0">
            {week.map((cell) => (
              <div
                key={cell.key}
                className={`w-3 h-3 rounded-sm transition-colors ${intensityClass(cell)}`}
                title={cell.future ? undefined : `${cell.count} lecture${cell.count === 1 ? '' : 's'} uploaded · ${cell.date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}`}
              />
            ))}
          </div>
        ))}
      </div>
      <div className="flex items-center gap-1.5 text-xs text-muted">
        <span>Less</span>
        <div className="w-3 h-3 rounded-sm bg-surface2" />
        <div className="w-3 h-3 rounded-sm bg-primary/40" />
        <div className="w-3 h-3 rounded-sm bg-primary/70" />
        <div className="w-3 h-3 rounded-sm bg-primary" />
        <span>More</span>
        <span className="ml-auto">Lecture uploads, last {WEEKS} weeks</span>
      </div>
    </div>
  );
}
