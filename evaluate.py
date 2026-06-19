"""
Evaluate a model config against a dataset.

Usage:
    python evaluate.py data/wc2022.csv models/v1.json [data/wc2018.csv]

The optional third argument is the training set used for the 'most common
historical score' baseline (avoids test-set leakage).
"""
from __future__ import annotations
import sys
from collections import Counter, defaultdict
from src.data import load_matches
from src.scoring import score_prediction
from src.classifier import classify, classify_v3, classify_v4
from src import model as model_io


def apply_model(matches: list[dict], cfg: dict) -> tuple[int, list[dict]]:
    t_lower = cfg["t_lower"]
    t_upper = cfg["t_upper"]
    canonical = cfg["canonical_scores"]
    details = []
    total = 0
    for m in matches:
        if model_io.is_v4(cfg):
            cat = classify_v4(m["fav_prob"], m["implied_ou"], t_lower, t_upper, cfg["ou_threshold"])
        elif model_io.is_v3(cfg):
            cat = classify_v3(m["fav_prob"], m["draw_prob"], t_lower, t_upper, cfg["d_threshold"])
        else:
            cat = classify(m["fav_prob"], t_lower, t_upper)
        pred = canonical[cat]
        pts = score_prediction(pred[0], pred[1], m["actual_fav"], m["actual_und"])
        total += pts
        details.append({**m, "category": cat, "pred": pred, "pts": pts})
    return total, details


def _score_fixed(matches, fav, und):
    return sum(score_prediction(fav, und, m["actual_fav"], m["actual_und"]) for m in matches)


def baselines(matches: list[dict], training_matches: list[dict] | None = None) -> dict[str, int]:
    b3 = 0
    for m in matches:
        p = m["fav_prob"] if m["fav_prob"] is not None else 0.0
        pred = (1, 0) if p >= 0.5 else (1, 1)
        b3 += score_prediction(pred[0], pred[1], m["actual_fav"], m["actual_und"])
    source = training_matches if training_matches else matches
    freq = Counter((m["actual_fav"], m["actual_und"]) for m in source)
    top, top_count = freq.most_common(1)[0]
    origin = "train" if training_matches else "test"
    label = f"most_common_from_{origin} ({top[0]}-{top[1]}, n={top_count})"
    return {
        "always_1_0":           _score_fixed(matches, 1, 0),
        "always_1_1":           _score_fixed(matches, 1, 1),
        "market_outcome_fixed": b3,
        label:                  _score_fixed(matches, top[0], top[1]),
    }


def main(path: str, model_path: str, training_path: str | None = None) -> None:
    cfg = model_io.load(model_path)
    matches = load_matches(path)
    training_matches = load_matches(training_path) if training_path else None
    n = len(matches)

    if model_io.is_v4(cfg):
        extra = f"  ou_threshold={cfg['ou_threshold']}"
    elif model_io.is_v3(cfg):
        extra = f"  d_threshold={cfg['d_threshold']}"
    else:
        extra = ""
    print(f"Model : {model_path}  (t_lower={cfg['t_lower']}, t_upper={cfg['t_upper']}{extra})")
    print(f"Scores: {cfg['canonical_scores']}")
    print(f"Data  : {n} matches from {path}")
    print()

    total, details = apply_model(matches, cfg)

    by_cat: dict[str, list] = defaultdict(list)
    for d in details:
        by_cat[d["category"]].append(d)

    display_cats = sorted(cfg["canonical_scores"].keys())
    for cat in display_cats:
        cat_matches = by_cat[cat]
        cat_pts = sum(d["pts"] for d in cat_matches)
        score = cfg["canonical_scores"][cat]
        if score:
            print(f"  {cat:15s}: {len(cat_matches):2d} matches  canonical={score[0]}-{score[1]}  pts={cat_pts}")

    print()
    print(f"  Model total: {total} pts / {n*3} max  ({total/n:.2f}/match)")

    bl = baselines(matches, training_matches)
    best_baseline = max(bl.values())
    print()
    print("--- Baselines ---")
    for name, pts in bl.items():
        print(f"  {name:35s}: {pts:3d} pts  ({pts/n:.2f}/match)")

    print()
    if total > best_baseline:
        print(f"  PASS  (+{total - best_baseline} pts over best baseline)")
    else:
        print(f"  FAIL  (best baseline: {best_baseline} pts, model: {total} pts)")

    exact_hits  = sum(1 for d in details if d["pts"] == 3)
    outcome_hits = sum(1 for d in details if d["pts"] == 1)
    misses       = sum(1 for d in details if d["pts"] == 0)
    print(f"  Exact / Outcome / Miss: {exact_hits} / {outcome_hits} / {misses}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python evaluate.py <data-csv> <model-json> [train-csv]")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
