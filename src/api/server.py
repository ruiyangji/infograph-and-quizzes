import asyncio
from datetime import datetime, timezone
import json
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.graph.engine import RealTimeGraphEngine
from src.ingestion.connectors import NYTimesConnector, RSSFeedConnector, XTwitterConnector
from src.ingestion.gatekeeper import CanonicalEntityResolver, SemanticGatekeeper
from src.models.schemas import (
    CurationMode,
    ExtractedEvent,
    NicheSubscription,
    SourceConnectorConfig,
    SourceType,
)
from src.quiz.elo_engine import AdaptiveEloQuizEngine, UserNicheProfile

app = FastAPI(
    title="NexusPulse Real-Time Intelligence Graph & Adaptive Quiz API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

gatekeeper = SemanticGatekeeper()
resolver = CanonicalEntityResolver()
graph_engine = RealTimeGraphEngine()
elo_engine = AdaptiveEloQuizEngine()
x_connector = XTwitterConnector()
nyt_connector = NYTimesConnector()
rss_connector = RSSFeedConnector()

NICHES: Dict[str, NicheSubscription] = {}
USERS: Dict[str, UserNicheProfile] = {
    "default_user": UserNicheProfile(user_id="default_user")
}
SSE_QUEUES: List[asyncio.Queue] = []


def _on_graph_mutation(msg: Dict[str, Any]) -> None:
    for q in list(SSE_QUEUES):
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            pass


graph_engine.subscribe_sse(_on_graph_mutation)


class CreateNichePayload(BaseModel):
    niche_id: str
    name: str
    description: str
    curation_mode: CurationMode = CurationMode.STRICT_WHITELIST
    pinned_sources: List[Dict[str, str]] = []
    inclusion_keywords: List[str] = []
    exclusion_keywords: List[str] = []
    natural_language_rule: str = ""
    color_hex: str = "#38bdf8"


class AnswerQuizPayload(BaseModel):
    user_id: str = "default_user"
    question_id: str
    selected_option_id: str


@app.get("/api/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok", "service": "NexusPulse Engine v1.0.0"}


@app.get("/api/niches")
def list_niches() -> List[Dict[str, Any]]:
    return [
        {
            "niche_id": n.niche_id,
            "name": n.name,
            "description": n.description,
            "curation_mode": n.curation_mode.value,
            "pinned_sources": [
                {
                    "source_id": s.source_id,
                    "source_type": s.source_type.value,
                    "identifier": s.identifier,
                    "display_name": s.display_name,
                }
                for s in n.pinned_sources
            ],
            "inclusion_keywords": n.inclusion_keywords,
            "exclusion_keywords": n.exclusion_keywords,
            "natural_language_rule": n.natural_language_rule,
            "color_hex": n.color_hex,
        }
        for n in NICHES.values()
    ]


@app.post("/api/niches")
def upsert_niche(payload: CreateNichePayload) -> Dict[str, Any]:
    sources = [
        SourceConnectorConfig(
            source_id=s.get("source_id", f"src_{idx}"),
            source_type=SourceType(s.get("source_type", "X_TWITTER")),
            identifier=s["identifier"],
            display_name=s.get("display_name", s["identifier"]),
        )
        for idx, s in enumerate(payload.pinned_sources)
    ]
    niche = NicheSubscription(
        niche_id=payload.niche_id,
        name=payload.name,
        description=payload.description,
        curation_mode=payload.curation_mode,
        pinned_sources=sources,
        inclusion_keywords=payload.inclusion_keywords,
        exclusion_keywords=payload.exclusion_keywords,
        natural_language_rule=payload.natural_language_rule,
        color_hex=payload.color_hex,
    )
    NICHES[niche.niche_id] = niche
    return {"status": "upserted", "niche_id": niche.niche_id}


@app.get("/api/graph")
def get_graph_state() -> Dict[str, Any]:
    return graph_engine.export_cytoscape_elements()


@app.get("/api/stream")
async def stream_graph_events():
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    SSE_QUEUES.append(q)

    async def event_generator():
        try:
            while True:
                msg = await q.get()
                yield f"data: {json.dumps(msg)}\n\n"
        finally:
            if q in SSE_QUEUES:
                SSE_QUEUES.remove(q)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
