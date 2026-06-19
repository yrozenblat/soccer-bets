"""
Entry point for the joint_optimization run.

Usage:
    python optimize.py data/wc2018.csv [models/v2.json]

Loads the training_set, runs the optimizer, prints the best configuration,
then scores all four baselines for comparison.
Optionally saves the best config to a model JSON file.
"""
from __future__ import annotations
import sys
from collections import Counter
from src.data import load_matches
from src.scoring import score_prediction
from src.optimizer import optimize, optimize_v3, optimize_v4
from src import model as model_io

# Threshold search space: favorite win probability from 0.45 to 0.80 in 0.025 steps.
THRESHOLD_VALUES = [round(0.45 + i * 0.025, 3) for i in range(15)]  # 0.450 … 0.800

# v3: draw probability split threshold search space (0.18 to 0.30 in 0.01 steps).
DRAW_THRESHOLD_VALUES = [round(0.18 + i * 0.01, 2) for i in range(13)]  # 0.18 … 0.30

# v4: implied O/U split threshold search space (2.0 to 3.0 in 0.05 steps).
OU_THRESHOLD_VALUES = [round(2.0 + i * 0.05, 2) for i in range(21)]  # 2.00 … 3.00


# ---------------------------------------------------------------------------
# Baselines
# ---------------------------------------------------------------------------

def _score_fixed(matches: list[dict], fav_goals: int, und_goals: int) -> int:
    return sum(
        score_prediction(fav_goals, und_goals, m["actual_fav"], m["actual_und"])
        for m in matches
    )


def baseline_always_1_0(matches: list[dict]) -> int:
    """Always predict favorite wins 1–0."""
    return _score_fixed(matches, 1, 0)


def baseline_always_1_1(matches: list[dict]) -> int:
    """Always predict 1–1."""
    return _score_fixed(matches, 1, 1)


def baseline_market_outcome_fixed_score(matches: list[dict]) -> int:
    """
    Follow the highest implied_probability outcome; assign a fixed score per outcome:
      favorite win → 1–0, draw → 1–1, underdog win → 0–1.
    """
    total = 0
    for m in matches:
        fav_prob = m["fav_prob"] if m["fav_prob"] is not None else 0.0
        draw_prob = m["draw_prob"]

        if draw_prob >= fav_prob and draw_prob >= (1 - fav_prob - draw_prob):
            pred = (1, 1)  # draw is most likely outcome
        elif fav_prob >= 0.5:
            pred = (1, 0)  # favorite win
        else:
            pred = (0, 1)  # underdog win

        total += score_prediction(pred[0], pred[1], m["actual_fav"], m["actual_und"])
    return total


def baseline_most_common_score(matches: list[dict]) -> int:
    """
    Derive the single most frequent score in the dataset and predict it for every match.
    Differentiates from baseline_always_1_0 when 1–0 is not the most common score.
    """
    freq = Counter((m["actual_fav"], m["actual_und"]) for m in matches)
    most_common_fav, most_common_und = freq.most_common(1)[0][0]
    return _score_fixed(matches, most_common_fav, most_common_und)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(path: str, output_path: str | None = None, v3: bool = False, v4: bool = False) -> None:
    matches = load_matches(path)
    n = len(matches)
    n_pairs = len(THRESHOLD_VALUES) * (len(THRESHOLD_VALUES) - 1) // 2
    print(f"Loaded {n} matches from {path}")

    if v4:
        n_combos = n_pairs * len(OU_THRESHOLD_VALUES)
        print(f"v4 search: {n_pairs} threshold pairs x {len(OU_THRESHOLD_VALUES)} O/U thresholds = {n_combos} combos")
        result = optimize_v4(matches, THRESHOLD_VALUES, OU_THRESHOLD_VALUES)
    elif v3:
        n_combos = n_pairs * len(DRAW_THRESHOLD_VALUES)
        print(f"v3 search: {n_pairs} threshold pairs x {len(DRAW_THRESHOLD_VALUES)} draw thresholds = {n_combos} combos")
        result = optimize_v3(matches, THRESHOLD_VALUES, DRAW_THRESHOLD_VALUES)
    else:
        print(f"Threshold search: {THRESHOLD_VALUES[0]}-{THRESHOLD_VALUES[-1]}  ({n_pairs} pairs)")
        result = optimize(matches, THRESHOLD_VALUES)

    print("\n--- Best configuration (training set) ---")
    if v4:
        d_tag = f"  ou_threshold={result['ou_threshold']:.2f}"
    elif v3:
        d_tag = f"  d_threshold={result['d_threshold']:.2f}"
    else:
        d_tag = ""
    print(f"  t_lower={result['t_lower']:.3f}  t_upper={result['t_upper']:.3f}{d_tag}")
    print(f"  Total: {result['total_points']} pts / {n*3} max  ({result['total_points']/n:.2f}/match)")
    print()
    for cat in sorted(result["canonical_scores"].keys()):
        score = result["canonical_scores"][cat]
        count = result["category_counts"][cat]
        pts   = result["category_points"][cat]
        score_str = f"{score[0]}-{score[1]}" if score else "n/a"
        print(f"  {cat:15s}: {count:2d} matches  canonical={score_str}  pts={pts}")

    b1 = baseline_always_1_0(matches)
    b2 = baseline_always_1_1(matches)
    b3 = baseline_market_outcome_fixed_score(matches)
    b4 = baseline_most_common_score(matches)

    print("\n--- Baselines ---")
    print(f"  Always 1-0 (favorite):           {b1:3d} pts  ({b1/n:.2f}/match)")
    print(f"  Always 1-1 (draw):               {b2:3d} pts  ({b2/n:.2f}/match)")
    print(f"  Market outcome + fixed score:    {b3:3d} pts  ({b3/n:.2f}/match)")
    print(f"  Most common score in dataset:    {b4:3d} pts  ({b4/n:.2f}/match)")

    best_baseline = max(b1, b2, b3, b4)
    model_pts = result["total_points"]
    print()
    if model_pts > best_baseline:
        print(f"  PASS - model beats all baselines  (+{model_pts - best_baseline} pts)")
    else:
        print(f"  FAIL - model does not beat all baselines  (best baseline: {best_baseline} pts)")

    if output_path:
        model_io.save(result, output_path)
        print(f"\n  Saved model config to {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python optimize.py <path-to-csv> [output-model.json] [--v3]")
        sys.exit(1)
    args = sys.argv[1:]
    use_v3 = "--v3" in args
    use_v4 = "--v4" in args
    args = [a for a in args if a not in ("--v3", "--v4")]
    main(args[0], args[1] if len(args) > 1 else None, v3=use_v3, v4=use_v4)
