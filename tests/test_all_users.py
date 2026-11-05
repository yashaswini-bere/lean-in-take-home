"""Rules that must hold for every member in the dataset, not only the planted ones."""
import json
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parent.parent / "seed" / "data"
USERS = json.loads((DATA / "users.json").read_text(encoding="utf-8"))
CIRCLES = {c["id"]: c for c in json.loads((DATA / "circles.json").read_text(encoding="utf-8"))}
MEMBERSHIPS = json.loads((DATA / "memberships.json").read_text(encoding="utf-8"))
ONLY_WHEN_RELEVANT = {"working-motherhood", "career-breaks", "being-the-only-one"}


def member_of(user_id):
    return {m["circle_id"] for m in MEMBERSHIPS if m["user_id"] == user_id}


@pytest.mark.parametrize("user", USERS, ids=lambda u: f"user{u['id']}")
def test_invariants(get, user):
    payload = get(user["id"])
    recommendations = payload["recommendations"]
    assert len(recommendations) == 5

    shown = [r["circle"]["id"] for r in recommendations]
    alternatives = [c["id"] for r in recommendations for c in r["similar_circles"]]
    assert len(set(shown + alternatives)) == len(shown + alternatives)

    for circle_id in shown + alternatives:
        circle = CIRCLES[circle_id]
        assert circle_id not in member_of(user["id"])
        assert circle["access"] == "public"
        assert circle["topic"] is not None
        assert circle["max_members"] is None or circle["member_count"] < circle["max_members"]
        assert circle_id not in {21, 32}  # the two dormant Circles

    topics = [r["circle"]["topic"] for r in recommendations]
    assert len(topics) == len(set(topics))
    assert [r["rank"] for r in recommendations] == [1, 2, 3, 4, 5]

    for rec in recommendations:
        assert 40 < len(rec["explanation"]) < 280
        assert user["first_name"] not in rec["explanation"]
        if rec["match_type"] == "interest":
            assert set(rec["matched_topics"]) & set(user["topic_interests"])
        if rec["match_type"] == "discovery":
            assert not rec["matched_topics"]


@pytest.mark.parametrize("user", USERS, ids=lambda u: f"user{u['id']}")
def test_life_circumstance_circles_need_a_reason(get, user):
    payload = get(user["id"])
    for rec in payload["recommendations"]:
        if rec["circle"]["topic"] in ONLY_WHEN_RELEVANT:
            assert rec["circle"]["topic"] in rec["matched_topics"]
