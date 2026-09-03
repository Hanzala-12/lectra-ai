import { Link } from 'react-router-dom';
import { ArrowLeft, Search } from 'lucide-react';

export function NotFound() {
  return (
    <div className="min-h-[80vh] flex flex-col items-center justify-center px-6 text-center">
      <div className="w-20 h-20 bg-primary-light rounded-full flex items-center justify-center mb-8">
        <Search className="w-8 h-8 text-primary" />
      </div>
      <h1 className="font-serif text-6xl font-semibold tracking-tight mb-4 text-text">404</h1>
      <h2 className="text-xl font-medium mb-6 text-muted">Page not found</h2>
      <p className="text-muted max-w-md mb-10 leading-relaxed">
        Sorry, we couldn't find the page you're looking for. It might have been moved or deleted.
      </p>
      <Link
        to="/"
        className="inline-flex items-center gap-2 bg-primary hover:bg-primary-dark text-white px-6 py-3 rounded-lg font-semibold transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Home
      </Link>
    </div>
  );
}
