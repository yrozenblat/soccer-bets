CATEGORIES = ("Dominant", "Contested", "Open")


def classify(fav_prob: float | None, t_lower: float, t_upper: float) -> str:
    """
    Assign a matchup_classification based on the favorite's implied_probability.
    fav_prob=None signals a tie — always classified as Open per domain rules.
    t_lower < t_upper; ranges are non-overlapping: [t_upper, 1] = Dominant,
    [t_lower, t_upper) = Contested, [0, t_lower) = Open.
    """
    if fav_prob is None or fav_prob < t_lower:
        return "Open"
    if fav_prob < t_upper:
        return "Contested"
    return "Dominant"
