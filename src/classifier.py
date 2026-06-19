CATEGORIES = ("Dominant", "Contested", "Open")

# v3 categories: each base category split by draw probability into Hi/Lo goals tier.
# Hi = lower draw_prob → more open/expansive → higher scoring expected.
# Lo = higher draw_prob → tighter/cagey → lower scoring expected.
CATEGORIES_V3 = tuple(
    f"{cat}-{tier}"
    for cat in CATEGORIES
    for tier in ("Hi", "Lo")
)


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


def classify_v3(
    fav_prob: float | None,
    draw_prob: float,
    t_lower: float,
    t_upper: float,
    d_threshold: float,
) -> str:
    """
    v3 classifier: adds a goals-tier split on draw_prob within each base category.
    draw_prob < d_threshold → Hi (lower draw prob, more expansive scoring).
    draw_prob >= d_threshold → Lo (higher draw prob, tighter/lower scoring).
    """
    cat = classify(fav_prob, t_lower, t_upper)
    tier = "Hi" if draw_prob < d_threshold else "Lo"
    return f"{cat}-{tier}"


def classify_v4(
    fav_prob: float | None,
    ou_line: float,
    t_lower: float,
    t_upper: float,
    ou_threshold: float,
) -> str:
    """
    v4 classifier: goals-tier split on Poisson-implied O/U line.
    ou_line >= ou_threshold → Hi (higher expected goals).
    ou_line <  ou_threshold → Lo (lower expected goals).
    """
    cat = classify(fav_prob, t_lower, t_upper)
    tier = "Hi" if ou_line >= ou_threshold else "Lo"
    return f"{cat}-{tier}"
