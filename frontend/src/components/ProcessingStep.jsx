/**
 * ProcessingStep.jsx
 * Step 3: Polls GET /api/jobs/{id}/status every 2.5s until done/failed.
 * Shows an animated spinner, progress bar, and per-CV status list.
 */

import { useEffect, useState } from 'react';
import { getJobStatus, getJobResults } from '../api';

// Safety net: stop polling if the backend never reaches a terminal state
// (e.g. it became unreachable). Generously longer than the server-side
// PROCESSING_TIMEOUT_SECONDS so a real timeout surfaces as a "failed" status
// first, with its specific error message.
const MAX_WAIT_MS = 180_000;

const STATUS_ICON = {
  processing: '⚙️',
  done:       '✅',
  error:      '❌',
  pending:    '⏳',
};

const STATUS_MSG = {
  processing: 'Analysing candidates…',
  pending:    'Starting pipeline…',
  completed:  'Finalising results…',
};

export default function ProcessingStep({ jobId, onComplete }) {
  const [status, setStatus]       = useState(null);
  const [error, setError]         = useState('');
  const [elapsed, setElapsed]     = useState(0);

  const totalCVs = status?.total_cvs ?? 0;
  const doneCVs  = (status?.cv_statuses ?? []).filter(cv => cv.status === 'done' || cv.status === 'error').length;
  const progress = status?.progress ?? 0;

  // Elapsed timer
  useEffect(() => {
    const t = setInterval(() => setElapsed(e => e + 1), 1000);
    return () => clearInterval(t);
  }, []);

  // Poll for status
  useEffect(() => {
    if (!jobId) return;

    let cancelled = false;
    const startedAt = Date.now();

    async function poll() {
      while (!cancelled) {
        try {
          const s = await getJobStatus(jobId);
          if (!cancelled) setStatus(s);

          if (s.status === 'completed') {
            const results = await getJobResults(jobId);
            if (!cancelled) onComplete(results);
            return;
          }

          if (s.status === 'failed') {
            if (!cancelled) setError(s.error || 'Job failed for an unknown reason.');
            return;
          }
        } catch (e) {
          if (!cancelled) setError(e.message);
          return;
        }

        if (Date.now() - startedAt > MAX_WAIT_MS) {
          if (!cancelled) setError('Screening timed out — the server stopped responding. Please try again.');
          return;
        }

        await new Promise(r => setTimeout(r, 2500));
      }
    }

    poll();
    return () => { cancelled = true; };
  }, [jobId, onComplete]);

  const statusLabel = status?.status ?? 'starting';

  // Estimate remaining time: ~3s per remaining CV
  const remaining = Math.max(0, totalCVs - doneCVs);
  const estSeconds = remaining * 3;
  const estMin = Math.floor(estSeconds / 60);
  const estSec = estSeconds % 60;
  const estText = totalCVs > 0 && progress > 0 && progress < 100
    ? estMin > 0 ? `~${estMin}m ${estSec}s left` : `~${estSec}s left`
    : '';

  return (
    <div>
      <div className="mb-20">
        <h2 className="section-title">Screening in Progress</h2>
        <p className="section-desc" style={{ marginBottom: 0 }}>
          The AI is parsing and scoring each résumé. This usually takes 20–60 seconds.
        </p>
      </div>

      <div className="processing-center">
        <div className="spinner-ring" id="processing-spinner" />

        <div style={{
          fontSize: '1.1rem',
          fontFamily: 'var(--font-display)',
          fontWeight: 700,
          marginBottom: 4,
          background: 'var(--grad-brand)',
          WebkitBackgroundClip: 'text',
          backgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
        }}>
          {STATUS_MSG[statusLabel] || 'Preparing…'}
        </div>

        <div className="progress-label" style={{ display: 'flex', justifyContent: 'center', gap: 12, alignItems: 'center' }}>
          <span>{progress}% complete</span>
          <span style={{ opacity: 0.4 }}>·</span>
          <span>{elapsed}s elapsed</span>
          {estText && (
            <>
              <span style={{ opacity: 0.4 }}>·</span>
              <span style={{ color: 'var(--accent-3)' }}>{estText}</span>
            </>
          )}
        </div>

        <div className="progress-track">
          <div className="progress-fill" style={{ width: `${progress}%` }} id="progress-bar" />
        </div>

        {totalCVs > 0 && (
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 8 }}>
            {doneCVs} of {totalCVs} CVs processed
          </div>
        )}

        {status?.cv_statuses?.length > 0 && (
          <div className="cv-status-list" id="cv-status-list">
            {status.cv_statuses.map((cv, i) => (
              <div
                className="cv-status-item"
                key={`${cv.filename}-${i}`}
                style={{ animationDelay: `${i * 0.05}s` }}
              >
                <span className="cv-status-icon">{STATUS_ICON[cv.status] ?? '⏳'}</span>
                <span className="cv-status-name" title={cv.filename}>{cv.filename}</span>
                <span className={`status-badge ${cv.status}`}>{cv.status}</span>
                {cv.error && (
                  <span style={{ fontSize: '0.72rem', color: 'var(--score-low)', marginLeft: 4 }}>
                    {cv.error.slice(0, 60)}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {error && <div className="error-box mt-24">⚠ {error}</div>}
    </div>
  );
}
