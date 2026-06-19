# WC2018 as training set, WC2022 as held-out test set

We use WC2018 (64 matches) to tune all model parameters — classification thresholds and canonical scores — and reserve WC2022 (64 matches) as a held-out test set evaluated exactly once after optimization is complete.

## Considered Options

**WC2022 for training, WC2018 for test**: WC2022 is more recent and may better reflect current playing styles and market efficiency. Rejected because WC2022 is the most recent complete tournament before WC2026 — it is the strongest available signal of how WC2026 will look. Using it for training and leaking its patterns into the model would leave no meaningful out-of-sample evaluation.

**Both tournaments for training, cross-validation for evaluation**: Maximizes training data (128 matches). Rejected because k-fold cross-validation on a small, non-i.i.d. time series (two distinct tournaments four years apart) produces unreliable fold estimates and no true held-out signal. The risk of subtle data leakage outweighs the benefit of 64 extra training matches.

## Consequences

The test set must never be consulted during optimization, threshold tuning, or score candidate selection. Any inspection of WC2022 results — even informally — invalidates the evaluation. If the model fails to beat all baselines on WC2022, no parameter re-tuning is permitted afterward; the result stands.
