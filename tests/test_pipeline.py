from datetime import datetime, timezone
import unittest

from src.graph.engine import RealTimeGraphEngine
from src.ingestion.connectors import NYTimesConnector, XTwitterConnector
from src.ingestion.gatekeeper import CanonicalEntityResolver, SemanticGatekeeper
from src.models.schemas import (
    CurationMode,
    ExtractedEvent,
    NicheSubscription,
    SourceConnectorConfig,
    SourceType,
)
from src.quiz.elo_engine import AdaptiveEloQuizEngine, UserNicheProfile


class TestNexusPulsePipeline(unittest.TestCase):
    def setUp(self):
        self.gatekeeper = SemanticGatekeeper()
        self.resolver = CanonicalEntityResolver()
        self.graph = RealTimeGraphEngine()
        self.elo = AdaptiveEloQuizEngine()

        self.ai_niche = NicheSubscription(
            niche_id="ai_compute",
            name="AI Compute & Semiconductors",
            description="Wafer yields, HBM memory, and AI cluster infrastructure",
            curation_mode=CurationMode.STRICT_WHITELIST,
            pinned_sources=[
                SourceConnectorConfig("src_1", SourceType.X_TWITTER, "@karpathy", "Andrej Karpathy"),
                SourceConnectorConfig("src_2", SourceType.NYT, "nyt:technology", "NYT Technology"),
            ],
            inclusion_keywords=["tsmc", "hbm", "compute", "wafer", "nvidia", "packaging"],
            exclusion_keywords=["crypto", "memecoin"],
        )

        self.energy_niche = NicheSubscription(
            niche_id="energy_grid",
            name="Energy Grid & Industrials",
            description="High-voltage transformers, substation bottlenecks, and municipal power",
            curation_mode=CurationMode.HYBRID_DISCOVERY,
            pinned_sources=[
                SourceConnectorConfig("src_3", SourceType.NYT, "nyt:climate", "NYT Climate & Energy"),
            ],
            inclusion_keywords=["transformer", "grid", "substation", "power", "megawatt"],
            exclusion_keywords=["celebrity"],
        )

    def test_strict_whitelist_vs_hybrid_gatekeeper(self):
        x_conn = XTwitterConnector()
        allowed_tweet = x_conn.normalize_tweet_payload(
            {"id": "1001", "text": "TSMC CoWoS wafer packaging and HBM3e supply remains the primary compute bottleneck."},
            handle="@karpathy",
            niche_id="ai_compute",
        )
        ok, reason = self.gatekeeper.evaluate(allowed_tweet, self.ai_niche)
        self.assertTrue(ok, reason)

        unpinned_tweet = x_conn.normalize_tweet_payload(
            {"id": "1002", "text": "TSMC wafer compute update from an unpinned account."},
            handle="@random_account",
            niche_id="ai_compute",
        )
        ok_unpinned, _ = self.gatekeeper.evaluate(unpinned_tweet, self.ai_niche)
        self.assertFalse(ok_unpinned)

    def test_entity_resolution_merges_aliases(self):
        e1 = self.resolver.resolve("TSMC", "ORGANIZATION", "ai_compute")
        e2 = self.resolver.resolve("Taiwan Semiconductor", "ORGANIZATION", "ai_compute")
        e3 = self.resolver.resolve("$TSM", "ORGANIZATION", "ai_compute")
        self.assertEqual(e1.uid, e2.uid)
        self.assertEqual(e2.uid, e3.uid)
        self.assertEqual(e1.canonical_name, "TSMC")

    def test_realtime_graph_cross_niche_linking_and_elo_quiz(self):
        sse_events = []
        self.graph.subscribe_sse(lambda msg: sse_events.append(msg))

        ent_tsmc = self.resolver.resolve("TSMC", "ORGANIZATION", "ai_compute")
        ent_grid = self.resolver.resolve("Grid Transformer", "TECHNOLOGY", "energy_grid")

        ev1 = ExtractedEvent(
            event_id="ev_ai_1",
            title="Hyperscalers accelerate rack-scale AI cluster deployments",
            summary="Next-gen AI clusters double rack power density.",
            mechanism="Surge in rack-level liquid cooling and power draw requirements",
            first_order_impact="Data center developers face 36-month lead times on high-voltage step-down transformers",
            niche_id="ai_compute",
            source_type=SourceType.X_TWITTER,
            source_identifier="@karpathy",
            source_url="https://x.com/karpathy/status/1001",
            published_at=datetime.now(timezone.utc),
            entities=[ent_tsmc],
        )
        ev2 = ExtractedEvent(
            event_id="ev_energy_1",
            title="Grain-oriented electrical steel shortage hits US utility substations",
            summary="Grid transformer manufacturers report acute bottleneck in core steel.",
            mechanism="Supply chain shortage in grain-oriented electrical steel",
            first_order_impact="Municipal utility interconnect queues stretch past 2028",
            niche_id="energy_grid",
            source_type=SourceType.NYT,
            source_identifier="nyt:climate",
            source_url="https://www.nytimes.com/2026/11/05/climate/grid-transformers.html",
            published_at=datetime.now(timezone.utc),
            entities=[ent_grid],
        )

        self.graph.ingest_event(ev1)
        edges = self.graph.ingest_event(ev2)

        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].relation_type.value, "BOTTLENECKS")
        self.assertGreaterEqual(len(sse_events), 3)  # 2 node upserts + 1 edge linked

        # Generate adaptive quiz calibrated to ~72% target win probability
        user = UserNicheProfile(user_id="usr_1")
        quiz = self.elo.generate_question_from_edge(edges[0], self.graph, user)
        win_prob = self.elo.predict_win_probability(user, quiz.niche_ids, quiz.difficulty_elo)
        self.assertAlmostEqual(win_prob, 0.72, places=2)
        self.assertEqual(len(quiz.options), 4)

        # Verify Elo rating increases on correct answer
        updated = self.elo.update_ratings(user, quiz, is_correct=True)
        self.assertGreater(updated["ai_compute"], 1200.0)
        self.assertGreater(updated["energy_grid"], 1200.0)


if __name__ == "__main__":
    unittest.main()
