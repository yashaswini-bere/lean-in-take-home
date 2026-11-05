# Lean In Circle Recommendations

An API that returns a ranked list of Circles for a member, with a short explanation of why each one was recommended.

- [Technical design doc](docs/TECHNICAL_DESIGN.md)
- [Database schema and rationale](docs/SCHEMA.md)

## Setup
Requires Python 3.11 or newer (tested on 3.13). The database builds itself from `seed/data` on first start.

**macOS or Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Windows (PowerShell)**
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open <http://127.0.0.1:8000/docs> for interactive API docs, or call it directly:

```bash
curl "http://127.0.0.1:8000/users/23/recommendations"
```

Run the tests with `pytest`. To rebuild the database, run `python -m app.seed`.

## API
`GET /users/{user_id}/recommendations`

| Parameter | Default | Meaning |
|---|---|---|
| `limit` | 5 | Number of recommendations, 1 to 20 |
| `debug` | false | Adds score breakdowns and every excluded Circle with its reasons |

Unknown users return `404`. Example for member 23, shortened to one result:

```json
{
  "user_id": 23,
  "personalization": "interests",
  "data_as_of": "2026-09-21T00:00:00Z",
  "recommendations": [
    {
      "rank": 1,
      "circle": {
        "id": 22,
        "name": "Level Up Collective",
        "format": "hybrid",
        "join_policy": "request",
        "slug": "level-up-collective",
        "description": "A supportive circle for women focused on getting promoted.",
        "topic": "getting-promoted",
        "topic_label": "Getting promoted",
        "cover_image_url": "https://images.example.org/circles/level-up-collective.jpg",
        "member_count": 14,
        "spots_left": 6
      },
      "explanation": "Focuses on getting promoted, one of your interests. Active group: 8 posts and 144 chat messages in the past 30 days. Meets online and in person; joining needs a leader's approval.",
      "match_type": "interest",
      "matched_topics": ["getting-promoted"],
      "similar_circles": []
    }
  ]
}
```

## The planted scenarios
Add `?debug=true` to any of these to see why Circles were left out.

| Scenario | Member | Result |
|---|---|---|
| Obvious matches | 7 | #6 Speak Up Circle and #5 Women Who Lead take the top two places |
| Duplicates | 15 | One Negotiation Circle in the list (#11); #10 and #12 appear as `similar_circles` |
| Full and inactive | 23 | #22 Level Up Collective ranks first; #20 (full) and #21 (inactive) are excluded |
| Cold start | 42 | Five open, active Circles on different topics, none in person, with wording that doesn't claim to know her |

Beyond these, the test suite checks every rule against all 100 members. Two dataset details also needed handling: #30 Early Career Collective is very active but unlisted, and the data ends in September 2026, so recency is measured from the snapshot rather than today's date.

## Project layout
```
app/
  main.py         API routes and response models
  ranker.py       Filter, score and diversify
  interests.py    Stated and profile-based interests
  explain.py      Member-facing explanations
  config.py       Every weight and threshold
  repository.py   SQL queries
  schema.sql      Database schema
  seed.py         Loads the JSON dataset
seed/             Provided dataset and generator
tests/            Scenario, all-member, rule and API tests
docs/             Design doc and schema rationale
```

## How AI was used
This project was built with Claude as a coding partner. Claude profiled the dataset and drafted the code, tests and docs. Reading the actual output, rather than relying only on passing tests, changed the design several times:

- An early version recommended Working Mothers United to a member who had never mentioned motherhood, because of one loose tag. Life-circumstance Circles now need a direct match.
- Matching tags against inferred interests produced recommendations that were hard to justify, so that combination was removed.
- Explanations began too long for a member to skim, so they were tightened and a length check was added to the tests.
- Profiling showed membership dates often predate the member's account, so those dates aren't used as a signal.

I ran the project and its tests locally on Windows and checked the results for the planted scenarios.
