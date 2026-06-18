/**
 * scoreWeights.js
 * Client-side scoring weights. Mirrors the backend defaults in
 * services/scorer.py (_WEIGHTS). Because every candidate already carries its
 * per-dimension sub-scores, the recruiter can re-weight the five dimensions
 * and the shortlist re-ranks instantly in the browser — no re-scoring round
 * trip to the LLM.
 */

export const WEIGHT_DIMS = [
  { key: 'hard_skills', label: 'Hard Skills' },
  { key: 'must_have', label: 'Must-Have' },
  { key: 'experience_fit', label: 'Experience' },
  { key: 'soft_skills', label: 'Soft Skills' },
  { key: 'domain_knowledge', label: 'Domain Knowledge' },
];

// Percentages — must match backend services/scorer.py defaults.
export const DEFAULT_WEIGHTS = {
  hard_skills: 35,
  must_have: 30,
  experience_fit: 15,
  soft_skills: 10,
  domain_knowledge: 10,
};

/** True when the given weights are (effectively) the backend defaults. */
export function isDefaultWeights(weights) {
  return WEIGHT_DIMS.every(d => Math.round(weights[d.key]) === DEFAULT_WEIGHTS[d.key]);
}

/**
 * Weighted total for one candidate's score_breakdown, given raw (un-normalised)
 * weights. Weights are normalised by their sum so the result stays on a 0–100
 * scale regardless of the slider values. Returns 0 if all weights are 0.
 */
export function weightedTotal(breakdown, weights) {
  const sum = WEIGHT_DIMS.reduce((s, d) => s + (weights[d.key] || 0), 0);
  if (sum <= 0) return 0;
  const raw = WEIGHT_DIMS.reduce(
    (s, d) => s + (breakdown?.[d.key] ?? 0) * (weights[d.key] || 0),
    0,
  );
  return raw / sum;
}

/**
 * Re-rank candidates by a custom weighting. Returns new candidate objects with
 * an overridden score_breakdown.total and freshly assigned 1..N ranks, sorted
 * best-first. The originals are left untouched.
 */
export function rerankByWeights(candidates, weights) {
  return candidates
    .map(c => ({
      ...c,
      score_breakdown: {
        ...c.score_breakdown,
        total: Math.round(weightedTotal(c.score_breakdown, weights) * 10) / 10,
      },
    }))
    .sort((a, b) => b.score_breakdown.total - a.score_breakdown.total)
    .map((c, i) => ({ ...c, rank: i + 1 }));
}
