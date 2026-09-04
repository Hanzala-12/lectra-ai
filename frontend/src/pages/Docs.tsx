import { useState } from 'react';
import { Copy, Check } from 'lucide-react';
import { Reveal } from '../components/Reveal';

const SAMPLE = `curl -X POST https://api.lectra.ai/v1/process-lecture \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -F "file=@/path/to/lecture.mp4" \\
  -F "generate_explanations=true" \\
  -F "generate_quiz=true" \\
  -F "language=en,ur"`;

export function Docs() {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(SAMPLE).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    });
  };

  return (
    <div className="max-w-5xl mx-auto px-8 sm:px-10 py-24">
      <Reveal>
        <h1 className="font-serif text-5xl font-semibold tracking-tight mb-6 text-text">API Documentation</h1>
        <p className="text-lg text-muted max-w-2xl mb-12 leading-relaxed">Integrate Lectra AI into your own LMS or educational applications with our REST API.</p>
      </Reveal>

      <Reveal delay={0.1}>
        <div className="bg-surface rounded-lg p-8">
          <h3 className="text-lg font-semibold mb-3 font-mono text-primary">POST /api/process-lecture</h3>
          <p className="text-muted mb-6">Upload a lecture recording to generate transcripts, explanations, and quizzes.</p>

          <div className="relative bg-surface2 rounded-lg p-4 font-mono text-sm text-muted overflow-x-auto">
            <button
              onClick={handleCopy}
              className="absolute top-3 right-3 flex items-center gap-1.5 text-xs font-medium bg-surface hover:bg-surface2 border border-border px-2.5 py-1.5 rounded-md text-muted hover:text-text transition-colors"
              aria-label="Copy code sample"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-success" /> : <Copy className="w-3.5 h-3.5" />}
              {copied ? 'Copied' : 'Copy'}
            </button>
            <pre className="pr-16">{SAMPLE}</pre>
          </div>
        </div>
      </Reveal>
    </div>
  );
}
