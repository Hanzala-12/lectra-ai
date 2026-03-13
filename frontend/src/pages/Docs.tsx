export function Docs() {
  return (
    <div className="max-w-7xl mx-auto px-6 py-24">
      <h1 className="font-display text-5xl mb-8">API Documentation</h1>
      <p className="text-xl text-muted max-w-3xl mb-12">Integrate LECTRA-AI into your own LMS or educational applications with our REST API.</p>
      
      <div className="bg-surface border border-border rounded-xl p-8 mb-8">
        <h3 className="text-xl font-bold mb-4 font-mono text-accent2">POST /api/process-lecture</h3>
        <p className="text-muted mb-6">Upload a lecture recording to generate transcripts, explanations, and quizzes.</p>
        
        <div className="bg-bg rounded-lg p-4 font-mono text-sm text-muted overflow-x-auto">
          <pre>
{`curl -X POST https://api.lectra.ai/v1/process-lecture \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -F "file=@/path/to/lecture.mp4" \\
  -F "generate_explanations=true" \\
  -F "generate_quiz=true" \\
  -F "language=en,ur"`}
          </pre>
        </div>
      </div>
    </div>
  );
}
