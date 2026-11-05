from typing import Dict, List, Optional, Tuple
import math
import re

from src.models.schemas import (
    CanonicalEntity,
    CurationMode,
    ExtractedEvent,
    NicheSubscription,
    RawIngestedItem,
)


class SemanticGatekeeper:
    '''
    Enforces user-defined Niche Curation Policies:
    1. STRICT_WHITELIST: Admits ONLY items matching pinned source identifiers.
    2. HYBRID_DISCOVERY: Admits pinned sources + AI Scout items that satisfy
       inclusion/exclusion keyword and semantic guardrails.
    '''

    def evaluate(self, item: RawIngestedItem, niche: NicheSubscription) -> Tuple[bool, str]:
        pinned_ids = {s.identifier.lower() for s in niche.pinned_sources}
        item_source = item.source_identifier.lower()
        is_pinned = item_source in pinned_ids

        if niche.curation_mode == CurationMode.STRICT_WHITELIST and not is_pinned:
            return (
                False,
                f"Rejected by STRICT_WHITELIST: '{item.source_identifier}' is not in pinned sources {sorted(pinned_ids)}",
            )

        combined_text = f"{item.title} {item.content}".lower()

        # Check explicit exclusion rules first
        for excl in niche.exclusion_keywords:
            if excl.lower() in combined_text:
                return False, f"Rejected by exclusion keyword: '{excl}'"

        # If inclusion keywords are configured, require at least one match (unless pinned with no inclusion filter)
        if niche.inclusion_keywords:
            matched_inc = [kw for kw in niche.inclusion_keywords if kw.lower() in combined_text]
            if not matched_inc and not is_pinned:
                return False, "Rejected: Hybrid discovery item did not match any inclusion keywords"
            if not matched_inc and is_pinned and len(niche.inclusion_keywords) > 0:
                return False, "Rejected: Pinned source item did not match niche topic filter"

        return True, "Accepted by Niche Semantic Gatekeeper"


class CanonicalEntityResolver:
    '''
    Resolves surface entity mentions (aliases, handles, tickers, abbreviations)
    into unique canonical Entity nodes using alias lookup + deterministic trigram embeddings.
    Ref: https://neo4j.com/blog/developer/entity-resolved-knowledge-graphs/
    '''

    DEFAULT_ALIAS_MAP: Dict[str, Tuple[str, str, str]] = {
        "tsmc": ("ent_tsmc", "TSMC", "ORGANIZATION"),
        "taiwan semiconductor": ("ent_tsmc", "TSMC", "ORGANIZATION"),
        "$tsm": ("ent_tsmc", "TSMC", "ORGANIZATION"),
        "asml": ("ent_asml", "ASML Holding", "ORGANIZATION"),
        "nvidia": ("ent_nvidia", "NVIDIA", "ORGANIZATION"),
        "$nvda": ("ent_nvidia", "NVIDIA", "ORGANIZATION"),
        "openai": ("ent_openai", "OpenAI", "ORGANIZATION"),
        "@openai": ("ent_openai", "OpenAI", "ORGANIZATION"),
        "eu ai act": ("ent_eu_ai_act", "EU AI Act", "POLICY"),
        "cobalt": ("ent_cobalt", "Refined Cobalt Supply", "COMMODITY"),
        "gallium": ("ent_gallium", "Gallium & Germanium Export Controls", "POLICY"),
        "crispr": ("ent_crispr", "CRISPR Prime Editing", "TECHNOLOGY"),
        "solid-state battery": ("ent_ssb", "Solid-State Battery Cells", "TECHNOLOGY"),
        "hbm3e": ("ent_hbm3e", "HBM3e High-Bandwidth Memory", "TECHNOLOGY"),
        "grid transformer": ("ent_grid_tx", "High-Voltage Grid Transformers", "TECHNOLOGY"),
    }

    def __init__(self, similarity_threshold: float = 0.82):
        self.similarity_threshold = similarity_threshold
        self.registry: Dict[str, CanonicalEntity] = {}
        self.alias_index: Dict[str, str] = {}
        for alias, (uid, name, etype) in self.DEFAULT_ALIAS_MAP.items():
            self.alias_index[alias] = uid
            if uid not in self.registry:
                self.registry[uid] = CanonicalEntity(
                    uid=uid,
                    canonical_name=name,
                    entity_type=etype,
                    niche_id="global",
                    aliases=[alias],
                    embedding=self.compute_trigram_embedding(name),
                )
            else:
                if alias not in self.registry[uid].aliases:
                    self.registry[uid].aliases.append(alias)

    @staticmethod
    def compute_trigram_embedding(text: str, dim: int = 32) -> List[float]:
        clean = re.sub(r"[^a-z0-9]", "", text.lower())
        vec = [0.0] * dim
        if not clean:
            return vec
        padded = f"  {clean}  "
        for i in range(len(padded) - 2):
            trigram = padded[i : i + 3]
            idx = hash(trigram) % dim
            vec[idx] += 1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [round(x / norm, 4) for x in vec]

    @staticmethod
    def cosine_similarity(a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a)) or 1.0
        nb = math.sqrt(sum(y * y for y in b)) or 1.0
        return dot / (na * nb)

    def resolve(self, raw_name: str, entity_type: str, niche_id: str) -> CanonicalEntity:
        norm = raw_name.strip().lower()
        if norm in self.alias_index:
            uid = self.alias_index[norm]
            ent = self.registry[uid]
            if raw_name not in ent.aliases:
                ent.aliases.append(raw_name)
            return ent

        cand_emb = self.compute_trigram_embedding(raw_name)
        best_uid: Optional[str] = None
        best_score = 0.0
        for uid, existing in self.registry.items():
            score = self.cosine_similarity(cand_emb, existing.embedding)
            if score > best_score:
                best_score = score
                best_uid = uid

        if best_uid and best_score >= self.similarity_threshold:
            ent = self.registry[best_uid]
            self.alias_index[norm] = best_uid
            if raw_name not in ent.aliases:
                ent.aliases.append(raw_name)
            return ent

        slug = re.sub(r"[^a-z0-9]+", "_", norm).strip("_")
        new_uid = f"ent_{slug}"
        new_ent = CanonicalEntity(
            uid=new_uid,
            canonical_name=raw_name.strip(),
            entity_type=entity_type,
            niche_id=niche_id,
            aliases=[raw_name.strip()],
            embedding=cand_emb,
        )
        self.registry[new_uid] = new_ent
        self.alias_index[norm] = new_uid
        return new_ent
