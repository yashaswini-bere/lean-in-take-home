-- Rationale for these tables and indexes: docs/SCHEMA.md
PRAGMA foreign_keys = ON;

CREATE TABLE topics (
    id     INTEGER PRIMARY KEY,
    slug   TEXT NOT NULL UNIQUE,
    label  TEXT NOT NULL,
    domain TEXT NOT NULL
);

CREATE TABLE users (
    id                   INTEGER PRIMARY KEY,
    first_name           TEXT NOT NULL,
    last_name            TEXT NOT NULL,
    has_photo            INTEGER NOT NULL CHECK (has_photo IN (0, 1)),
    bio                  TEXT,
    job_title            TEXT,
    company              TEXT,
    industry             TEXT,
    location             TEXT,
    joined_at            TEXT NOT NULL,
    profile_completeness REAL NOT NULL CHECK (profile_completeness BETWEEN 0 AND 1)
);

CREATE TABLE user_topic_interests (
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic_slug TEXT    NOT NULL REFERENCES topics(slug),
    PRIMARY KEY (user_id, topic_slug)
) WITHOUT ROWID;

CREATE TABLE circles (
    id                INTEGER PRIMARY KEY,
    name              TEXT NOT NULL,
    slug              TEXT NOT NULL UNIQUE,
    description       TEXT,
    topic_slug        TEXT REFERENCES topics(slug),
    cover_image_url   TEXT,
    format            TEXT NOT NULL CHECK (format IN ('in_person', 'virtual', 'hybrid')),
    access            TEXT NOT NULL CHECK (access IN ('public', 'unlisted')),
    join_policy       TEXT NOT NULL CHECK (join_policy IN ('open', 'request')),
    max_members       INTEGER CHECK (max_members IS NULL OR max_members > 0),
    member_count      INTEGER NOT NULL CHECK (member_count >= 0),
    created_at        TEXT NOT NULL,
    last_activity_at  TEXT NOT NULL,
    feed_posts_30d    INTEGER NOT NULL CHECK (feed_posts_30d >= 0),
    chat_messages_30d INTEGER NOT NULL CHECK (chat_messages_30d >= 0)
);

-- Tags are documented as free-form, so they are not foreign keys to topics.
CREATE TABLE circle_tags (
    circle_id INTEGER NOT NULL REFERENCES circles(id) ON DELETE CASCADE,
    tag       TEXT    NOT NULL,
    PRIMARY KEY (circle_id, tag)
) WITHOUT ROWID;

CREATE TABLE memberships (
    user_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    circle_id INTEGER NOT NULL REFERENCES circles(id) ON DELETE CASCADE,
    role      TEXT    NOT NULL CHECK (role IN ('member', 'leader')),
    joined_at TEXT    NOT NULL,
    PRIMARY KEY (user_id, circle_id)
) WITHOUT ROWID;

CREATE TABLE activity_posts (
    id             INTEGER PRIMARY KEY,
    circle_id      INTEGER NOT NULL REFERENCES circles(id) ON DELETE CASCADE,
    author_user_id INTEGER NOT NULL REFERENCES users(id),
    body           TEXT    NOT NULL,
    reaction_count INTEGER NOT NULL CHECK (reaction_count >= 0),
    comment_count  INTEGER NOT NULL CHECK (comment_count >= 0),
    save_count     INTEGER NOT NULL CHECK (save_count >= 0),
    created_at     TEXT    NOT NULL
);

-- "Which Circles match this topic?" (candidate lookup)
CREATE INDEX idx_circles_topic ON circles(topic_slug);
CREATE INDEX idx_circle_tags_tag ON circle_tags(tag, circle_id);
-- The memberships primary key covers "which Circles is this user in?".
-- This one covers "who is in this Circle, and who leads it?".
CREATE INDEX idx_memberships_circle_role ON memberships(circle_id, role);
-- Engagement over a recent window, per Circle.
CREATE INDEX idx_activity_circle_created ON activity_posts(circle_id, created_at);
