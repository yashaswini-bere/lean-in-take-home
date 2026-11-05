"""All SQL lives here. Everything else works with plain dataclasses."""
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class Member:
    id: int
    bio: str | None
    job_title: str | None
    location: str | None
    stated_topics: frozenset[str]
    circle_ids: frozenset[int]


@dataclass(frozen=True)
class Circle:
    id: int
    name: str
    slug: str
    description: str | None
    topic: str | None
    tags: frozenset[str]
    cover_image_url: str | None
    format: str
    access: str
    join_policy: str
    max_members: int | None
    member_count: int
    last_activity_at: datetime
    feed_posts_30d: int
    chat_messages_30d: int
    engagement_per_post: float


def _parse(timestamp: str) -> datetime:
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


def _to_stored(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def data_as_of(db: sqlite3.Connection) -> datetime:
    """The newest moment in the data, used as "now" when measuring recency.

    The dataset is a fixed snapshot, so the system clock would make every Circle
    look stale. In production this would be replaced by the current time.
    """
    row = db.execute(
        """SELECT MAX(latest) FROM (
               SELECT MAX(last_activity_at) AS latest FROM circles
               UNION ALL
               SELECT MAX(created_at) FROM activity_posts
           )"""
    ).fetchone()
    return _parse(row[0])


def topic_labels(db: sqlite3.Connection) -> dict[str, str]:
    return {r["slug"]: r["label"] for r in db.execute("SELECT slug, label FROM topics")}


def get_member(db: sqlite3.Connection, user_id: int) -> Member | None:
    row = db.execute(
        "SELECT id, bio, job_title, location FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    if row is None:
        return None
    topics = db.execute(
        "SELECT topic_slug FROM user_topic_interests WHERE user_id = ?", (user_id,)
    )
    circles = db.execute(
        "SELECT circle_id FROM memberships WHERE user_id = ?", (user_id,)
    )
    return Member(
        id=row["id"],
        bio=row["bio"],
        job_title=row["job_title"],
        location=row["location"],
        stated_topics=frozenset(r["topic_slug"] for r in topics),
        circle_ids=frozenset(r["circle_id"] for r in circles),
    )


def get_circles(db: sqlite3.Connection, as_of: datetime) -> list[Circle]:
    window_start = _to_stored(as_of - timedelta(days=30))
    tags: dict[int, set[str]] = {}
    for row in db.execute("SELECT circle_id, tag FROM circle_tags"):
        tags.setdefault(row["circle_id"], set()).add(row["tag"])

    rows = db.execute(
        """SELECT c.*,
                  COALESCE(e.engagement_per_post, 0) AS engagement_per_post
           FROM circles c
           LEFT JOIN (
               SELECT circle_id,
                      AVG(reaction_count + comment_count + save_count)
                          AS engagement_per_post
               FROM activity_posts
               WHERE created_at >= ?
               GROUP BY circle_id
           ) e ON e.circle_id = c.id
           ORDER BY c.id""",
        (window_start,),
    )
    return [
        Circle(
            id=r["id"],
            name=r["name"],
            slug=r["slug"],
            description=r["description"],
            topic=r["topic_slug"],
            tags=frozenset(tags.get(r["id"], set())),
            cover_image_url=r["cover_image_url"],
            format=r["format"],
            access=r["access"],
            join_policy=r["join_policy"],
            max_members=r["max_members"],
            member_count=r["member_count"],
            last_activity_at=_parse(r["last_activity_at"]),
            feed_posts_30d=r["feed_posts_30d"],
            chat_messages_30d=r["chat_messages_30d"],
            engagement_per_post=r["engagement_per_post"],
        )
        for r in rows
    ]
