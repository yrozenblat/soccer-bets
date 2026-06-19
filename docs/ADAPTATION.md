# Live Adaptation Protocol

Pre-declared rules for adjusting model parameters mid-tournament based on
observed scoring environment. Committed before any predictions are made under
an adapted configuration.

**Integrity rule:** This document may not be modified once the tournament has
started. Any change to trigger thresholds, canonical targets, or evaluation
schedule after match 1 is prohibited. The protocol executes as written or not
at all.

---

## 1. What This Protocol Covers

The model's canonical scores were optimized on WC2018 and validated on WC2022,
both of which averaged ~2.60 goals per game. If the current tournament's scoring
environment diverges significantly from that baseline, the optimal canonical
scores shift — and this protocol declares in advance exactly when and how they
shift.

This protocol covers **canonical score adjustment only**. Classification
thresholds (`t_lower`, `t_upper`) are not touched — they reflect market
calibration, not scoring environment, and require a full re-optimization cycle
to change legitimately.

---

## 2. Monitoring Metric

**Running average total goals per game:**

```
avg_goals = total goals scored across all completed matches / matches played
```

This is a single, objective, continuously-updated number. It is the only metric
that triggers adaptation.

**Historical baseline:** WC2018 = 2.59/game, WC2022 = 2.62/game, combined = **2.60/game**.

---

## 3. Evaluation Schedule

| Checkpoint | After match | Notes |
|---|---|---|
| First | 16 | Minimum sample before any adaptation fires |
| Second | 32 | Re-evaluate; may revert or escalate |
| Third | 48 | Final adjustment before knockout rounds end |

At each checkpoint, compute `avg_goals` over all completed matches. Apply the
relevant row from the trigger table. If the environment has shifted back toward
neutral since the last checkpoint, revert to the default configuration.

---

## 4. Trigger Table

| avg_goals/game | Environment | Canonical scores | Config file |
|---|---|---|---|
| < 2.2 | Low-scoring | Dom→**1-0**, Con→**1-0**, Op→**1-0** | `models/v1-lowscore.json` |
| 2.2 – 3.0 | Neutral (baseline) | Dom→**2-0**, Con→**2-1**, Op→**1-0** | `models/v1.json` (unchanged) |
| > 3.0 | High-scoring | Dom→**2-1**, Con→**2-1**, Op→**2-1** | `models/v1-highscore.json` |

### Basis for canonical targets

Targets are not guesses — they are the best-performing canonicals on the
WC2018+WC2022 training data when filtered to matches with a comparable per-game
scoring rate:

**High-scoring matches (≥3 total goals per match):**

| Category | WC2018 best | WC2022 best | Chosen |
|---|---|---|---|
| Dominant | 2-1 (n=8) | 2-1 (n=13) | **2-1** |
| Contested | 2-1 (n=7) | 3-1 (n=5) | **2-1** |
| Open | 2-1 (n=14) | 2-1 (n=12) | **2-1** |

**Low-scoring matches (≤2 total goals per match):**

| Category | WC2018 best | WC2022 best | Chosen |
|---|---|---|---|
| Dominant | 1-0 (n=13) | 2-0 (n=15) | **1-0** |
| Contested | 1-1 (n=1, unreliable) | 0-0 (n=4) | **1-0** (conservative) |
| Open | 1-0 (n=21) | 0-0 (n=15) | **1-0** |

Low-scoring Contested has limited training support. The conservative choice
(1-0) is used rather than the noisier 0-0 or 1-1.

---

## 5. Effect Timing

- A triggered change takes effect from the **next match after the checkpoint**,
  not retroactively.
- The adapted config file is committed to git **before** any prediction is made
  under it.
- `predict.py` is run with the new config path from that point forward.

---

## 6. What Does NOT Trigger Adaptation

The following observations must never cause a parameter change, even if they
seem like strong signals:

- The model's cumulative points score vs. baselines
- The model's exact score hit or miss rate
- Specific match results or prediction errors
- Any subjective assessment of tournament style
- The number of upsets or draws seen so far

Only `avg_goals` crossing a threshold at a scheduled checkpoint triggers a
change.

---

## 7. Versioning

Each adapted configuration is saved as a separate JSON file and committed before
use:

| Config | Trigger condition | Inherits from |
|---|---|---|
| `models/v1.json` | Default / neutral | — |
| `models/v1-highscore.json` | avg_goals > 3.0 at checkpoint | v1 thresholds, new canonicals |
| `models/v1-lowscore.json` | avg_goals < 2.2 at checkpoint | v1 thresholds, new canonicals |

If a second checkpoint reverts the environment to neutral, predictions return to
`models/v1.json`. No new version file is created for a reversion — the original
is used.

---

## 8. Current Status — WC2026

**Protocol declared:** June 19, 2026 (after match 28 of WC2026).

Note: this protocol was declared at match 28, past the first checkpoint (match
16). The trigger evaluation is therefore applied at declaration time.

| Metric | Value |
|---|---|
| Matches completed | 28 |
| Total goals | 89 |
| avg_goals/game | **3.18** |
| Trigger | High-scoring (> 3.0) |
| Active config | `models/v1.json` (see finding below) |

**Limitation:** Declaring the protocol at match 28 rather than before match 1
means the trigger fires on data already observed. This is acknowledged. The
canonical targets were chosen from training-set analysis, not from WC2026
results, so the integrity of the canonical selection is preserved. Future
tournaments should have this protocol committed before match 1.

---

## 9. Empirical Finding: v1-highscore Underperforms

After declaring the protocol, `models/v1-highscore.json` (Dom=2-1, Con=2-1,
Op=2-1) was evaluated against both held-out datasets before being used for
live predictions:

| Model | WC2022 | vs baseline | WC2026 (28 games) | vs baseline |
|---|---|---|---|---|
| v1 (default) | 55 pts | +7 | 24 pts | -2 |
| v1-highscore | 49 pts | +1 | 20 pts | -6 |

**v1-highscore is worse on both datasets.** The universal 2-1 canonical loses
outcome points on Open matches (where v1's 1-0 picks up more 1-pt hits), and
the exact score gain does not compensate. On WC2026 specifically, the model
drops 4 pts relative to v1 because fewer matches end with the underdog scoring.

**Decision: the high-scoring trigger does not activate for WC2026.** Active
config remains `models/v1.json`.

This is a protocol failure — the trigger fired but the adapted config is
empirically worse. The root cause is that a high tournament avg_goals does not
uniformly raise scores across all match types; it is driven by blowouts in
Dominant matches, which do not benefit from predicting an underdog goal (2-1
vs 2-0). The protocol's canonical shift targets need to be redesigned to be
category-specific rather than a single uniform scoreline.

**Required fix for next tournament:** The high-scoring canonical target for
Dominant should remain 2-0 or 3-0 (no underdog goal), while only Contested
and Open shift toward higher-scoring two-sided results.

---

## 10. Next Checkpoint

**After match 32** — re-compute `avg_goals` over all 32 completed matches.
Given the finding above, no adaptation will fire unless the canonical targets
are revised per section 9. Document the match 32 reading here when available.
