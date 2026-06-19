from __future__ import annotations
import pandas as pd

# Columns expected in the CSV (football-data.co.uk format).
# Override via keyword args to load_matches() if your CSV differs.
DEFAULT_COLS = dict(
    home_team="HomeTeam",
    away_team="AwayTeam",
    home_goals="FTHG",
    away_goals="FTAG",
    home_odds="B365H",
    draw_odds="B365D",
    away_odds="B365A",
)


def _normalize(home_odds: float, draw_odds: float, away_odds: float) -> tuple[float, float, float]:
    """Convert bookmaker odds to vig-free implied_probabilities summing to 1.0."""
    raw_h = 1 / home_odds
    raw_d = 1 / draw_odds
    raw_a = 1 / away_odds
    total = raw_h + raw_d + raw_a
    return raw_h / total, raw_d / total, raw_a / total


def load_matches(path: str, **col_overrides) -> list[dict]:
    """
    Load match data from a CSV file and return a list of match dicts.

    Each match dict contains:
      home_team, away_team     — team names
      fav_prob                 — favorite's implied_probability (None if tied)
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
            fav_prob = home_prob
            actual_fav, actual_und = home_goals, away_goals
            home_is_fav = True
        elif away_prob > home_prob:
            fav_prob = away_prob
            actual_fav, actual_und = away_goals, home_goals
            home_is_fav = False
        else:
            # Tied implied probabilities — classified as Open regardless of thresholds.
            fav_prob = None
            actual_fav, actual_und = home_goals, away_goals
            home_is_fav = True  # arbitrary; Open canonical score handles orientation

        matches.append(
            dict(
                home_team=row[cols["home_team"]],
                away_team=row[cols["away_team"]],
                fav_prob=fav_prob,
                draw_prob=draw_prob,
                actual_fav=actual_fav,
                actual_und=actual_und,
                home_is_fav=home_is_fav,
            )
        )

    return matches
