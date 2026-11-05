"""The four planted scenarios from the dataset README."""


def ids(payload):
    return [r["circle"]["id"] for r in payload["recommendations"]]


def card(payload, circle_id):
    return next(r for r in payload["recommendations"] if r["circle"]["id"] == circle_id)


def test_cold_start_user_42(get):
    payload = get(42)
    assert payload["personalization"] == "none"
    assert payload["next_step"]
    assert len(payload["recommendations"]) == 5
    for rec in payload["recommendations"]:
        assert rec["match_type"] == "discovery"
        assert rec["circle"]["format"] != "in_person"  # we don't know where she is
        assert rec["circle"]["join_policy"] == "open"
        assert "your interests" not in rec["explanation"]
        assert "your profile" not in rec["explanation"].lower()
    assert len({r["circle"]["topic"] for r in payload["recommendations"]}) == 5


def test_cold_start_does_not_assume_personal_circumstances(get):
    topics = {r["circle"]["topic"] for r in get(42)["recommendations"]}
    assert not topics & {"working-motherhood", "career-breaks", "being-the-only-one"}
    assert not set(ids(get(42))) & {27, 28}


def test_obvious_matches_user_7(get):
    payload = get(7)
    assert set(ids(payload)[:2]) == {5, 6}
    assert "public speaking" in card(payload, 6)["explanation"]
    assert "leadership skills" in card(payload, 5)["explanation"]


def test_duplicates_user_15(get):
    payload = get(15)
    negotiation = [i for i in ids(payload) if i in {10, 11, 12}]
    assert len(negotiation) == 1
    lead = card(payload, negotiation[0])
    assert {c["id"] for c in lead["similar_circles"]} == {10, 11, 12} - set(negotiation)
    assert lead["rank"] <= 2


def test_duplicates_unlisted_circle_is_not_offered_to_user_15(get):
    payload = get(15)
    every_id = set(ids(payload)) | {
        c["id"] for r in payload["recommendations"] for c in r["similar_circles"]
    }
    assert 30 not in every_id  # active confidence Circle, but unlisted


def test_full_and_inactive_user_23(get):
    payload = get(23, debug=True)
    assert ids(payload)[0] == 22
    assert not set(ids(payload)) & {20, 21}
    excluded = {e["id"]: e["reasons"] for e in payload["excluded"]}
    assert "full" in excluded[20]
    assert "inactive" in excluded[21]
    alternatives = {c["id"] for r in payload["recommendations"] for c in r["similar_circles"]}
    assert not alternatives & {20, 21}
    assert "leader's approval" in card(payload, 22)["explanation"]
