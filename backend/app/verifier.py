"""Exact truth verification for a repeated change-ringing block.

A composition rings ``N = block_size * repeats`` steps starting from rounds
(the ascending row).  Only steps ``0 .. N-1`` are compared for repeats; step
``N`` is used solely for the rounds check.

The implementation never simulates up to ``10**12`` repeats.  Writing ``Q``
for the product of one block and ``B_r`` for the row permutation at offset
``r`` inside a block, the row at step ``t = a*L + r`` is

    P_t = Q ** a  composed with  B_r.

Rows are grouped by the left cosets of the cyclic subgroup ``<Q>``.  Inside
one coset the row is fixed by a single exponent modulo the block order ``m``;
intersecting the resulting arithmetic progression of round indices with
``[0, repeats)`` (a modular interval intersection) yields the witness without
any large enumeration.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import gcd

from .permutation import Perm, compose, identity, inverse, order, power, product

STATUS_PASS = "pass"
STATUS_FAIL = "fail"
OUTCOME_COLLISION = "collision"
OUTCOME_NOT_HOME = "not_home"


@dataclass(frozen=True)
class Witness:
    first_step: int
    second_step: int
    row: tuple[int, ...]


@dataclass(frozen=True)
class VerificationResult:
    status: str
    outcome: str | None
    bells: int
    block_size: int
    repeats: int
    total_steps: int
    block_order: int
    witness: Witness | None
    final_row: tuple[int, ...] | None


@dataclass(frozen=True)
class _CycleInfo:
    members: tuple[int, ...]  # members[k] = Q**k applied to the root
    offset: tuple[int, ...]  # offset[point] = exponent of point in the cycle

    @property
    def root(self) -> int:
        return self.members[0]


def _cycle_info(Q: Perm) -> list[_CycleInfo]:
    n = len(Q)
    seen = [False] * n
    infos: list[_CycleInfo] = []
    for start in range(n):
        if seen[start]:
            continue
        members: list[int] = []
        x = start
        while not seen[x]:
            seen[x] = True
            members.append(x)
            x = Q[x]
        offset = [0] * n
        for k, v in enumerate(members):
            offset[v] = k
        infos.append(_CycleInfo(tuple(members), tuple(offset)))
    return infos


def _cyclic_exponent(h: Perm, infos: list[_CycleInfo]) -> int | None:
    """Return ``e`` with ``h = Q**e`` (e in [0, order)), or ``None``.

    Membership in the cyclic subgroup is decided cycle by cycle: on every
    cycle of ``Q`` the map must be a uniform rotation, and all rotations
    must be compatible with one global exponent (CRT over cycle lengths).
    """
    rem = 0  # current constraint: e ≡ rem (mod mod)
    mod = 1
    for info in infos:
        offset = info.offset
        c = len(info.members)
        base = info.root
        hb = h[base]
        if hb not in info.members:
            return None
        s = offset[hb]  # base sits at offset 0, so the rotation is s
        for v in info.members:
            hv = h[v]
            if hv not in info.members or (offset[hv] - offset[v]) % c != s:
                return None
        # Merge e ≡ s (mod c) into e ≡ rem (mod mod).
        g = gcd(mod, c)
        if (s - rem) % g != 0:
            return None
        if c // g > 1:
            k = (((s - rem) // g) * pow(mod // g, -1, c // g)) % (c // g)
            rem = (rem + mod * k) % (mod * (c // g))
            mod = mod * (c // g)
    return rem


def _coset_key(B: Perm, Q: Perm, m: int) -> Perm:
    """Canonical name of the left coset ``<Q> o B``.

    The lexicographically smallest member of the coset is a unique name.
    With at most 12 bells the order of any element is at most Landau's
    g(12) = 60, so walking the whole cyclic coset is exact and cheap.
    """
    best = B
    cur = B
    for _ in range(m - 1):
        cur = compose(Q, cur)
        if cur < best:
            best = cur
    return best


@dataclass
class _Coset:
    rep: Perm
    entries: list[tuple[int, int]]  # (offset r, exponent c_r with B_r = Q**c_r o rep)


def smallest_positive_residue(d: int, modulus: int) -> int:
    """Smallest positive integer congruent to ``d`` modulo ``modulus``.

    The admissible round differences form the arithmetic progression
    d, d+m, d+2m, ... ; this is the first point of that progression, i.e. the
    intersection of the modular residue class with the positive integers.
    """
    r = d % modulus
    return r if r != 0 else modulus


def modular_interval_has_point(d: int, modulus: int, upper: int) -> bool:
    """Whether the residue class d (mod m) meets the integer interval [1, upper].

    This is a modular interval intersection: the progression
    ``{smallest_positive_residue(d, m) + k*m}`` shares a point with
    ``[1, upper]`` exactly when its first element does not exceed ``upper``.
    """
    return smallest_positive_residue(d, modulus) <= upper


def verify(block: list[Perm], repeats: int) -> VerificationResult:
    if not block:
        raise ValueError("block must contain at least one permutation")
    if repeats < 1:
        raise ValueError("repeats must be at least 1")
    n = len(block[0])
    length = len(block)
    total = length * repeats

    q = product(block)
    m = order(q)
    infos = _cycle_info(q)

    # B_r is reached after the first r changes; step t = a*L + r has row
    # P_t = (Q**a) o B_r.
    prefixes: list[Perm] = [identity(n)]
    cur = identity(n)
    for j in range(length - 1):
        cur = compose(cur, block[j])
        prefixes.append(cur)

    # Phase 1: a repeat inside round 0 has its second step below L, which no
    # cross-round repeat can beat.  A single O(L) scan finds it exactly; this
    # also means that afterwards every coset holds each residue at most once.
    round_zero: dict[Perm, int] = {}
    for r, b in enumerate(prefixes):
        earlier = round_zero.get(b)
        if earlier is not None:
            return VerificationResult(
                status=STATUS_FAIL,
                outcome=OUTCOME_COLLISION,
                bells=n,
                block_size=length,
                repeats=repeats,
                total_steps=total,
                block_order=m,
                witness=Witness(earlier, r, b),
                final_row=None,
            )
        round_zero[b] = r

    # Assign every prefix to its coset of <Q>, together with the shift
    # c_r such that B_r = Q**c_r o rep.
    cosets: dict[Perm, _Coset] = {}
    for r, b in enumerate(prefixes):
        key = _coset_key(b, q, m)
        coset = cosets.get(key)
        if coset is None:
            coset = _Coset(rep=key, entries=[])
            cosets[key] = coset
        h = compose(b, inverse(coset.rep))
        exponent = _cyclic_exponent(h, infos)
        if exponent is None:  # pragma: no cover - equal keys guarantee membership
            raise RuntimeError("internal coset assignment failed")
        coset.entries.append((r, exponent))    # Phase 2: only cross-round repeats remain.  Since round 0 has no
    # duplicate, every coset contains a residue at most once and therefore at
    # most m entries; the total number of offset pairs is O(L*m) <= 147_500.
    # Candidate repeated pairs are keyed by (second step, first step).
    best: tuple[int, int] | None = None
    best_coset: _Coset | None = None
    best_residue = 0
    for coset in cosets.values():
        entries = coset.entries
        for idx in range(len(entries)):
            u, cu = entries[idx]
            # Same offset in a later round (delta rounds must be a multiple of m).
            if m <= repeats - 1:
                cand = (m * length + u, u)
                if best is None or cand < best:
                    best, best_coset, best_residue = cand, coset, cu
            for jdx in range(idx + 1, len(entries)):
                v, cv = entries[jdx]
                # Two different offsets: place the earlier one in round 0 and
                # the later one in the smallest feasible positive round, in
                # both orientations.  Rows agree exactly when
                # b - a ≡ c_first - c_later (mod m).
                for first, c_first, later, c_later in (
                    (u, cu, v, cv),
                    (v, cv, u, cu),
                ):
                    delta = smallest_positive_residue(c_first - c_later, m)
                    # Modular interval intersection: the round difference
                    # must actually fit into [1, repeats-1].
                    if modular_interval_has_point(
                        c_first - c_later, m, repeats - 1
                    ):
                        cand = (delta * length + later, first)
                        if best is None or cand < best:
                            best, best_coset, best_residue = (
                                cand,
                                coset,
                                (delta + c_later) % m,
                            )

    if best is not None:
        second_step, _ = best
        coset = best_coset
        assert coset is not None
        k = best_residue
        # Resolve the true earliest occurrence of the repeated row (the
        # second-step minimization only fixes the later occurrence).
        first_step = min(
            a0 * length + w
            for w, cw in coset.entries
            if (a0 := (k - cw) % m) < repeats and a0 * length + w < second_step
        )
        row = compose(power(q, k), coset.rep)
        return VerificationResult(
            status=STATUS_FAIL,
            outcome=OUTCOME_COLLISION,
            bells=n,
            block_size=length,
            repeats=repeats,
            total_steps=total,
            block_order=m,
            witness=Witness(first_step, second_step, row),
            final_row=None,
        )

    final_perm = power(q, repeats)  # step N = round `repeats`, offset 0
    if final_perm == identity(n):
        return VerificationResult(
            status=STATUS_PASS,
            outcome=None,
            bells=n,
            block_size=length,
            repeats=repeats,
            total_steps=total,
            block_order=m,
            witness=None,
            final_row=None,
        )

    return VerificationResult(
        status=STATUS_FAIL,
        outcome=OUTCOME_NOT_HOME,
        bells=n,
        block_size=length,
        repeats=repeats,
        total_steps=total,
        block_order=m,
        witness=None,
        final_row=final_perm,
    )
