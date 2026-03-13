export function Dashboard() {
  return (
    <div className="max-w-7xl mx-auto px-6 py-12">
      <h1 className="font-display text-4xl mb-2">Student Dashboard</h1>
      <p className="text-muted mb-8">Welcome back. Here's your learning overview.</p>
      
      <div className="grid md:grid-cols-4 gap-6 mb-12">
        <div className="bg-surface border border-border rounded-xl p-6">
          <div className="text-sm font-mono text-muted uppercase tracking-widest mb-2">Lectures</div>
          <div className="font-display text-4xl text-accent2">12</div>
        </div>
        <div className="bg-surface border border-border rounded-xl p-6">
          <div className="text-sm font-mono text-muted uppercase tracking-widest mb-2">Quizzes</div>
          <div className="font-display text-4xl text-teal">8</div>
        </div>
        <div className="bg-surface border border-border rounded-xl p-6">
          <div className="text-sm font-mono text-muted uppercase tracking-widest mb-2">Avg Score</div>
          <div className="font-display text-4xl text-purple">84%</div>
        </div>
        <div className="bg-surface border border-border rounded-xl p-6">
          <div className="text-sm font-mono text-muted uppercase tracking-widest mb-2">Hours Saved</div>
          <div className="font-display text-4xl text-amber">18</div>
        </div>
      </div>
      
      <div className="grid md:grid-cols-3 gap-8">
        <div className="md:col-span-2">
          <h2 className="font-bold text-xl mb-4">Recent Lectures</h2>
          <div className="space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="bg-surface border border-border rounded-xl p-4 flex items-center justify-between">
                <div>
                  <h3 className="font-bold">Introduction to Machine Learning - Lecture {i}</h3>
                  <p className="text-sm text-muted">CS401 • Oct {10 + i}, 2026</p>
                </div>
                <button className="text-sm font-medium text-accent hover:text-accent2">View</button>
              </div>
            ))}
          </div>
        </div>
        
        <div>
          <h2 className="font-bold text-xl mb-4">Active Study Plan</h2>
          <div className="bg-amber-light border border-amber/20 rounded-xl p-6">
            <h3 className="font-bold text-amber mb-2">Weak Topics Alert</h3>
            <p className="text-sm text-amber/80 mb-4">You scored below 60% on "Gradient Descent" in your last quiz.</p>
            <button className="w-full bg-amber text-white py-2 rounded-lg text-sm font-bold">Review Topic</button>
          </div>
        </div>
      </div>
    </div>
  );
}
