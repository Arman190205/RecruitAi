"""
services/skill_matcher.py
-------------------------
Semantic skill / requirement matching — the deterministic, math-based half of
scoring.

Given a list of *required* items (from the JD) and a list of *candidate* items
(from the CV), it computes how many requirements the candidate covers — matching
by MEANING, not exact string, so "k8s" counts as "Kubernetes".

Two backends, chosen automatically at runtime:
  - **embeddings**  (sentence-transformers) → true semantic cosine similarity.
                     Used when the library is installed.
  - **fuzzy fallback** (normalise + synonym map + token overlap) → no heavy
                     dependency. Used when embeddings aren't available (e.g. on a
                     memory-constrained free-tier host).

Either way the output is a real, auditable number — `coverage` is literally
"% of required items the candidate has" — instead of an LLM's guessed score.
"""

import logging
import re

logger = logging.getLogger(__name__)

# ─── Common tech aliases (used by BOTH backends to normalise inputs) ───────────
# Keeps the fuzzy fallback useful and gives the embedding model cleaner tokens.
_SYNONYMS = {
    "k8s": "kubernetes",
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "ml": "machine learning",
    "dl": "deep learning",
    "ai": "artificial intelligence",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "gcp": "google cloud platform",
    "aws": "amazon web services",
    "pg": "postgresql",
    "postgres": "postgresql",
    "k8": "kubernetes",
    "react.js": "react",
    "reactjs": "react",
    "node": "node.js",
    "nodejs": "node.js",
    "tf": "tensorflow",
    "ci/cd": "continuous integration continuous deployment",
}

_MATCH_THRESHOLD = 0.55  # cosine sim (embeddings) above which two items "match"

# Lazily-initialised embedding backend.
_model = None
_backend: str | None = None  # "embeddings" | "fuzzy"


def _normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = (text or "").lower().strip()
    text = re.sub(r"[^a-z0-9+#./ ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _expand(text: str) -> str:
    """Replace known aliases token-wise (e.g. 'k8s' → 'kubernetes')."""
    tokens = [_SYNONYMS.get(t, t) for t in text.split()]
    # also handle whole-string aliases like "ci/cd"
    return _SYNONYMS.get(text, " ".join(tokens))


def _ensure_backend() -> None:
    """Pick the matching backend once, on first use."""
    global _model, _backend
    if _backend is not None:
        return
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore

        _model = SentenceTransformer("all-MiniLM-L6-v2")
        _backend = "embeddings"
        logger.info("skill_matcher: using sentence-transformers embeddings backend")
    except Exception as exc:  # ImportError, or model download/load failure
        _backend = "fuzzy"
        logger.info(
            "skill_matcher: embeddings unavailable (%s) — using fuzzy fallback", exc
        )


def backend_name() -> str:
    """Return which matching backend is active ('embeddings' or 'fuzzy')."""
    _ensure_backend()
    return _backend  # type: ignore[return-value]


def match_coverage(
    required: list[str],
    candidate: list[str],
    threshold: float = _MATCH_THRESHOLD,
) -> tuple[float, list[str], list[str]]:
    """
    Compute how well ``candidate`` items cover ``required`` items.

    Returns:
        (coverage, matched, missing) where
          - coverage : float 0–100  = % of required items matched
          - matched  : the required items the candidate satisfies
          - missing  : the required items the candidate lacks
    """
    required = [r for r in (required or []) if r and r.strip()]
    if not required:
        return 100.0, [], []  # nothing required → fully covered
    candidate = [c for c in (candidate or []) if c and c.strip()]
    if not candidate:
        return 0.0, [], list(required)

    _ensure_backend()
    if _backend == "embeddings":
        hits = _embed_match(required, candidate, threshold)
    else:
        hits = _fuzzy_match(required, candidate)

    matched = [r for r, ok in zip(required, hits) if ok]
    missing = [r for r, ok in zip(required, hits) if not ok]
    coverage = round(100.0 * len(matched) / len(required), 1)
    return coverage, matched, missing


# ─── Backend: embeddings ───────────────────────────────────────────────────────

def _embed_match(required: list[str], candidate: list[str], threshold: float) -> list[bool]:
    """For each required item, True if its best cosine sim to any candidate ≥ threshold."""
    from sentence_transformers import util  # type: ignore

    req_emb = _model.encode([_expand(_normalize(r)) for r in required], convert_to_tensor=True)
    cand_emb = _model.encode([_expand(_normalize(c)) for c in candidate], convert_to_tensor=True)
    sim = util.cos_sim(req_emb, cand_emb)  # shape: [len(required) x len(candidate)]
    return [float(sim[i].max()) >= threshold for i in range(len(required))]


# ─── Backend: fuzzy fallback ────────────────────────────────────────────────────

def _fuzzy_match(required: list[str], candidate: list[str]) -> list[bool]:
    """For each required item, True if any candidate item is a fuzzy hit."""
    cand_norm = [_expand(_normalize(c)) for c in candidate]
    return [any(_fuzzy_hit(_expand(_normalize(r)), cn) for cn in cand_norm) for r in required]


def _fuzzy_hit(a: str, b: str) -> bool:
    """Exact / substring / token-overlap match between two normalised strings."""
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    ta, tb = set(a.split()), set(b.split())
    if ta and tb:
        jaccard = len(ta & tb) / len(ta | tb)
        return jaccard >= 0.5
    return False
