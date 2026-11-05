# NexusPulse: Real-Time Cross-Niche Intelligence Graph & Adaptive Quiz Platform

NexusPulse ingests breaking events from your pinned **X (Twitter) handles**, **New York Times sections**, and **custom RSS/Substack feeds**, connects non-obvious dots across your subscribed niches on a live **Palantir-style Knowledge Graph**, and drills you via **Kahoot-style adaptive quizzes** calibrated to keep your accuracy in the 70–75% flow zone.

## Commit-by-Commit Milestone Implementation

| Commit | Milestone | Module & Scope |
| :--- | :--- | :--- |
| `Commit 1` | **Architecture & Research** | `docs/RESEARCH_AND_ARCHITECTURE.md`, `docs/SCOPE_AND_MILESTONES.md` |
| `Commit 2` | **Milestone 1 (Part A)** | `src/models/schemas.py`, `src/ingestion/connectors.py` (X API v2, NYT Top Stories & Article Search APIs, RSS) |
| `Commit 3` | **Milestone 1 (Part B)** | `src/ingestion/gatekeeper.py` (`STRICT_WHITELIST` vs `HYBRID_DISCOVERY` Semantic Gatekeeper & Entity Resolver) |
| `Commit 4` | **Milestone 2** | `src/graph/engine.py` (Neo4j Cypher `UNWIND MERGE` engine, cross-niche causal linker, live SSE broadcaster) |
| `Commit 5` | **Milestone 3** | `src/quiz/elo_engine.py`, `tests/test_pipeline.py` (Multivariate Elo with 0.25 guessing floor & real-entity distractors) |
| `Commit 6` | **Milestone 4 (Part A)** | `src/api/server.py` (FastAPI REST & Server-Sent Events streaming server) |
| `Commit 7` | **Milestone 4 (Part B)** | `src/ui/index.html` (Interactive Palantir Graph Canvas, Timed Kahoot Drill & Niche Studio UI) |
| `Commit 8` | **Milestone 5** | `src/ui/manifest.json`, `scripts/setup_github_milestones.sh`, `README.md` (PWA config & GitHub sync CLI) |

## Quickstart

### 1. Run Unit Tests
```bash
PYTHONPATH=. python3 -m unittest discover -s tests -p "test_*.py" -v
```

### 2. Launch the FastAPI Streaming Server
```bash
uvicorn src.api.server:app --reload --port 8000
```

### 3. Push Commit History & Milestones to Your GitHub Repository
```bash
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
./scripts/setup_github_milestones.sh <your-username>/<your-repo>
```
