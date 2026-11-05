# Technical Design: Recommending Circles

## What I built
`GET /users/{id}/recommendations` (FastAPI, SQLite) returns ranked Circles with member-facing explanations, in three steps:

1. **Filter.** Remove Circles that are joined, unlisted, full, dormant, or have no topic.
2. **Score.** `0.60 relevance + 0.25 health + 0.10 format fit + 0.05 ease of joining`. Fit leads; health chooses among Circles that fit.
3. **Diversify.** One Circle per topic, with up to two others as `similar_circles` so members can still choose a format.

## Signals
| Used | Why |
|---|---|
| Stated interests, Circle topic | Strongest evidence of what a member wants |
| Tags | Weaker: free-form and often loosely related |
| Bio and job title | Fixed phrase rules, quoted back in the explanation |
| Posts, chat, recency, engagement | Together show a living group; log-scaled so volume can't dominate |
| Memberships | Exclude joined Circles; lower topics already covered |

**Left out:** photo and profile completeness (would penalize newcomers), company and industry (often contradict each other), and membership dates (205 of 441 predate the member's account).

## Key tradeoffs
- **Weighted rules, not ML.** There is no outcome data to train on. The weights in `config.py` are judgment calls that need testing against real joins.
- **Template explanations, not an LLM.** Each clause comes from a real ranking signal, so it can't invent a reason, at the cost of less natural wording.
- **Same topic counts as duplicate.** Simple, but it also collapses Circles that differ in audience.
- **No assumptions about personal circumstances.** Motherhood, career-break and "only one" Circles appear only if a member's own interests or profile name that topic. The Latina Coalition and Women of the 405 have no topic, so they belong in search until members can opt in to identity or place.
- **In-person fit is unknown.** Circles have no location, and each in-person Circle's members span 2 to 8 cities, so it can't be inferred. These rank lower and the explanation says to check. A Circle location is my top data request.
- **Snapshot time.** Recency is measured from the newest record, because the system clock would make every Circle look stale.

## Production scale
- **Data:** Postgres, a topic-based candidate query, and health scores precomputed from activity events instead of per request.
- **Serving:** per-member cache, capacity rechecked at read time, and authentication.
- **Fairness:** cap exposure so popular Circles don't absorb every new member. Here, one Circle appears in 59 of 100 lists.
- **Learning:** log impressions, joins and 30-day retention, then A/B test weights. Success is members staying active, not clicks.

## With more time
Collaborative filtering on real join data, embedding-based duplicate detection, and a cold-start onboarding prompt.
