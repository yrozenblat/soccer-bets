"""
Generate predictions for upcoming matches.

Usage:
    python predict.py data/upcoming.csv [models/v1.json]
    python predict.py data/upcoming.csv --poisson

Input CSV columns: HomeTeam, AwayTeam, HomeProb, DrawProb, AwayProb
Probabilities are Polymarket prices (approx vig-free); script normalises them.
Defaults to models/v1.json if no model path given.
"""
from __future__ import annotations
import csv
import sys
from src.classifier import classify, classify_v3, classify_v4
from src.poisson import implied_ou as _implied_ou, max_ep_score
from src import model as model_io


def predict_poisson(path: str) -> None:
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print("Mode: Poisson max-expected-points (no model)")
    print()
    print(f"{'Match':<35} {'lam_h':6} {'lam_a':6}  Prediction")
    print("-" * 72)
    for r in rows:
        home = r["HomeTeam"]
        away = r["AwayTeam"]
        ph   = float(r["HomeProb"])
        pd   = float(r["DrawProb"])
        pa   = float(r["AwayProb"])

        total = ph + pd + pa
        ph, pd, pa = ph / total, pd / total, pa / total

        from src.poisson import _fit_lambdas
        lam_h, lam_a = _fit_lambdas(ph, pd, pa)
        hg, ag = max_ep_score(ph, pd, pa)

        match_str = f"{home} vs {away}"
        pred_str  = f"{home} {hg}-{ag} {away}"
        print(f"{match_str:<35} {lam_h:6.3f} {lam_a:6.3f}  {pred_str}")


def predict(path: str, model_path: str = "models/v1.json") -> None:
    cfg = model_io.load(model_path)
    t_lower = cfg["t_lower"]
    t_upper = cfg["t_upper"]
    canonical = cfg["canonical_scores"]
    v3 = model_io.is_v3(cfg)
    d_threshold = cfg.get("d_threshold")

    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"Model: {model_path}  (t_lower={t_lower}, t_upper={t_upper})")
    print()
    print(f"{'Match':<35} {'Cat':10} {'Fav%':6}  Prediction")
    print("-" * 72)
    for r in rows:
        home = r["HomeTeam"]
        away = r["AwayTeam"]
        ph   = float(r["HomeProb"])
        pd   = float(r["DrawProb"])
        pa   = float(r["AwayProb"])

        total = ph + pd + pa
        ph, pd, pa = ph / total, pd / total, pa / total

        if ph > pa:
            fav_prob, home_is_fav = ph, True
        elif pa > ph:
            fav_prob, home_is_fav = pa, False
        else:
            fav_prob, home_is_fav = None, True

        if model_io.is_v4(cfg):
            ou_line = _implied_ou(ph, pd, pa)
            cat = classify_v4(fav_prob, ou_line, t_lower, t_upper, cfg["ou_threshold"])
        elif v3:
            cat = classify_v3(fav_prob, pd, t_lower, t_upper, d_threshold)
        else:
            cat = classify(fav_prob, t_lower, t_upper)
        fav_goals, und_goals = canonical[cat]
        home_goals = fav_goals if home_is_fav else und_goals
        away_goals = und_goals if home_is_fav else fav_goals

        prob_str  = f"{fav_prob*100:.1f}%" if fav_prob else "tied"
        match_str = f"{home} vs {away}"
        pred_str  = f"{home} {home_goals}-{away_goals} {away}"
        print(f"{match_str:<35} {cat:10} {prob_str:6}  {pred_str}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python predict.py <upcoming-csv> [model-json | --poisson]")
        sys.exit(1)

    csv_path = sys.argv[1]
    if len(sys.argv) > 2 and sys.argv[2] == "--poisson":
        predict_poisson(csv_path)
    else:
        predict(csv_path, sys.argv[2] if len(sys.argv) > 2 else "models/v1.json")
