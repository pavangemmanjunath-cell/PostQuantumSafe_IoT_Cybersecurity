"""Small dependency-free statistics helpers shared by the benchmark scripts.

Kept separate from the scripts so the tests can import them (the benchmarks
directory is not a package).
"""

from __future__ import annotations

import math
from collections.abc import Collection, Sequence


def average_ranks(values: Sequence[float]) -> list[float]:
    """1-based ranks; tied values receive the mean of the ranks they span (the standard Spearman tie rule)."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        mean_rank = (i + j) / 2 + 1  # ranks i+1 .. j+1
        for k in range(i, j + 1):
            ranks[order[k]] = mean_rank
        i = j + 1
    return ranks


def spearman(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    """Spearman rank correlation with average ranks for ties (Pearson correlation of the ranks).

    Returns None when either sequence has no rank variance (fewer than two distinct values), where the
    coefficient is undefined.
    """
    if len(xs) != len(ys):
        raise ValueError("sequences must have the same length")
    if len(xs) < 2:
        return None
    rx, ry = average_ranks(xs), average_ranks(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry, strict=True))
    vx = sum((a - mx) ** 2 for a in rx)
    vy = sum((b - my) ** 2 for b in ry)
    if vx == 0 or vy == 0:
        return None
    return cov / math.sqrt(vx * vy)


def jaccard(a: Collection[object], b: Collection[object]) -> float:
    """Jaccard similarity |A ∩ B| / |A ∪ B| of two collections treated as sets; two empty sets are identical (1.0)."""
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / len(sa | sb)
