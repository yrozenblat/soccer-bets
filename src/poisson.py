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


def implied_ou(p_home: float, p_draw: float, p_away: float) -> float:
    """
    Solve for (lambda_home, lambda_away) that best fit the given probabilities,
    then return lambda_home + lambda_away as the implied O/U line.

    Args:
        p_home, p_draw, p_away: vig-free implied probabilities summing to 1.0

    Returns:
        Implied total goals (O/U line), e.g. 2.47 means roughly O/U 2.5.
    """
    def loss(params):
        lam_h, lam_a = params
        if lam_h <= 0 or lam_a <= 0:
            return 1e6
        ph, pd, pa = _match_probs(lam_h, lam_a)
        return (ph - p_home) ** 2 + (pd - p_draw) ** 2 + (pa - p_away) ** 2

    # Initial guess: symmetric around 1.3 goals each (typical WC match)
    result = minimize(loss, x0=[1.3, 1.0], method="Nelder-Mead",
                      options={"xatol": 1e-5, "fatol": 1e-8, "maxiter": 5000})
    lam_h, lam_a = result.x
    return max(lam_h, 0.0) + max(lam_a, 0.0)
