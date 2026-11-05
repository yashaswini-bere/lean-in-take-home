"""Work out what a member cares about, and keep track of how we know."""
from dataclasses import dataclass

from app.repository import Member


@dataclass(frozen=True)
class Interest:
    topic: str
    source: str  # "stated" or "profile"
    because: str | None = None  # finishes a sentence for a profile-based match


# Explicit phrases rather than fuzzy matching, so that every inference can be
# read here and repeated back to the member accurately.
#
# Nothing here infers motherhood, identity or any other personal circumstance a
# member has not put in those words.
BIO_RULES: list[tuple[str, tuple[str, ...], str]] = [
    ("career break", ("career-breaks",), "your profile mentions returning from a career break"),
    ("first-time manager", ("managing-a-team",), "your profile mentions you're a first-time manager"),
    ("leadership toolkit", ("leadership-skills",), "your profile mentions building your leadership toolkit"),
    ("leadership role", ("leadership-skills",), "your profile mentions a move into leadership"),
    ("mentoring", ("sponsorship-mentorship",), "your profile mentions mentoring"),
    ("pay equity", ("negotiation",), "your profile mentions pay equity"),
    ("promotion paths", ("getting-promoted",), "your profile mentions promotion paths"),
    ("next level", ("getting-promoted",), "your profile mentions reaching the next level"),
    ("comp conversation", ("negotiation",), "your profile mentions a compensation conversation"),
    ("career changer", ("networking",), "your profile mentions a career change"),
]

# Only titles that clearly manage people. "Product Manager" and "Community
# Manager" are left out on purpose.
PEOPLE_MANAGER_TITLES = {
    "Engineering Manager",
    "Sales Manager",
    "Finance Manager",
    "Operations Manager",
    "Nonprofit Director",
}


def member_interests(member: Member) -> dict[str, Interest]:
    interests = {t: Interest(t, "stated") for t in member.stated_topics}

    bio = (member.bio or "").lower()
    for phrase, topics, because in BIO_RULES:
        if phrase in bio:
            for topic in topics:
                interests.setdefault(topic, Interest(topic, "profile", because))

    if member.job_title in PEOPLE_MANAGER_TITLES:
        interests.setdefault(
            "managing-a-team",
            Interest(
                "managing-a-team",
                "profile",
                f"your title is {member.job_title}",
            ),
        )
    return interests
