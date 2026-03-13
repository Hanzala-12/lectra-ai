export function Features() {
  return (
    <div className="max-w-7xl mx-auto px-6 py-24">
      <h1 className="font-display text-5xl mb-8">Features</h1>
      <p className="text-xl text-muted max-w-3xl">Deep-dive on what LECTRA-AI does. Each feature explained with context and relevant use case for students.</p>
      
      <div className="grid md:grid-cols-2 gap-12 mt-16">
        <div className="bg-surface border border-border rounded-2xl p-8">
          <h3 className="text-2xl font-bold mb-4">Smart Transcription</h3>
          <p className="text-muted leading-relaxed">Highly accurate, timestamped transcripts generated using advanced speech-to-text models. Perfect for searching through hours of lectures instantly.</p>
        </div>
        <div className="bg-surface border border-border rounded-2xl p-8">
          <h3 className="text-2xl font-bold mb-4">Multilingual AI Explanations</h3>
          <p className="text-muted leading-relaxed">Get complex topics broken down into simple terms. Available in English, Urdu, and Roman Urdu so you can understand concepts in your native language.</p>
        </div>
        <div className="bg-surface border border-border rounded-2xl p-8">
          <h3 className="text-2xl font-bold mb-4">Auto-Generated Quizzes</h3>
          <p className="text-muted leading-relaxed">Test your knowledge immediately after a lecture. We automatically generate multiple-choice and short-answer questions based on the transcript.</p>
        </div>
        <div className="bg-surface border border-border rounded-2xl p-8">
          <h3 className="text-2xl font-bold mb-4">Learning Analytics</h3>
          <p className="text-muted leading-relaxed">Track your progress over time. Our dashboard identifies your weak topics and suggests personalized study plans to help you ace your exams.</p>
        </div>
      </div>
    </div>
  );
}
