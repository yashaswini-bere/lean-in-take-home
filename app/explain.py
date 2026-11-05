"""Turn ranking signals into the sentences a member reads.

Explanations are templates, not LLM output. Every clause is built from a signal
that really affected the ranking, so a sentence cannot claim something untrue.
"""
from app import config
from app.ranker import Scored
from app.repository import Circle


def spots_left(circle: Circle) -> int | None:
    if circle.max_members is None:
        return None
    return max(circle.max_members - circle.member_count, 0)


def _join_labels(labels: list[str]) -> str:
    if len(labels) <= 1:
        return "".join(labels)
    return ", ".join(labels[:-1]) + " and " + labels[-1]


def _why_it_fits(scored: Scored, labels: dict[str, str], personalized: bool) -> str:
    def label(topic: str) -> str:
        return labels[topic].lower()

    circle_topic = label(scored.circle.topic)
    main = next((i for i, kind in scored.matches if kind == "topic"), None)
    tagged = [label(i.topic) for i, kind in scored.matches if kind == "tag"]

    if main and main.source == "stated":
        sentence = f"Focuses on {circle_topic}, one of your interests"
        if tagged:
            sentence += f", and also covers {_join_labels(tagged)}"
        return sentence + "."

    if main:
        because = main.because[0].upper() + main.because[1:]
        sentence = f"{because}, and this Circle focuses on {circle_topic}"
        if tagged:
            sentence += f". It also covers {_join_labels(tagged)}, from your interests"
        return sentence + "."

    if tagged:
        return (
            f"Focuses on {circle_topic} and also covers {_join_labels(tagged)}, "
            "from your interests."
        )

    if personalized:
        return f"Something new to explore: a Circle on {circle_topic}."
    return f"A good place to start while we get to know you: a Circle on {circle_topic}."


def _activity(circle: Circle) -> str:
    posts = "post" if circle.feed_posts_30d == 1 else "posts"
    counts = (
        f"{circle.feed_posts_30d} {posts} and {circle.chat_messages_30d} chat messages "
        "in the past 30 days."
    )
    if circle.feed_posts_30d >= config.ACTIVE_POSTS_30D:
        return f"Active group: {counts}"
    return counts[0].upper() + counts[1:]


def _logistics(circle: Circle) -> str:
    meets = {
        "virtual": "Meets online",
        "hybrid": "Meets online and in person",
        "in_person": "Meets in person, so check that it's near you",
    }[circle.format]
    joining = "open to join" if circle.join_policy == "open" else "joining needs a leader's approval"
    sentence = f"{meets}; {joining}."
    left = spots_left(circle)
    if left is not None and left <= config.SPOTS_LEFT_NOTICE:
        sentence += f" {left} {'spot' if left == 1 else 'spots'} left."
    return sentence


def explanation(scored: Scored, labels: dict[str, str], personalized: bool) -> str:
    parts = [_why_it_fits(scored, labels, personalized)]
    if scored.covered_by and any(kind == "topic" for _, kind in scored.matches):
        parts.append(f"Adds a new group alongside {scored.covered_by}.")
    parts.append(_activity(scored.circle))
    parts.append(_logistics(scored.circle))
    return " ".join(parts)
