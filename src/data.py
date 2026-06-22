from __future__ import annotations
import math
import pandas as pd
from .poisson import implied_ou as _implied_ou

DEFAULT_COLS = dict(
    home_team="HomeTeam",
    away_team="AwayTeam",
    home_goals="FTHG",
    away_goals="FTAG",
    home_odds="B365H",
    draw_odds="B365D",
    away_odds="B365A",
    ou_over="B365O25",   # real bookmaker over-2.5 odds (optional)
    ou_under="B365U25",  # real bookmaker under-2.5 odds (optional)
)


def _normalize(home_odds: float, draw_odds: float, away_odds: float) -> tuple[float, float, float]:
    """Convert bookmaker odds to vig-free implied_probabilities summing to 1.0."""
    raw_h = 1 / home_odds
    raw_d = 1 / draw_odds
    raw_a = 1 / away_odds
    total = raw_h + raw_d + raw_a
    return raw_h / total, raw_d / total, raw_a / total


def _ou_from_bookmaker_odds(over_odds: float, under_odds: float) -> float:
    """
    Derive implied O/U line from bookmaker over/under 2.5 odds.
    Normalises to get p(over 2.5), then binary-searches for Poisson lambda
    such that P(goals >= 3 | Poisson(lambda)) = p_over.
    Returns lambda (implied total goals).
    """
    p_over  = 1 / over_odds
    p_under = 1 / under_odds
    p_over_norm = p_over / (p_over + p_under)   # vig-free

    lo, hi = 0.1, 15.0
    for _ in range(40):
        mid = (lo + hi) / 2
        p3plus = 1 - sum(
            math.exp(-mid) * mid**k / math.factorial(k)
            for k in range(3)
        )
        if p3plus < p_over_norm:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _safe_float(val) -> float | None:
    """Return float if val is a valid positive number, else None."""
    try:
        f = float(val)
        if math.isnan(f) or f <= 1.0:
            return None
        return f
    except (TypeError, ValueError):
        return None


def load_matches(path: str, **col_overrides) -> list[dict]:
    """
    Load match data from a CSV file and return a list of match dicts.

    Each match dict contains:
      home_team, away_team     — team names
      fav_prob                 — favorite's implied_probability (None if tied)
      draw_prob                — vig-free draw probability
      implied_ou               — implied total goals (real O/U odds if available,
                                 else Poisson-derived from 1x2 odds)
      has_real_ou              — True when real bookmaker O/U odds were used
      actual_fav, actual_und   — actual goals in favorite-relative terms
      home_is_fav              — True if home team is the favorite
    """
    cols = {**DEFAULT_COLS, **col_overrides}
    df = pd.read_csv(path, encoding="utf-8")

    matches = []
    for _, row in df.iterrows():
        home_prob, draw_prob, away_prob = _normalize(
            row[cols["home_odds"]],
            row[cols["draw_odds"]],
            row[cols["away_odds"]],
        )

        home_goals = int(row[cols["home_goals"]])
        away_goals = int(row[cols["away_goals"]])

        if home_prob > away_prob:
            fav_prob, actual_fav, actual_und, home_is_fav = home_prob, home_goals, away_goals, True
        elif away_prob > home_prob:
            fav_prob, actual_fav, actual_und, home_is_fav = away_prob, away_goals, home_goals, False
        else:
            fav_prob, actual_fav, actual_und, home_is_fav = None, home_goals, away_goals, True

        # Real O/U from bookmaker odds if available, else Poisson fallback
        real_ou = None
        ou_over_col  = cols.get("ou_over",  "B365O25")
        ou_under_col = cols.get("ou_under", "B365U25")
        ov = _safe_float(row.get(ou_over_col))
        un = _safe_float(row.get(ou_under_col))
        if ov is not None and un is not None:
            try:
                real_ou = _ou_from_bookmaker_odds(ov, un)
            except Exception:
                pass

        matches.append(dict(
            home_team=row[cols["home_team"]],
            away_team=row[cols["away_team"]],
            fav_prob=fav_prob,
            draw_prob=draw_prob,
            implied_ou=real_ou if real_ou is not None else _implied_ou(home_prob, draw_prob, away_prob),
            has_real_ou=real_ou is not None,
            actual_fav=actual_fav,
            actual_und=actual_und,
            home_is_fav=home_is_fav,
        ))

    return matches
