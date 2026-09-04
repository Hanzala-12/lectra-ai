import { useEffect, useRef, useState } from 'react';
import { LogOut, ChevronDown } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import type { Student } from '../lib/api';

interface ProfileMenuProps {
  student: Student;
  onLogout: () => void;
  /** Icon-only trigger (mobile header) instead of avatar + name + chevron (desktop sidebar). */
  compact?: boolean;
  /** Which way the dropdown opens relative to its trigger — 'up' for a
   * sidebar trigger pinned near the bottom of the screen, 'down' for a
   * trigger in a top header. */
  openDirection?: 'up' | 'down';
}

/**
 * Replaces what used to be a static avatar+name block with a
 * hover:bg-surface2 state that implied it was clickable but had no
 * onClick — a real dead-click bug (reported: "I click my name, I don't get
 * options, unlike other apps"). Now it's an actual dropdown; Log out moved
 * in here from its old always-visible icon button.
 */
export function ProfileMenu({ student, onLogout, compact = false, openDirection = 'up' }: ProfileMenuProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const initials = (student.name || student.username || '?').slice(0, 2).toUpperCase();

  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  return (
    <div ref={rootRef} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className={`flex items-center gap-3 rounded-lg hover:bg-surface2 transition-colors ${compact ? 'p-1.5' : 'w-full px-1 py-2'}`}
        aria-expanded={open}
        aria-haspopup="menu"
      >
        <div className="w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center text-xs font-bold shrink-0">
          {initials}
        </div>
        {!compact && (
          <>
            <div className="min-w-0 flex-1 text-left">
              <p className="text-sm font-semibold text-text truncate">{student.name}</p>
              <p className="text-xs text-muted truncate">@{student.username}</p>
            </div>
            <ChevronDown className={`w-4 h-4 text-muted shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
          </>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: openDirection === 'up' ? 6 : -6, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: openDirection === 'up' ? 6 : -6, scale: 0.97 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            className={`absolute z-30 w-56 bg-surface border border-border rounded-lg shadow-soft-lg overflow-hidden ${
              openDirection === 'up' ? 'bottom-full mb-2' : 'top-full mt-2'
            } ${compact ? 'right-0' : 'left-0'}`}
            role="menu"
          >
            <div className="px-4 py-3 border-b border-border">
              <p className="text-sm font-semibold text-text truncate">{student.name}</p>
              <p className="text-xs text-muted truncate">{student.email || `@${student.username}`}</p>
            </div>
            <button
              role="menuitem"
              onClick={() => {
                setOpen(false);
                onLogout();
              }}
              className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-muted hover:text-error hover:bg-error-light transition-colors"
            >
              <LogOut className="w-4 h-4" /> Log out
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
