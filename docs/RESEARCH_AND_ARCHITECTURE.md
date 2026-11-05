# Technical Research & System Architecture

This document synthesizes the foundational engineering research backing **NexusPulse**—a real-time cross-niche intelligence graph and Kahoot-style adaptive learning platform.

## 1. Multi-Source Ingestion & Granular Curation Research

### 1.1 The New York Times Developer APIs
- **Base REST Endpoint**: `https://api.nytimes.com/svc` authenticated via query string `api-key` ([dltHub NYT Python API Docs](https://dlthub.com/context/source/nytimes-data), [PublicAPIs NYT Guide](https://publicapis.io/new-york-times-api)).
- **Core Resources Used**:
  - **Top Stories API** (`topstories/v2/{section}.json`, data selector: `results`): Used when a user pins specific NYT sections (e.g., `technology`, `business`, `science`, `climate`, `world`) to a subscribed niche.
  - **Article Search API** (`search/v2/articlesearch.json`, data selector: `response.docs`): Supports Lucene-style filter queries (`fq`) for author bylines, news desks, and keyword constraints.
  - **Times Newswire API** (`news/v3/content/{source}/{section}.json`, data selector: `results`): Provides real-time streaming of published NYT articles.

### 1.2 X (Twitter) API v2
- **Timeline & Stream Endpoints**:
  - **User Post Timeline** (`https://api.x.com/2/users/:id/tweets`): Supports stateful polling via `since_id`, granular field selection (`tweet.fields=created_at,public_metrics,entities,referenced_tweets`), and author expansions ([X Developer Platform Migration Guide](https://generaltranslation.mintlify.app/x-api/posts/timelines/migrate/standard-to-twitter-api-v2)).
  - **Filtered Stream** (`https://api.x.com/2/tweets/search/stream`): Enables multi-rule real-time ingestion with zero-downtime rule updates ([Data365 X API v2 Analysis](https://data365.co/blog/twitter-api-v2)).
  - **Rate-Limit Resilience**: Endpoints reset on 15-minute rolling windows ([Sorsa X API Rate Limits](https://api.sorsa.io/blog/twitter-api-rate-limits-2026)); our connector implements token-bucket backoff and `since_id` checkpointing.

### 1.3 User Curation Modes: Strict Whitelist vs. Hybrid Discovery
Each subscribed Niche defines a `CurationPolicy`:
1. `STRICT_WHITELIST`: Only events originating from user-pinned handles (e.g., `@karpathy`, `@semiengineering`), specific NYT sections, or whitelisted RSS feeds are admitted.
2. `HYBRID_DISCOVERY`: Prioritizes pinned sources while permitting the AI Scout to admit high-authority corroborating events that pass the user's natural-language inclusion/exclusion guardrails.

---

## 2. Entity-Resolved Knowledge Graph (ERKG) Architecture

Based on the [Neo4j Entity Resolved Knowledge Graphs Architecture](https://neo4j.com/blog/developer/entity-resolved-knowledge-graphs/) and the [Neo4j LLM Knowledge Graph Builder](https://neo4j.com/labs/genai-ecosystem/llm-graph-builder/):

- **Two-Layer Graph Topology**:
  1. **Provenance Layer (`:Record` / `:Event`)**: Preserves exact source attribution (X Tweet ID, NYT URI, publication timestamp, author, verbatim snippet).
  2. **Semantic Entity Layer (`:Entity` & `:Niche`)**: Canonical real-world actors, technologies, policies, and organizations.
- **Entity Resolution & Deduplication**:
  - Combines alias lookup tables, normalized string tokens, and cosine similarity over vector embeddings to merge surface variations (e.g., `"OpenAI"`, `"OAI"`, `"@OpenAI"`) into a single canonical `:Entity` UID.
- **Cypher Uniqueness & Atomic Batch Upserts**:
  - Enforces node key constraints (`CREATE CONSTRAINT entity_uid_key IF NOT EXISTS FOR (e:Entity) REQUIRE e.uid IS NODE KEY`) and uses atomic `UNWIND $rows AS row MERGE` transactions to prevent duplicate nodes and update edge confidence weights in real time.

---

## 3. Multivariate Elo Rating & Adaptive Quiz Calibration

Grounded in peer-reviewed educational data mining research ([Adaptation of the Multi-Concept Multivariate Elo Rating System, arXiv:2403.07908v1](https://arxiv.org/html/2403.07908v1)):

- **Guessing-Corrected Logistic Probability**:
  For a multiple-choice question $i$ with $n_{\text{opt}} = 4$ options, the baseline random guessing rate is $P(\text{guess}) = 1 / n_{\text{opt}} = 0.25$. The probability that user $u$ with effective skill $\lambda_{ui}$ answers question $i$ of difficulty $\mu_i$ correctly is:
  $$\Pr(a_{ui} = 1 \mid \lambda_{ui}, \mu_i) = \frac{1}{n_{\text{opt}}} + \frac{1 - 1/n_{\text{opt}}}{1 + e^{-(\lambda_{ui} - \mu_i) / s}}$$
  where $s = 400 / \ln(10)$ scales logits to classic Elo points (or unit logit scale when $s=1$).
- **Dynamic Uncertainty Function $U(n)$**:
  To converge rapidly on new niches while preventing wild swings after dozens of drills, static $K$ is replaced by:
  $$U(n) = \max\left(K_{\min}, \frac{a}{1 + b \cdot n}\right)$$
  where $n$ is the user's prior attempt count in that niche, $a = 1.0$ (or $40.0$ on the 1200-Elo scale), $b = 0.15$, and $K_{\min}$ guarantees ongoing adaptation to evolving user mastery.
- **Multi-Niche Skill Decomposition**:
  When a question bridges $\delta$ distinct niches $s_1, \dots, s_\delta$, effective user skill is the mean across those niches:
  $$\lambda_{ui} = \frac{1}{\delta} \sum_{k=1}^{\delta} \theta_{u, s_k}$$
  After each attempt, each involved niche rating $\theta_{u, s_k}$ updates independently based on the surprise residual $(a_{ui} - \Pr(a_{ui}=1))$.
