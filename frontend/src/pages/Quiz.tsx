export function Quiz() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-12">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-4xl font-bold tracking-tight mb-2">Quiz & Assessment</h1>
          <p className="text-muted">Machine Learning - Lecture 3</p>
        </div>
        <div className="text-right">
          <div className="text-sm font-mono text-muted uppercase tracking-widest mb-1">Score</div>
          <div className="text-3xl font-bold tracking-tight text-success">85%</div>
        </div>
      </div>
      
      <div className="bg-surface border border-border rounded-2xl p-8 mb-8 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <h3 className="font-bold text-xl">Question 1 of 10</h3>
          <span className="text-xs font-mono bg-surface2 px-3 py-1 rounded-full text-muted uppercase tracking-widest border border-border">Multiple Choice</span>
        </div>
        
        <p className="text-lg mb-8 leading-relaxed">What is the primary purpose of the learning rate in gradient descent?</p>
        
        <div className="space-y-4">
          {[
            "To determine the number of iterations needed to converge.",
            "To control the size of the steps taken towards the minimum of the loss function.",
            "To calculate the derivative of the loss function with respect to the weights.",
            "To initialize the weights of the model before training begins."
          ].map((option, i) => (
            <label key={i} className={`flex items-start gap-4 p-4 rounded-xl border cursor-pointer transition-all duration-200 ${i === 1 ? 'border-success bg-success-light/30 shadow-sm' : 'border-border hover:border-primary/50 bg-surface hover:bg-surface2'}`}>
              <input type="radio" name="q1" className="mt-1 w-4 h-4 accent-success" defaultChecked={i === 1} />
              <span className="text-sm leading-relaxed">{option}</span>
            </label>
          ))}
        </div>
        
        <div className="mt-8 pt-8 border-t border-border flex items-center justify-between">
          <button className="text-muted hover:text-text font-medium text-sm transition-colors">Previous</button>
          <button className="bg-primary hover:bg-primary-dark text-white px-8 py-3 rounded-xl font-bold transition-colors shadow-sm">Next Question</button>
        </div>
      </div>
      
      <div className="bg-surface border border-border rounded-xl p-6 shadow-sm">
        <h4 className="font-bold mb-4">Topic Performance</h4>
        <div className="space-y-4">
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>Linear Regression</span>
              <span className="font-mono text-success">100%</span>
            </div>
            <div className="w-full bg-surface2 rounded-full h-2 overflow-hidden border border-border">
              <div className="bg-success h-2 rounded-full" style={{width: '100%'}}></div>
            </div>
          </div>
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>Gradient Descent</span>
              <span className="font-mono text-warning">60%</span>
            </div>
            <div className="w-full bg-surface2 rounded-full h-2 overflow-hidden border border-border">
              <div className="bg-warning h-2 rounded-full" style={{width: '60%'}}></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
