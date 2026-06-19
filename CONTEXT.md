# World Cup 2026 Prediction Model

A classification-based system for predicting FIFA World Cup 2026 match outcomes and exact scores, optimized for a points game where outcome = 1pt and exact score = 3pt.

## Language

**matchup_classification**:
The category a match is assigned to before kickoff, based on pre-match market data. Drives both the predicted outcome and the predicted exact score.
_Avoid_: matchup type, betting-profile category, classification, profile

**points_scoring**:
The objective function. A prediction earns 3 points for a correct exact score, 1 point for a correct outcome (win/draw/loss) when the exact score is wrong, and 0 points otherwise. Correct exact score and correct outcome are mutually exclusive scoring tiers — never additive.
_Avoid_: reward function, scoring rule

**joint_optimization**:
The backtesting strategy that searches over all candidate `classification_threshold` values and `canonical_score` assignments together, including optional secondary signals like draw probability, and selects the configuration that maximizes total points on the `training_set`.
_Avoid_: grid search, two-pass tuning, sequential optimization

**matchup_classification** (count):
Exactly 3 categories — Dominant, Contested, Open — separated by 2 `classification_threshold` values. Reducing from 5 to 3 ensures sufficient matches per category in the `training_set`.

**Dominant**: favorite win probability ≥ upper threshold. One-sided match.
**Contested**: favorite win probability between lower and upper threshold. Favorite likely but match is live.
**Open**: favorite win probability < lower threshold. Either team can win; draw is common.

**classification_threshold**:
A tunable win-probability boundary that separates two adjacent `matchup_classification` categories. Thresholds are non-overlapping — each probability value belongs to exactly one category. Values are set and adjusted through backtesting on the training set only.
_Avoid_: cutoff, boundary, limit

**training_set**:
WC2018 (64 matches) — the only data used to tune `classification_threshold` values and `canonical_score` assignments. WC2022 is never consulted during optimization.
_Avoid_: in-sample data, historical data

**test_set**:
WC2022 (64 matches) — held out entirely from optimization. Evaluated once, after all parameters are fixed, to measure real generalization.
_Avoid_: validation set, out-of-sample data

**canonical_score**:
The single exact scoreline assigned to a `matchup_classification`, selected by `joint_optimization` from a fixed candidate list of the most historically frequent WC scorelines. One canonical score per classification — not a ranked list.
_Avoid_: predicted score, recommended score, best guess

**implied_probability**:
A team's win probability derived from closing odds after normalizing all outcomes (win/draw/loss) to sum to exactly 1.0. Raw bookmaker-implied values are never used directly — vig is always removed first.
_Avoid_: raw probability, bookmaker probability, odds-implied probability

**closing_odds**:
The pre-match probability snapshot used for all classification and backtesting. Taken as the final bookmaker line immediately before kickoff. No intra-match or post-kickoff data is ever used.
_Avoid_: opening odds, live odds, pre-match odds (too vague)

**favorite**:
The team with the higher `implied_probability`. All scores are expressed favorite-relative (favorite goals – underdog goals). When outputting a prediction, the score is reoriented to the actual match teams. If both teams have equal implied probability, no favorite exists and the match is classified as Open regardless of thresholds.
_Avoid_: home team, Team A, stronger side

**baseline**:
A naive prediction strategy the model must outperform on the `test_set` to be considered valid. The model must beat all four baselines simultaneously — beating some but not all is a failure:
1. Always predict 1–0 (favorite wins every match)
2. Always predict 1–1 (every match is a draw)
3. Always follow highest `implied_probability` outcome with a fixed score (e.g., 1–0 or 1–1)
4. Always predict the single most common WC scoreline historically
_Avoid_: benchmark, control, naive model

**score_candidate_list**:
The fixed set of favorite-relative scorelines the optimizer may assign as a `canonical_score`. Category-specific:
- Dominant and Contested: 1–0, 2–0, 2–1, 3–0, 3–1, 1–1, 0–0, 2–2 (favorite wins or draw only)
- Open: same list plus 0–1, 0–2, 1–2 (upsets allowed)
No scoreline outside these lists is considered.
_Avoid_: score pool, possible scores
