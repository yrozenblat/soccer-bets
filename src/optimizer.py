from __future__ import annotations
import itertools
from .scoring import score_prediction
from .classifier import classify, CATEGORIES, classify_v3, CATEGORIES_V3, classify_v4

# score_candidate_list per category (favorite-relative: fav_goals, und_goals)
SCORE_CANDIDATES: dict[str, list[tuple[int, int]]] = {
    "Dominant": [(1, 0), (2, 0), (2, 1), (3, 0), (3, 1), (1, 1), (0, 0), (2, 2)],
    "Contested": [(1, 0), (2, 0), (2, 1), (3, 0), (3, 1), (1, 1), (0, 0), (2, 2)],
    "Open":      [(1, 0), (2, 0), (2, 1), (3, 0), (3, 1), (1, 1), (0, 0), (2, 2),
                  (0, 1), (0, 2), (1, 2)],
}


def _best_canonical_score(
    matches: list[dict], category: str
) -> tuple[tuple[int, int] | None, int]:
    """
    Find the canonical_score from the score_candidate_list that maximizes
    total points_scoring for the given matches.
    Returns (score, total_points). Returns (None, 0) if no matches.
    """
    if not matches:
        return None, 0

    best_score, best_pts = None, -1
    for cand in SCORE_CANDIDATES[category]:
        pts = sum(
            score_prediction(cand[0], cand[1], m["actual_fav"], m["actual_und"])
            for m in matches
        )
        if pts > best_pts:
            best_pts = pts
            best_score = cand

    return best_score, best_pts


def optimize(
    matches: list[dict],
    threshold_values: list[float],
) -> dict:
    """
    joint_optimization: grid search over all (t_lower, t_upper) pairs.

    For each valid pair, classifies every match, finds the best canonical_score
    per category, and records total points. Returns the configuration with the
    highest total points on the provided matches (training_set).

    Args:
        matches: output of data.load_matches()
        threshold_values: sorted list of candidate threshold values to try

    Returns dict with keys:
        t_lower, t_upper       — winning classification_threshold pair
        canonical_scores       — {category: (fav_goals, und_goals)}
        category_counts        — {category: match_count}
        category_points        — {category: points}
        total_points           — sum of all points
    """
    best: dict | None = None
    best_pts = -1

    for t_lower, t_upper in itertools.combinations(threshold_values, 2):
        # classify every match
        buckets: dict[str, list[dict]] = {c: [] for c in CATEGORIES}
        for m in matches:
            cat = classify(m["fav_prob"], t_lower, t_upper)
            buckets[cat].append(m)

        # find best canonical score per category
        canonical: dict[str, tuple[int, int] | None] = {}
        cat_pts: dict[str, int] = {}
        total = 0
        for cat in CATEGORIES:
            score, pts = _best_canonical_score(buckets[cat], cat)
            canonical[cat] = score
            cat_pts[cat] = pts
            total += pts

        if total > best_pts:
            best_pts = total
            best = dict(
                t_lower=t_lower,
                t_upper=t_upper,
                canonical_scores=canonical,
                category_counts={c: len(buckets[c]) for c in CATEGORIES},
                category_points=cat_pts,
                total_points=total,
            )

    return best  # end optimize


# ---------------------------------------------------------------------------
# v3: 6-category optimizer (base category × goals tier split on draw_prob)
# ---------------------------------------------------------------------------

SCORE_CANDIDATES_V3: dict[str, list[tuple[int, int]]] = {
    f"{cat}-{tier}": SCORE_CANDIDATES[cat]
    for cat in CATEGORIES
    for tier in ("Hi", "Lo")
}


def optimize_v3(
    matches: list[dict],
    threshold_values: list[float],
    draw_threshold_values: list[float],
) -> dict:
    """
    v3 joint_optimization: grid search over (t_lower, t_upper, d_threshold).

    Classifies every match into one of 6 categories (base × goals tier),
    finds the best canonical_score per category, returns the best config.

    Returns dict with keys:
        t_lower, t_upper, d_threshold
        canonical_scores       — {category: (fav_goals, und_goals)}
        category_counts        — {category: match_count}
        category_points        — {category: points}
        total_points
    """
    best: dict | None = None
    best_pts = -1

    for t_lower, t_upper in itertools.combinations(threshold_values, 2):
        for d_threshold in draw_threshold_values:
            buckets: dict[str, list[dict]] = {c: [] for c in CATEGORIES_V3}
            for m in matches:
                cat = classify_v3(m["fav_prob"], m["draw_prob"], t_lower, t_upper, d_threshold)
                buckets[cat].append(m)

            canonical: dict[str, tuple[int, int] | None] = {}
            cat_pts: dict[str, int] = {}
            total = 0
            for cat in CATEGORIES_V3:
                base_cat = cat.split("-")[0]
                score, pts = _best_canonical_score(buckets[cat], base_cat)
                canonical[cat] = score
                cat_pts[cat] = pts
                total += pts

            if total > best_pts:
                best_pts = total
                best = dict(
                    t_lower=t_lower,
                    t_upper=t_upper,
                    d_threshold=d_threshold,
                    canonical_scores=canonical,
                    category_counts={c: len(buckets[c]) for c in CATEGORIES_V3},
                    category_points=cat_pts,
                    total_points=total,
                )

    return best


def optimize_v4(
    matches: list[dict],
    threshold_values: list[float],
    ou_threshold_values: list[float],
) -> dict:
    """
    v4 joint_optimization: grid search over (t_lower, t_upper, ou_threshold).

    Classifies every match into one of 6 categories using Poisson-implied O/U
    as the goals-tier split (Hi/Lo). Requires matches to have an 'implied_ou' field.
    """
    best: dict | None = None
    best_pts = -1

    for t_lower, t_upper in itertools.combinations(threshold_values, 2):
        for ou_threshold in ou_threshold_values:
            buckets: dict[str, list[dict]] = {c: [] for c in CATEGORIES_V3}
            for m in matches:
                cat = classify_v4(m["fav_prob"], m["implied_ou"], t_lower, t_upper, ou_threshold)
                buckets[cat].append(m)

            canonical: dict[str, tuple[int, int] | None] = {}
            cat_pts: dict[str, int] = {}
            total = 0
            for cat in CATEGORIES_V3:
                base_cat = cat.split("-")[0]
                score, pts = _best_canonical_score(buckets[cat], base_cat)
                canonical[cat] = score
                cat_pts[cat] = pts
                total += pts

            if total > best_pts:
                best_pts = total
                best = dict(
                    t_lower=t_lower,
                    t_upper=t_upper,
                    ou_threshold=ou_threshold,
                    canonical_scores=canonical,
                    category_counts={c: len(buckets[c]) for c in CATEGORIES_V3},
                    category_points=cat_pts,
                    total_points=total,
                )

    return best
