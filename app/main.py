from contextlib import asynccontextmanager
from datetime import datetime
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from app import config, repository
from app.db import connect, db_path
from app.explain import explanation, spots_left
from app.ranker import recommend
from app.seed import seed


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not db_path().exists():
        seed()
    yield


app = FastAPI(
    title="Lean In Circle Recommendations",
    description="Ranked Circles for a member, each with a member-facing explanation.",
    version="1.0.0",
    lifespan=lifespan,
)


class CircleSummary(BaseModel):
    id: int
    name: str
    format: Literal["in_person", "virtual", "hybrid"]
    join_policy: Literal["open", "request"]


class CircleDetail(CircleSummary):
    slug: str
    description: str | None
    topic: str
    topic_label: str
    cover_image_url: str | None
    member_count: int
    spots_left: int | None


class ScoreBreakdown(BaseModel):
    score: float
    relevance: float
    health: float
    format_fit: float
    join_ease: float
    already_covered_by: str | None


class Recommendation(BaseModel):
    rank: int
    circle: CircleDetail
    explanation: str
    match_type: Literal["interest", "profile", "discovery"]
    matched_topics: list[str]
    similar_circles: list[CircleSummary]
    debug: ScoreBreakdown | None = None


class ExcludedCircle(BaseModel):
    id: int
    name: str
    reasons: list[str]


class RecommendationResponse(BaseModel):
    user_id: int
    personalization: Literal["interests", "profile", "none"]
    next_step: str | None
    data_as_of: datetime
    recommendations: list[Recommendation]
    excluded: list[ExcludedCircle] | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/users/{user_id}/recommendations", response_model_exclude_none=True)
def get_recommendations(
    user_id: int,
    limit: int = Query(config.DEFAULT_LIMIT, ge=1, le=config.MAX_LIMIT),
    debug: bool = Query(False, description="Include scores and excluded Circles."),
) -> RecommendationResponse:
    with connect() as db:
        member = repository.get_member(db, user_id)
        if member is None:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        as_of = repository.data_as_of(db)
        labels = repository.topic_labels(db)
        result = recommend(member, repository.get_circles(db, as_of), as_of, limit)

    sources = {i.source for i in result.interests.values()}
    personalization = (
        "interests" if "stated" in sources else "profile" if sources else "none"
    )

    items = []
    for rank, pick in enumerate(result.picks, start=1):
        circle = pick.circle
        match_sources = {i.source for i, _ in pick.matches}
        items.append(
            Recommendation(
                rank=rank,
                circle=CircleDetail(
                    id=circle.id,
                    name=circle.name,
                    slug=circle.slug,
                    description=circle.description,
                    topic=circle.topic,
                    topic_label=labels[circle.topic],
                    cover_image_url=circle.cover_image_url,
                    format=circle.format,
                    join_policy=circle.join_policy,
                    member_count=circle.member_count,
                    spots_left=spots_left(circle),
                ),
                explanation=explanation(pick, labels, personalization != "none"),
                match_type=(
                    "interest"
                    if "stated" in match_sources
                    else "profile"
                    if match_sources
                    else "discovery"
                ),
                matched_topics=[i.topic for i, _ in pick.matches],
                similar_circles=[
                    CircleSummary(
                        id=a.id, name=a.name, format=a.format, join_policy=a.join_policy
                    )
                    for a in pick.alternatives
                ],
                debug=ScoreBreakdown(
                    score=round(pick.score, 3),
                    relevance=round(pick.relevance, 3),
                    health=round(pick.health, 3),
                    format_fit=pick.format_fit,
                    join_ease=pick.join_ease,
                    already_covered_by=pick.covered_by,
                )
                if debug
                else None,
            )
        )

    return RecommendationResponse(
        user_id=user_id,
        personalization=personalization,
        next_step=(
            "Add a few topics you care about to get recommendations made for you."
            if "stated" not in sources
            else None
        ),
        data_as_of=as_of,
        recommendations=items,
        excluded=[
            ExcludedCircle(id=c.id, name=c.name, reasons=reasons)
            for c, reasons in result.excluded
        ]
        if debug
        else None,
    )
