/**
 * CandidateCard.jsx
 * Expandable card for a single ranked candidate.
 */

import { useState, useCallback } from 'react';
import { scoreColor } from '../scoreBands';

const SCORE_DIMS = [
  { key: 'hard_skills', label: 'Hard Skills', weight: '35%' },
  { key: 'must_have', label: 'Must-Have', weight: '30%' },
  { key: 'experience_fit', label: 'Experience', weight: '15%' },
  { key: 'soft_skills', label: 'Soft Skills', weight: '10%' },
  { key: 'domain_knowledge', label: 'Domain Knowledge', weight: '10%' },
];

function rankBadgeClass(rank) {
  if (rank === 1) return 'r1';
  if (rank === 2) return 'r2';
  if (rank === 3) return 'r3';
  return 'rn';
}

function rankEmoji(rank) {
  if (rank === 1) return '🥇';
  if (rank === 2) return '🥈';
  if (rank === 3) return '🥉';
  return `#${rank}`;
}

export default function CandidateCard({ candidate, style }) {
  const [open, setOpen] = useState(false);
  const sb = candidate.score_breakdown;
  const total = sb?.total ?? 0;
  const color = scoreColor(total);
  const isGem = candidate.is_bias_flagged;

  const handleToggle = useCallback(() => setOpen(o => !o), []);
  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setOpen(o => !o); }
  }, []);

  return (
    <div className={`candidate-card rank-${candidate.rank <= 3 ? candidate.rank : 'n'}${isGem ? ' hidden-gem' : ''}`} style={style} id={`candidate-${candidate.candidate_id}`}>
      <div className="card-summary" onClick={handleToggle} onKeyDown={handleKeyDown} role="button" tabIndex={0} aria-expanded={open} aria-label={`${candidate.name}, rank ${candidate.rank}, score ${Math.round(total)}. ${open ? 'Click to collapse' : 'Click to expand'}`}>
        <div className={`rank-badge ${rankBadgeClass(candidate.rank)}`}>{rankEmoji(candidate.rank)}</div>
        <div className="candidate-info">
          <div className="candidate-name">{candidate.name}</div>
          <div className="candidate-file">{candidate.filename}</div>
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'flex-end', flex: 1 }}>
          {SCORE_DIMS.slice(0, 3).map(d => {
            const val = sb?.[d.key] ?? 0;
            const c = scoreColor(val);
            return (
              <div key={d.key} style={{ fontSize: '0.68rem', fontWeight: 700, padding: '2px 8px', borderRadius: 12, background: `${c}18`, border: `1px solid ${c}44`, color: c, whiteSpace: 'nowrap' }}>
                {d.label.split(' ')[0]} {Math.round(val)}
              </div>
            );
          })}
        </div>
        {isGem && <div className="gem-badge">💎 Hidden Gem</div>}
        <div className="score-circle" style={{ borderColor: color, color }}>
          <span className="score-circle-value" style={{ color }}>{Math.round(total)}</span>
          <span className="score-circle-label" style={{ color: 'var(--text-muted)' }}>/ 100</span>
        </div>
        <span className={`expand-chevron ${open ? 'open' : ''}`}>▼</span>
      </div>

      <div className={`card-detail ${open ? 'open' : ''}`}>
        <div className="detail-grid">
          <div>
            <div className="detail-section-title">Score Breakdown</div>
            <div className="score-bars">
              {SCORE_DIMS.map(d => {
                const val = sb?.[d.key] ?? 0;
                const c = scoreColor(val);
                return (
                  <div className="score-bar-row" key={d.key}>
                    <span className="score-bar-label" title={`Weight: ${d.weight}`}>{d.label}</span>
                    <div className="score-bar-track">
                      <div className="score-bar-fill" style={{ width: open ? `${val}%` : '0%', background: c }} />
                    </div>
                    <span className="score-bar-num" style={{ color: c }}>{Math.round(val)}</span>
                  </div>
                );
              })}
            </div>
          </div>
          <div>
            {candidate.gaps?.length > 0 && (
              <div className="mb-20">
                <div className="detail-section-title">Identified Gaps</div>
                <div className="gaps-list">
                  {candidate.gaps.map((g, i) => <div className="gap-item" key={i}>{g}</div>)}
                </div>
              </div>
            )}
            {candidate.interview_questions?.length > 0 && (
              <div>
                <div className="detail-section-title">Interview Questions</div>
                <div className="questions-list">
                  {candidate.interview_questions.map((q, i) => (
                    <div className="question-item" key={i}>
                      <span className="question-num">Q{i + 1}</span>
                      <span>{q}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
        {candidate.explanation && (
          <div>
            <div className="detail-section-title">AI Assessment</div>
            <div className="explanation-text">{candidate.explanation}</div>
          </div>
        )}
        {isGem && candidate.bias_note && (
          <div className="bias-note-box">
            <span className="bias-note-icon">💎</span>
            <span>{candidate.bias_note}</span>
          </div>
        )}
        {(candidate.email || candidate.phone) && (
          <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border)', display: 'flex', gap: 20, flexWrap: 'wrap' }}>
            {candidate.email && (
              <a href={`mailto:${candidate.email}`} style={{ fontSize: '0.82rem', color: 'var(--accent-3)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 6 }} onClick={e => e.stopPropagation()}>
                <span>✉</span> {candidate.email}
              </a>
            )}
            {candidate.phone && (
              <a href={`tel:${candidate.phone}`} style={{ fontSize: '0.82rem', color: 'var(--accent-3)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 6 }} onClick={e => e.stopPropagation()}>
                <span>📞</span> {candidate.phone}
              </a>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
