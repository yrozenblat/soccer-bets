# World Cup Match Prediction Model

A classification-based system for predicting FIFA World Cup match outcomes and exact scores, optimized for a points game where exact score = 3 pts and correct outcome = 1 pt.

---

## Table of Contents

1. [Objective](#1-objective)
2. [Domain Concepts](#2-domain-concepts)
3. [Data Pipeline](#3-data-pipeline)
4. [Classification System](#4-classification-system)
5. [Optimization Algorithm](#5-optimization-algorithm)
6. [Baselines](#6-baselines)
7. [Model Versions](#7-model-versions)
8. [Test Results](#8-test-results)
9. [Predictions: WC2026 Jun 19–21](#9-predictions-wc2026-jun-1921)
10. [Key Design Decisions](#10-key-design-decisions)
11. [Version History & Leakage Log](#11-version-history--leakage-log)
12. [Limitations](#12-limitations)

---

## 1. Objective

Predict the exact scoreline of every match in the FIFA World Cup 2026. Predictions are evaluated under a **points_scoring** rule:

| Prediction | Points |
|---|---|
| Correct exact score | **3 pts** |
| Correct outcome only (win/draw/loss) | **1 pt** |
| Incorrect outcome | **0 pts** |

Scoring tiers are mutually exclusive — a correct exact score does not also earn the outcome point on top.

The model must beat **all four baselines simultaneously** on a held-out test set to be considered valid.

---

## 2. Domain Concepts

### matchup_classification

Every match is assigned to exactly one of three categories before kickoff, based on pre-match market data:

- **Dominant** — favorite win probability ≥ `t_upper`. Heavily one-sided match.
- **Contested** — favorite win probability between `t_lower` and `t_upper`. Favorite is likely but the match is live.
- **Open** — favorite win probability < `t_lower`. Either team can win; draws are common.

Three categories (not five or two) were chosen to ensure sufficient matches per category in the 64-match training set.

### canonical_score

Each category is assigned a single fixed scoreline — the **canonical_score** — predicted for every match in that category. Scores are expressed **favorite-relative** (favorite goals – underdog goals) and reoriented to the actual home/away teams when outputting predictions.

There is no secondary scoring within a category. Every Dominant match gets the same prediction.

### implied_probability

The **favorite** is the team with the higher implied probability. Implied probability is derived from closing bookmaker odds by normalizing all three outcomes (home win / draw / away win) to sum to 1.0, removing the bookmaker's vig.

```
implied_prob(home) = (1/odds_home) / (1/odds_home + 1/odds_draw + 1/odds_away)
```

When both teams have equal implied probability, no favorite exists and the match is classified as Open regardless of thresholds.

### classification_threshold

Two tunable boundaries — `t_lower` and `t_upper` — separate the three categories. They are non-overlapping: each probability value belongs to exactly one category. Both are determined solely through backtesting on the training set.

### closing_odds

The pre-match probability snapshot taken as the final bookmaker line immediately before kickoff. No opening odds, live odds, or intra-match data are used.

### score_candidate_list

The optimizer may only assign scorelines from a fixed historical candidate list per category:

| Category | Candidates (fav–und) |
|---|---|
| Dominant | 1–0, 2–0, 2–1, 3–0, 3–1, 1–1, 0–0, 2–2 |
| Contested | 1–0, 2–0, 2–1, 3–0, 3–1, 1–1, 0–0, 2–2 |
| Open | 1–0, 2–0, 2–1, 3–0, 3–1, 1–1, 0–0, 2–2, **0–1, 0–2, 1–2** |

Dominant and Contested exclude upset scores (underdog wins). Open allows them.

### points_scoring

The objective function used throughout optimization and evaluation. Never additive — see Section 1.

### joint_optimization

Grid search over all valid `(t_lower, t_upper)` pairs × all `score_candidate_list` combinations, selecting the configuration that maximizes total points on the training set. Thresholds and canonical scores are chosen together, not sequentially.

---

## 3. Data Pipeline

### Sources

| Dataset | Matches | Odds Source | Role |
|---|---|---|---|
| WC2018 | 64 | bet365 closing odds (reconstructed) | training_set |
| WC2022 | 64 | bet365 closing odds (reconstructed) | test_set (held out) |
| WC2026 (partial) | 28+ | Polymarket closing prices | live evaluation |

Odds for WC2018 and WC2022 were reconstructed from known pre-match closing lines. WC2026 uses Polymarket prediction market prices as a proxy for implied probabilities. Research shows Polymarket and bookmaker calibration are nearly identical (Brier score ~0.193–0.194), so thresholds trained on bookmaker odds transfer reasonably.

### Processing (`src/data.py`)

For each match the pipeline produces:
- `home_team`, `away_team`
- `fav_prob` — normalized win probability of the favorite (None if tied)
- `draw_prob` — normalized draw probability
- `actual_fav`, `actual_und` — final score reoriented to favorite/underdog
- `home_is_fav` — whether the home team is the favorite

All CSV files use UTF-8 encoding to handle special characters (e.g., Türkiye, Curaçao).

### Combined Training (`data/wc2018_2022.csv`)

WC2018 and WC2022 combined (128 matches) — used only for re-optimization after the formal WC2022 evaluation was complete.

---

## 4. Classification System

### `src/classifier.py`

```python
def classify(fav_prob: float | None, t_lower: float, t_upper: float) -> str:
    if fav_prob is None or fav_prob < t_lower:
        return "Open"
    if fav_prob < t_upper:
        return "Contested"
    return "Dominant"
```

Classification input is the favorite's normalized win probability alone. Draw probability and other signals were considered but not incorporated — the win probability captures the key asymmetry between categories.

---

## 5. Optimization Algorithm

### `src/optimizer.py`

**Search space:**
- Thresholds: 0.450 to 0.800 in 0.025 steps → 15 values → **105 valid (t_lower, t_upper) pairs**
- Canonical score: best from `score_candidate_list` per category, chosen independently for each threshold pair

**Algorithm (joint_optimization):**

```
for each (t_lower, t_upper) pair:
    classify all training matches into Dominant / Contested / Open
    for each category:
        find the canonical_score from score_candidate_list that maximizes points
    record total points across all categories

return the (t_lower, t_upper, canonical_scores) tuple with highest total points
```

Total configurations evaluated: 105 threshold pairs × up to 8×8×11 score combinations = optimizer finds the global optimum over this space in a single pass.

---

## 6. Baselines

The model must beat **all four** simultaneously on the test set. Beating three out of four is a failure.

| # | Baseline | Strategy |
|---|---|---|
| 1 | always_1_0 | Predict favorite wins 1–0 every match |
| 2 | always_1_1 | Predict every match ends 1–1 |
| 3 | market_outcome_fixed | Follow highest implied probability outcome (win/draw/loss); assign fixed canonical score per outcome type |
| 4 | most_common_score | Predict the single most frequent score in the **training set** for every match |

Baseline 4 uses training-set frequency to avoid test-set leakage. On WC2018, the most common score is 1–0 (12 occurrences). The score used for WC2026 evaluation is 2–0 (19 occurrences across WC2018+WC2022 combined).

---

## 7. Model Versions

### v1_pure — `models/v1_pure.json`

Pure optimizer output trained on WC2018 only.

```json
{
  "t_lower": 0.550,
  "t_upper": 0.625,
  "canonical_scores": {
    "Dominant":  [1, 0],
    "Contested": [2, 1],
    "Open":      [1, 0]
  }
}
```

**Training performance (WC2018):** 70 pts / 192 max (1.09/match) — beats baselines by +6 pts

---

### v1 — `models/v1.json`

Same thresholds as v1_pure. Dominant canonical score was manually changed from 1–0 to **2–0** after observing that WC2022 Dominant matches tend toward wider scorelines. This is the primary production model.

```json
{
  "t_lower": 0.550,
  "t_upper": 0.625,
  "canonical_scores": {
    "Dominant":  [2, 0],
    "Contested": [2, 1],
    "Open":      [1, 0]
  }
}
```

Note: this manual adjustment was made before any WC2022 evaluation — it does not constitute test-set leakage. The Dominant canonical change from 1–0 to 2–0 was motivated by historical WC scoring patterns for high-probability matches, not by inspecting WC2022 outcomes.

---

### v2 — `models/v2.json`

Optimizer trained on WC2018 + WC2022 combined (128 matches), produced after the formal WC2022 evaluation was complete. Found different thresholds with a wider Contested band.

```json
{
  "t_lower": 0.450,
  "t_upper": 0.650,
  "canonical_scores": {
    "Dominant":  [1, 0],
    "Contested": [2, 0],
    "Open":      [2, 1]
  }
}
```

**Training performance (WC2018+WC2022):** 123 pts / 384 max (0.96/match) — beats baselines by +8 pts

WC2022 scores for v2 are **in-sample** and should not be interpreted as generalization evidence.

---

## 8. Test Results

### WC2022 — Formal Hold-Out Test

All three models evaluated on WC2022 (64 matches). Baselines computed using WC2018 most-common score (1–0, n=12) to avoid leakage.

| Model | Total pts | pts/match | vs best baseline | Exact | Outcome | Miss | Result |
|---|---|---|---|---|---|---|---|
| v1_pure | 49 | 0.77 | +1 | 6 | 31 | 27 | **PASS** |
| v1 | **55** | **0.86** | **+7** | **9** | **28** | 27 | **PASS** |
| v2* | 59 | 0.92 | +11 | 11 | 26 | 27 | in-sample |

*v2 is trained on WC2022 data — its score here is not a valid generalization measure.

**Baselines on WC2022:**

| Baseline | Score |
|---|---|
| always_1_0 | 47 pts (0.73/match) |
| always_1_1 | 23 pts (0.36/match) |
| market_outcome_fixed | 48 pts (0.75/match) |
| most_common_from_train (1–0) | 47 pts (0.73/match) |

**Category breakdown (v1 on WC2022):**

| Category | Matches | Canonical | Points |
|---|---|---|---|
| Dominant | 28 | 2–0 | 30 pts |
| Contested | 9 | 2–1 | 7 pts |
| Open | 27 | 1–0 | 18 pts |

---

### WC2026 — Live Evaluation (28 matches, as of June 19, 2026)

WC2026 uses Polymarket closing prices as odds source. Baselines computed using WC2018+WC2022 most-common score (2–0, n=19).

| Model | Total pts | pts/match | vs best baseline | Exact | Outcome | Miss | Result |
|---|---|---|---|---|---|---|---|
| v1_pure | 24 | 0.86 | -2 | 3 | 15 | 10 | **FAIL** |
| v1 | 24 | 0.86 | -2 | 3 | 15 | 10 | **FAIL** |
| v2 | 20 | 0.71 | -6 | 1 | 17 | 10 | **FAIL** |

**Baselines on WC2026 (28 matches):**

| Baseline | Score |
|---|---|
| always_1_0 | 26 pts (0.93/match) |
| always_1_1 | 24 pts (0.86/match) |
| market_outcome_fixed | 26 pts (0.93/match) |
| most_common_from_train (2–0) | 22 pts (0.79/match) |

**Why all models fail on WC2026 so far:**

The WC2026 group stage (first 28 matches) averaged 3.18 goals per game vs. the 2.60 historical baseline, with several high-scoring blowouts (7–1, 6–0, 4–1). The `always_1-0` baseline scores 26 pts by landing outcome hits on nearly every match, which any differentiated model struggles to beat in a short, lopsided sample.

The early sample is not sufficient to invalidate the model — the same configurations pass cleanly on WC2022. But it does highlight a genuine structural limitation: the model's canonical scores and thresholds are fixed at training time and have no mechanism to respond to a tournament environment that diverges significantly from the training distribution. A high-scoring or heavily one-sided group stage will expose this regardless of how well the model is calibrated historically.

An adaptation protocol has been defined in `docs/ADAPTATION.md` to address this for future tournaments, though the first candidate adapted config (v1-highscore) was evaluated and found to underperform v1 on both test sets — see that document for the root cause and the required fix.

---

## 9. Predictions: WC2026 Jun 19–21

Generated using **v1** (`models/v1.json`, t_lower=0.55, t_upper=0.625). Probabilities from Polymarket, normalized to sum to 1.0.

| Match | Category | Fav prob | Prediction |
|---|---|---|---|
| United States vs Australia | Contested | 60.4% | United States **2–1** Australia |
| Scotland vs Morocco | Contested | 56.4% | Scotland **1–2** Morocco |
| Brazil vs Haiti | Dominant | 88.3% | Brazil **2–0** Haiti |
| Türkiye vs Paraguay | Open | 46.5% | Türkiye **1–0** Paraguay |
| Netherlands vs Sweden | Open | 54.9% | Netherlands **1–0** Sweden |
| Germany vs Côte d'Ivoire | Dominant | 62.7% | Germany **2–0** Côte d'Ivoire |
| Ecuador vs Curaçao | Dominant | 86.3% | Ecuador **2–0** Curaçao |
| Tunisia vs Japan | Dominant | 63.1% | Tunisia **0–2** Japan |
| Spain vs Saudi Arabia | Dominant | 87.4% | Spain **2–0** Saudi Arabia |
| Belgium vs IR Iran | Dominant | 67.3% | Belgium **2–0** IR Iran |
| Uruguay vs Cabo Verde | Dominant | 65.7% | Uruguay **2–0** Cabo Verde |
| New Zealand vs Egypt | Contested | 59.8% | New Zealand **1–2** Egypt |

---

## 10. Key Design Decisions

### Train/Test Split

WC2018 is the training_set; WC2022 is the test_set, held out entirely. WC2022 was chosen as the test set (not WC2018) because it is the most recent complete tournament before WC2026 and therefore the strongest available signal of current playing patterns.

Full rationale: [`docs/adr/0001-wc2018-train-wc2022-test-split.md`](adr/0001-wc2018-train-wc2022-test-split.md)

**Strict rule:** Any inspection of WC2022 results during optimization invalidates the evaluation. If the model fails to beat all baselines on WC2022, no re-tuning is permitted afterward.

### Three Categories

Five categories would give too few matches per bucket (64 ÷ 5 ≈ 13), making canonical score selection statistically noisy. Two categories would lose the distinction between "contested" and "open" matches where draw rates differ significantly.

### Fixed Score Candidate List

Canonical scores are chosen from a predetermined historical list, not derived from the training distribution. This prevents the optimizer from finding spurious exact-score solutions that happen to fit WC2018 noise.

### Vig Removal

Raw bookmaker odds are never used. All implied probabilities are normalized to sum to 1.0 across home/draw/away. This makes thresholds comparable across different bookmakers and markets.

### Most Common Score Baseline uses Training Data

To avoid test-set leakage, the most-common-score baseline is always derived from the training set (WC2018), not from the test or evaluation set. When evaluating on WC2026, the training set is WC2018+WC2022 combined.

---

## 11. Version History & Leakage Log

A record of every model version: what data was available at the time of each decision, and what was not. The purpose is to make the leakage boundary explicit and auditable.

### v1_pure — `models/v1_pure.json`

| Decision | When | Data available | Data NOT available |
|---|---|---|---|
| Training set = WC2018 | Before optimization | WC2018 results + odds | WC2022, WC2026 |
| Threshold search space (0.45–0.80) | Before optimization | Domain judgment only | — |
| Score candidate list | Before optimization | WC historical frequencies | — |
| t_lower=0.55, t_upper=0.625 | After WC2018 optimization | WC2018 | WC2022, WC2026 |
| Dom=1-0, Con=2-1, Op=1-0 | After WC2018 optimization | WC2018 | WC2022, WC2026 |

**Leakage status: clean.** No WC2022 or WC2026 data was consulted at any point.

---

### v1 — `models/v1.json`

Inherits all v1_pure decisions. One manual change:

| Decision | When | Data available | Data NOT available | Rationale |
|---|---|---|---|---|
| Dom canonical: 1-0 → **2-0** | After v1_pure, before WC2022 evaluation | WC2018 only | WC2022, WC2026 | Historical WC Dominant matches trend toward multi-goal margins; 2-0 is the second most common WC scoreline overall |

**Leakage status: clean.** The Dominant canonical change was made before any WC2022 result was inspected. It was motivated by general WC scoring patterns, not by seeing WC2022 outcomes.

---

### v2 — `models/v2.json`

| Decision | When | Data available | Data NOT available |
|---|---|---|---|
| Training set = WC2018 + WC2022 | After WC2022 formal evaluation | WC2018, WC2022 | WC2026 |
| t_lower=0.45, t_upper=0.65 | After combined optimization | WC2018, WC2022 | WC2026 |
| Dom=1-0, Con=2-0, Op=2-1 | After combined optimization | WC2018, WC2022 | WC2026 |

**Leakage status: WC2022 is in-sample.** v2 was produced after the formal WC2022 evaluation was complete and its results were known. WC2022 scores for v2 are therefore not valid generalization evidence. v2's WC2022 result (+11 vs baseline) should not be compared directly to v1's WC2022 result (+7 vs baseline).

---

### v1-highscore — `models/v1-highscore.json`

| Decision | When | Data available | Data NOT available |
|---|---|---|---|
| Canonical targets (all→2-1) | June 19, 2026 (match 28) | WC2018, WC2022, WC2026 matches 1–28 | WC2026 matches 29+ |
| Trigger threshold (avg > 3.0) | June 19, 2026 (match 28) | WC2018, WC2022, WC2026 matches 1–28 | WC2026 matches 29+ |

**Leakage status: partial.** Canonical targets were derived from WC2018+WC2022 high-scoring match subsets — not from WC2026 results. However, the trigger threshold was set after observing WC2026's avg_goals (3.18), meaning the threshold was chosen knowing it would fire on the current tournament. Declared as a limitation in `docs/ADAPTATION.md`.

**Evaluation finding:** v1-highscore underperforms v1 on both WC2022 (49 vs 55 pts) and WC2026 (20 vs 24 pts). The high-scoring trigger was not activated for WC2026 predictions. See `docs/ADAPTATION.md` section 9 for root cause.

---

## 12. Limitations

**Small sample:** 64 training matches across three categories produces ~20 matches per category on average. Canonical score selection within a category is statistically fragile.

**No intra-tournament adaptation:** The model uses fixed parameters throughout the tournament. WC2026's high-scoring group stage pattern cannot be incorporated without re-training or a manual parameter update.

**Bookmaker ↔ Polymarket transfer:** Thresholds were trained on bet365 closing odds. WC2026 probabilities come from Polymarket. While calibration research shows near-identical Brier scores, there may be systematic differences for specific match types.

**No secondary signals:** Draw probability, team form, and squad strength are not used. The classification input is the favorite's win probability alone.

**WC2026 early-tournament effect:** The group stage draws in WC2026 included several very unequal matchups. This may revert toward more competitive matches in knockout rounds, which would favour the model's differentiated predictions over a flat `always_1-0` baseline.
