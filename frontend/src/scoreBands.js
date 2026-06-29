/**
 * scoreBands.js
 * Single source of truth for how a 0–100 score maps to a band, a colour,
 * and a human-readable range. Used by CandidateCard (score colours), and by
 * ResultsStep (filter buttons + the colour legend) so they can never drift
 * out of sync.
 */

export const SCORE_BANDS = [
  { key: 'great', label: 'Strong',  range: '≥75',   color: 'var(--score-great)', test: v => v >= 75 },
  { key: 'good',  label: 'Good',    range: '55–74', color: 'var(--score-good)',  test: v => v >= 55 && v < 75 },
  { key: 'mid',   label: 'Average', range: '35–54', color: 'var(--score-mid)',   test: v => v >= 35 && v < 55 },
  { key: 'low',   label: 'Weak',    range: '<35',   color: 'var(--score-low)',   test: v => v < 35 },
];

/** The band a given score falls into (always returns a band). */
export function scoreBand(val) {
  return SCORE_BANDS.find(b => b.test(val)) ?? SCORE_BANDS[SCORE_BANDS.length - 1];
}

/** CSS colour variable for a given score. */
export function scoreColor(val) {
  return scoreBand(val).color;
}
