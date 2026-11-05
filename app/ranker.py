"""Rank Circles for a member in three steps: filter, score, then diversify."""
import math
from dataclasses import dataclass, field
from datetime import datetime

from app import config
from app.interests import Interest, member_interests
from app.repository import Circle, Member


@dataclass
class Scored:
    circle: Circle
    score: float
    relevance: float
    health: float
    format_fit: float
    join_ease: float
    matches: list[tuple[Interest, str]]  # (interest, "topic" or "tag")
    covered_by: str | None = None
    alternatives: list[Circle] = field(default_factory=list)


@dataclass
class Result:
    interests: dict[str, Interest]
    picks: list[Scored]
    excluded: list[tuple[Circle, list[str]]]


def is_full(circle: Circle) -> bool:
    return circle.max_members is not None and circle.member_count >= circle.max_members


def days_since_activity(circle: Circle, as_of: datetime) -> float:
    return max((as_of - circle.last_activity_at).total_seconds() / 86400, 0)


def is_inactive(circle: Circle, as_of: datetime) -> bool:
    silent = days_since_activity(circle, as_of) > config.INACTIVE_AFTER_DAYS
    no_conversation = (
        circle.feed_posts_30d == 0
        and circle.chat_messages_30d < config.MIN_CHAT_WITHOUT_POSTS
    )
    return silent or no_conversation


def exclusion_reasons(circle: Circle, member: Member, as_of: datetime) -> list[str]:
    """Hard rules. No score can bring back a Circle that fails one of these."""
    reasons = []
    if circle.id in member.circle_ids:
        reasons.append("already_a_member")
    if circle.access != "public":
        reasons.append("unlisted")
    if is_full(circle):
        reasons.append("full")
    if is_inactive(circle, as_of):
        reasons.append("inactive")
    if circle.topic is None:
        # No topic, tags or description: nothing to match or explain honestly.
        reasons.append("no_topic")
    return reasons


def _scaled(value: float, reference: float) -> float:
    return min(math.log1p(value) / math.log1p(reference), 1.0)


def health_score(circle: Circle, as_of: datetime) -> float:
    age = days_since_activity(circle, as_of)
    recency = 0.5 ** (age / config.RECENCY_HALF_LIFE_DAYS)
    return (
        config.HEALTH_RECENCY * recency
        + config.HEALTH_POSTS * _scaled(circle.feed_posts_30d, config.POSTS_REFERENCE)
        + config.HEALTH_CHAT * _scaled(circle.chat_messages_30d, config.CHAT_REFERENCE)
        + config.HEALTH_ENGAGEMENT
        * _scaled(circle.engagement_per_post, config.ENGAGEMENT_REFERENCE)
    )


def _match_strength(interest: Interest, kind: str) -> float:
    if interest.source == "stated":
        return config.STATED_TOPIC if kind == "topic" else config.STATED_TAG
    return config.PROFILE_TOPIC


def find_matches(
    circle: Circle, interests: dict[str, Interest]
) -> list[tuple[Interest, str]]:
    matches = []
    if circle.topic in interests:
        matches.append((interests[circle.topic], "topic"))
    for tag in sorted(circle.tags - {circle.topic}):
        if tag in interests and interests[tag].source == "stated":
            matches.append((interests[tag], "tag"))
    matches.sort(key=lambda m: -_match_strength(*m))
    return matches


def relevance_score(matches: list[tuple[Interest, str]]) -> float:
    if not matches:
        return 0.0
    best = _match_strength(*matches[0])
    return min(best + config.EXTRA_MATCH_BONUS * (len(matches) - 1), 1.0)


def format_score(circle: Circle, member: Member) -> float:
    if circle.format != "in_person":
        return config.FORMAT_REMOTE_FRIENDLY
    if member.location and member.location != "Remote":
        return config.FORMAT_IN_PERSON_LOCATION_KNOWN
    return config.FORMAT_IN_PERSON_NO_LOCATION


def _score(
    circle: Circle,
    member: Member,
    interests: dict[str, Interest],
    covered: dict[str, str],
    as_of: datetime,
) -> Scored:
    matches = find_matches(circle, interests)
    relevance = relevance_score(matches)
    health = health_score(circle, as_of)
    format_fit = format_score(circle, member)
    join_ease = config.JOIN_OPEN if circle.join_policy == "open" else config.JOIN_REQUEST
    score = (
        config.WEIGHT_RELEVANCE * relevance
        + config.WEIGHT_HEALTH * health
        + config.WEIGHT_FORMAT * format_fit
        + config.WEIGHT_JOIN * join_ease
    )
    covered_by = covered.get(circle.topic)
    if covered_by:
        score *= config.ALREADY_COVERED_MULTIPLIER
    return Scored(
        circle, score, relevance, health, format_fit, join_ease, matches, covered_by
    )


def _skip_reason(scored: Scored, interests: dict[str, Interest]) -> str | None:
    topic = scored.circle.topic
    if topic in config.ONLY_WHEN_RELEVANT and topic not in interests:
        return "topic_not_assumed"
    if not scored.matches and scored.health < config.DISCOVERY_MIN_HEALTH:
        return "no_match_and_low_activity"
    return None


def recommend(
    member: Member, circles: list[Circle], as_of: datetime, limit: int = config.DEFAULT_LIMIT
) -> Result:
    interests = member_interests(member)
    # Topics the member already has a Circle for, mapped to that Circle's name.
    covered = {
        c.topic: c.name for c in circles if c.id in member.circle_ids and c.topic
    }

    candidates: list[Scored] = []
    excluded: list[tuple[Circle, list[str]]] = []
    for circle in circles:
        reasons = exclusion_reasons(circle, member, as_of)
        if reasons:
            excluded.append((circle, reasons))
            continue
        scored = _score(circle, member, interests, covered, as_of)
        skip = _skip_reason(scored, interests)
        if skip:
            excluded.append((circle, [skip]))
        else:
            candidates.append(scored)

    candidates.sort(key=lambda s: (-s.score, s.circle.id))

    # One Circle per topic, with the next-best kept as alternatives on its card.
    picks: list[Scored] = []
    by_topic: dict[str, Scored] = {}
    for scored in candidates:
        lead = by_topic.get(scored.circle.topic)
        if lead is None:
            by_topic[scored.circle.topic] = scored
            picks.append(scored)
        elif len(lead.alternatives) < config.MAX_ALTERNATIVES:
            lead.alternatives.append(scored.circle)

    return Result(interests, picks[:limit], excluded)
