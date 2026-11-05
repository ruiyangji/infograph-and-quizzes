#!/usr/bin/env bash
# setup_github_milestones.sh
# Automated script to create milestones and issues in your GitHub repository using GitHub CLI (gh)
#
# Prerequisite: gh auth login
# Usage: ./setup_github_milestones.sh <repo-name> (or run inside your cloned repository)

set -e

if [ -n "$1" ]; then
  REPO_FLAG="--repo $1"
else
  REPO_FLAG=""
fi

echo "Creating Milestones..."

gh milestone create $REPO_FLAG --title "Milestone 1: Ingestion Pipeline & Canonical Entity Extraction" \
  --description "Establish real-time data ingestion across 5 core niches with structured entity normalization." \
  --due-date "$(date -d "+14 days" +%Y-%m-%d 2>/dev/null || date -v+14d +%Y-%m-%d)"

gh milestone create $REPO_FLAG --title "Milestone 2: Real-Time Graph Ingestion & Streaming Backend" \
  --description "Deploy graph database infrastructure, cross-niche inference agent, and real-time streaming gateway." \
  --due-date "$(date -d "+28 days" +%Y-%m-%d 2>/dev/null || date -v+28d +%Y-%m-%d)"

gh milestone create $REPO_FLAG --title "Milestone 3: Adaptive Quiz Engine & Distractor Generator" \
  --description "Build the Kahoot-style quiz generation pipeline with dynamic difficulty scaling." \
  --due-date "$(date -d "+42 days" +%Y-%m-%d 2>/dev/null || date -v+42d +%Y-%m-%d)"

gh milestone create $REPO_FLAG --title "Milestone 4: Interactive Graph Canvas & Palantir UI" \
  --description "Build the interactive frontend workbench with graph visualization and timeline controls." \
  --due-date "$(date -d "+56 days" +%Y-%m-%d 2>/dev/null || date -v+56d +%Y-%m-%d)"

gh milestone create $REPO_FLAG --title "Milestone 5: End-to-End PWA Polish, Analytics & Beta Launch" \
  --description "Unify the daily 3-minute loop, deploy mobile PWA, and release closed beta." \
  --due-date "$(date -d "+70 days" +%Y-%m-%d 2>/dev/null || date -v+70d +%Y-%m-%d)"

echo "Creating Initial Backlog Issues..."

gh issue create $REPO_FLAG --milestone "Milestone 1: Ingestion Pipeline & Canonical Entity Extraction" \
  --title "feat(ingest): set up RSS/webhook ingestion daemon" \
  --body "Implement a FastAPI worker service that periodically fetches articles from RSS feeds and incoming webhooks, storing raw HTML/text in a staging queue."

gh issue create $REPO_FLAG --milestone "Milestone 1: Ingestion Pipeline & Canonical Entity Extraction" \
  --title "feat(nlp): structured entity extraction and canonicalization" \
  --body "Build extraction prompt that outputs structured Pydantic models with entity names, domains, and event descriptions."

gh issue create $REPO_FLAG --milestone "Milestone 2: Real-Time Graph Ingestion & Streaming Backend" \
  --title "feat(graph): Neo4j schema definition and atomic upsert operations" \
  --body "Configure Neo4j instance, define node uniqueness constraints, and write Cypher queries for edge insertion."

gh issue create $REPO_FLAG --milestone "Milestone 3: Adaptive Quiz Engine & Distractor Generator" \
  --title "feat(engine): adaptive Elo rating and distractor generation" \
  --body "Create the daily quiz generation agent with distractor validation and user rating updates."

gh issue create $REPO_FLAG --milestone "Milestone 4: Interactive Graph Canvas & Palantir UI" \
  --title "feat(ui): interactive React Flow canvas with live SSE updates" \
  --body "Build the visual workbench allowing users to explore nodes, view relationship metadata, and watch live updates."

echo "All milestones and initial backlog issues created successfully!"
