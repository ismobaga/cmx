"""Forward-backward over the token chain with a 'stay in the same language'
transition prior. Turns per-token emissions into per-token posteriors."""
from __future__ import annotations

import math
from typing import Mapping, Sequence

FLOOR = 1e-4


def _lse(xs: Sequence[float]) -> float:
    m = max(xs)
    return m + math.log(sum(math.exp(x - m) for x in xs))


def posteriors(emissions: Sequence[Mapping[str, float]], labels: Sequence[str],
               stay: float = 0.8) -> list[dict[str, float]]:
    T, K = len(emissions), len(labels)
    if T == 0:
        return []
    ls, lw = math.log(stay), math.log((1 - stay) / (K - 1))
    trans = [[ls if i == j else lw for j in range(K)] for i in range(K)]
    E = [[math.log(max(e.get(l, 0.0), FLOOR)) for l in labels] for e in emissions]

    a = [[0.0] * K for _ in range(T)]
    for k in range(K):
        a[0][k] = -math.log(K) + E[0][k]
    for t in range(1, T):
        for k in range(K):
            a[t][k] = E[t][k] + _lse([a[t - 1][j] + trans[j][k] for j in range(K)])

    b = [[0.0] * K for _ in range(T)]
    for t in range(T - 2, -1, -1):
        for j in range(K):
            b[t][j] = _lse([trans[j][k] + E[t + 1][k] + b[t + 1][k] for k in range(K)])

    out = []
    for t in range(T):
        s = [a[t][k] + b[t][k] for k in range(K)]
        z = _lse(s)
        out.append({labels[k]: math.exp(s[k] - z) for k in range(K)})
    return out
