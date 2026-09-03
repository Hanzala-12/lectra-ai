export function Features() {
  return (
    <div className="max-w-5xl mx-auto px-8 sm:px-10 py-24">
      <h1 className="font-serif text-5xl font-semibold tracking-tight mb-6 text-text">Features</h1>
      <p className="text-lg text-muted max-w-2xl leading-relaxed">Deep-dive on what Lectra AI does. Each feature explained with context and relevant use cases for students.</p>

      <div className="grid md:grid-cols-2 gap-5 mt-16">
        <div className="bg-surface rounded-lg p-8">
          <h3 className="font-serif text-2xl font-semibold mb-3 tracking-tight text-text">Smart Transcription</h3>
          <p className="text-muted leading-relaxed">Highly accurate, timestamped transcripts generated using advanced speech-to-text models. Perfect for searching through hours of lectures instantly.</p>
        </div>
        <div className="bg-surface rounded-lg p-8">
          <h3 className="font-serif text-2xl font-semibold mb-3 tracking-tight text-text">Multilingual AI Explanations</h3>
          <p className="text-muted leading-relaxed">Get complex topics broken down into simple terms. Available in English, Urdu, and Roman Urdu so you can understand concepts in your native language.</p>
        </div>
        <div className="bg-surface rounded-lg p-8">
          <h3 className="font-serif text-2xl font-semibold mb-3 tracking-tight text-text">Auto-Generated Quizzes</h3>
          <p className="text-muted leading-relaxed">Test your knowledge immediately after a lecture. We automatically generate multiple-choice questions based on the transcript.</p>
        </div>
        <div className="bg-surface rounded-lg p-8">
          <h3 className="font-serif text-2xl font-semibold mb-3 tracking-tight text-text">Learning Analytics</h3>
          <p className="text-muted leading-relaxed">Track your progress over time. Our dashboard identifies your weak topics and suggests personalized study plans to help you ace your exams.</p>
        </div>
      </div>
    </div>
  );
}
