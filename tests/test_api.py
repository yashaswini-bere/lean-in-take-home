def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_unknown_user_is_404(client):
    assert client.get("/users/99999/recommendations").status_code == 404


def test_limit_is_validated(client):
    assert client.get("/users/7/recommendations?limit=0").status_code == 422
    assert client.get("/users/7/recommendations?limit=21").status_code == 422
    assert len(client.get("/users/7/recommendations?limit=2").json()["recommendations"]) == 2


def test_scores_only_appear_in_debug(get):
    assert "debug" not in get(7)["recommendations"][0]
    assert "excluded" not in get(7)
    assert "score" in get(7, debug=True)["recommendations"][0]["debug"]


def test_results_are_deterministic(get):
    assert get(15) == get(15)


def test_activity_is_measured_from_the_snapshot_not_the_system_clock(get):
    # The data ends in September 2026. With the system clock as "now", recency
    # would decay for every Circle and dormancy checks would drift over time.
    assert get(7)["data_as_of"].startswith("2026-09-21")
