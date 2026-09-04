import { useEffect, useState } from 'react';
import { Link, Navigate, useLocation, useNavigate, useOutlet } from 'react-router-dom';
import { LayoutDashboard, UploadCloud, Library, LineChart, MessageSquare, GraduationCap, LogOut, Loader2, Plus } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import { api, getToken, type Student } from '../lib/api';

export function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const element = useOutlet();
  const [student, setStudent] = useState<Student | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (!getToken()) {
      setChecking(false);
      return;
    }
    api
      .me()
      .then(setStudent)
      .catch(() => {
        /* req() already clears an invalid/expired token on 401 */
      })
      .finally(() => setChecking(false));
  }, []);

  const handleLogout = async () => {
    await api.logout().catch(() => {});
    navigate('/login');
  };

  // No token at all — don't even wait on the network, bounce immediately.
  if (!checking && !getToken()) {
    return <Navigate to="/login" replace />;
  }

  if (checking) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center text-muted gap-2">
        <Loader2 className="w-5 h-5 animate-spin" /> Checking session…
      </div>
    );
  }

  const navItems = [
    { path: '/app/dashboard', icon: <LayoutDashboard className="w-[18px] h-[18px]" />, label: 'Dashboard' },
    { path: '/app/library', icon: <Library className="w-[18px] h-[18px]" />, label: 'Library' },
    { path: '/app/analytics', icon: <LineChart className="w-[18px] h-[18px]" />, label: 'Analytics' },
    { path: '/app/chat', icon: <MessageSquare className="w-[18px] h-[18px]" />, label: 'AI Chat' },
  ];

  const initials = (student?.name || student?.username || '?').slice(0, 2).toUpperCase();

  return (
    <div className="min-h-screen bg-bg text-text flex flex-col items-center">
      <div className="flex flex-col md:flex-row max-w-[1400px] mx-auto w-full flex-1">
        {/* Sidebar — same flat tone as the page, separated only by a hairline
            border. Depth comes from the surface cards, not the chrome. */}
        <aside className="w-64 shrink-0 hidden md:flex md:flex-col py-7 px-5 min-h-screen sticky top-0 border-r border-border">
          <Link to="/" className="flex items-center gap-2.5 group px-1 mb-8">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-white transition-transform group-hover:scale-105">
              <GraduationCap className="w-4 h-4" />
            </div>
            <span className="font-serif font-semibold text-xl tracking-tight text-text">
              Lectra
            </span>
          </Link>

          <Link
            to="/app/upload"
            className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg font-semibold text-sm mb-8 transition-colors bg-primary text-white hover:bg-primary-dark"
          >
            <Plus className="w-4 h-4" strokeWidth={2.5} /> Upload lecture
          </Link>

          <nav className="flex flex-col gap-0.5 flex-1">
            <p className="label-caps px-3 text-muted mb-2">Workspace</p>
            {navItems.map(item => {
              const isActive = location.pathname === item.path || (item.path === '/app/dashboard' && location.pathname === '/app');
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'text-primary-dark font-semibold'
                      : 'text-muted hover:bg-surface2 hover:text-text'
                  }`}
                >
                  {isActive && (
                    <motion.div
                      layoutId="sidebar-active-pill"
                      className="absolute inset-0 -z-10 rounded-lg bg-primary-light"
                      transition={{ type: 'spring', stiffness: 380, damping: 32 }}
                    />
                  )}
                  {item.icon}
                  {item.label}
                </Link>
              );
            })}
          </nav>

          {student && (
            <div className="mt-auto pt-4 border-t border-border">
              <div className="flex items-center gap-3 px-1 py-2 rounded-lg hover:bg-surface2 transition-colors group">
                <div className="w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center text-xs font-bold shrink-0">
                  {initials}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-text truncate">{student.name}</p>
                  <p className="text-xs text-muted truncate">@{student.username}</p>
                </div>
                <button
                  onClick={handleLogout}
                  title="Log out"
                  className="text-muted hover:text-error transition-colors p-1.5 rounded-lg hover:bg-error-light shrink-0"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </aside>

        {/* Mobile Nav Header */}
        <div className="md:hidden w-full flex flex-col sticky top-0 bg-bg z-20 border-b border-border">
          <div className="py-4 px-6 flex items-center justify-between">
            <Link to="/" className="flex items-center gap-2 group">
              <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center text-white">
                <GraduationCap className="w-3.5 h-3.5" />
              </div>
              <span className="font-serif font-semibold text-xl tracking-tight text-text">
                Lectra
              </span>
            </Link>
            {student && (
              <button onClick={handleLogout} className="flex items-center gap-1.5 text-xs text-muted hover:text-text transition-colors">
                <LogOut className="w-3.5 h-3.5" /> Log out
              </button>
            )}
          </div>
          {/* Mobile Nav (horizontal scroll) */}
          <div className="w-full overflow-x-auto flex gap-2 px-6 pb-4 hide-scrollbar">
            <Link
              to="/app/upload"
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg font-semibold whitespace-nowrap text-sm transition-colors shrink-0 ${
                location.pathname === '/app/upload' ? 'bg-primary-dark text-white' : 'bg-primary text-white'
              }`}
            >
              <Plus className="w-4 h-4" /> Upload
            </Link>
            {navItems.map(item => {
              const isActive = location.pathname === item.path || (item.path === '/app/dashboard' && location.pathname === '/app');
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`relative flex items-center gap-2 px-4 py-2 rounded-lg font-medium whitespace-nowrap text-sm transition-colors shrink-0 ${isActive ? 'text-primary-dark' : 'bg-surface2 text-muted hover:text-text'}`}
                >
                  {isActive && (
                    <motion.div
                      layoutId="mobile-nav-active-pill"
                      className="absolute inset-0 -z-10 rounded-lg bg-primary-light"
                      transition={{ type: 'spring', stiffness: 380, damping: 32 }}
                    />
                  )}
                  {item.icon}
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>

        {/* Main Content */}
        <main className="flex-1 min-w-0">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25, ease: 'easeOut' }}
              className="w-full h-full"
            >
              {element}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
