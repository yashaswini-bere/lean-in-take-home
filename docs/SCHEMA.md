# Database Schema

The DDL is in [`app/schema.sql`](../app/schema.sql). SQLite keeps setup to zero, and the design moves to Postgres with few changes.

```
topics ──< user_topic_interests >── users ──< memberships >── circles ──< circle_tags
   └───────────────────────────────────────────────────────────┘  └──< activity_posts
                       circles.topic_slug (nullable)
```

| Table | Purpose | Notes |
|---|---|---|
| `topics` | 22-topic taxonomy | Gives labels for explanations |
| `users` | Member profiles | Nullable fields match the data |
| `user_topic_interests` | Stated interests | Join table, so "who cares about X?" stays queryable |
| `circles` | Circle profile and activity aggregates | `topic_slug` is nullable because two Circles have no topic |
| `circle_tags` | Free-form tags | Deliberately no foreign key to `topics`, because the data dictionary calls tags free-form |
| `memberships` | Who belongs where | Primary key `(user_id, circle_id)` prevents duplicates; a leader is a member with `role = 'leader'` |
| `activity_posts` | Feed posts and engagement | Source of engagement per post |

## Design decisions
- **Derived, not stored.** "Full" and "inactive" are computed when needed. A stored flag could disagree with `member_count` or go stale.
- **Aggregates kept as provided.** `feed_posts_30d` and `chat_messages_30d` stay on `circles` because the source of chat counts is not in the dataset, and raw chat text is excluded for privacy.
- **Constraints guard the enums.** `CHECK` constraints cover format, access, join policy and role, so bad data fails at load time.
- **Timestamps are ISO-8601 text.** They use one fixed format, so text comparison gives correct date order.

## Indexes
| Index | Query it serves |
|---|---|
| `memberships` primary key | The Circles a member already belongs to (leftmost column `user_id`) |
| `idx_memberships_circle_role` | A Circle's members and leaders |
| `idx_activity_circle_created` | Engagement per Circle over a recent window |
| `idx_circles_topic`, `idx_circle_tags_tag` | Finding candidate Circles by topic |

The current service scores all 40 Circles, so the two topic indexes aren't needed yet. They support the topic-based candidate query the design doc proposes at scale, and I kept them to show that path.
