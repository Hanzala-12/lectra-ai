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

      {/* Leadership & Team Section */}
      <section className="py-20 bg-surface/30">
        <div className="max-w-7xl mx-auto px-6">
          <div className="mb-16">
            <h2 className="text-3xl font-display font-bold mb-4">Meet the Team</h2>
            <p className="text-muted max-w-2xl text-lg">
              We are a dedicated group of final year students at NUCES computing pushing the boundaries of what is possible with applied machine learning in the classroom.
            </p>
          </div>

          {/* Supervisor Card */}
          <div className="mb-16">
            <h3 className="text-sm font-mono uppercase tracking-widest text-muted mb-6">Project Supervisor</h3>
            <div className="bg-surface border border-border p-8 rounded-2xl hover:border-accent/50 transition-all duration-300 hover:shadow-lg flex flex-col md:flex-row gap-8 items-center md:items-start group">
              <div className="w-32 h-32 md:w-40 md:h-40 rounded-2xl overflow-hidden shrink-0 bg-accent/10 border border-border group-hover:scale-105 transition-transform duration-500 relative">
                <img 
                  src="data:image/jpeg;base64,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" 
                  alt="M. Umer Iqbal" 
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    const target = e.target as HTMLImageElement;
                    target.src = "https://ui-avatars.com/api/?name=Umer+Iqbal&size=200&background=random"; // Fallback if image not found
                  }}
                />
              </div>
              <div>
                <h3 className="text-3xl font-bold mb-2">M. Umer Iqbal</h3>
                <div className="text-accent font-semibold tracking-wide uppercase mb-4 mb-2">Lecturer, School of Computing (CFD Campus)</div>
                <p className="text-muted leading-relaxed text-lg max-w-3xl mb-6">
                  An expert in Evolutionary Algorithms, Computational Optimization, and Requirement Engineering with a distinguished MS(CS) from FAST-NUCES. He provides invaluable mentorship, academic direction, and industry insights for the Lectra-AI project.
                </p>
                <div className="flex items-center gap-4">
                  <a href="https://scholar.google.com/citations?user=zmYMwvgAAAAJ&hl=en" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-sm font-medium text-text bg-bg border border-border px-4 py-2 rounded-lg hover:border-accent transition-colors">
                    Google Scholar <ArrowRight className="w-4 h-4" />
                  </a>
                </div>
              </div>
            </div>
          </div>

          <h3 className="text-sm font-mono uppercase tracking-widest text-muted mb-6">Core Development Team</h3>
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
