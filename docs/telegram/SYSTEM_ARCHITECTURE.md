# SYSTEM\_ARCHITECTURE.md

# Telegram-First Datafarm Architecture

## Overview

This document outlines the architecture of a high-throughput, near-real-time Telegram-first data ingestion, enrichment, and serving system. The system is designed to scale modularly, support low-latency streaming, and serve both historical and real-time queries. The architecture prioritizes technical clarity and modularity to support future expansion to other sources (RSS, Reddit, X, OSINT listeners).

---

## 1. Sources

* **Telegram (Telethon / Pyrogram)**: Primary high-frequency source. Messages are fetched per channel and published as events.
* **RSS / Other feeds**: Future sources; will be ingested via dedicated producer pipelines.

## 2. Producers

* **Telegram Producer**

  * Converts raw Telegram messages into structured events.
  * Keys messages by `channel_id` for partitioning.
  * Publishes to the broker (`raw.telegram`).
* **RSS Producer (future)**

  * Converts feed items into structured events for the broker.

## 3. Broker / Event Log

* **Topics**

  * `raw.telegram`: unprocessed messages.
  * `norm.telegram`: normalized and deduplicated messages.
  * `enriched.telegram`: messages with embeddings and metadata.
  * `ranked.telegram`: filtered, scored messages for downstream consumption.
  * `dead.letter`: captures failed processing events.
* **Responsibilities**

  * Durable, replayable log for all events.
  * Decouples ingestion from processing.
  * Supports backpressure management.

## 4. Stream Processors

* **Normalizer**

  * Deduplication (hash-based).
  * Canonicalization of fields.
  * Publishes normalized events to `norm.telegram`.
  * Errors routed to `dead.letter`.
* **Enricher**

  * Calls external AI (Gemini) asynchronously.
  * Extracts entities, classifications, embeddings.
  * Publishes enriched messages to `enriched.telegram`.
  * Embeddings also written to vector store (pgvector / Qdrant).
* **Ranker / Filter**

  * Applies scoring, filtering, and routing metadata.
  * Emits to `ranked.telegram` for both sink service and WS subscribers.
  * Errors routed to `dead.letter`.

## 5. Low-Latency State Layer

* **Redis**

  * Rate-limiting per-channel.
  * Tracks per-channel cursors (last processed message IDs).
  * Caches ephemeral features (keywords, partial embeddings).
  * Coordinates in-flight enrichment jobs to prevent duplication.

## 6. Sinks / System of Record

* **PostgreSQL 15**

  * Tables: `telegram_messages`, `telegram_channels`, `news_entries`, `feed_cache`, `tags / article_tags`.
  * Receives idempotent upserts from the DB Sink Service.
  * Serves historical queries via REST API.
* **Vector Store**

  * pgvector (inside Postgres) or Qdrant.
  * Stores embeddings for semantic search and clustering.

## 7. API / Realtime Layer

* **FastAPI REST**

  * Historical reads, search, analytics.
  * Reads from Postgres and vector store.
* **WebSocket Gateway**

  * Subscribes to `ranked.telegram` topic.
  * Pushes near-real-time updates to connected clients.

## 8. Frontend

* **Next.js UI**

  * Consumes REST and WS endpoints.
  * Provides dashboards for live feeds, geolocation mapping, timeline analysis, and topic clustering.

## 9. Observability

* **OpenTelemetry**

  * Traces and metrics for all producers, processors, sinks, and API endpoints.
* **Prometheus + Grafana**

  * Metrics visualization and alerting.

## 10. Metadata Enrichment

* Named Entities: persons, organizations, locations, equipment.
* Event Type: conflict, election, protest, policy, trade, disaster.
* Geolocation: normalized coordinates from text/media.
* Source Credibility: per-channel trust scores.
* Sentiment / Stance Analysis.
* Virality / Urgency Scoring.
* Language Normalization & Translation.
* Temporal normalization (timestamps).
* Clustering for narrative tracking.

## 11. Hosting Strategy (Budget / Student-Friendly)

* **Broker**: Redpanda Cloud free tier (managed Kafka-compatible broker).
* **Postgres / pgvector**: Neon.tech free tier or Supabase.
* **Redis**: Upstash free tier.
* **Vector Search**: pgvector initially; Qdrant Cloud if scaling >1M embeddings.
* **Model inference**: external AI (Gemini / OpenAI).
* **API / Frontend**: Railway free tier or Vercel free tier for Next.js.
* **Observability**: Grafana Cloud free tier.

## 12. Scaling Notes

* The system is **modular**, allowing independent scaling of processors.
* Backpressure handled by broker topics.
* Autoscaling of workers requires orchestration (Kubernetes, Nomad, or serverless triggers).
* Redis and Postgres remain the hot-path state/cache and persistent store respectively.
* Vector store must scale horizontally if embeddings exceed millions.

## 13. Data Flow Summary

```
Sources (TG / RSS) → Producer → raw.telegram → Normalizer → norm.telegram → Enricher → enriched.telegram → Ranker/Filter → ranked.telegram → DB Sink Service → PostgreSQL + Vector Store
ranked.telegram → WS Gateway → Next.js Frontend
API REST → PostgreSQL + Vector Store for historical queries
Redis → ephemeral state, rate-limits, in-flight job coordination
Dead-letter queue → error handling
Observability → OpenTelemetry → Prometheus/Grafana
```

## 14. Future Adaptability

* New sources (X, Reddit, OSINT robots) can be added as independent producers feeding raw event topics.
* Additional stream processors (summarizers, language-specific enrichers) can be inserted at appropriate stages.
* Vector index supports RAG-style LLM queries without modifying the core ingestion flow.

---

**End of SYSTEM\_ARCHITECTURE.md**
