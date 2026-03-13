export function Blog() {
  return (
    <div className="max-w-7xl mx-auto px-6 py-24">
      <h1 className="font-display text-5xl mb-8">Blog & Resources</h1>
      <p className="text-xl text-muted max-w-3xl mb-12">Study tips, technical deep dives, and product updates.</p>
      
      <div className="grid md:grid-cols-2 gap-8">
        <div className="bg-surface border border-border rounded-xl p-8 hover:border-accent transition-colors cursor-pointer">
          <span className="text-xs font-mono text-accent2 uppercase tracking-widest mb-4 block">Technical Explainer</span>
          <h3 className="text-2xl font-bold mb-4">How we generate accurate Urdu explanations for complex CS topics</h3>
          <p className="text-muted">A deep dive into our fine-tuned LLM pipeline and how we handle Roman Urdu translation without losing technical accuracy.</p>
        </div>
        <div className="bg-surface border border-border rounded-xl p-8 hover:border-accent transition-colors cursor-pointer">
          <span className="text-xs font-mono text-teal uppercase tracking-widest mb-4 block">Study Guide</span>
          <h3 className="text-2xl font-bold mb-4">Stop re-watching lectures: The active recall method</h3>
          <p className="text-muted">How to use LECTRA-AI's auto-generated quizzes to implement active recall and spaced repetition for your midterms.</p>
        </div>
      </div>
    </div>
  );
}
