/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'motion/react';
import { Layout } from './components/Layout';
import { AppLayout } from './components/AppLayout';
import { Home } from './pages/Home';
import { App as DemoApp } from './pages/App';
import { Features } from './pages/Features';
import { Docs } from './pages/Docs';
import { About } from './pages/About';
import { Login } from './pages/Login';
import { Signup } from './pages/Signup';
import { Dashboard } from './pages/Dashboard';
import { Library } from './pages/Library';
import { Quiz } from './pages/Quiz';
import { Analytics } from './pages/Analytics';
import { Chat } from './pages/Chat';
import { Lecture } from './pages/Lecture';
import { NotFound } from './pages/NotFound';

function AnimatedRoutes() {
  const location = useLocation();
  // Using location.pathname.split('/')[1] allows Layout routes to share a key
  // and AppLayout routes to share a key, so we only animate the top-level shell 
  // when switching between the main website and the app layout.
  const layoutKey = location.pathname.startsWith('/app') ? 'app' : 'public';

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={layoutKey}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        transition={{ duration: 0.3 }}
        className="w-full min-h-screen"
      >
        <Routes location={location}>
          <Route path="/" element={<Layout />}>
            <Route index element={<Home />} />
            
            <Route path="features" element={<Features />} />
          <Route path="docs" element={<Docs />} />
          <Route path="about" element={<About />} />
          <Route path="login" element={<Login />} />
          <Route path="signup" element={<Signup />} />
          
          {/* Placeholders for other routes */}
          <Route path="use-cases" element={<div className="p-24 text-center text-xl">Use Cases Page</div>} />
          <Route path="privacy" element={<div className="p-24 text-center text-xl">Privacy Policy</div>} />
          <Route path="terms" element={<div className="p-24 text-center text-xl">Terms of Service</div>} />
          
          <Route path="*" element={<NotFound />} />
        </Route>

        <Route path="/app" element={<AppLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="upload" element={<DemoApp />} />
          <Route path="library" element={<Library />} />
          <Route path="lecture/:id" element={<Lecture />} />
          <Route path="quiz" element={<Quiz />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="chat" element={<Chat />} />
        </Route>
        </Routes>
      </motion.div>
    </AnimatePresence>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AnimatedRoutes />
    </BrowserRouter>
  );
}

