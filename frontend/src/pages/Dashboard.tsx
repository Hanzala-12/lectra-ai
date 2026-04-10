export function Dashboard() {
  return (
    <div className="max-w-7xl mx-auto px-6 py-12">
      <h1 className="text-4xl font-bold tracking-tight mb-2">Student Dashboard</h1>
      <p className="text-muted mb-8">Welcome back. Here's your learning overview.</p>
      
      <div className="grid md:grid-cols-4 gap-6 mb-12">
        <div className="bg-surface border border-border rounded-xl p-6 shadow-sm">
          <div className="text-sm font-mono text-muted uppercase tracking-widest mb-2">Lectures</div>
          <div className="text-4xl font-bold tracking-tight text-primary">12</div>
        </div>
        <div className="bg-surface border border-border rounded-xl p-6 shadow-sm">
          <div className="text-sm font-mono text-muted uppercase tracking-widest mb-2">Quizzes</div>
          <div className="text-4xl font-bold tracking-tight text-success">8</div>
        </div>
        <div className="bg-surface border border-border rounded-xl p-6 shadow-sm">
          <div className="text-sm font-mono text-muted uppercase tracking-widest mb-2">Avg Score</div>
          <div className="text-4xl font-bold tracking-tight text-accent">84%</div>
        </div>
        <div className="bg-surface border border-border rounded-xl p-6 shadow-sm">
          <div className="text-sm font-mono text-muted uppercase tracking-widest mb-2">Hours Saved</div>
          <div className="text-4xl font-bold tracking-tight text-warning">18</div>
        </div>
      </div>
      
      <div className="grid md:grid-cols-3 gap-8">
        <div className="md:col-span-2">
          <h2 className="font-bold text-xl mb-4">Recent Lectures</h2>
          <div className="space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="bg-surface border border-border rounded-xl p-4 flex items-center justify-between shadow-sm hover:shadow-md transition-shadow">
                <div>
                  <h3 className="font-bold">Introduction to Machine Learning - Lecture {i}</h3>
                  <p className="text-sm text-muted">CS401 • Oct {10 + i}, 2026</p>
                </div>
                <button className="text-sm font-medium text-primary hover:text-primary-dark transition-colors">View</button>
              </div>
            ))}
          </div>
        </div>
        
        <div>
          <h2 className="font-bold text-xl mb-4">Active Study Plan</h2>
          <div className="bg-warning-light/50 border border-warning/20 rounded-xl p-6 shadow-sm">
            <h3 className="font-bold text-warning mb-2">Weak Topics Alert</h3>
            <p className="text-sm text-text mb-4">You scored below 60% on "Gradient Descent" in your last quiz.</p>
            <button className="w-full bg-warning hover:bg-warning/90 text-white py-2 rounded-lg text-sm font-bold transition-colors shadow-sm">Review Topic</button>
          </div>
        </div>
      </div>
    </div>
  );
}
