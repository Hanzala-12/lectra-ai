import { CheckCircle2 } from 'lucide-react';
import { Link } from 'react-router-dom';

export function Pricing() {
  return (
    <div className="max-w-7xl mx-auto px-6 py-24">
      <div className="text-center mb-16">
        <h1 className="font-display text-5xl mb-6">Simple, student-friendly <em className="text-accent2 not-italic">pricing.</em></h1>
        <p className="text-xl text-muted max-w-2xl mx-auto">Start for free. Upgrade when you need more power for finals week.</p>
      </div>

      <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto mb-24">
        {/* Free */}
        <div className="bg-surface border border-border rounded-2xl p-8 flex flex-col">
          <h3 className="text-xl font-bold mb-2">Free</h3>
          <div className="flex items-baseline gap-1 mb-6">
            <span className="text-4xl font-display">$0</span>
            <span className="text-sm text-muted">/mo</span>
          </div>
          <ul className="space-y-4 mb-8 flex-1">
            <li className="flex items-start gap-3 text-sm text-muted"><CheckCircle2 className="w-5 h-5 text-teal shrink-0" /> 3 lectures per month</li>
            <li className="flex items-start gap-3 text-sm text-muted"><CheckCircle2 className="w-5 h-5 text-teal shrink-0" /> Up to 60 min per lecture</li>
            <li className="flex items-start gap-3 text-sm text-muted"><CheckCircle2 className="w-5 h-5 text-teal shrink-0" /> Basic English transcripts</li>
          </ul>
          <Link to="/app/dashboard" className="w-full text-center bg-surface2 hover:bg-surface border border-border text-text py-3 rounded-xl font-bold transition-colors">
            Start Free
          </Link>
        </div>
        
        {/* Pro */}
        <div className="bg-surface border-2 border-accent rounded-2xl p-8 flex flex-col relative transform md:-translate-y-4 shadow-[0_0_40px_rgba(124,107,255,0.15)]">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-accent text-white text-xs font-bold px-4 py-1 rounded-full">
            Most Popular
          </div>
          <h3 className="text-xl font-bold mb-2">Pro Scholar</h3>
          <div className="flex items-baseline gap-1 mb-6">
            <span className="text-4xl font-display">$9</span>
            <span className="text-sm text-muted">/mo</span>
          </div>
          <ul className="space-y-4 mb-8 flex-1">
            <li className="flex items-start gap-3 text-sm"><CheckCircle2 className="w-5 h-5 text-accent2 shrink-0" /> Unlimited lectures</li>
            <li className="flex items-start gap-3 text-sm"><CheckCircle2 className="w-5 h-5 text-accent2 shrink-0" /> Up to 3h per lecture</li>
            <li className="flex items-start gap-3 text-sm"><CheckCircle2 className="w-5 h-5 text-accent2 shrink-0" /> Urdu & Roman Urdu explanations</li>
            <li className="flex items-start gap-3 text-sm"><CheckCircle2 className="w-5 h-5 text-accent2 shrink-0" /> Unlimited quizzes & chat</li>
          </ul>
          <button className="w-full text-center bg-accent hover:bg-accent/90 text-white py-3 rounded-xl font-bold transition-colors">
            Get Pro
          </button>
        </div>
        
        {/* Team */}
        <div className="bg-surface border border-border rounded-2xl p-8 flex flex-col">
          <h3 className="text-xl font-bold mb-2">Study Group</h3>
          <div className="flex items-baseline gap-1 mb-6">
            <span className="text-4xl font-display">$24</span>
            <span className="text-sm text-muted">/mo</span>
          </div>
          <ul className="space-y-4 mb-8 flex-1">
            <li className="flex items-start gap-3 text-sm text-muted"><CheckCircle2 className="w-5 h-5 text-teal shrink-0" /> Everything in Pro</li>
            <li className="flex items-start gap-3 text-sm text-muted"><CheckCircle2 className="w-5 h-5 text-teal shrink-0" /> 5 student accounts</li>
            <li className="flex items-start gap-3 text-sm text-muted"><CheckCircle2 className="w-5 h-5 text-teal shrink-0" /> Shared lecture library</li>
          </ul>
          <button className="w-full text-center bg-surface2 hover:bg-surface border border-border text-text py-3 rounded-xl font-bold transition-colors">
            View Groups
          </button>
        </div>
      </div>

      {/* FAQ */}
      <div className="max-w-3xl mx-auto">
        <h2 className="text-2xl font-bold mb-8 text-center">Frequently Asked Questions</h2>
        <div className="space-y-4">
          <div className="bg-surface border border-border rounded-xl p-6">
            <h4 className="font-bold mb-2">Is my audio stored on your servers?</h4>
            <p className="text-muted text-sm">Files are processed and securely stored in your personal library. You can delete them at any time.</p>
          </div>
          <div className="bg-surface border border-border rounded-xl p-6">
            <h4 className="font-bold mb-2">Do you offer discounts for entire universities?</h4>
            <p className="text-muted text-sm">Yes, contact us for an institutional license. We can integrate directly with your LMS.</p>
          </div>
          <div className="bg-surface border border-border rounded-xl p-6">
            <h4 className="font-bold mb-2">How accurate are the Urdu explanations?</h4>
            <p className="text-muted text-sm">Our models are specifically fine-tuned on academic content and Pakistani educational contexts for high accuracy.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
