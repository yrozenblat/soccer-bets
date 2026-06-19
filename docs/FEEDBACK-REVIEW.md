# Feedback Review & Action Items

Review of external feedback on the WC2026 prediction model design and documentation.

---

## Feedback Item 1: Differentiation for Pool Play

> "If many competitors will pick 1–0 or 2–0, optimize not only expected points but also differentiation."

**Assessment: Valid framing, out of scope for current architecture.**

This is a real consideration if the model is used in a scored pool where you compete against other people's predictions. In that context the value of a correct prediction depends not just on its expected points but on how many others also got it right — a contrarian correct prediction is worth more than a consensus correct one.

However, acting on this requires knowing (or modelling) what opponents are likely to pick. That turns the problem into a game-theory optimization on top of a prediction problem, and it's a fundamentally different objective function from the one the model is built around.

**Action: Document as a known limitation, do not build toward it unless the pool format is confirmed to reward differentiation and opponent pick distributions are available.**

---

## Feedback Item 2: Reframe the WC2026 Failure

> "The doc says the current WC2026 failure is 'not a structural model failure.' I'd soften that. It may be partly bad luck, but it also exposes a structural weakness: the model cannot adjust to a lopsided/high-scoring tournament environment."

**Assessment: Fully agree. Current wording is defensively wrong.**

"Not a structural model failure" is inaccurate. The model does have a structural weakness here: it has no mechanism to detect or respond to a tournament environment that differs significantly from its training distribution. WC2026's group stage (26/28 favorite wins, multiple 6–0 and 7–1 results) is far outside the WC2018/WC2022 pattern, and the model has no adaptation pathway.

The fact that 28 matches is a small sample and results may revert is true — but that is a reason not to panic, not a reason to deny the structural gap.

**Action: Rewrite the WC2026 failure explanation in `docs/MODEL.md` to acknowledge the structural limitation honestly. Suggested language: "The early sample is not sufficient to invalidate the model, but it highlights a genuine structural limitation: the model cannot adjust to a tournament environment that differs significantly from its training distribution. This is expected behavior, not noise."**

---

## Feedback Item 3: Add Total-Goals Information

> "Add total-goals information."

**Assessment: Strongest upgrade on the list. High priority.**

The over/under market (expected total goals per match) is pre-match, publicly available, and does not violate any data principle — it's just another odds-derived signal like the win probability we already use. It directly addresses the WC2026 failure mode: a Dominant match with O/U 3.5 should predict a higher-scoring canonical than a Dominant match with O/U 1.8.

This would add a second classification dimension: the current win-probability axis captures match competitiveness; a goals axis would capture match tempo. Together they produce a finer grid of match types without requiring more categories (a high-prob / high-goals Dominant is still Dominant, but selects from a different part of the candidate list).

Operationally this means adding an `ou_line` column to the data pipeline and extending `joint_optimization` to also search over an O/U split threshold.

**Action: Design and implement as a model upgrade (v3 candidate). Requires sourcing O/U closing lines for WC2018 and WC2022 training data.**

---

## Feedback Item 4: Replace Fixed Canonical Scores with Expected-Points Score Selection

> "Replace fixed canonical scores with expected-points score selection."

**Assessment: Partially implemented already; the remaining gap is lower priority.**

The current optimizer already does expected-points selection — it picks the candidate from the `score_candidate_list` that maximizes total `points_scoring` on the training set. The fixed candidate list is what constrains it.

What the feedback is likely pointing toward is removing the fixed candidate list entirely and considering all plausible scorelines weighted by their historical probability, rather than argmax over a predetermined set. This is more principled in theory. In practice, with 64 training matches and ~20 per category, it risks overfitting to spurious exact scores that happened to appear in WC2018.

The fixed candidate list is a regularizer as much as a design choice. The right upgrade here is probably to extend the list rather than remove it, and to validate that no scoreline outside the list would have performed better across both WC2018 and WC2022.

**Action: Run a post-hoc audit to confirm no out-of-list scoreline would have outperformed the current canonicals on WC2022. If one does, add it to the candidate list with a note. Full probabilistic reframe is lower priority.**

---

## Feedback Item 5: Pre-Declared Live Adaptation Mechanism

> "Add a pre-declared live adaptation mechanism."

**Assessment: High integrity value. Should be done before the next round of predictions.**

The model currently has no declared adaptation rule. Any mid-tournament parameter change risks looking like data snooping — adjusting because the results so far suggested it, even if framed as principled. The right fix is to declare the adaptation rule *before* seeing more results, so that any future change is a rule executing, not a post-hoc response.

Example of a pre-declared rule: "If after match 16 the tournament average goals per game exceeds 3.0, the Dominant canonical score shifts from 2–0 to 3–0 for the remainder of the tournament." This is testable, declared in advance, and not triggered by inspecting which specific games were scored correctly.

**Action: Write and commit a pre-declared adaptation protocol to `docs/ADAPTATION.md` before the next set of matches is played. The protocol must specify: trigger condition (metric + threshold + minimum sample), which parameter changes, and when it takes effect. Once committed, it is binding — no adjustment to the trigger after the fact.**

---

## Feedback Item 6: Clarify Leakage and Versioning

> "Clarify leakage/versioning."

**Assessment: Fair. The Dominant=2-0 manual tweak is the ambiguous point.**

The doc is clear on the WC2022 hold-out boundary but does not fully explain the status of the Dominant canonical change from 1–0 to 2–0 in v1. That change was made before any WC2022 evaluation and was motivated by historical WC scoring patterns — it does not constitute test-set leakage. But a reader could reasonably wonder.

The versioning section should make explicit: what data each version was trained on, what decisions were made before vs. after each dataset was inspected, and what the chain of custody was.

**Action: Add a "Version History & Leakage Log" section to `docs/MODEL.md` that documents, for each model version, exactly what was and was not known at the time of each parameter decision.**

---

## Summary: Action Items

| # | Action | Priority | File |
|---|---|---|---|
| 1 | Rewrite WC2026 failure explanation to acknowledge structural limitation | High | `docs/MODEL.md` |
| 2 | Write and commit pre-declared adaptation protocol before next matches | High | `docs/ADAPTATION.md` (new) |
| 3 | Add "Version History & Leakage Log" section | Medium | `docs/MODEL.md` |
| 4 | Design total-goals dimension upgrade (v3 candidate) | Medium | new issue / ADR |
| 5 | Audit out-of-list scorelines against WC2022 | Low | one-off script |
| 6 | Document pool-play differentiation as known limitation | Low | `docs/MODEL.md` |
