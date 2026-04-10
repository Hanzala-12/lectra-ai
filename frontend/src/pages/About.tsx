import React, { useEffect, useRef, useState } from 'react';
import { Github, Linkedin, ArrowRight, Code, BookOpen, BrainCircuit } from 'lucide-react';
import { Link } from 'react-router-dom';

const FadeIn = ({ children, delay = 0, direction = 'up', className = '' }: { children: React.ReactNode, delay?: number, direction?: 'up' | 'down' | 'left' | 'right', className?: string, key?: React.Key }) => {
  const [isVisible, setIsVisible] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      setIsVisible(entry.isIntersecting);
    }, { threshold: 0.15 });

    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  const getTransform = () => {
    switch(direction) {
      case 'up': return 'translateY(40px)';
      case 'down': return 'translateY(-40px)';
      case 'left': return 'translateX(40px)';
      case 'right': return 'translateX(-40px)';
      default: return 'translateY(40px)';
    }
  };

  return (
    <div
      ref={ref}
      className={`${className} transition-all duration-1000 ease-out`}
      style={{
        opacity: isVisible ? 1 : 0,
        transform: isVisible ? 'translate(0)' : getTransform(),
        transitionDelay: isVisible ? `${delay}ms` : '0ms'
      }}
    >
      {children}
    </div>
  );
};

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
      <section className="relative pt-32 pb-20 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-primary/5 to-transparent pointer-events-none" />
        <div className="absolute right-0 top-0 w-1/2 h-full bg-gradient-to-l from-primary/10 to-transparent blur-3xl rounded-full opacity-50 transform translate-x-1/2 -translate-y-1/4 pointer-events-none" />
        
        <div className="max-w-7xl mx-auto px-6 relative">
          <FadeIn className="max-w-3xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-sm font-medium mb-6 border border-primary/20">
              <BrainCircuit className="w-4 h-4" />
              Revolutionizing Audio Intelligence
            </div>
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-8">
              Pioneering the Future of <br/>
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-accent">Applied Sound AI</span>
            </h1>
            <p className="text-xl text-muted leading-relaxed mb-10">
              Lectra-AI is engineered to bridge the gap between noisy environments and crystal-clear understanding. We build enterprise-grade audio enhancement and structural transcribing explicitly tailored for complex, real-world acoustic scenarios.
            </p>
          </FadeIn>
        </div>
      </section>

      {/* Leadership & Team Section */}
      <section className="py-24 bg-surface/30 border-t border-border">
        <div className="max-w-7xl mx-auto px-6">
          <FadeIn direction="up">
            <div className="mb-20 text-center max-w-3xl mx-auto">
              <h2 className="text-4xl font-bold tracking-tight mb-6">The Minds Behind Lectra-AI</h2>
              <p className="text-muted text-lg">
                Our team represents a convergence of academic excellence and top-tier computing engineering from NUCES CFD, dedicated to pushing the boundaries of applied machine learning.
              </p>
            </div>
          </FadeIn>

          {/* Supervisor Card - Image Right, Text Left */}
          <FadeIn direction="left" className="mb-32">
            <div className="flex flex-col lg:flex-row items-center gap-16 relative">
              {/* Text Side (Left) */}
              <div className="flex-1 order-2 lg:order-1">
                <div className="flex items-center gap-2 mb-4">
                  <div className="h-px w-8 bg-primary"></div>
                  <span className="text-sm font-mono uppercase tracking-widest text-primary">Academic Leadership</span>
                </div>
                <h3 className="text-4xl font-bold mb-2 tracking-tight">M. Umer Iqbal</h3>
                <div className="text-muted font-medium text-lg tracking-wide mb-6">Project Supervisor & Lecturer, NUCES CFD</div>
                
                <p className="text-text/80 leading-relaxed text-lg mb-8">
                  An expert in Evolutionary Algorithms, Computational Optimization, and Requirement Engineering with a distinguished MS(CS) from FAST-NUCES. Sir Umer Iqbal provides the strategic vision, rigorous academic constraints, and crucial industry insights that steer the Lectra-AI platform toward scalable, enterprise-ready solutions.
                </p>
                
                <a href="https://scholar.google.com/citations?user=zmYMwvgAAAAJ&hl=en" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 font-medium text-white bg-primary px-6 py-3 rounded-lg hover:bg-primary-dark transition-all duration-300 shadow-sm">
                  <BookOpen className="w-4 h-4" />
                  View Research Publications
                </a>
              </div>
              
              {/* Image Side (Right) */}
              <div className="flex-1 order-1 lg:order-2 w-full">
                <div className="relative aspect-square max-w-md ml-auto">
                  <div className="absolute inset-0 bg-gradient-to-tr from-primary to-accent rounded-3xl transform rotate-3 scale-105 opacity-20 blur-lg"></div>
                  <div className="w-full h-full rounded-3xl overflow-hidden bg-surface border border-border relative z-10 shadow-xl">
                    <img 
                      src="/supervisor.jpg" 
                      alt="M. Umer Iqbal" 
                      className="w-full h-full object-cover transition-transform duration-700 hover:scale-105"
                      onError={(e) => {
                        const target = e.target as HTMLImageElement;
                        target.src = "https://ui-avatars.com/api/?name=Umer+Iqbal&size=800&background=random";
                      }}
                    />
                  </div>
                </div>
              </div>
            </div>
          </FadeIn>

          <FadeIn direction="up">
            <div className="flex items-center gap-4 mb-16">
              <h3 className="text-3xl font-bold tracking-tight">Core Development Team</h3>
              <div className="flex-1 h-px bg-gradient-to-r from-border to-transparent"></div>
            </div>
          </FadeIn>

          <div className="flex flex-col gap-24">
            {team.map((member, idx) => {
              const isEven = idx % 2 === 0;
              return (
                <FadeIn key={idx} direction={isEven ? "right" : "left"} delay={idx * 100}>
                  <div className={`flex flex-col gap-12 items-center ${isEven ? 'md:flex-row' : 'md:flex-row-reverse'}`}>
                    
                    {/* Image Side */}
                    <div className="w-full md:w-5/12 lg:w-1/3">
                      <div className="aspect-square rounded-3xl overflow-hidden bg-surface border border-border shadow-md group">
                        <img 
                          src={member.image} 
                          alt={member.name}
                          className="w-full h-full object-cover grayscale opacity-80 group-hover:grayscale-0 group-hover:opacity-100 transition-all duration-700 group-hover:scale-105"
                        />
                      </div>
                    </div>
                    
                    {/* Text Side */}
                    <div className="w-full md:w-7/12 lg:w-2/3 flex flex-col justify-center">
                      <h3 className="text-3xl font-bold mb-2 tracking-tight">{member.name}</h3>
                      <div className="text-primary font-semibold tracking-wide uppercase mb-6 flex items-center gap-2 text-sm">
                        <Code className="w-4 h-4" />
                        {member.role}
                      </div>
                      
                      <p className="text-muted leading-relaxed text-lg mb-8 max-w-2xl">
                        {member.bio}
                      </p>
                      
                      <div className="flex flex-wrap gap-2 mb-8">
                        {member.expertise.map((skill, i) => (
                          <span key={i} className="px-3 py-1 bg-surface border border-border rounded-md text-sm font-medium text-text/80 shadow-sm">
                            {skill}
                          </span>
                        ))}
                      </div>

                      <div className="flex items-center gap-4">
                        <a href={member.github} className="p-3 bg-surface border border-border rounded-xl text-muted hover:text-primary hover:border-primary transition-all duration-300 shadow-sm">
                          <Github className="w-5 h-5" />
                        </a>
                        <a href={member.linkedin} className="p-3 bg-surface border border-border rounded-xl text-muted hover:text-primary hover:border-primary transition-all duration-300 shadow-sm">
                          <Linkedin className="w-5 h-5" />
                        </a>
                      </div>
                    </div>

                  </div>
                </FadeIn>
              );
            })}
          </div>
        </div>
      </section>

      {/* Modern B2B CTA Section */}
      <section className="py-32 relative overflow-hidden bg-surface">
        {/* Abstract Background patterns */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-px bg-gradient-to-r from-transparent via-primary to-transparent opacity-50" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-primary/5 via-transparent to-transparent pointer-events-none" />
        
        <FadeIn direction="up">
          <div className="max-w-4xl mx-auto px-6 text-center relative z-10">
            <h2 className="text-5xl font-bold tracking-tight mb-6">Experience the Difference</h2>
            <p className="text-xl text-muted mb-12 leading-relaxed max-w-2xl mx-auto">
              Our advanced diarization and noise-cancellation models are ready to transform your audio. Fully free, open-source, and engineered for scale.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-6">
              <Link
                to="/app/upload"
                className="flex items-center gap-3 bg-primary text-white hover:bg-primary-dark px-8 py-4 rounded-xl font-bold transition-all duration-300 shadow-md hover:shadow-lg hover:-translate-y-1 text-lg"
              >
                Access the Platform
                <ArrowRight className="w-5 h-5" />
              </Link>
              <a
                href="https://github.com"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3 bg-surface text-text border border-border hover:border-primary hover:text-primary px-8 py-4 rounded-xl font-bold transition-all duration-300 text-lg shadow-sm"
              >
                <Github className="w-5 h-5" />
                View Source
              </a>
            </div>
          </div>
        </FadeIn>
      </section>
    </div>
  );
}
