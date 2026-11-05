# Project Specification: Real-Time Intelligence Graph & Adaptive Quiz Platform

An intelligence platform that ingests real-time events from custom-curated and AI-discovered sources across subscribed niches, continuously constructs a dynamic knowledge graph of cross-domain connections, and delivers daily gamified micro-drills to build conversational currency.

---

## 1. End Goals & Core Product Philosophy

Most news aggregators fail because they optimize for **reading volume** rather than **conversational retention and synthesis**. When tracking multiple fast-moving niches, users face two main bottlenecks: noisy feeds and passive reading decay.

This system is built around four concrete end goals:

| End Goal | What It Means for the User | System Success Metric |
| :--- | :--- | :--- |
| **1. Precision Signal Curation** | You control the exact sources per niche (specific X/Twitter accounts, NYT sections, Substack feeds, or strict source whitelists) or let AI auto-discover high-signal feeds. | >90% of ingested events pass the user's relevance threshold with zero off-topic clutter. |
| **2. Live Cross-Niche Synthesis** | As news breaks in Niche A, the AI automatically detects structural, causal, or supply-chain collisions with Niche B and links them on a live visual canvas. | Cross-domain connections surface within <15 seconds of ingestion with verified source citations. |
| **3. Active Recall via Adaptive Quizzes** | Instead of reading walls of text, you play a 3-minute Kahoot-style morning drill calibrated to keep you in a 70–75% accuracy "flow state." | User maintains a 70–75% win rate across niches while leveling up from 1-hop to multi-hop questions. |
| **4. Instant Conversational Currency** | Every quiz answer and graph connection equips you with a sharp, counter-intuitive 1-sentence insight you can bring up immediately in meetings or conversations. | Users complete the daily briefing in under 3 minutes and retain 3+ high-signal talking points. |

---

## 2. User Experience (UX) & Interaction Design

The product experience is structured into three distinct user journeys: **Curation (Setup)**, **The 3-Minute Daily Drill (Active Recall)**, and **The Palantir Graph Workbench (Deep Exploration)**.

### Flow 1: Niche Studio & Granular Source Curation
When creating or editing a subscribed niche (e.g., *"Next-Gen Geothermal"*, *"EU Tech Regulation"*, or *"Synthetic Biology"*), the user configures a **Source Policy**:

1. **Source Filtering Modes**:
   - **Strict Whitelist Mode ("Only Pick From These")**: The AI *only* ingests events from the exact accounts, publications, or URLs specified by the user.
   - **Hybrid Discovery Mode ("My Sources + AI Scout")**: Prioritizes user-pinned sources while allowing the AI to pull corroborating breakthroughs from trusted external feeds.
2. **Multi-Channel Connectors**:
   - **Social & Micro-Feeds**: Specific X/Twitter handles (e.g., `@semiengineering`), Bluesky accounts, or Reddit communities with minimum engagement or semantic relevance filters.
   - **Tier-1 Publications & Sections**: Specific New York Times desks (e.g., NYT DealBook, NYT Climate), Financial Times, Reuters, or industry journals filtered by keyword or author.
   - **Custom RSS, Newsletters & Filings**: Substack feeds, arXiv categories, SEC EDGAR alerts, or custom webhook endpoints.
3. **Natural Language Guardrails**:
   - Users can attach plain-English curation rules to any niche: *"Only pull articles from NYT Technology and @karpathy that discuss hardware compute bottlenecks; ignore consumer chatbot reviews."*

### Flow 2: The 3-Minute Daily Drill (Kahoot Mode)
When the user opens the app each morning, they enter a rapid-fire, gamified briefing:

* **Screen 1: The Timed Prediction Card**:
  - Displays a breaking event from one of the user's pinned sources (e.g., *"NYT reports new maritime insurance restrictions in the Red Sea"*).
  - Poses a timed, high-stakes question connecting it to another subscribed niche: *"Which of your tracked European EV suppliers faces an immediate Q4 component delay as a result?"*
  - Presents 4 plausible options drawn from real entities active in the news that morning.
* **Screen 2: The Reveal & Pocket Talking Point**:
  - Immediately reveals whether the choice was right or a "trap distractor."
  - Highlights a **Conversational One-Liner Card**: A punchy, 1-sentence synthesis explaining the hidden mechanism so the user can bring it up effortlessly in conversation.
  - Displays a mini-snippet of the live graph node connection with a **"Dive into Graph"** button.

### Flow 3: The Palantir-Style Live Graph Workbench
For deeper exploration, the user switches to the full-screen dark-mode canvas:

* **Live Pulsing Nodes**: Nodes are color-coded by niche and sized by source authority and cross-niche centrality. As new articles arrive from X or NYT, nodes animate into place.
* **Typed Causal Edges**: Directed edges carry explicit verbs (`BOTTLENECKS`, `SUPPLIES`, `REGULATES`, `CONTRADICTS`, `ANALOGOUS_TO`).
* **Evidence Drawer**: Clicking any node or edge opens a side drawer showing the exact source tweet or NYT paragraph, the AI's multi-hop reasoning chain, and historical context over the past 30 days.

---

## 3. Technical Architecture: How to Build It

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    1. SOURCE CURATION & INGESTION LAYER                 │
│  [X/Twitter API]   [NYT API / RSS]   [Substack/Web]   [AI Scout Agent]  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│               2. SEMANTIC GATEKEEPER & CANONICAL EXTRACTION             │
│  • Enforces "Whitelist-Only" vs "Hybrid" rules per Niche                │
│  • Evaluates user's natural language inclusion/exclusion filters        │
│  • Extracts canonical Entities, Events, and Mechanisms (Pydantic)       │
└──────────────────┬───────────────────────────────────┬──────────────────┘
                   │                                   │
                   ▼                                   ▼
┌──────────────────────────────────────┐ ┌────────────────────────────────┐
│   3. REAL-TIME GRAPH ENGINE (Neo4j)  │ │   4. ADAPTIVE QUIZ & ELO ENGINE│
│  • Atomic MERGE of Entities & Edges  │ │  • Tracks User Niche Elo Score │
│  • Multi-hop Cross-Niche Linker      │ │  • Selects 1-hop / 2-hop / Trap│
│  • Pushes live diffs via SSE/WS      │ │  • Real-Entity Distractor Gen  │
└──────────────────┬───────────────────┘ └─────────────┬──────────────────┘
                   │                                   │
                   └─────────────────┬─────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   5. INTERACTIVE FRONTEND (Next.js PWA)                 │
│     [Niche Studio UI]     [Kahoot Drill Mode]     [React Flow Canvas]   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Layer 1: Multi-Source Connector & Semantic Gatekeeper
* **Connector Adapters**:
  - **X/Twitter Ingestion**: Uses X API v2 filtered stream or scheduled list polling for user-specified handles, stripping retweets/replies unless threads contain primary links or analysis.
  - **NYT & Publication Ingestion**: Integrates the New York Times Top Stories / Article Search APIs and section-specific RSS feeds, paired with headless readability extraction (`trafilatura`) for full-text parsing.
* **The Gatekeeper Filter (LLM Pre-Pass)**:
  - Before an item enters the graph, a fast model (Gemini 1.5 Flash) evaluates the raw post/article against the user's Niche Policy (e.g., checking Strict Whitelist permissions and natural language prompt rules). Noise is dropped immediately.

### Layer 2: Real-Time Knowledge Graph & Cross-Niche Linker
* **Canonical Entity Resolution**:
  - Generates embeddings (`text-embedding-3-small` or Gemini embeddings) for every extracted entity and checks `pgvector` + Neo4j for existing nodes (merging `@elonmusk`, `Tesla CEO`, and `Elon Musk` into one canonical node).
* **Cross-Niche Synthesis Agent**:
  - When a new event is committed to Niche A, a Cypher query fetches active nodes from the last 14 days in Niches B, C, and D.
  - The reasoning model evaluates top candidate pairs for non-obvious causal or structural links, writing verified edges into Neo4j and broadcasting the update over Server-Sent Events (SSE).

### Layer 3: Adaptive Quiz & Plausible Distractor Engine
* **Elo Calibration Formula**:
  - Each user has an Elo rating $R$ per niche, initialized at 1200. Each generated question is assigned a difficulty rating $Q$ based on hop count and semantic distance:
    - **Tier 1 ($Q = 1000$)**: Direct 1-hop summary from a single pinned source.
    - **Tier 2 ($Q = 1250$)**: 2-hop synthesis connecting a pinned X account in Niche A to an NYT article in Niche B.
    - **Tier 3 ($Q = 1500$)**: Counter-intuitive second-order effect or false-correlation trap.
  - Expected win probability is calculated as $P = \frac{1}{1 + 10^{(Q - R)/400}}$, picking questions where $P \approx 0.72$.
* **Real-World Distractor Enforcement**:
  - Queries Neo4j for 3 sibling nodes in the target niche that were active in the last 48 hours *without* an edge to the source event, guaranteeing high-plausibility distractors.

---

## 4. GitHub Milestones & Implementation Roadmap

### Milestone 1: Niche Studio & Multi-Source Ingestion Connectors
*Duration: Weeks 1–2 | Target Release: v0.1.0-alpha*
* **Epic Objective**: Build the customizable Niche configuration engine supporting X/Twitter handles, NYT sections, RSS feeds, and Strict Whitelist vs. Hybrid filtering rules.
* **Key Deliverables**:
  - Database schema in Supabase for `Niches`, `SourceConnectors`, and `CurationPolicies` (`STRICT_WHITELIST` vs `HYBRID_DISCOVERY`).
  - X/Twitter handle poller, NYT API integration, and generic RSS/Readability scraper.
  - LLM Semantic Gatekeeper that filters incoming items against user natural-language criteria.
  - Canonical entity extraction and deduplication pipeline.

### Milestone 2: Real-Time Graph Engine & Cross-Niche Synthesizer
*Duration: Weeks 3–4 | Target Release: v0.2.0-alpha*
* **Epic Objective**: Deploy Neo4j graph ontology, cross-domain relationship inference, and real-time SSE streaming.
* **Key Deliverables**:
  - Neo4j constraints and Cypher upsert procedures for `Entity`, `Event`, `Source`, and `Niche` nodes.
  - Cross-niche synthesis agent that evaluates incoming events against adjacent niches and writes typed causal edges.
  - FastAPI Server-Sent Events (SSE) broadcaster pushing live graph mutations to the frontend.

### Milestone 3: Adaptive Quiz Engine & Talking Point Synthesizer
*Duration: Weeks 5–6 | Target Release: v0.3.0-beta*
* **Epic Objective**: Implement the Elo-calibrated Kahoot quiz generator, real-entity distractor selector, and conversational one-liner generator.
* **Key Deliverables**:
  - Per-niche Elo rating calculator targeting a 70–75% accuracy zone.
  - Graph-backed distractor query pulling real concurrent entities from Neo4j.
  - Multi-tier question generator (1-hop, 2-hop cross-niche, and counter-intuitive traps) with 1-sentence conversational takeaways.

### Milestone 4: Palantir Graph Workbench & Kahoot Drill UI
*Duration: Weeks 7–8 | Target Release: v0.4.0-beta*
* **Epic Objective**: Build the interactive Next.js frontend uniting the Niche Studio, 3-minute Quiz Drill, and live React Flow graph canvas.
* **Key Deliverables**:
  - Niche Studio UI for toggling Strict/Hybrid modes and pasting X handles, NYT sections, and prompt rules.
  - Timed Kahoot-style quiz interface with streak counters, animated reveals, and talking-point bookmarking.
  - Dark-mode React Flow / Cytoscape canvas with live SSE node pulsing, source badges (X, NYT, RSS), and evidence side-drawer.

### Milestone 5: Mobile PWA, Daily Notifications & v1.0 Launch
*Duration: Weeks 9–10 | Target Release: v1.0.0*
* **Epic Objective**: Package the platform as an installable mobile PWA with morning briefing push notifications and retention analytics.
* **Key Deliverables**:
  - PWA manifest, service workers, and push notifications when a high-confidence cross-niche link is discovered.
  - Saved "Pocket Deck" of bookmarked conversational talking points for quick review before meetings or social events.
  - Automated CI/CD deployment pipeline.
