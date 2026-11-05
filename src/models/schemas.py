from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional


class CurationMode(str, Enum):
    STRICT_WHITELIST = "STRICT_WHITELIST"
    HYBRID_DISCOVERY = "HYBRID_DISCOVERY"


class SourceType(str, Enum):
    X_TWITTER = "X_TWITTER"
    NYT = "NYT"
    RSS_SUBSTACK = "RSS_SUBSTACK"
    AI_SCOUT = "AI_SCOUT"


class RelationType(str, Enum):
    SUPPLIES = "SUPPLIES"
    REGULATES = "REGULATES"
    BOTTLENECKS = "BOTTLENECKS"
    COMPETES_WITH = "COMPETES_WITH"
    ANALOGOUS_TO = "ANALOGOUS_TO"
    AMPLIFIES = "AMPLIFIES"


@dataclass
class SourceConnectorConfig:
    source_id: str
    source_type: SourceType
    identifier: str  # e.g., "@karpathy", "technology" (NYT section), or RSS URL
    display_name: str
    authority_weight: float = 1.0


@dataclass
class NicheSubscription:
    niche_id: str
    name: str
    description: str
    curation_mode: CurationMode
    pinned_sources: List[SourceConnectorConfig] = field(default_factory=list)
    inclusion_keywords: List[str] = field(default_factory=list)
    exclusion_keywords: List[str] = field(default_factory=list)
    natural_language_rule: str = ""
    color_hex: str = "#38bdf8"


@dataclass
class RawIngestedItem:
    external_id: str
    source_type: SourceType
    source_identifier: str
    source_display_name: str
    title: str
    content: str
    url: str
    published_at: datetime
    niche_id: str
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class CanonicalEntity:
    uid: str
    canonical_name: str
    entity_type: str  # ORGANIZATION, TECHNOLOGY, POLICY, COMMODITY, PERSON
    niche_id: str
    aliases: List[str] = field(default_factory=list)
    embedding: List[float] = field(default_factory=list)


@dataclass
class ExtractedEvent:
    event_id: str
    title: str
    summary: str
    mechanism: str
    first_order_impact: str
    niche_id: str
    source_type: SourceType
    source_identifier: str
    source_url: str
    published_at: datetime
    entities: List[CanonicalEntity] = field(default_factory=list)


@dataclass
class CrossNicheEdge:
    edge_id: str
    source_entity_uid: str
    target_entity_uid: str
    source_niche_id: str
    target_niche_id: str
    relation_type: RelationType
    confidence: float
    mechanism_rationale: str
    talking_point_one_liner: str
    supporting_event_ids: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
