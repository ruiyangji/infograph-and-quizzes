from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
import hashlib

from src.models.schemas import (
    CanonicalEntity,
    CrossNicheEdge,
    ExtractedEvent,
    RelationType,
)


class RealTimeGraphEngine:
    '''
    Palantir-Style Knowledge Graph Engine supporting:
    1. Neo4j Cypher constraint & atomic UNWIND MERGE query generation.
    2. In-memory property graph mirror for instant zero-latency local execution & unit testing.
    3. Cross-niche synthesis linker that discovers multi-hop connections across disparate niches.
    4. Real-time Server-Sent Events (SSE) broadcaster for live UI canvas pulsing.
    '''

    CYPHER_CONSTRAINTS = [
        "CREATE CONSTRAINT entity_uid_key IF NOT EXISTS FOR (e:Entity) REQUIRE e.uid IS NODE KEY",
        "CREATE CONSTRAINT event_id_key IF NOT EXISTS FOR (ev:Event) REQUIRE ev.event_id IS NODE KEY",
        "CREATE CONSTRAINT niche_id_key IF NOT EXISTS FOR (n:Niche) REQUIRE n.niche_id IS NODE KEY",
    ]

    CYPHER_BATCH_UPSERT_ENTITIES = '''
    UNWIND $rows AS row
    MERGE (e:Entity {uid: row.uid})
    ON CREATE SET e.canonical_name = row.canonical_name,
                  e.entity_type = row.entity_type,
                  e.niche_id = row.niche_id,
                  e.aliases = row.aliases,
                  e.created_at = datetime()
    ON MATCH SET  e.aliases = row.aliases,
                  e.updated_at = datetime()
    '''

    CYPHER_UPSERT_CROSS_NICHE_EDGE = '''
    MATCH (src:Entity {uid: $source_uid})
    MATCH (dst:Entity {uid: $target_uid})
    MERGE (src)-[r:CROSS_NICHE_LINK {edge_id: $edge_id}]->(dst)
    SET r.relation_type = $relation_type,
        r.confidence = $confidence,
        r.mechanism_rationale = $mechanism_rationale,
        r.talking_point_one_liner = $talking_point_one_liner,
        r.source_niche_id = $source_niche_id,
        r.target_niche_id = $target_niche_id,
        r.updated_at = datetime()
    RETURN r
    '''

    def __init__(self):
        self.entities: Dict[str, CanonicalEntity] = {}
        self.events: Dict[str, ExtractedEvent] = {}
        self.edges: Dict[str, CrossNicheEdge] = {}
        self.sse_subscribers: List[Callable[[Dict[str, Any]], None]] = []

    def subscribe_sse(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self.sse_subscribers.append(callback)

    def _broadcast(self, event_type: str, payload: Dict[str, Any]) -> None:
        message = {
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": payload,
        }
        for sub in self.sse_subscribers:
            sub(message)

    def ingest_event(self, event: ExtractedEvent) -> List[CrossNicheEdge]:
        self.events[event.event_id] = event
        for ent in event.entities:
            self.entities[ent.uid] = ent
            self._broadcast(
                "node_upserted",
                {
                    "uid": ent.uid,
                    "label": ent.canonical_name,
                    "entity_type": ent.entity_type,
                    "niche_id": event.niche_id,
                    "source_type": event.source_type.value,
                    "source_identifier": event.source_identifier,
                    "source_url": event.source_url,
                },
            )

        # Evaluate cross-niche connections against existing events in OTHER niches
        discovered_edges: List[CrossNicheEdge] = []
        for other_id, other_event in self.events.items():
            if other_event.niche_id == event.niche_id:
                continue
            edge = self._infer_cross_niche_link(event, other_event)
            if edge:
                self.edges[edge.edge_id] = edge
                discovered_edges.append(edge)
                self._broadcast(
                    "edge_linked",
                    {
                        "edge_id": edge.edge_id,
                        "source": edge.source_entity_uid,
                        "target": edge.target_entity_uid,
                        "relation_type": edge.relation_type.value,
                        "confidence": edge.confidence,
                        "talking_point": edge.talking_point_one_liner,
                    },
                )
        return discovered_edges

    def _infer_cross_niche_link(
        self, event_a: ExtractedEvent, event_b: ExtractedEvent
    ) -> Optional[CrossNicheEdge]:
        if not event_a.entities or not event_b.entities:
            return None

        ent_a = event_a.entities[0]
        ent_b = event_b.entities[0]

        text_a = f"{event_a.title} {event_a.mechanism} {event_a.first_order_impact}".lower()
        text_b = f"{event_b.title} {event_b.mechanism} {event_b.first_order_impact}".lower()

        # Structural mechanism matching rules (in production augmented with LLM structured output)
        relation = RelationType.ANALOGOUS_TO
        confidence = 0.76
        if any(w in text_a or w in text_b for w in ["shortage", "delay", "bottleneck", "curb", "tariff", "grid"]):
            relation = RelationType.BOTTLENECKS
            confidence = 0.89
        elif any(w in text_a or w in text_b for w in ["regulation", "act", "compliance", "antitrust", "mandate"]):
            relation = RelationType.REGULATES
            confidence = 0.85
        elif any(w in text_a or w in text_b for w in ["wafer", "packaging", "supplier", "substrate", "cooling"]):
            relation = RelationType.SUPPLIES
            confidence = 0.87

        pair_key = "_".join(sorted([ent_a.uid, ent_b.uid]))
        edge_id = "edge_" + hashlib.md5(pair_key.encode("utf-8")).hexdigest()[:10]

        rationale = (
            f"{event_a.source_identifier} reported '{event_a.title}' ({event_a.mechanism}), "
            f"which directly intersects with {event_b.source_identifier}'s coverage of "
            f"'{event_b.title}' via {relation.value.lower().replace('_', ' ')} dynamics."
        )
        one_liner = (
            f"While everyone is watching {ent_a.canonical_name} in {event_a.niche_id}, "
            f"the second-order squeeze hits {ent_b.canonical_name} ({event_b.niche_id}) "
            f"because {event_a.first_order_impact.lower().rstrip('.')}."
        )

        return CrossNicheEdge(
            edge_id=edge_id,
            source_entity_uid=ent_a.uid,
            target_entity_uid=ent_b.uid,
            source_niche_id=event_a.niche_id,
            target_niche_id=event_b.niche_id,
            relation_type=relation,
            confidence=confidence,
            mechanism_rationale=rationale,
            talking_point_one_liner=one_liner,
            supporting_event_ids=[event_a.event_id, event_b.event_id],
        )

    def get_distractor_entities(
        self,
        target_niche_id: str,
        exclude_uids: List[str],
        count: int = 3,
    ) -> List[CanonicalEntity]:
        '''
        Retrieves real, active entities from the graph in the target niche
        that are NOT linked to the source entity to serve as plausible distractors.
        '''
        excluded = set(exclude_uids)
        candidates = [
            e
            for e in self.entities.values()
            if e.uid not in excluded and (e.niche_id == target_niche_id or e.niche_id == "global")
        ]
        return candidates[:count]

    def export_cytoscape_elements(self) -> Dict[str, List[Dict[str, Any]]]:
        nodes = [
            {
                "data": {
                    "id": e.uid,
                    "label": e.canonical_name,
                    "type": e.entity_type,
                    "niche_id": e.niche_id,
                    "aliases": e.aliases,
                }
            }
            for e in self.entities.values()
        ]
        edges = [
            {
                "data": {
                    "id": ed.edge_id,
                    "source": ed.source_entity_uid,
                    "target": ed.target_entity_uid,
                    "label": ed.relation_type.value,
                    "confidence": ed.confidence,
                    "rationale": ed.mechanism_rationale,
                    "talking_point": ed.talking_point_one_liner,
                }
            }
            for ed in self.edges.values()
        ]
        return {"nodes": nodes, "edges": edges}
