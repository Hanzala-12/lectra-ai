import { Github, Linkedin, ArrowRight, Code, BookOpen, BrainCircuit } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Reveal } from '../components/Reveal';

export function About() {
  const team = [
    {
      name: "Hassan Raza",
      role: "AI & Backend Engineer",
      bio: "Focuses on building robust deep learning pipelines and scaling APIs for real-time audio inference. Drives the core architecture bringing AI to production.",
      image: "https://ui-avatars.com/api/?name=Hassan+Raza&size=400&background=random",
      github: "#",
      linkedin: "#",
      expertise: ["Deep Learning", "Python", "API Architecture"]
    },
    {
      name: "M Hanzala Yaqoob",
      role: "Full-Stack Developer",
      bio: "Passionate about creating seamless user experiences and bridging complex AI systems with elegant, intuitive front-end interfaces that drive adoption.",
      image: "https://ui-avatars.com/api/?name=M+Hanzala+Yaqoob&size=400&background=random",
      github: "#",
      linkedin: "#",
      expertise: ["React", "TypeScript", "System Integration"]
    },
    {
      name: "Muhammad Zohair Hassnain",
      role: "Speech & Audio Processing Specialist",
      bio: "Specializes in optimizing signal processing and diarization models to perform flawlessly in noisy environments, ensuring pristine audio quality.",
      image: "https://ui-avatars.com/api/?name=Muhammad+Zohair+Hassnain&size=400&background=random",
      github: "#",
      linkedin: "#",
      expertise: ["Signal Processing", "Diarization", "Model Optimization"]
    }
  ];

  return (
    <div className="min-h-screen bg-bg">
      {/* Hero Section */}
      <section className="pt-28 pb-20">
        <div className="max-w-4xl mx-auto px-8 sm:px-10">
          <Reveal>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-light text-primary-dark text-sm font-medium mb-6">
              <BrainCircuit className="w-4 h-4" />
              Revolutionizing Audio Intelligence
            </div>
            <h1 className="font-serif text-5xl md:text-6xl font-semibold tracking-tight mb-8 leading-[1.1] text-text">
              Pioneering the future of <span className="text-primary">applied sound AI</span>
            </h1>
            <p className="text-lg text-muted leading-relaxed">
              Lectra AI is engineered to bridge the gap between noisy environments and crystal-clear understanding. We build enterprise-grade audio enhancement and structural transcribing explicitly tailored for complex, real-world acoustic scenarios.
            </p>
          </Reveal>
        </div>
      </section>

      {/* Leadership & Team Section */}
      <section className="py-24 border-t border-border">
        <div className="max-w-5xl mx-auto px-8 sm:px-10">
          <Reveal>
            <div className="mb-20 text-center max-w-2xl mx-auto">
              <h2 className="font-serif text-4xl font-semibold tracking-tight mb-5 text-text">The minds behind Lectra AI</h2>
              <p className="text-muted text-[15px] leading-relaxed">
                Our team represents a convergence of academic excellence and top-tier computing engineering from NUCES CFD, dedicated to pushing the boundaries of applied machine learning.
              </p>
            </div>
          </Reveal>

          {/* Supervisor Card */}
          <Reveal direction="left" className="mb-28">
            <div className="flex flex-col lg:flex-row items-center gap-14">
              <div className="flex-1 order-2 lg:order-1">
                <p className="label-caps text-primary mb-4">Academic Leadership</p>
                <h3 className="font-serif text-3xl font-semibold mb-2 tracking-tight text-text">M. Umer Iqbal</h3>
                <div className="text-muted font-medium mb-6">Project Supervisor &amp; Lecturer, NUCES CFD</div>

                <p className="text-muted leading-relaxed mb-8">
                  An expert in Evolutionary Algorithms, Computational Optimization, and Requirement Engineering with a distinguished MS(CS) from FAST-NUCES. Sir Umer Iqbal provides the strategic vision, rigorous academic constraints, and crucial industry insights that steer the Lectra AI platform toward scalable, enterprise-ready solutions.
                </p>

                <a href="https://scholar.google.com/citations?user=zmYMwvgAAAAJ&hl=en" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 font-semibold text-white bg-primary px-6 py-3 rounded-lg hover:bg-primary-dark transition-colors">
                  <BookOpen className="w-4 h-4" />
                  View Research Publications
                </a>
              </div>

              <div className="flex-1 order-1 lg:order-2 w-full">
                <div className="relative aspect-square max-w-sm ml-auto">
                  <div className="w-full h-full rounded-lg overflow-hidden bg-surface">
                    <img
                      src="/supervisor.jpg"
                      alt="M. Umer Iqbal"
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        const target = e.target as HTMLImageElement;
                        target.src = "https://ui-avatars.com/api/?name=Umer+Iqbal&size=800&background=random";
                      }}
                    />
                  </div>
                </div>
              </div>
            </div>
          </Reveal>

          <Reveal>
            <div className="flex items-center gap-4 mb-16">
              <h3 className="font-serif text-2xl font-semibold tracking-tight text-text">Core development team</h3>
              <div className="flex-1 h-px bg-border"></div>
            </div>
          </Reveal>

          <div className="flex flex-col gap-20">
            {team.map((member, idx) => {
              const isEven = idx % 2 === 0;
              return (
                <Reveal key={idx} direction={isEven ? "right" : "left"} delay={idx * 0.1}>
                  <div className={`flex flex-col gap-10 items-center ${isEven ? 'md:flex-row' : 'md:flex-row-reverse'}`}>

                    <div className="w-full md:w-5/12 lg:w-1/3">
                      <div className="aspect-square rounded-lg overflow-hidden bg-surface">
                        <img
                          src={member.image}
                          alt={member.name}
                          className="w-full h-full object-cover"
                        />
                      </div>
                    </div>

                    <div className="w-full md:w-7/12 lg:w-2/3 flex flex-col justify-center">
                      <h3 className="font-serif text-2xl font-semibold mb-2 tracking-tight text-text">{member.name}</h3>
                      <div className="label-caps text-primary mb-5 flex items-center gap-2">
                        <Code className="w-3.5 h-3.5" />
                        {member.role}
                      </div>

                      <p className="text-muted leading-relaxed mb-6 max-w-2xl">
                        {member.bio}
                      </p>

                      <div className="flex flex-wrap gap-2 mb-6">
                        {member.expertise.map((skill, i) => (
                          <span key={i} className="px-3 py-1 bg-surface2 rounded-full text-xs font-medium text-text">
                            {skill}
                          </span>
                        ))}
                      </div>

                      <div className="flex items-center gap-3">
                        <a href={member.github} className="p-2.5 bg-surface2 rounded-lg text-muted hover:text-primary transition-colors">
                          <Github className="w-4 h-4" />
                        </a>
                        <a href={member.linkedin} className="p-2.5 bg-surface2 rounded-lg text-muted hover:text-primary transition-colors">
                          <Linkedin className="w-4 h-4" />
                        </a>
                      </div>
                    </div>

                  </div>
                </Reveal>
              );
            })}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-28 border-t border-border">
        <Reveal>
          <div className="max-w-2xl mx-auto px-8 sm:px-10 text-center">
            <h2 className="font-serif text-4xl font-semibold tracking-tight mb-6 text-text">Experience the difference</h2>
            <p className="text-lg text-muted mb-10 leading-relaxed">
              Our advanced diarization and noise-cancellation models are ready to transform your audio. Fully free, open-source, and engineered for scale.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <Link
                to="/app/upload"
                className="flex items-center gap-2 bg-primary text-white hover:bg-primary-dark px-7 py-3.5 rounded-lg font-semibold transition-colors"
              >
                Access the Platform
                <ArrowRight className="w-4 h-4" />
              </Link>
              <a
                href="https://github.com"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 border border-border text-text hover:bg-surface2 px-7 py-3.5 rounded-lg font-medium transition-colors"
              >
                <Github className="w-4 h-4" />
                View Source
              </a>
            </div>
          </div>
        </Reveal>
      </section>
    </div>
  );
}
