def score_prediction(pred_fav: int, pred_und: int, actual_fav: int, actual_und: int) -> int:
    """
    Score a single prediction under the points_scoring rules.
    All values are in favorite-relative terms (favorite goals, underdog goals).
    Returns 3 for exact score, 1 for correct outcome, 0 otherwise.
    """
    if pred_fav == actual_fav and pred_und == actual_und:
        return 3

    def outcome(fav, und):
        if fav > und:
            return "fav"
        if fav == und:
            return "draw"
        return "und"

    if outcome(pred_fav, pred_und) == outcome(actual_fav, actual_und):
        return 1

    return 0
