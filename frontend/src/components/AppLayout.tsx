import { Link, Outlet, useLocation } from 'react-router-dom';
import { LayoutDashboard, UploadCloud, Library, HelpCircle, LineChart, MessageSquare } from 'lucide-react';

export function AppLayout() {
  const location = useLocation();
  
  const navItems = [
    { path: '/app/dashboard', icon: <LayoutDashboard className="w-5 h-5" />, label: 'Dashboard' },
    { path: '/app/upload', icon: <UploadCloud className="w-5 h-5" />, label: 'Upload' },
    { path: '/app/library', icon: <Library className="w-5 h-5" />, label: 'Library' },
    { path: '/app/quiz', icon: <HelpCircle className="w-5 h-5" />, label: 'Quizzes' },
    { path: '/app/analytics', icon: <LineChart className="w-5 h-5" />, label: 'Analytics' },
    { path: '/app/chat', icon: <MessageSquare className="w-5 h-5" />, label: 'AI Chat' },
  ];

  return (
    <div className="flex flex-col md:flex-row max-w-7xl mx-auto w-full px-6">
      {/* Sidebar */}
      <aside className="w-64 shrink-0 hidden md:block py-12 pr-8 border-r border-border min-h-[calc(100vh-6rem)]">
        <nav className="flex flex-col gap-2">
          {navItems.map(item => {
            const isActive = location.pathname === item.path || (item.path === '/app/dashboard' && location.pathname === '/app');
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl font-medium transition-colors ${isActive ? 'bg-accent text-white shadow-sm' : 'text-muted hover:bg-surface hover:text-text'}`}
              >
                {item.icon}
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>
      
      {/* Mobile Nav (horizontal scroll) */}
      <div className="md:hidden w-full overflow-x-auto flex gap-2 py-4 border-b border-border">
         {navItems.map(item => {
            const isActive = location.pathname === item.path || (item.path === '/app/dashboard' && location.pathname === '/app');
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium whitespace-nowrap text-sm ${isActive ? 'bg-accent text-white' : 'bg-surface text-muted'}`}
              >
                {item.icon}
                {item.label}
              </Link>
            );
          })}
      </div>

      {/* Main Content */}
      <main className="flex-1 min-w-0">
        <Outlet />
      </main>
    </div>
  );
}
