/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { AppLayout } from './components/AppLayout';
import { Home } from './pages/Home';
import { App as DemoApp } from './pages/App';
import { Features } from './pages/Features';
import { Docs } from './pages/Docs';
import { About } from './pages/About';
import { Dashboard } from './pages/Dashboard';
import { Library } from './pages/Library';
import { Quiz } from './pages/Quiz';
import { Analytics } from './pages/Analytics';
import { Chat } from './pages/Chat';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          
          <Route path="app" element={<AppLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="upload" element={<DemoApp />} />
            <Route path="library" element={<Library />} />
            <Route path="quiz" element={<Quiz />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="chat" element={<Chat />} />
          </Route>
          
          <Route path="features" element={<Features />} />
          <Route path="docs" element={<Docs />} />
          <Route path="about" element={<About />} />
          
          {/* Placeholders for other routes */}
          <Route path="use-cases" element={<div className="p-24 text-center text-xl">Use Cases Page</div>} />
          <Route path="privacy" element={<div className="p-24 text-center text-xl">Privacy Policy</div>} />
          <Route path="terms" element={<div className="p-24 text-center text-xl">Terms of Service</div>} />
          
          <Route path="*" element={<div className="p-24 text-center text-xl">404 Not Found</div>} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
