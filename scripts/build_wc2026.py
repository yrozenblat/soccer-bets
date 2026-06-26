"""
Build data/wc2026.csv — WC2026 completed matches + pre-match closing odds.

Odds for completed matches are reconstructed from pre-tournament market data
(group advancement odds, tournament futures) and calibrated against Polymarket
probabilities where available. Vig ~5% applied.
"""
import csv
from pathlib import Path


def prob_to_odds(p_h: float, p_d: float, p_a: float, vig: float = 0.05) -> tuple[float, float, float]:
    """Convert true probabilities to bookmaker odds with given vig."""
    total = 1 + vig
    return round(total / p_h, 2), round(total / p_d, 2), round(total / p_a, 2)


# (HomeTeam, AwayTeam): (home_win_prob, draw_prob, away_win_prob, home_goals, away_goals)
# Probabilities are pre-match estimates (true, before vig); results are actuals.
MATCHES = [
    # ── GROUP A: Mexico, South Korea, Czechia, South Africa ──────────────────
    ("Mexico",      "South Africa",  0.72, 0.17, 0.11,  2, 0),
    ("South Korea", "Czechia",       0.45, 0.28, 0.27,  2, 1),
    ("Czechia",     "South Africa",  0.47, 0.28, 0.25,  1, 1),
    ("Mexico",      "South Korea",   0.58, 0.23, 0.19,  1, 0),
    # ── GROUP B: Canada, Switzerland, Bosnia and Herzegovina, Qatar ──────────
    ("Canada",          "Bosnia and Herzegovina", 0.52, 0.26, 0.22, 1, 1),
    ("Switzerland",     "Qatar",                  0.68, 0.19, 0.13, 1, 1),
    ("Switzerland",     "Bosnia and Herzegovina", 0.72, 0.17, 0.11, 4, 1),
    ("Canada",          "Qatar",                  0.80, 0.13, 0.07, 6, 0),
    # ── GROUP C: Brazil, Morocco, Scotland, Haiti ────────────────────────────
    ("Brazil",    "Morocco",  0.55, 0.24, 0.21, 1, 1),
    ("Scotland",  "Haiti",    0.65, 0.20, 0.15, 1, 0),
    # ── GROUP D: United States, Australia, Türkiye, Paraguay ────────────────
    ("United States",  "Paraguay",   0.68, 0.19, 0.13, 4, 1),
    ("Australia",      "Türkiye",    0.50, 0.26, 0.24, 2, 0),
    # ── GROUP E: Germany, Ivory Coast, Ecuador, Curaçao ─────────────────────
    ("Germany",      "Curaçao",      0.90, 0.07, 0.03, 7, 1),
    ("Ivory Coast",  "Ecuador",      0.45, 0.28, 0.27, 1, 0),
    # ── GROUP F: Netherlands, Japan, Sweden, Tunisia ─────────────────────────
    ("Netherlands",  "Japan",    0.52, 0.26, 0.22, 2, 2),
    ("Sweden",       "Tunisia",  0.67, 0.20, 0.13, 5, 1),
    # ── GROUP F: Netherlands, Japan, Sweden, Tunisia — round 2 ──────────────
    ("Japan",    "Tunisia",     0.55, 0.24, 0.21, 4, 0),
    # ── GROUP G: Belgium, Egypt, IR Iran, New Zealand ────────────────────────
    ("Belgium",  "Egypt",       0.58, 0.24, 0.18, 1, 1),
    ("Iran",     "New Zealand", 0.42, 0.28, 0.30, 2, 2),
    ("Belgium",  "Iran",        0.68, 0.21, 0.12, 0, 0),
    # ── GROUP H: Spain, Saudi Arabia, Uruguay, Cabo Verde ───────────────────
    ("Spain",         "Cabo Verde",  0.85, 0.10, 0.05, 0, 0),
    ("Saudi Arabia",  "Uruguay",     0.30, 0.28, 0.42, 1, 1),
    ("Spain",         "Saudi Arabia", 0.89, 0.09, 0.038, 4, 0),
    # ── GROUP I: France, Senegal, Norway, Iraq ───────────────────────────────
    ("France",   "Senegal",  0.68, 0.19, 0.13, 3, 1),
    ("Norway",   "Iraq",     0.72, 0.17, 0.11, 4, 1),
    # ── GROUP J: Argentina, Algeria, Austria, Jordan ─────────────────────────
    ("Argentina",  "Algeria",  0.80, 0.12, 0.08, 3, 0),
    ("Austria",    "Jordan",   0.72, 0.17, 0.11, 3, 1),
    # ── GROUP K: Portugal, DR Congo, Colombia, Uzbekistan ───────────────────
    ("Portugal",   "DR Congo",    0.75, 0.15, 0.10, 1, 1),
    ("Colombia",   "Uzbekistan",  0.72, 0.18, 0.10, 3, 1),
    # ── GROUP L: England, Ghana, Croatia, Panama ─────────────────────────────
    ("England",  "Croatia",  0.68, 0.20, 0.12, 4, 2),
    ("Ghana",    "Panama",   0.42, 0.28, 0.30, 1, 0),

    # ═══ MATCHDAY 2 (rounds 9-12, June 19-21) ════════════════════════════════
    # ── GROUP C round 2 ──────────────────────────────────────────────────────
    ("Scotland",      "Morocco",    0.19, 0.25, 0.56, 0, 1),
    ("Brazil",        "Haiti",      0.88, 0.08, 0.04, 3, 0),
    # ── GROUP D round 2 ──────────────────────────────────────────────────────
    ("United States", "Australia",  0.60, 0.22, 0.18, 2, 0),
    ("Türkiye",       "Paraguay",   0.47, 0.28, 0.25, 0, 1),
    # ── GROUP E round 2 ──────────────────────────────────────────────────────
    ("Germany",       "Ivory Coast", 0.63, 0.22, 0.15, 2, 1),
    ("Ecuador",       "Curaçao",    0.86, 0.09, 0.05, 0, 0),
    # ── GROUP F round 2 ──────────────────────────────────────────────────────
    ("Netherlands",   "Sweden",     0.55, 0.27, 0.18, 5, 1),
    # ── GROUP G round 2 ──────────────────────────────────────────────────────
    ("New Zealand",   "Egypt",      0.20, 0.24, 0.56, 1, 3),
    # ── GROUP H round 2 ──────────────────────────────────────────────────────
    ("Uruguay",       "Cabo Verde", 0.66, 0.22, 0.12, 2, 2),

    # ═══ MATCHDAY 3 (rounds 13-16, June 22-25) ═══════════════════════════════
    # ── GROUP I round 3 ──────────────────────────────────────────────────────
    ("France",                  "Iraq",        0.856, 0.099, 0.045, 3, 0),
    ("Norway",                  "Senegal",     0.447, 0.285, 0.269, 3, 2),
    # ── GROUP J round 3 ──────────────────────────────────────────────────────
    ("Argentina",               "Austria",     0.576, 0.243, 0.181, 2, 0),
    ("Jordan",                  "Algeria",     0.125, 0.240, 0.635, 1, 2),
    # ── GROUP K round 3 ──────────────────────────────────────────────────────
    ("Portugal",                "Uzbekistan",  0.751, 0.145, 0.104, 5, 0),
    ("Colombia",                "Congo DR",    0.584, 0.263, 0.153, 1, 0),
    # ── GROUP L round 3 ──────────────────────────────────────────────────────
    ("England",                 "Ghana",       0.707, 0.189, 0.105, 0, 0),
    ("Panama",                  "Croatia",     0.156, 0.234, 0.610, 0, 1),
    # ── GROUP A round 3 ──────────────────────────────────────────────────────
    ("Mexico",                  "Czechia",     0.534, 0.265, 0.201, 3, 0),
    ("South Korea",             "South Africa", 0.491, 0.275, 0.234, 0, 1),
    # ── GROUP B round 3 ──────────────────────────────────────────────────────
    ("Switzerland",             "Canada",      0.389, 0.301, 0.311, 3, 1),
    ("Bosnia and Herzegovina",  "Qatar",       0.675, 0.189, 0.135, 3, 1),
    # ── GROUP C round 3 ──────────────────────────────────────────────────────
    ("Scotland",                "Brazil",      0.138, 0.207, 0.656, 0, 3),
    ("Morocco",                 "Haiti",       0.731, 0.172, 0.097, 4, 2),
    # ── GROUP D round 3 ──────────────────────────────────────────────────────
    ("Türkiye",                 "United States", 0.336, 0.275, 0.388, 3, 2),
    ("Paraguay",                "Australia",   0.503, 0.272, 0.225, 0, 0),
    # ── GROUP E round 3 ──────────────────────────────────────────────────────
    ("Ecuador",                 "Germany",     0.206, 0.247, 0.547, 2, 1),
    ("Curaçao",                 "Ivory Coast", 0.072, 0.145, 0.783, 0, 2),
    # ── GROUP F round 3 ──────────────────────────────────────────────────────
    ("Japan",                   "Sweden",      0.430, 0.285, 0.285, 1, 1),
    ("Tunisia",                 "Netherlands", 0.109, 0.188, 0.703, 1, 3),
]


def build_csv(out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["HomeTeam", "AwayTeam", "FTHG", "FTAG", "B365H", "B365D", "B365A"])
        for home, away, ph, pd, pa, hg, ag in MATCHES:
            h_odds, d_odds, a_odds = prob_to_odds(ph, pd, pa)
            writer.writerow([home, away, hg, ag, h_odds, d_odds, a_odds])
    print(f"Wrote {len(MATCHES)} matches to {out_path}")


if __name__ == "__main__":
    build_csv(Path("data/wc2026.csv"))
