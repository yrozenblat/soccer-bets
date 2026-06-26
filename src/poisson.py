"""
Derive implied over/under line from H/D/A probabilities using a Poisson model.

Each team's goals are modeled as independent Poisson(lambda). Given the
vig-free P(home_win), P(draw), P(away_win) from bookmaker odds, we solve
numerically for (lambda_home, lambda_away) that best reproduce those
probabilities. The implied O/U line is lambda_home + lambda_away.
"""
from __future__ import annotations
import math
from scipy.optimize import minimize


def _poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def _match_probs(lam_h: float, lam_a: float, max_goals: int = 8) -> tuple[float, float, float]:
    """Compute P(home win), P(draw), P(away win) from Poisson lambdas."""
    p_home = p_draw = p_away = 0.0
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            p = _poisson_pmf(i, lam_h) * _poisson_pmf(j, lam_a)
            if i > j:
                p_home += p
            elif i == j:
                p_draw += p
            else:
                p_away += p
    return p_home, p_draw, p_away


def _fit_lambdas(p_home: float, p_draw: float, p_away: float) -> tuple[float, float]:
    """Return (lambda_home, lambda_away) that best fit the given 1x2 probabilities."""
    def loss(params):
        lam_h, lam_a = params
        if lam_h <= 0 or lam_a <= 0:
            return 1e6
        ph, pd, pa = _match_probs(lam_h, lam_a)
        return (ph - p_home) ** 2 + (pd - p_draw) ** 2 + (pa - p_away) ** 2

    result = minimize(loss, x0=[1.3, 1.0], method="Nelder-Mead",
                      options={"xatol": 1e-5, "fatol": 1e-8, "maxiter": 5000})
    lam_h, lam_a = result.x
    return max(lam_h, 0.0), max(lam_a, 0.0)


def max_ep_score(p_home: float, p_draw: float, p_away: float,
                 max_goals: int = 8) -> tuple[int, int]:
    """
    Return the (home_goals, away_goals) prediction that maximises expected points.

    Expected points for predicting score (i, j):
        E[pts] = P(correct outcome) + 2 * P(exact score)

    This is equivalent to: 1 pt for correct outcome + 2 bonus pts for exact match.
    """
    lam_h, lam_a = _fit_lambdas(p_home, p_draw, p_away)
    ph_win, pd_win, pa_win = _match_probs(lam_h, lam_a, max_goals)

    best_score = (1, 0)
    best_ep = -1.0
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            p_exact = _poisson_pmf(i, lam_h) * _poisson_pmf(j, lam_a)
            if i > j:
                p_outcome = ph_win
            elif i < j:
                p_outcome = pa_win
            else:
                p_outcome = pd_win
            ep = p_outcome + 2 * p_exact
            if ep > best_ep:
                best_ep = ep
                best_score = (i, j)
    return best_score


def implied_ou(p_home: float, p_draw: float, p_away: float) -> float:
    """
    Solve for (lambda_home, lambda_away) that best fit the given probabilities,
    then return lambda_home + lambda_away as the implied O/U line.

    Args:
        p_home, p_draw, p_away: vig-free implied probabilities summing to 1.0

    Returns:
        Implied total goals (O/U line), e.g. 2.47 means roughly O/U 2.5.
    """
    lam_h, lam_a = _fit_lambdas(p_home, p_draw, p_away)
    return lam_h + lam_a
