import { BarChart2, TrendingUp, AlertTriangle, Download } from 'lucide-react';

export function Analytics() {
  return (
    <div className="max-w-7xl mx-auto px-6 py-12">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-4xl font-bold tracking-tight">Learning Analytics</h1>
        <button className="flex items-center gap-2 px-6 py-2 rounded-lg bg-surface border border-border text-sm font-medium hover:bg-surface2 transition-colors shadow-sm">
          <Download className="w-4 h-4" /> Export Report
        </button>
      </div>
      
      <div className="grid md:grid-cols-3 gap-8 mb-12">
        <div className="bg-surface border border-border rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-lg">Overall Progress</h3>
            <TrendingUp className="w-5 h-5 text-success" />
          </div>
          <div className="text-5xl font-bold tracking-tight text-primary mb-2">78%</div>
          <p className="text-sm text-muted">+5% from last month</p>
        </div>
        
        <div className="bg-surface border border-border rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-lg">Weakest Topic</h3>
            <AlertTriangle className="w-5 h-5 text-warning" />
          </div>
          <div className="text-3xl font-bold tracking-tight text-warning mb-2 leading-tight">Gradient<br/>Descent</div>
          <p className="text-sm text-muted">Scored 45% on average</p>
        </div>
        
        <div className="bg-surface border border-border rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-lg">Strongest Topic</h3>
            <BarChart2 className="w-5 h-5 text-accent" />
          </div>
          <div className="text-3xl font-bold tracking-tight text-accent mb-2 leading-tight">Linear<br/>Regression</div>
          <p className="text-sm text-muted">Scored 95% on average</p>
        </div>
      </div>
      
      <div className="grid md:grid-cols-2 gap-8">
        <div className="bg-surface border border-border rounded-xl p-8 shadow-sm">
          <h3 className="font-bold text-xl mb-6">Topic Performance Over Time</h3>
          <div className="h-64 flex items-end gap-4">
            {/* Mock Chart */}
            {[40, 55, 60, 75, 82, 90].map((h, i) => (
              <div key={i} className="flex-1 bg-primary-light rounded-t-lg relative group">
                <div className="absolute bottom-0 w-full bg-primary rounded-t-lg transition-all" style={{height: `${h}%`}}></div>
                <div className="opacity-0 group-hover:opacity-100 absolute -top-8 left-1/2 -translate-x-1/2 bg-text text-white text-xs px-2 py-1 rounded transition-opacity shadow-sm">{h}%</div>
              </div>
            ))}
          </div>
          <div className="flex justify-between mt-4 text-xs font-mono text-muted uppercase tracking-widest">
            <span>Week 1</span>
            <span>Week 6</span>
          </div>
        </div>
        
        <div className="bg-surface border border-border rounded-xl p-8 shadow-sm">
          <h3 className="font-bold text-xl mb-6">Mistake Heatmap</h3>
          <div className="grid grid-cols-5 gap-2 h-64">
            {/* Mock Heatmap */}
            {Array.from({length: 25}).map((_, i) => (
              <div key={i} className={`rounded-md ${
                Math.random() > 0.8 ? 'bg-error-light border border-error/20' : 
                Math.random() > 0.5 ? 'bg-warning-light border border-warning/20' : 
                'bg-success-light border border-success/20'
              }`} title={`Topic ${i+1}`}></div>
            ))}
          </div>
          <div className="flex items-center gap-4 mt-6 text-xs text-muted">
            <div className="flex items-center gap-1"><div className="w-3 h-3 bg-error-light border border-error/20 rounded"></div> Many Mistakes</div>
            <div className="flex items-center gap-1"><div className="w-3 h-3 bg-warning-light border border-warning/20 rounded"></div> Some Mistakes</div>
            <div className="flex items-center gap-1"><div className="w-3 h-3 bg-success-light border border-success/20 rounded"></div> Few Mistakes</div>
          </div>
        </div>
      </div>
    </div>
  );
}
