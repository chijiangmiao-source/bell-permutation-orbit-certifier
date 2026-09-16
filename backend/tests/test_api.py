"""FastAPI endpoint and Pydantic validation tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_verify_pass_plain_minimus():
    resp = client.post(
        "/api/verify",
        json={"bells": 4, "repeats": 2, "block": [[2, 1, 3, 4]]},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "pass"
    assert data["outcome"] is None
    assert data["witness"] is None
    assert data["block_order"] == 2
    assert data["total_steps"] == 2


def test_verify_collision_witness_uses_one_based_rows():
    resp = client.post(
        "/api/verify",
        json={"bells": 4, "repeats": 3, "block": [[2, 1, 3, 4]]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "fail"
    assert data["outcome"] == "collision"
    assert data["witness"] == {
        "first_step": 0,
        "second_step": 2,
        "row": [1, 2, 3, 4],
    }
    assert data["final_row"] is None


def test_verify_not_home_returns_final_row():
    resp = client.post(
        "/api/verify",
        json={"bells": 4, "repeats": 1, "block": [[2, 3, 1, 4]]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "fail"
    assert data["outcome"] == "not_home"
    assert data["final_row"] == [2, 3, 1, 4]


def test_trillion_repeats_accepted_and_fast():
    resp = client.post(
        "/api/verify",
        json={"bells": 4, "repeats": 1_000_000_000_000, "block": [[2, 1, 3, 4]]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "fail"
    assert data["outcome"] == "collision"
    assert data["witness"]["second_step"] == 2


def test_bells_below_range_rejected():
    resp = client.post(
        "/api/verify",
        json={"bells": 3, "repeats": 1, "block": [[2, 1, 3]]},
    )
    assert resp.status_code == 422
    err = resp.json()["error"]
    assert err["field"] == "bells"


def test_bells_above_range_rejected():
    resp = client.post(
        "/api/verify",
        json={"bells": 13, "repeats": 1, "block": [list(range(1, 14))]},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["field"] == "bells"


def test_repeats_above_trillion_rejected():
    resp = client.post(
        "/api/verify",
        json={
            "bells": 4,
            "repeats": 1_000_000_000_001,
            "block": [[2, 1, 3, 4]],
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["field"] == "repeats"


def test_block_wrong_length_points_to_first_bad_item():
    resp = client.post(
        "/api/verify",
        json={
            "bells": 4,
            "repeats": 1,
            "block": [[2, 1, 3, 4], [2, 1, 4]],
        },
    )
    assert resp.status_code == 422
    err = resp.json()["error"]
    assert err["field"] == "block[1]"
    assert "Value error" not in err["message"]
    assert "block[1] has length 3, expected 4" == err["message"]


def test_block_duplicate_bell_points_to_first_bad_item():
    resp = client.post(
        "/api/verify",
        json={
            "bells": 4,
            "repeats": 1,
            "block": [[2, 1, 3, 4], [2, 2, 3, 4]],
        },
    )
    assert resp.status_code == 422
    field = resp.json()["error"]["field"]
    assert field == "block[1]"


def test_block_empty_rejected():
    resp = client.post(
        "/api/verify",
        json={"bells": 4, "repeats": 1, "block": []},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["field"] == "block"


def test_block_too_large_rejected():
    resp = client.post(
        "/api/verify",
        json={
            "bells": 4,
            "repeats": 1,
            "block": [[2, 1, 3, 4]] * 5001,
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["field"] == "block"


def test_non_integer_bells_rejected():
    resp = client.post(
        "/api/verify",
        json={"bells": 4.5, "repeats": 1, "block": [[2, 1, 3, 4]]},
    )
    assert resp.status_code == 422
