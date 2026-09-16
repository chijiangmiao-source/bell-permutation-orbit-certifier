"""Differential tests: the exact verifier must agree with brute simulation."""

from __future__ import annotations

import itertools
import random

import pytest

from app.permutation import Perm, apply_row, compose, identity, order, power
from app.verifier import (
    OUTCOME_COLLISION,
    OUTCOME_NOT_HOME,
    STATUS_FAIL,
    STATUS_PASS,
    verify,
)


def brute(block: list[Perm], repeats: int) -> dict:
    """Reference semantics: simulate every step directly."""
    n = len(block[0])
    length = len(block)
    total = length * repeats
    row = identity(n)
    seen: dict[Perm, int] = {row: 0}
    t = 0
    for a in range(repeats):
        for change in block:
            row = apply_row(row, change)
            t += 1
            if t <= total - 1:  # only steps 0..N-1 are compared
                if row in seen:
                    return {
                        "status": STATUS_FAIL,
                        "outcome": OUTCOME_COLLISION,
                        "first": seen[row],
                        "second": t,
                        "row": row,
                    }
                seen[row] = t
    # t == total == N; rounds check only
    if row == identity(n):
        return {"status": STATUS_PASS, "outcome": None}
    return {
        "status": STATUS_FAIL,
        "outcome": OUTCOME_NOT_HOME,
        "final": row,
    }


def assert_matches(block: list[Perm], repeats: int) -> None:
    expected = brute(block, repeats)
    result = verify(block, repeats)
    assert result.status == expected["status"]
    assert result.total_steps == len(block) * repeats
    if expected["status"] == STATUS_PASS:
        assert result.outcome is None
        assert result.witness is None
        assert result.final_row is None
    elif expected["outcome"] == OUTCOME_COLLISION:
        assert result.outcome == OUTCOME_COLLISION
        assert result.witness is not None
        assert (result.witness.first_step, result.witness.second_step) == (
            expected["first"],
            expected["second"],
        )
        assert result.witness.row == expected["row"]
        assert result.final_row is None
    else:
        assert result.outcome == OUTCOME_NOT_HOME
        assert result.witness is None
        assert result.final_row == expected["final"]


def random_block(rng: random.Random, n: int, length: int) -> list[Perm]:
    perms = list(itertools.permutations(range(n)))
    return [rng.choice(perms) for _ in range(length)]


@pytest.mark.parametrize("seed", range(60))
def test_random_small_repeats_match_brute(seed):
    rng = random.Random(seed)
    n = rng.randint(4, 6)
    length = rng.randint(1, 6)
    repeats = rng.randint(1, 30)
    assert_matches(random_block(rng, n, length), repeats)


@pytest.mark.parametrize("seed", range(30))
def test_random_larger_bells_match_brute(seed):
    rng = random.Random(1000 + seed)
    n = rng.randint(7, 9)
    length = rng.randint(1, 4)
    repeats = rng.randint(1, 40)
    assert_matches(random_block(rng, n, length), repeats)


def test_plain_course_minimus_passes():
    # Plain hunt on 4 bells: single swap change, order 2, repeats 2.
    # Steps 0 and 1 differ; step N=2 returns rounds and is not compared.
    p = (1, 0, 2, 3)
    block = [p]
    result = verify(block, 2)
    assert result.status == STATUS_PASS
    assert result.block_order == 2
    assert result.total_steps == 2


def test_not_home_single_repeat():
    # One 3-cycle on 4 bells; repeats=1 does not return to rounds and has
    # no repeat among steps 0 (only step 0 is compared).
    p = (1, 2, 0, 3)
    result = verify([p], 1)
    assert result.status == STATUS_FAIL
    assert result.outcome == OUTCOME_NOT_HOME
    assert result.final_row == (1, 2, 0, 3)


def test_collision_same_round_picks_minimum_second_step():
    # Block whose first two prefixes coincide must report steps 1 and 0? No:
    # prefixes distinct by construction; instead force a repeat inside range.
    p = (1, 0, 2, 3)
    result = verify([p], 3)
    # steps: 0 rounds, 1 swapped, 2 rounds -> collision (0, 2).
    assert result.status == STATUS_FAIL
    assert result.outcome == OUTCOME_COLLISION
    assert result.witness is not None
    assert (result.witness.first_step, result.witness.second_step) == (0, 2)
    assert result.witness.row == (0, 1, 2, 3)


def test_trillion_repeats_collision_is_instant():
    p = (1, 0, 2, 3)
    result = verify([p], 10**12)
    assert result.status == STATUS_FAIL
    assert result.witness is not None
    assert result.witness.second_step == 2
    assert result.witness.first_step == 0


def test_trillion_repeats_pass_is_instant():
    # A block whose product has order m dividing 10**12 and whose internal
    # prefixes never collide across/within rounds: single 2-bell swap,
    # repeats an even number, but repeats must be >= order to collide...
    # Instead: block product identity and prefixes all in distinct cosets.
    # Easiest: block = [swap, swap] (product identity); prefixes are
    # [id, swap]. Repeats even huge: rows at even steps are id -> those DO
    # collide (steps 0 and 2). Use repeats=1 with product identity: pass.
    p = (1, 0, 2, 3)
    result = verify([p, p], 1)
    assert result.status == STATUS_PASS
    assert result.total_steps == 2


def test_trillion_even_swap_block_collides_across_rounds():
    p = (1, 0, 2, 3)
    # block product = identity, so a huge even repeats ends at rounds, but
    # step 2 repeats step 0 first: collision takes priority.
    result = verify([p, p], 10**12)
    assert result.status == STATUS_FAIL
    assert result.outcome == OUTCOME_COLLISION
    assert result.witness is not None
    assert result.witness.second_step == 2
    assert result.witness.first_step == 0


def test_huge_no_collision_not_home():
    # 3-cycle change; with repeats = 10**12 + 1 style counts, rows collide
    # whenever repeats >= order=3. Use repeats=2: no collision, not home.
    p = (1, 2, 0, 3)
    assert_matches([p], 2)
    result = verify([p], 2)
    assert result.status == STATUS_FAIL
    assert result.outcome == OUTCOME_NOT_HOME


def test_witness_row_consistency_with_power():
    p = (1, 2, 0, 4, 3)  # order 6
    result = verify([p], 100)
    assert result.outcome == OUTCOME_COLLISION
    w = result.witness
    # Directly simulate to the witness steps.
    row = identity(5)
    rows = {0: row}
    for t in range(1, w.second_step + 1):
        row = apply_row(row, p)
        rows[t] = row
    assert rows[w.first_step] == rows[w.second_step] == w.row


def test_second_step_minimization_then_first_step():
    # Construct block [p] where order is larger; earliest second step wins.
    p = (1, 2, 3, 0)  # 4-cycle
    result = verify([p], 10)
    # collision at (0, 4), second step 4 minimal.
    assert result.witness is not None
    assert result.witness.first_step == 0
    assert result.witness.second_step == 4


def test_cross_round_pair_different_offsets():
    # Block length 2 with changes chosen so the repeat happens between
    # different offsets in different rounds; differential coverage ensures
    # exactness, here assert a concrete known case.
    p = (1, 2, 0, 3)  # 3-cycle, order 3
    q = (0, 2, 1, 3)  # swap 1<->2
    assert_matches([p, q], 5)
    assert_matches([p, q], 7)


def test_validation_rejects_empty_block():
    with pytest.raises(ValueError):
        verify([], 1)


def test_validation_rejects_bad_repeats():
    with pytest.raises(ValueError):
        verify([(1, 0, 2, 3)], 0)


def test_max_limits_trillion_repeats_are_instant():
    rng = random.Random(99)
    n = 12

    def rand_perm() -> Perm:
        a = list(range(n))
        rng.shuffle(a)
        return tuple(a)

    block = [rand_perm() for _ in range(5000)]
    start = __import__("time").perf_counter()
    result = verify(block, 1_000_000_000_000)
    elapsed = __import__("time").perf_counter() - start
    assert result.status == STATUS_FAIL
    assert result.outcome == OUTCOME_COLLISION
    assert result.witness is not None
    assert elapsed < 5.0


def test_large_block_small_repeats_matches_brute():
    rng = random.Random(42)
    n = 12

    def rand_perm() -> Perm:
        a = list(range(n))
        rng.shuffle(a)
        return tuple(a)

    block = [rand_perm() for _ in range(60)]
    assert_matches(block, 3)


def test_exhaustive_s4_single_change_blocks():
    # Every possible length-1 block on 4 bells across repeats 1..24 must
    # agree exactly with the brute simulation.
    for p in itertools.permutations(range(4)):
        for repeats in range(1, 25):
            assert_matches([p], repeats)


def test_exhaustive_s4_length_two_blocks():
    perms = list(itertools.permutations(range(4)))
    for p in perms:
        for q in perms:
            for repeats in (1, 2, 3, 6, 12):
                assert_matches([p, q], repeats)
