import { Search, Filter, Play, FileText, HelpCircle } from 'lucide-react';

export function Library() {
  return (
    <div className="max-w-7xl mx-auto px-6 py-12">
      <div className="flex items-center justify-between mb-8">
        <h1 className="font-display text-4xl">Smart Lecture Library</h1>
        <button className="bg-accent text-white px-6 py-2 rounded-lg font-bold">Upload New</button>
      </div>
      
      <div className="flex gap-4 mb-8">
        <div className="flex-1 relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-muted w-5 h-5" />
          <input 
            type="text" 
            placeholder="Search transcripts, notes, or topics..." 
            className="w-full pl-12 pr-4 py-3 rounded-xl border border-border bg-surface focus:border-accent outline-none"
          />
        </div>
        <button className="flex items-center gap-2 px-6 py-3 rounded-xl border border-border bg-surface hover:bg-surface2 transition-colors">
          <Filter className="w-5 h-5" /> Filters
        </button>
      </div>
      
      <div className="grid md:grid-cols-3 gap-6">
        {[1, 2, 3, 4, 5, 6].map(i => (
          <div key={i} className="bg-surface border border-border rounded-xl overflow-hidden hover:border-accent2 transition-colors cursor-pointer group">
            <div className="h-32 bg-surface2 relative">
              <div className="absolute inset-0 flex items-center justify-center">
                <Play className="w-12 h-12 text-muted group-hover:text-accent2 transition-colors" />
              </div>
              <div className="absolute bottom-2 right-2 bg-text/80 text-white text-xs px-2 py-1 rounded">1:15:00</div>
            </div>
            <div className="p-6">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-[10px] font-mono uppercase tracking-widest bg-accent-light text-accent px-2 py-1 rounded">CS401</span>
                <span className="text-xs text-muted">Oct {10 + i}, 2026</span>
              </div>
              <h3 className="font-bold text-lg mb-2 line-clamp-1">Machine Learning - Lecture {i}</h3>
              <p className="text-sm text-muted line-clamp-2 mb-4">In this lecture, we cover the fundamentals of supervised learning, focusing on linear regression and gradient descent algorithms.</p>
              
              <div className="flex items-center gap-4 pt-4 border-t border-border">
                <button className="flex items-center gap-1 text-xs font-medium text-muted hover:text-accent2"><FileText className="w-4 h-4" /> Notes</button>
                <button className="flex items-center gap-1 text-xs font-medium text-muted hover:text-teal"><HelpCircle className="w-4 h-4" /> Quiz</button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
