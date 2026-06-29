/**
 * App.jsx
 * Root component. Manages the 4-step wizard state machine:
 *   1. JD Input  →  2. CV Upload  →  3. Processing  →  4. Results
 */

import { useState, useCallback, useEffect } from 'react';
import StepIndicator    from './components/StepIndicator';
import JDStep           from './components/JDStep';
import UploadStep       from './components/UploadStep';
import ProcessingStep   from './components/ProcessingStep';
import ResultsStep      from './components/ResultsStep';

function getInitialTheme() {
  try {
    const stored = localStorage.getItem('recruitai-theme');
    if (stored) return stored;
  } catch (_) { void _; } // eslint-disable-line
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

export default function App() {
  const [step, setStep]         = useState(1);   // 1 | 2 | 3 | 4
  const [parsedJD, setParsedJD]   = useState(null);
  const [jobId, setJobId]         = useState(null);
  const [results, setResults]     = useState(null);
  const [theme, setTheme]         = useState(getInitialTheme);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    // eslint-disable-next-line
    try { localStorage.setItem('recruitai-theme', theme); } catch (_) { void _; }
  }, [theme]);

  function toggleTheme() {
    setTheme(t => t === 'dark' ? 'light' : 'dark');
  }

  // Step 1 → 2
  function handleJDParsed(jd) {
    setParsedJD(jd);
    setStep(2);
  }

  // Step 2 → 3
  function handleUploaded(id) {
    setJobId(id);
    setStep(3);
  }

  // Step 3 → 4
  const handleComplete = useCallback((res) => {
    setResults(res);
    setStep(4);
  }, []);

  // Reset to step 1
  function handleRestart() {
    setParsedJD(null);
    setJobId(null);
    setResults(null);
    setStep(1);
  }

  return (
    <div className="app-wrapper">
      {/* ── Header ── */}
      <header className="header">
        <div className="container header-inner">
          <a className="logo" href="/" aria-label="RecruitAI Home">
            <div className="logo-icon" aria-hidden="true">⚡</div>
            <span className="logo-name">Recruit<span>AI</span></span>
          </a>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div className="header-badge">Powered by Groq · Llama 3.3</div>
            <button
              className="theme-toggle"
              onClick={toggleTheme}
              aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
              title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            >
              {theme === 'dark' ? '☀️' : '🌙'}
            </button>
          </div>
        </div>
      </header>

      {/* ── Main ── */}
      <main style={{ flex: 1, paddingBottom: 64 }}>
        <div className="container">
          {/* Hero — only on step 1 */}
          {step === 1 && (
            <section className="hero" aria-label="Hero">
              <div className="hero-tag">AI Recruitment Platform</div>
              <h1 className="hero-title">
                Screen smarter.<br />
                <span className="grad-text">Hire better.</span>
              </h1>
              <p className="hero-subtitle">
                Paste a job description, upload résumés, and let our AI rank every candidate
                with transparent scores, gap analysis, and tailored interview questions.
              </p>
            </section>
          )}

          {/* Step header for steps 2–4 */}
          {step > 1 && (
            <div style={{ paddingTop: 40, paddingBottom: 8 }}>
              {parsedJD?.job_title && (
                <div style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 8,
                  fontSize: '0.8rem',
                  color: 'var(--text-muted)',
                  marginBottom: 12,
                  background: 'var(--bg-glass)',
                  border: '1px solid var(--border)',
                  borderRadius: '20px',
                  padding: '4px 12px',
                }}>
                  <span>📋</span>
                  <span>{parsedJD.job_title}</span>
                  {parsedJD.experience_level && (
                    <span style={{ color: 'var(--accent-1)' }}>· {parsedJD.experience_level}</span>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Step indicator */}
          <StepIndicator currentStep={step} />

          {/* Step panels */}
          <div className="glass-card">
            {step === 1 && (
              <JDStep onParsed={handleJDParsed} />
            )}
            {step === 2 && (
              <UploadStep
                parsedJD={parsedJD}
                onUploaded={handleUploaded}
                onBack={() => setStep(1)}
              />
            )}
            {step === 3 && (
              <ProcessingStep
                jobId={jobId}
                onComplete={handleComplete}
              />
            )}
            {step === 4 && (
              <ResultsStep
                results={results}
                onRestart={handleRestart}
              />
            )}
          </div>
        </div>
      </main>

      {/* ── Footer ── */}
      <footer className="footer">
        <div className="container">
          RecruitAI · AI-Augmented Candidate Screening
        </div>
      </footer>
    </div>
  );
}
