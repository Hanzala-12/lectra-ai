import { useEffect, useState } from 'react';
import { Link, Navigate, useLocation, useNavigate, useOutlet } from 'react-router-dom';
import { LayoutDashboard, UploadCloud, Library, HelpCircle, LineChart, MessageSquare, GraduationCap, LogOut, Loader2 } from 'lucide-react';
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
    { path: '/app/dashboard', icon: <LayoutDashboard className="w-5 h-5" />, label: 'Dashboard' },
    { path: '/app/upload', icon: <UploadCloud className="w-5 h-5" />, label: 'Upload' },
    { path: '/app/library', icon: <Library className="w-5 h-5" />, label: 'Library' },
    { path: '/app/quiz', icon: <HelpCircle className="w-5 h-5" />, label: 'Quizzes' },
    { path: '/app/analytics', icon: <LineChart className="w-5 h-5" />, label: 'Analytics' },
    { path: '/app/chat', icon: <MessageSquare className="w-5 h-5" />, label: 'AI Chat' },
  ];

  return (
    <div className="min-h-screen bg-bg text-text flex flex-col items-center">
      <div className="flex flex-col md:flex-row max-w-7xl mx-auto w-full px-6 flex-1">
        {/* Sidebar */}
        <aside className="w-64 shrink-0 hidden md:flex md:flex-col py-8 pr-8 border-r border-border min-h-[calc(100vh-6rem)]">
        <div className="mb-8 px-4">
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-white transition-transform group-hover:scale-105 shadow-sm">
              <GraduationCap className="w-4 h-4" />
            </div>
            <span className="font-bold text-xl tracking-tight text-primary">
              Lectra
            </span>
          </Link>
        </div>
        <nav className="flex flex-col gap-2 flex-1">
          {navItems.map(item => {
            const isActive = location.pathname === item.path || (item.path === '/app/dashboard' && location.pathname === '/app');
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl font-medium transition-all duration-200 ${isActive ? 'bg-accent text-white shadow-sm' : 'text-muted hover:bg-surface2 hover:text-text'}`}
              >
                {item.icon}
                {item.label}
              </Link>
            );
          })}
        </nav>
        {student && (
          <div className="mt-auto pt-4 border-t border-border px-4">
            <p className="text-sm font-medium text-text truncate">{student.name}</p>
            <p className="text-xs text-muted truncate mb-3">@{student.username}</p>
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 text-sm text-muted hover:text-error transition-colors"
            >
              <LogOut className="w-4 h-4" /> Log out
            </button>
          </div>
        )}
      </aside>

      {/* Mobile Nav Header */}
      <div className="md:hidden w-full flex flex-col border-b border-border">
        <div className="py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-white transition-transform group-hover:scale-105 shadow-sm">
              <GraduationCap className="w-4 h-4" />
            </div>
            <span className="font-bold text-xl tracking-tight text-primary">
              Lectra
            </span>
          </Link>
          {student && (
            <button onClick={handleLogout} className="flex items-center gap-1.5 text-xs text-muted hover:text-error transition-colors">
              <LogOut className="w-3.5 h-3.5" /> Log out
            </button>
          )}
        </div>
        {/* Mobile Nav (horizontal scroll) */}
        <div className="w-full overflow-x-auto flex gap-2 pb-4 hide-scrollbar">
           {navItems.map(item => {
              const isActive = location.pathname === item.path || (item.path === '/app/dashboard' && location.pathname === '/app');
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium whitespace-nowrap text-sm transition-colors ${isActive ? 'bg-accent text-white' : 'bg-surface2 text-muted hover:text-text'}`}
                >
                  {item.icon}
                  {item.label}
                </Link>
              );
            })}
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-1 min-w-0 py-8 md:py-12 md:pl-8">
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
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
