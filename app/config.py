"""Every ranking number lives here so it can be read, questioned and tuned."""

# Topic-match strength. A Circle's main topic counts for more than its tags,
# because tags are free-form and the data shows they can be loosely related.
# Tags are not matched against inferred interests: two weak signals in a row
# produced recommendations that were hard to justify.
STATED_TOPIC = 0.85
STATED_TAG = 0.40
PROFILE_TOPIC = 0.55
EXTRA_MATCH_BONUS = 0.15  # for each further interest the same Circle matches

# Final score. Fit leads, because an active Circle on the wrong subject does not
# help a member. Health then chooses among Circles that fit.
WEIGHT_RELEVANCE = 0.60
WEIGHT_HEALTH = 0.25
WEIGHT_FORMAT = 0.10
WEIGHT_JOIN = 0.05

# Circle health. Reference values sit near the top of the observed range.
HEALTH_RECENCY = 0.30
HEALTH_POSTS = 0.30
HEALTH_CHAT = 0.20
HEALTH_ENGAGEMENT = 0.20
RECENCY_HALF_LIFE_DAYS = 14
POSTS_REFERENCE = 20
CHAT_REFERENCE = 200
ENGAGEMENT_REFERENCE = 20  # reactions + comments + saves per recent post

# A Circle is dormant if it has been silent this long, or has almost no
# conversation at all.
INACTIVE_AFTER_DAYS = 60
MIN_CHAT_WITHOUT_POSTS = 5

# Format fit. No Circle has a location, so in-person fit cannot be confirmed.
FORMAT_REMOTE_FRIENDLY = 1.0
FORMAT_IN_PERSON_LOCATION_KNOWN = 0.5
FORMAT_IN_PERSON_NO_LOCATION = 0.2  # location is blank or "Remote"

JOIN_OPEN = 1.0
JOIN_REQUEST = 0.4

# Applied to a Circle whose topic the member already has a Circle for.
ALREADY_COVERED_MULTIPLIER = 0.7

MAX_ALTERNATIVES = 2
DEFAULT_LIMIT = 5
MAX_LIMIT = 20

# Suggestions with no match to the member must clear this health bar.
DISCOVERY_MIN_HEALTH = 0.55

# These speak to a life circumstance. They appear only when the member's own
# interests or profile point to that topic, never because of a passing tag and
# never as a generic suggestion.
ONLY_WHEN_RELEVANT = {"working-motherhood", "career-breaks", "being-the-only-one"}

SPOTS_LEFT_NOTICE = 2
ACTIVE_POSTS_30D = 8
