import { Send, Bot, User, Clock, ChevronDown } from 'lucide-react';

export function Chat() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-12 flex flex-col h-[calc(100vh-80px)]">
      <div className="flex items-center justify-between mb-6 shrink-0">
        <div>
          <h1 className="font-display text-3xl mb-1">Ask Your Lecture</h1>
          <p className="text-sm text-muted">Powered by RAG</p>
        </div>
        
        <div className="relative">
          <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface border border-border text-sm font-medium hover:bg-surface2 transition-colors">
            Machine Learning - Lecture 3
            <ChevronDown className="w-4 h-4 text-muted" />
          </button>
        </div>
      </div>
      
      <div className="flex-1 bg-surface border border-border rounded-2xl overflow-hidden flex flex-col shadow-sm">
        <div className="flex-1 p-6 overflow-y-auto space-y-6">
          
          {/* AI Welcome */}
          <div className="flex gap-4">
            <div className="w-8 h-8 rounded-full bg-accent-light flex items-center justify-center shrink-0">
              <Bot className="w-5 h-5 text-accent" />
            </div>
            <div className="bg-surface2 rounded-2xl rounded-tl-none p-4 max-w-[80%]">
              <p className="text-sm leading-relaxed">Hi! I'm ready to answer questions about "Machine Learning - Lecture 3". You can ask me in English, Urdu, or Roman Urdu.</p>
            </div>
          </div>
          
          {/* User Question */}
          <div className="flex gap-4 flex-row-reverse">
            <div className="w-8 h-8 rounded-full bg-teal-light flex items-center justify-center shrink-0">
              <User className="w-5 h-5 text-teal" />
            </div>
            <div className="bg-accent text-white rounded-2xl rounded-tr-none p-4 max-w-[80%]">
              <p className="text-sm leading-relaxed">Can you explain gradient descent again? Specifically the learning rate part.</p>
            </div>
          </div>
          
          {/* AI Answer with Citation */}
          <div className="flex gap-4">
            <div className="w-8 h-8 rounded-full bg-accent-light flex items-center justify-center shrink-0">
              <Bot className="w-5 h-5 text-accent" />
            </div>
            <div className="bg-surface2 rounded-2xl rounded-tl-none p-4 max-w-[80%]">
              <p className="text-sm leading-relaxed mb-3">Gradient descent is an optimization algorithm used to minimize the loss function. The learning rate determines the size of the steps taken towards the minimum.</p>
              <p className="text-sm leading-relaxed mb-4">If the learning rate is too large, you might overshoot the minimum. If it's too small, it will take a very long time to converge.</p>
              
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-muted uppercase tracking-widest">Source:</span>
                <button className="flex items-center gap-1 px-2 py-1 rounded bg-surface border border-border text-xs font-medium hover:border-accent2 transition-colors">
                  <Clock className="w-3 h-3 text-accent" /> 14:32
                </button>
                <button className="flex items-center gap-1 px-2 py-1 rounded bg-surface border border-border text-xs font-medium hover:border-accent2 transition-colors">
                  <Clock className="w-3 h-3 text-accent" /> 16:05
                </button>
              </div>
            </div>
          </div>
          
          {/* User Question Urdu */}
          <div className="flex gap-4 flex-row-reverse">
            <div className="w-8 h-8 rounded-full bg-teal-light flex items-center justify-center shrink-0">
              <User className="w-5 h-5 text-teal" />
            </div>
            <div className="bg-accent text-white rounded-2xl rounded-tr-none p-4 max-w-[80%]">
              <p className="text-sm leading-relaxed">Mujhe samajh nahi aya, thora asaan alfaz mein batao.</p>
            </div>
          </div>
          
          {/* AI Answer Urdu */}
          <div className="flex gap-4">
            <div className="w-8 h-8 rounded-full bg-accent-light flex items-center justify-center shrink-0">
              <Bot className="w-5 h-5 text-accent" />
            </div>
            <div className="bg-surface2 rounded-2xl rounded-tl-none p-4 max-w-[80%]">
              <p className="text-sm leading-relaxed mb-3">Zaroor. Farz karein aap ek pahari (hill) se neechay utar rahay hain aur aapki aankhon par patti bandhi hai. Aapko sab se nichlay point (minimum loss) tak pohanchna hai.</p>
              <p className="text-sm leading-relaxed mb-4">Learning rate aapke qadam (steps) ka size hai. Agar aap bohat baray qadam lein ge (high learning rate), toh aap shayad nichlay point se aagay nikal jayein. Agar aap bohat chotay qadam lein ge (low learning rate), toh aapko pohanchne mein bohat waqt lagay ga.</p>
            </div>
          </div>
          
        </div>
        
        <div className="p-4 bg-surface border-t border-border">
          <div className="relative">
            <input 
              type="text" 
              placeholder="Ask a question about this lecture..." 
              className="w-full pl-4 pr-12 py-3 rounded-xl border border-border bg-bg focus:border-accent outline-none"
            />
            <button className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-lg bg-accent text-white flex items-center justify-center hover:bg-accent2 transition-colors">
              <Send className="w-4 h-4 ml-0.5" />
            </button>
          </div>
          <div className="flex items-center justify-between mt-2 px-2">
            <span className="text-[10px] font-mono text-muted uppercase tracking-widest">Press Enter to send</span>
            <div className="flex gap-2">
              <button className="text-[10px] font-mono text-accent uppercase tracking-widest hover:underline">English</button>
              <button className="text-[10px] font-mono text-muted uppercase tracking-widest hover:underline">Urdu</button>
              <button className="text-[10px] font-mono text-muted uppercase tracking-widest hover:underline">Roman Urdu</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
