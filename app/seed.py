"""Build the SQLite database from the JSON dataset: python -m app.seed"""
import json

from app.db import ROOT, connect, db_path

DATA = ROOT / "seed" / "data"


def _load(name: str) -> list[dict]:
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


def seed() -> None:
    path = db_path()
    path.unlink(missing_ok=True)
    with connect() as db:
        db.executescript((ROOT / "app" / "schema.sql").read_text(encoding="utf-8"))

        db.executemany(
            "INSERT INTO topics VALUES (:id, :slug, :label, :domain)", _load("topics")
        )

        users = _load("users")
        db.executemany(
            """INSERT INTO users VALUES (:id, :first_name, :last_name, :has_photo, :bio,
               :job_title, :company, :industry, :location, :joined_at,
               :profile_completeness)""",
            users,
        )
        db.executemany(
            "INSERT INTO user_topic_interests VALUES (?, ?)",
            [(u["id"], slug) for u in users for slug in u["topic_interests"]],
        )

        circles = _load("circles")
        db.executemany(
            """INSERT INTO circles VALUES (:id, :name, :slug, :description, :topic,
               :cover_image_url, :format, :access, :join_policy, :max_members,
               :member_count, :created_at, :last_activity_at, :feed_posts_30d,
               :chat_messages_30d)""",
            circles,
        )
        # INSERT OR IGNORE because one Circle in the dataset repeats a tag.
        db.executemany(
            "INSERT OR IGNORE INTO circle_tags VALUES (?, ?)",
            [(c["id"], tag) for c in circles for tag in c["tags"]],
        )

        db.executemany(
            "INSERT INTO memberships VALUES (:user_id, :circle_id, :role, :joined_at)",
            _load("memberships"),
        )
        db.executemany(
            """INSERT INTO activity_posts VALUES (:id, :circle_id, :author_user_id, :body,
               :reaction_count, :comment_count, :save_count, :created_at)""",
            _load("activity"),
        )
    print(f"Seeded {path}")


if __name__ == "__main__":
    seed()
