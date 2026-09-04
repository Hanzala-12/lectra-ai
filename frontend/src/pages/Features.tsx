import { BookOpen, Languages, Target, LineChart, Sparkles } from 'lucide-react';
import { Reveal, StaggerGroup, StaggerItem } from '../components/Reveal';

const FEATURES = [
  {
    icon: <BookOpen className="w-5 h-5 text-primary" />,
    title: 'Smart Transcription',
    desc: 'Highly accurate, timestamped transcripts generated using advanced speech-to-text models. Perfect for searching through hours of lectures instantly.',
  },
  {
    icon: <Languages className="w-5 h-5 text-primary" />,
    title: 'Multilingual AI Explanations',
    desc: 'Get complex topics broken down into simple terms. Available in English, Urdu, and Roman Urdu so you can understand concepts in your native language.',
  },
  {
    icon: <Target className="w-5 h-5 text-primary" />,
    title: 'Auto-Generated Quizzes',
    desc: 'Test your knowledge immediately after a lecture. We automatically generate multiple-choice questions based on the transcript.',
  },
  {
    icon: <LineChart className="w-5 h-5 text-primary" />,
    title: 'Learning Analytics',
    desc: 'Track your progress over time. Our dashboard identifies your weak topics and suggests personalized study plans to help you ace your exams.',
  },
];

export function Features() {
  return (
    <div className="max-w-5xl mx-auto px-8 sm:px-10 py-24">
      <Reveal>
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface text-sm font-medium text-muted mb-6">
          <Sparkles className="w-3.5 h-3.5 text-primary" />
          What Lectra AI does
        </div>
        <h1 className="font-serif text-5xl font-semibold tracking-tight mb-6 text-text">Features</h1>
        <p className="text-lg text-muted max-w-2xl leading-relaxed">Deep-dive on what Lectra AI does. Each feature explained with context and relevant use cases for students.</p>
      </Reveal>

      <StaggerGroup className="grid md:grid-cols-2 gap-5 mt-16">
        {FEATURES.map((f) => (
          <StaggerItem
            key={f.title}
            className="bg-surface rounded-lg p-8 border border-transparent hover:border-primary/25 transition-colors duration-300"
          >
            <div className="w-10 h-10 rounded-lg bg-primary-light flex items-center justify-center mb-5">
              {f.icon}
            </div>
            <h3 className="font-serif text-2xl font-semibold mb-3 tracking-tight text-text">{f.title}</h3>
            <p className="text-muted leading-relaxed">{f.desc}</p>
          </StaggerItem>
        ))}
      </StaggerGroup>
    </div>
  );
}
