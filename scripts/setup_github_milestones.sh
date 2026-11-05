#!/usr/bin/env bash
set -e

REPO="${1:-ruiyangji/infograph-and-quizzes}"

echo "Creating Milestones on $REPO via GitHub REST API..."

gh api "repos/$REPO/milestones" -f title="Milestone 1: Ingestion Pipeline & Canonical Entity Extraction" \
  -f description="Establish real-time data ingestion across core niches with structured entity normalization." \
  -f due_on="$(date -v+14d -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -d "+14 days" -u +"%Y-%m-%dT%H:%M:%SZ")" >/dev/null

gh api "repos/$REPO/milestones" -f title="Milestone 2: Real-Time Graph Ingestion & Streaming Backend" \
  -f description="Deploy graph database infrastructure, cross-niche inference agent, and real-time streaming gateway." \
  -f due_on="$(date -v+28d -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -d "+28 days" -u +"%Y-%m-%dT%H:%M:%SZ")" >/dev/null

gh api "repos/$REPO/milestones" -f title="Milestone 3: Adaptive Quiz Engine & Distractor Generator" \
  -f description="Build the Kahoot-style quiz generation pipeline with dynamic difficulty scaling." \
  -f due_on="$(date -v+42d -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -d "+42 days" -u +"%Y-%m-%dT%H:%M:%SZ")" >/dev/null

gh api "repos/$REPO/milestones" -f title="Milestone 4: Interactive Graph Canvas & Palantir UI" \
  -f description="Build the interactive frontend workbench with graph visualization and timeline controls." \
  -f due_on="$(date -v+56d -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -d "+56 days" -u +"%Y-%m-%dT%H:%M:%SZ")" >/dev/null

gh api "repos/$REPO/milestones" -f title="Milestone 5: End-to-End PWA Polish, Analytics & Beta Launch" \
  -f description="Unify the daily 3-minute loop, deploy mobile PWA, and release closed beta." \
  -f due_on="$(date -v+70d -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -d "+70 days" -u +"%Y-%m-%dT%H:%M:%SZ")" >/dev/null

echo "Creating Initial Backlog Issues..."

gh issue create --repo "$REPO" --milestone "Milestone 1: Ingestion Pipeline & Canonical Entity Extraction" \
  --title "feat(ingest): set up RSS/webhook ingestion daemon" \
  --body "Implement a FastAPI worker service that periodically fetches articles from RSS feeds and incoming webhooks."

gh issue create --repo "$REPO" --milestone "Milestone 1: Ingestion Pipeline & Canonical Entity Extraction" \
  --title "feat(nlp): structured entity extraction and canonicalization" \
  --body "Build extraction prompt that outputs structured Pydantic models with entity names, domains, and event descriptions."

gh issue create --repo "$REPO" --milestone "Milestone 2: Real-Time Graph Ingestion & Streaming Backend" \
  --title "feat(graph): Neo4j schema definition and atomic upsert operations" \
  --body "Configure Neo4j instance, define node uniqueness constraints, and write Cypher queries for edge insertion."

gh issue create --repo "$REPO" --milestone "Milestone 3: Adaptive Quiz Engine & Distractor Generator" \
  --title "feat(engine): adaptive Elo rating and distractor generation" \
  --body "Create the daily quiz generation agent with distractor validation and user rating updates."

gh issue create --repo "$REPO" --milestone "Milestone 4: Interactive Graph Canvas & Palantir UI" \
  --title "feat(ui): interactive graph canvas with live SSE updates" \
  --body "Build the visual workbench allowing users to explore nodes, view relationship metadata, and watch live updates."

echo "All 5 milestones and 5 backlog issues created on https://github.com/$REPO/milestones"
