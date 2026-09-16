"""Change-ringing permutation primitives.

Conventions
-----------
A *permutation* ``p`` is a tuple ``p[0], p[1], ..., p[n-1]`` of zero-based
positions.  One change-ringing step forms a new row ``new`` from ``old`` with::

    new[i] = old[p[i]]

so applying change ``p`` followed by change ``q`` is the permutation
``c[i] = p[q[i]]`` (see :func:`compose`).  Starting from the ascending row
``(0, 1, ..., n-1)``, a row reached through permutations ``p0, p1, ...`` is
itself exactly the composed permutation, which keeps all of the fast
group-theory machinery exact.
"""

from __future__ import annotations

from math import gcd
from typing import Iterable, Sequence

Perm = tuple[int, ...]


def identity(bells: int) -> Perm:
    return tuple(range(bells))


def normalize(p: Sequence[int]) -> Perm:
    return tuple(p)


def inverse(p: Sequence[int]) -> Perm:
    """Inverse permutation ``q`` with ``q[p[i]] = i``."""
    out = [0] * len(p)
    for i, x in enumerate(p):
        out[x] = i
    return tuple(out)


def compose(p: Sequence[int], q: Sequence[int]) -> Perm:
    """``compose(p, q)[i] = p[q[i]]``: apply ``q`` first, then ``p``."""
    if len(p) != len(q):
        raise ValueError("cannot compose permutations of different degrees")
    return tuple(p[q[i]] for i in range(len(p)))


def power(p: Sequence[int], exponent: int) -> Perm:
    """Exact integer power of a permutation; supports exponents up to 10**12."""
    if exponent < 0:
        return power(inverse(p), -exponent)
    n = len(p)
    result = identity(n)
    base = normalize(p)
    while exponent:
        if exponent & 1:
            result = compose(result, base)
        exponent >>= 1
        if exponent:
            base = compose(base, base)
    return result


def cycles(p: Sequence[int]) -> list[tuple[int, ...]]:
    """Disjoint cycle decomposition (cycles of length 1 included)."""
    seen = [False] * len(p)
    out: list[tuple[int, ...]] = []
    for start in range(len(p)):
        if seen[start]:
            continue
        cyc: list[int] = []
        x = start
        while not seen[x]:
            seen[x] = True
            cyc.append(x)
            x = p[x]
        out.append(tuple(cyc))
    return out


def order(p: Sequence[int]) -> int:
    """Order of ``p``: LCM of its cycle lengths."""
    m = 1
    for cyc in cycles(p):
        m = lcm(m, len(cyc))
    return m


def lcm(a: int, b: int) -> int:
    return abs(a * b) // gcd(a, b) if a and b else 0


def apply_row(row: Sequence[int], p: Sequence[int]) -> Perm:
    """One ringing step: ``new[i] = old[p[i]]``."""
    return tuple(row[p[i]] for i in range(len(p)))


def product(perms: Iterable[Sequence[int]]) -> Perm:
    """Left-to-right product of a (possibly empty) sequence of changes."""
    it = iter(perms)
    try:
        acc = normalize(next(it))
    except StopIteration:
        raise ValueError("product requires at least one permutation")
    for q in it:
        acc = compose(acc, q)
    return acc
