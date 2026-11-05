from datetime import datetime, timedelta, timezone

from app.explain import explanation, spots_left
from app.interests import member_interests
from app.ranker import health_score, is_full, is_inactive, recommend
from app.repository import Circle, Member

NOW = datetime(2026, 9, 21, tzinfo=timezone.utc)


def circle(**overrides):
    values = dict(
        id=1, name="Test Circle", slug="test", description="d", topic="negotiation",
        tags=frozenset(), cover_image_url=None, format="virtual", access="public",
        join_policy="open", max_members=None, member_count=5, last_activity_at=NOW,
        feed_posts_30d=10, chat_messages_30d=50, engagement_per_post=10.0,
    )
    return Circle(**{**values, **overrides})


def member(**overrides):
    values = dict(
        id=1, bio=None, job_title=None, location=None,
        stated_topics=frozenset(), circle_ids=frozenset(),
    )
    return Member(**{**values, **overrides})


def test_null_capacity_is_never_full():
    assert not is_full(circle(max_members=None, member_count=500))


def test_capacity_boundary():
    assert is_full(circle(max_members=5, member_count=5))
    assert not is_full(circle(max_members=6, member_count=5))
    assert spots_left(circle(max_members=6, member_count=5)) == 1


def test_inactive_rules():
    assert is_inactive(circle(last_activity_at=NOW - timedelta(days=61)), NOW)
    assert is_inactive(circle(feed_posts_30d=0, chat_messages_30d=3), NOW)
    assert not is_inactive(circle(feed_posts_30d=0, chat_messages_30d=5), NOW)
    assert not is_inactive(circle(last_activity_at=NOW - timedelta(days=60)), NOW)


def test_quieter_circles_score_lower_on_health():
    busy = circle()
    quiet = circle(feed_posts_30d=2, chat_messages_30d=5, engagement_per_post=2.0)
    assert health_score(busy, NOW) > health_score(quiet, NOW)


def test_stated_interest_beats_profile_inference():
    interests = member_interests(
        member(bio="First-time manager.", stated_topics=frozenset({"managing-a-team"}))
    )
    assert interests["managing-a-team"].source == "stated"


def test_bio_inference_and_manager_titles():
    assert "career-breaks" in member_interests(member(bio="Back after a career break."))
    assert "managing-a-team" in member_interests(member(job_title="Engineering Manager"))
    assert "managing-a-team" not in member_interests(member(job_title="Product Manager"))


def test_nothing_personal_is_inferred_from_a_blank_profile():
    assert member_interests(member()) == {}


def test_tag_alone_does_not_surface_a_life_circumstance_circle():
    circles = [circle(id=1, topic="working-motherhood", tags=frozenset({"negotiation"}))]
    result = recommend(member(stated_topics=frozenset({"negotiation"})), circles, NOW)
    assert result.picks == []


def test_topic_she_already_has_a_circle_for_is_deprioritized():
    circles = [
        circle(id=1, name="Mine", topic="negotiation"),
        circle(id=2, name="Second", topic="negotiation"),
        circle(id=3, name="Other", topic="confidence", feed_posts_30d=4),
    ]
    result = recommend(
        member(
            stated_topics=frozenset({"negotiation", "confidence"}),
            circle_ids=frozenset({1}),
        ),
        circles,
        NOW,
    )
    assert [p.circle.id for p in result.picks] == [3, 2]
    text = explanation(result.picks[1], {"negotiation": "Negotiation", "confidence": "Confidence"}, True)
    assert "alongside Mine" in text
