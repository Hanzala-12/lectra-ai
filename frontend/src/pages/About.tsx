import React from 'react';
import { Github, Linkedin, Mail, ArrowRight, Code } from 'lucide-react';
import { Link } from 'react-router-dom';

export function About() {
  const team = [
    {
      name: "Hassan Raza",
      role: "AI & Backend Engineer",
      bio: "Focuses on building robust deep learning pipelines and scaling APIs for real-time audio inference.",
      github: "#",
      linkedin: "#"
    },
    {
      name: "M Hanzala Yaqoob",
      role: "Full-Stack Developer",
      bio: "Passionate about creating seamless user experiences and bridging complex AI systems with intuitive UI.",
      github: "#",
      linkedin: "#"
    },
    {
      name: "Muhammad Zohair Hassnain",
      role: "Speech & Audio Processing Specialist",
      bio: "Specializes in optimizing signal processing and diarization models to perform flawlessly in noisy environments.",
      github: "#",
      linkedin: "#"
    }
  ];

  return (
    <div className="min-h-screen bg-bg">
      {/* Hero Section */}
      <section className="relative pt-32 pb-20 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-accent/5 to-transparent pointer-events-none" />
        <div className="max-w-7xl mx-auto px-6 relative">
          <div className="max-w-3xl">
            <h1 className="text-5xl md:text-6xl font-display font-bold tracking-tight mb-6">
              Empowering Education through <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent to-accent2">AI Sound</span>
            </h1>
            <p className="text-xl text-muted leading-relaxed">
              Lectra-AI was born out of a simple necessity: students struggled with low-quality, noisy lecture recordings that were impossible to study from. We set out to change that by building an intelligent audio enhancement platform tailored specifically for NUCES CFD and universities worldwide.
            </p>
          </div>
        </div>
      </section>

      {/* Team Section */}
      <section className="py-20 bg-surface/30">
        <div className="max-w-7xl mx-auto px-6">
          <div className="mb-16">
            <h2 className="text-3xl font-display font-bold mb-4">Meet the Team</h2>
            <p className="text-muted max-w-2xl text-lg">
              We are a dedicated group of final year students at NUCES computing pushing the boundaries of what is possible with applied machine learning in the classroom.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {team.map((member, idx) => (
              <div key={idx} className="bg-surface border border-border p-8 rounded-2xl hover:border-accent/50 transition-all duration-300 hover:shadow-lg group">
                <div className="w-16 h-16 bg-accent/10 text-accent rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                  <Code className="w-8 h-8" />
                </div>
                <h3 className="text-2xl font-bold mb-1">{member.name}</h3>
                <div className="text-accent text-sm font-semibold tracking-wide uppercase mb-4">{member.role}</div>
                <p className="text-muted leading-relaxed mb-8 h-24">
                  {member.bio}
                </p>
                <div className="flex items-center gap-4">
                  <a href={member.github} className="text-muted hover:text-text transition-colors">
                    <Github className="w-5 h-5" />
                  </a>
                  <a href={member.linkedin} className="text-muted hover:text-text transition-colors">
                    <Linkedin className="w-5 h-5" />
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 relative overflow-hidden">
        <div className="max-w-4xl mx-auto px-6 text-center relative z-10">
          <h2 className="text-4xl font-display font-bold mb-6">Want to see our work in action?</h2>
          <p className="text-xl text-muted mb-10 leading-relaxed max-w-2xl mx-auto">
            Try our platform yourself and experience crystal-clear audio transcription with perfect speaker separation. Fully free and open-source.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/app/upload"
              className="flex items-center gap-2 bg-text text-bg hover:bg-white px-8 py-4 rounded-xl font-bold transition-all duration-300 shadow-xl hover:shadow-2xl hover:-translate-y-1"
            >
              Try the App
              <ArrowRight className="w-5 h-5" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
