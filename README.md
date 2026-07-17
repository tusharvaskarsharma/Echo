# Echo — AI-Powered Living Legacy Platform

> *An AI-powered living legacy system that preserves how a person thinks, speaks, and loves — so the people who matter most never lose them.*

**Hackathon:** OpenAI Hackathon (Devpost)
**Stack:** Gemini Live Audio · Groq persona generation · Next.js 14 · FastAPI · Supabase · Pinecone · Redis · librosa · CREPE Pitch Tracking · ElevenLabs Voice Clone · Acoustic Fingerprint Engine

---

## Table of Contents

1. [Executive Summary & The Hook](#1-executive-summary--the-hook)
   - [Project Name & Core Value Proposition](#11-project-name--core-value-proposition)
   - [Market Validity: Target User Personas](#12-market-validity-target-user-personas)
   - [Market Statistics & Why Now](#13-market-statistics--why-now)
2. [Comprehensive System Architecture](#2-comprehensive-system-architecture)
   - [Architecture Overview](#21-architecture-overview)
   - [Exact Tech Stack](#22-exact-tech-stack)
3. [Architectural Blueprint & File Structure](#3-architectural-blueprint--file-structure)
   - [Production-Grade Repository Structure](#31-production-grade-repository-structure)
   - [Key File Explanations](#32-key-file-explanations)
4. [Step-by-Step Building Process & Data Flow](#4-step-by-step-building-process--data-flow)
   - [Phase 1 — Data Collection & Ingestion: The Interview Session Pipeline](#phase-1--data-collection--ingestion-the-interview-session-pipeline)
   - [Phase 2 — Backend & AI Logic: The Family Conversation Pipeline](#phase-2--backend--ai-logic-the-family-conversation-pipeline)
   - [Phase 3 — Frontend Integration: Building the UI/UX](#phase-3--frontend-integration-building-the-uiux)
5. [The Hackathon Winning Edge](#5-the-hackathon-winning-edge)
   - [What Makes This Win in a 3-Minute Demo](#51-what-makes-this-win-in-a-3-minute-demo)
   - [The 3-Minute Demo Script](#52-the-3-minute-demo-script)
6. [Personalised Voice Fingerprint Engine (Future Roadmap)](#6-personalised-voice-fingerprint-engine-future-roadmap)
   - [The Six Acoustic Dimensions Echo Will Capture](#61-the-six-acoustic-dimensions-echo-will-capture)
   - [The Technical Pipeline — End to End](#62-the-technical-pipeline--end-to-end)
   - [Step-by-Step Technical Detail](#63-step-by-step-technical-detail)
   - [The Three-Phase Voice Roadmap](#64-the-three-phase-voice-roadmap)
   - [New Files & Services Required for Voice](#65-new-files--services-required-for-voice)
   - [New Tech Stack Additions for Voice](#66-new-tech-stack-additions-for-voice)
   - [The Consent Architecture for Voice Cloning](#67-the-consent-architecture-for-voice-cloning)

---

## 1. Executive Summary & The Hook

### 1.1 Project Name & Core Value Proposition

**Echo** is a consent-first, multimodal AI platform that transforms structured life-narrative sessions into a deeply personal, privately hosted "voice model" of a human being. Unlike a memorial website or a static recording, Echo enables family members to have *new* conversations with a loved one's preserved memory — conversations grounded exclusively in what that person actually shared, recalled in their voice, reasoning style, and emotional cadence.

> **Core Value Proposition:** Echo uses Gemini Live voice sessions, Groq-powered retrieval-grounded persona responses, and a consent-governed memory graph to let families continue meaningful conversations with the mind of someone they've lost — not a simulation, but a reflection.

**Critical ethical differentiator:** Echo never fabricates. If a grandmother never shared a memory about a topic, her Echo responds: *"I don't have a memory of that — I wish I did."* This boundary is technically enforced through RAG-only generation with a strict no-hallucination system prompt, making Echo trustworthy rather than uncanny.

---

### 1.2 Market Validity: Target User Personas

#### Primary Persona — The Subject

**Demographics:**
- Age 55–80, often retired or semi-retired
- Has grandchildren or adult children who live remotely
- May have received an early-stage diagnosis (dementia, cancer)
- Moderate tech comfort — uses smartphone daily
- Deeply values being understood and remembered accurately

**Pain Points:**
- Fear that their stories, values, and personality will be forgotten
- No structured, dignified way to record their inner life
- Existing options (memoir writing, video diaries) feel like work
- Concerned about who controls their digital likeness after death
- Wants to give grandchildren something real, not a photo album

#### Secondary Persona — The Family Member

- Adult child, age 30–55, often geographically distant
- Has questions they never asked while they had the chance
- Wants to share a grandparent's wisdom with their own children
- Tech-savvy, emotionally motivated, high willingness to pay

#### Tertiary Persona — The Proactive Planner

- Age 35–55, any health status
- Has watched a parent die without documenting their story
- Motivated by not repeating that loss for their own children
- Uses tools like life insurance, wills — treats this as legacy infrastructure

---

### 1.3 Market Statistics & Why Now

| Metric | Value | Source |
|--------|-------|--------|
| People globally living with dementia | **55M+** (projected to triple by 2050) | WHO, 2023 |
| Global death care / end-of-life services market | **$110B** (growing 5.8% CAGR) | Industry reports |
| Adults who regret not asking a deceased parent more questions | **67%** | Pew, 2022 |

Three converging forces make this the right moment:

1. **Gemini Live** provides low-latency bidirectional audio over WebSockets, so a subject can have a natural spoken interview without exposing a long-lived provider key to the browser.
2. **Groq-hosted Llama 3.3 70B** produces retrieval-grounded persona responses and structured memory extraction on a configurable developer-tier model.
3. **Cultural moment** — post-COVID emphasis on digital legacy, combined with growing distrust of "AI ghost" companies that do this without consent, creates an opening for an ethical, subject-first competitor.

> **The competitive gap:** Existing players (HereAfter AI, StoryFile, Eternos) collect video recordings and build chatbots from transcripts. None use live audio AI for collection, none offer fine-tuned persona models, and none have a robust consent architecture. Echo is not a better version of these products — it is a fundamentally different category.

---

## 2. Comprehensive System Architecture

### 2.1 Architecture Overview

Echo is composed of four principal layers:

- **Next.js 14 frontend** with real-time WebSocket connections for audio streaming
- **FastAPI backend** orchestrating the AI pipeline and business logic
- **Dual-database layer** — PostgreSQL via Supabase for structured data, Pinecone for vector embeddings
- **Multi-model AI layer** — Gemini Live for native session audio and Gemini embeddings; Groq Llama for persona generation, structured extraction, and audio transcription

Redis handles session state and job queuing. All infrastructure is containerized and deployable on Railway or Fly.io within a hackathon window.

---

### 2.2 Exact Tech Stack

| Layer | Technology | Specific Reason for Choice |
|-------|------------|---------------------------|
| Frontend Framework | Next.js 14 (App Router) | Server Components reduce client bundle for emotionally sensitive UI. App Router enables streaming SSR for progressive loading. Built-in API routes eliminate a separate BFF layer during hackathon speed constraints. |
| Frontend Language | TypeScript 5.4 | Type safety across the memory graph schema prevents silent runtime errors in production-critical data paths. Shared types between frontend and FastAPI via `openapi-typescript`. |
| UI Components | shadcn/ui + Tailwind CSS | shadcn's copy-paste model means zero install overhead for accessible components (dialogs, toasts, sliders). Tailwind prevents style conflicts. The unstyled foundation allows the warm, human aesthetic Echo requires. |
| Real-time Audio | Gemini Live API + WebSocket | The browser streams 16 kHz PCM and receives native audio through Gemini Live. FastAPI mints a constrained, one-use ephemeral token; the Gemini API key never reaches the browser. |
| Backend Framework | FastAPI (Python 3.12) | FastAPI owns provider credentials, Supabase JWT validation, and the provider-neutral memory pipeline while keeping long-lived keys server-side. |
| Task Queue | Celery + Redis | Post-session processing (transcription cleanup, memory graph construction, embedding generation, fine-tune job submission) is asynchronous and long-running. Celery with Redis as broker handles this without blocking the API. Redis also stores ephemeral session state. |
| Primary Database | PostgreSQL via Supabase | Supabase provides row-level security (RLS) out of the box — essential for Echo's consent architecture where subjects control exactly which rows are accessible to which family members. Realtime subscriptions enable live UI updates during session processing. |
| Vector Database | Pinecone (Serverless) | Memory retrieval during family conversations requires semantic search across hundreds of memory fragments. Pinecone's serverless tier eliminates index management overhead and provides <50ms p99 query latency. Metadata filtering enables consent-aware retrieval by access level. |
| File Storage | Supabase Storage (S3-compatible) | Audio recordings and processed transcripts are large binary objects. Supabase Storage integrates with RLS policies, so storage access inherits the same consent rules as database rows without duplicate permission logic. |
| Interview AI | Gemini Live (`gemini-3.1-flash-live-preview`) | Native audio input/output over the documented Live WebSocket protocol. The model conducts an empathetic interview while the web app displays input and output transcription. |
| Persona Model | Groq Llama 3.3 70B (configurable) | Groq streams retrieval-grounded persona answers using `GROQ_PERSONA_MODEL`; the default is `llama-3.3-70b-versatile` and can be changed without code edits. |
| Voice Synthesis | Gemini Live native audio | Spoken responses are supplied by the Live session. The separate persona conversation endpoint is text streaming, so it does not claim a second TTS provider. |
| Memory Extraction | Groq transcription + structured Llama output | Groq transcribes uploads with `whisper-large-v3-turbo`; Groq Llama returns JSON memory fragments with emotion tags, people, timestamps, and confidence. |
| Embeddings | Gemini `gemini-embedding-001` | The embedding service requests 3072 dimensions so the existing Pinecone index contract remains intact. |
| Auth | Supabase Auth (email/password + Google/GitHub OAuth) | Verified-email signup, password reset, OAuth callback exchange, browser-session refresh, and FastAPI JWT validation. JWTs flow through Supabase RLS and FastAPI middleware. |
| Deployment | Railway (backend + workers) + Vercel (frontend) | Railway supports persistent WebSocket connections and Celery workers without container orchestration overhead. Vercel's Edge Network provides optimal latency for the Next.js frontend. Both support one-command deploys from GitHub — critical for hackathon iteration speed. |
| Observability | Langfuse | Langfuse traces every LLM call with input/output logging, latency, cost tracking, and session-level grouping. Essential for debugging prompt failures during a live hackathon demo under pressure. |

---

## 3. Architectural Blueprint & File Structure

### 3.1 Production-Grade Repository Structure

```
echo/                                    # Monorepo root
├── .env.example                         # All required env vars documented
├── docker-compose.yml                   # Local: postgres, redis, pgadmin
├── turbo.json                           # Turborepo pipeline config
├── package.json                         # Workspace root — no direct deps
│
├── apps/
│   ├── web/                             # Next.js 14 frontend
│   │   ├── next.config.ts               # Experimental: serverComponentsExternalPackages
│   │   ├── tailwind.config.ts           # Echo design tokens (warm palette, radius system)
│   │   ├── middleware.ts                # Supabase auth middleware — protects all /app routes
│   │   │
│   │   ├── app/                         # App Router root
│   │   │   ├── (auth)/
│   │   │   │   ├── login/
│   │   │   │   │   └── page.tsx         # Magic link + SMS OTP login
│   │   │   │   └── callback/
│   │   │   │       └── route.ts         # Supabase auth callback handler
│   │   │   │
│   │   │   ├── (subject)/               # Routes for the person being recorded
│   │   │   │   ├── dashboard/
│   │   │   │   │   └── page.tsx         # Memory map overview, session history
│   │   │   │   ├── session/
│   │   │   │   │   ├── page.tsx         # Interview session entry point
│   │   │   │   │   └── layout.tsx       # Minimal chrome — no distractions during session
│   │   │   │   ├── memories/
│   │   │   │   │   ├── page.tsx         # Visual memory graph with consent controls
│   │   │   │   │   └── [id]/page.tsx    # Individual memory review + edit + privacy toggle
│   │   │   │   └── legacy/
│   │   │   │       └── page.tsx         # Manage legacy contacts, access levels, revocation
│   │   │   │
│   │   │   ├── (family)/                # Routes for approved family members
│   │   │   │   ├── invite/[token]/
│   │   │   │   │   └── page.tsx         # Accept legacy invitation — consent acknowledgment UI
│   │   │   │   └── conversation/[echoId]/
│   │   │   │       └── page.tsx         # The family conversation interface (voice + text)
│   │   │   │
│   │   │   └── api/                     # Next.js API routes (thin proxies to FastAPI)
│   │   │       ├── session/
│   │   │       │   └── token/route.ts   # Mint ephemeral Realtime API token (server-side)
│   │   │       └── audio/
│   │   │           └── playback/route.ts# Proxy TTS audio stream to client
│   │   │
│   │   ├── components/
│   │   │   ├── session/
│   │   │   │   ├── AudioOrb.tsx         # Animated orb that pulses with audio amplitude
│   │   │   │   ├── TranscriptStream.tsx # Real-time transcript with emotion badges
│   │   │   │   ├── SessionControls.tsx  # Pause/resume/end session controls
│   │   │   │   └── MemoryFlash.tsx      # Pop-up when a new memory is tagged (real-time)
│   │   │   ├── memory/
│   │   │   │   ├── MemoryGraph.tsx      # D3-powered force graph of memory nodes
│   │   │   │   ├── MemoryCard.tsx       # Individual memory tile with privacy toggle
│   │   │   │   └── ConsentSlider.tsx    # Three-state (private/family/public) toggle
│   │   │   ├── conversation/
│   │   │   │   ├── VoiceInput.tsx       # Family member speaks — WebRTC capture
│   │   │   │   ├── EchoResponse.tsx     # Audio playback of Echo's response with waveform
│   │   │   │   └── ConversationLog.tsx  # Running transcript of the family conversation
│   │   │   └── ui/                      # shadcn/ui primitives (Button, Dialog, etc.)
│   │   │
│   │   ├── hooks/
│   │   │   ├── useRealtimeSession.ts    # Gemini Live WebSocket lifecycle
│   │   │   ├── useAudioAmplitude.ts     # Web Audio API amplitude for orb animation
│   │   │   └── useMemoryGraph.ts        # SWR fetcher + real-time Supabase subscription
│   │   │
│   │   └── lib/
│   │       ├── supabase/client.ts       # Browser Supabase client (anon key)
│   │       ├── supabase/server.ts       # Server-side Supabase client (service role)
│   │       └── api.ts                   # Typed FastAPI client (from openapi-typescript)
│   │
│   └── api/                             # FastAPI backend
│       ├── pyproject.toml               # FastAPI, Celery, Supabase, Pinecone, and provider-neutral HTTP deps
│       ├── Dockerfile                   # Multi-stage: builder (uv install) → runtime
│       │
│       ├── app/
│       │   ├── main.py                  # FastAPI app factory, CORS, lifespan context
│       │   ├── config.py                # Pydantic Settings — all env vars with validation
│       │   │
│       │   ├── routers/
│       │   │   ├── sessions.py          # POST /sessions, GET /sessions/{id}, PATCH status
│       │   │   ├── memories.py          # CRUD for memory fragments + consent updates
│       │   │   ├── echo.py              # POST /echo/converse — the family conversation endpoint
│       │   │   ├── finetune.py          # Trigger + poll fine-tune jobs
│       │   │
│       │   ├── services/
│       │   │   ├── memory_extractor.py  # Groq JSON output → MemoryFragment schema
│       │   │   ├── embedding_service.py # Batch embed + upsert to Pinecone
│       │   │   ├── retrieval_service.py # Consent-aware semantic retrieval from Pinecone
│       │   │   ├── persona_service.py   # Query fine-tuned model + build response
│       │   │   └── finetune_builder.py  # Construct JSONL training file from memory graph
│       │   │
│       │   ├── workers/                 # Celery tasks
│       │   │   ├── celery_app.py        # Celery instance + Redis broker config
│       │   │   ├── process_session.py   # Full post-session pipeline task
│       │   │   └── retrain_persona.py   # Incremental fine-tune after new sessions
│       │   │
│       │   ├── models/                  # Pydantic schemas (request/response + DB)
│       │   │   ├── session.py
│       │   │   ├── memory.py            # MemoryFragment, ConsentLevel enum, EmotionTag enum
│       │   │   ├── echo.py              # ConversationTurn, EchoResponse
│       │   │   └── finetune.py          # TrainingExample JSONL schema
│       │   │
│       │   └── db/
│       │       ├── client.py            # asyncpg pool + Supabase service role client
│       │       └── migrations/          # Raw SQL migrations (numbered, applied via supabase CLI)
│       │           ├── 001_subjects.sql
│       │           ├── 002_sessions.sql
│       │           ├── 003_memories.sql
│       │           ├── 004_echo_profiles.sql
│       │           ├── 005_legacy_contacts.sql
│       │           └── 006_rls_policies.sql
│
├── packages/
│   └── shared-types/                    # Auto-generated from FastAPI OpenAPI spec
│       └── index.ts                     # Shared TS types consumed by web app
│
└── scripts/
    ├── seed_demo.py                     # Populate demo subject with pre-built memory graph
    ├── build_training_data.py           # Standalone: generate JSONL from a subject's memories
    └── export_echo.py                   # Export all subject data as portable archive (GDPR)
```

---

### 3.2 Key File Explanations

#### `app/routers/echo.py` — The Core Conversation Endpoint

This route receives a family member's question, validates their access level against the subject's consent settings, queries Pinecone for relevant memory fragments (filtered by `consent_level IN ['family', 'public']` metadata), constructs a retrieval-augmented Groq prompt, and streams the text response with source citations. Live spoken interviews are handled separately by Gemini Live.

#### `app/services/memory_extractor.py` — Structured Memory Extraction

After a session, Groq's transcription endpoint produces a raw transcript. `memory_extractor.py` sends that transcript to the configured Groq persona model in JSON mode and validates the resulting `MemoryFragment` objects. Each fragment contains: `content`, `emotion_tags`, `people_mentioned`, `time_period`, `topics`, and `confidence_score`. This structured extraction is what makes retrieval precise rather than searching raw transcript text.

#### `006_rls_policies.sql` — The Consent Enforcement Layer

Row-Level Security policies are the technical backbone of consent. The `memories` table has policies ensuring: subjects can read/write all their own rows; family members can only SELECT rows where `consent_level != 'private'` AND their `user_id` appears in the `legacy_contacts` table for that subject; service role bypasses RLS for worker processes. This means even if an API bug existed, the database itself would refuse to return unauthorized memories.

---

## 4. Step-by-Step Building Process & Data Flow

### Phase 1 — Data Collection & Ingestion: The Interview Session Pipeline

**Step 1 — Subject Authentication & Session Initialization**

Subject visits the web app and authenticates with a verified email/password account or a configured Google/GitHub OAuth provider. On session start, the Next.js frontend calls `POST /api/session/token`, which server-side mints a constrained Gemini Live ephemeral token. The browser connects directly to Gemini Live through its WebSocket endpoint; the Gemini API key never leaves the server.

FastAPI simultaneously creates a session record in PostgreSQL: `INSERT INTO sessions (subject_id, started_at, status='active', interview_phase) VALUES (...)`. The session ID is returned and stored in React state.

**Step 2 — WebSocket Connection to Gemini Live**

The `useRealtimeSession` hook uses Gemini Live's bidirectional WebSocket protocol. The backend is the single source of truth for `GEMINI_LIVE_MODEL`: it creates a one-use token constrained to that model and returns it to the browser, which sends 16kHz PCM microphone frames and receives native audio responses.

The system prompt instructs the model to act as a warm, patient life-narrative interviewer and follow emotional threads rather than a rigid script. The app displays Gemini's input/output transcripts; durable memories are created through the authenticated memory API and post-session extraction pipeline.

**Step 3 — Real-Time Audio Capture & Streaming**

The browser's Web Audio API captures microphone input. PCM audio chunks are resampled to 16 kHz, base64 encoded, and sent as Gemini Live `realtimeInput.audio` messages. Gemini returns native PCM audio plus input/output transcriptions over the same WebSocket.

**Step 4 — Authenticated Memory Capture**

Typed session notes and post-session uploads are associated with the current Supabase user. The backend applies the same user scope to session, subject, memory, and Pinecone namespace operations; post-session processing turns transcripts into reviewed memory fragments before embedding.

**Step 5 — Session End & Post-Processing Trigger**

When the subject ends the session, the frontend sends `PATCH /sessions/{id}` with `status='completed'`. FastAPI triggers the Celery task `process_session.delay(session_id)` and returns immediately. The subject sees a "Your session is being processed — usually takes 3–5 minutes" screen. The Celery worker then executes the full processing pipeline.

**Step 6 — Celery Worker: Transcript Cleanup & Deep Memory Extraction**

The worker fetches raw audio from Supabase Storage and sends it to Groq's transcription endpoint using `whisper-large-v3-turbo`. It then submits the transcript to `memory_extractor.py`, which uses the configured Groq model in JSON mode and validates the result against the `MemoryFragment` schema.

**Step 7 — Embedding & Pinecone Upsert**

Each extracted `MemoryFragment` is serialized as a rich text string:
```
[MEMORY] {content} [EMOTION] {emotion_tags} [TOPICS] {topics} [PEOPLE] {people_mentioned} [ERA] {time_period}
```
This format ensures the embedding captures all semantic dimensions. Batches are submitted to Gemini `gemini-embedding-001` with 3072 output dimensions. The resulting vectors are upserted to Pinecone with metadata: `{ subject_id, memory_id, consent_level, session_id, emotion_tags[], topics[], confidence_score }`. The `consent_level` metadata field is what makes retrieval consent-aware.

---

### Phase 2 — Backend & AI Logic: The Family Conversation Pipeline

**Step 1 — Persona Dataset: Building Evaluation Pairs**

Once a subject has completed 3+ sessions (~150+ memory fragments), the `finetune_builder.py` service generates a JSONL training file. Each training example is a `{"messages": [...]}` object where the system message sets the persona context, the user message is a plausible question a family member might ask, and the assistant message is a response written in the subject's voice — synthesized from their actual memory fragments, speech patterns extracted from transcripts (filler words, sentence rhythm, vocabulary level), and values identified across sessions.

Groq does not offer a hosted fine-tuning equivalent in this architecture. Echo retains the consent-scoped JSONL as an evaluation/persona dataset and uses retrieval-grounded Groq generation instead of uploading private memories to a third-party fine-tuning job.

**Step 2 — Family Member Query Reception & Authorization**

A family member's question arrives at `POST /echo/{echo_id}/converse` as text or an audio blob. FastAPI validates the JWT, checks the `legacy_contacts` table to verify approved access, and determines the access level (`family` or `public`). Audio is transcribed through Groq before the pipeline continues.

**Step 3 — Consent-Aware Semantic Retrieval**

The query is embedded with `gemini-embedding-001`. `retrieval_service.py` queries Pinecone with: the query vector, `top_k=12`, and a metadata filter:
```json
{"$and": [{"subject_id": {"$eq": subject_id}}, {"consent_level": {"$in": allowed_levels}}]}
```
The top results are ranked by a reciprocal rank fusion of vector similarity score and a recency boost factor. Critically, if fewer than 3 results clear a minimum similarity threshold of 0.72, the system prepares a "no memory found" response rather than hallucinating.

**Step 4 — Persona Model Prompt Construction**

The retrieval results are formatted into a structured context block injected into the configured Groq model's system prompt. The prompt has three layers:
1. A static persona anchor describing the subject's name, age, speech style, and core values
2. The dynamic retrieval block with the top memory fragments labeled as `[MEMORY {n}]`
3. A strict behavioral instruction: *"You may only draw on the memories provided above. If the question cannot be answered from these memories, say so warmly and specifically — do not invent details. Never speculate about events not captured in your memories."*

The Groq persona model then generates a response that sounds like the subject while being constrained to factual recall.

**Step 5 — Streaming Persona Response**

The Groq persona response is streamed token-by-token as Server-Sent Events with its memory citations. Spoken conversations use the Gemini Live session rather than a separate TTS path.

**Step 6 — Conversation Logging & Attribution**

Every conversation turn is logged to the `conversation_history` table with: question text, response text, memory fragment IDs used (for attribution), latency metrics, and token counts. This enables a "citations" feature where the family member can tap any part of Echo's response and see the exact session and memory fragment it came from — a transparency feature that builds trust and reinforces the "this is real" quality of the response.

---

### Phase 3 — Frontend Integration: Building the UI/UX

**Step 1 — The Interview Session UI — AudioOrb Component**

The interview experience is intentionally minimal. A full-screen view shows only the `AudioOrb` — a soft, glowing circle that scales with audio amplitude using Web Audio API's `AnalyserNode` and a `requestAnimationFrame` loop. When the AI is speaking, the orb pulses in a warm amber. When the subject is speaking, it pulses in a soft purple. The transcript appears below in real-time, and `MemoryFlash` cards slide in from the right when a memory is tagged. This UI is intentionally non-threatening for elderly users — large type, no menus, one button to pause and one to end.

**Step 2 — The Memory Graph — Consent Review UI**

After processing completes, Supabase Realtime triggers a push notification to the subject's browser via `useMemoryGraph`. The memory graph renders with D3's force-directed layout — memory nodes clustered by topic, sized by emotional intensity, colored by era. Clicking a node opens a `MemoryCard` showing the full text and a three-state `ConsentSlider`: Private (padlock icon), Family Only (family icon), or Legacy (globe icon). Changes trigger `PATCH /memories/{id}` and simultaneously update the Pinecone metadata via a background job so consent changes take effect within seconds for family conversations.

**Step 3 — The Family Conversation UI**

The family conversation page is two-pane: a conversation log on the left (showing the ongoing dialogue with citations), and the audio interface on the right. Family members can either type questions or hold a button to speak. Voice input is captured via WebRTC, sent to the API as audio, transcribed, processed, and Echo's response plays back automatically with a subtle waveform animation. Below each Echo response, a collapsed "Sources" accordion shows which memories were used, linkable to the original session recording timestamp. This citation layer is what makes the experience feel real rather than uncanny.

**Step 4 — State Management & Real-Time Sync**

The app avoids a global state manager (Redux, Zustand) to stay lean for a hackathon. Instead: Supabase Realtime subscriptions drive memory graph updates; SWR handles server state with optimistic updates for consent toggles; React Context holds session state during an active interview; and the WebSocket lifecycle is entirely encapsulated in the `useRealtimeSession` hook. This architecture means the entire data flow is observable and debuggable without DevTools plugins.

---

## 5. The Hackathon Winning Edge

### 5.1 What Makes This Win in a 3-Minute Demo

The goal of a hackathon demo is not to show features — it is to create an emotional moment that judges remember when they are deliberating at midnight. Every technical decision below is in service of producing that moment.

#### Wow Factor 01 — The Live Interview Demo
**Show the AI actually interviewing a real person, on screen, in real time**

Open the demo with the presenter's own grandmother (or a stand-in) on screen. Gemini Live conducts a 90-second interview: it asks a warm opening question, responds empathically to her answer, and probes deeper. Judges see the transcript appearing in real time. The browser uses only a constrained ephemeral credential, not a long-lived key.

#### Wow Factor 02 — The Memory Graph Reveal
**A visual constellation of a person's inner life**

After the session, cut to the memory graph: 40+ nodes forming a glowing constellation — clustered by family, career, values, and place. Each node pulses gently. The presenter zooms into one — "The summer she almost didn't go to college" — and reads the memory fragment aloud. Then they toggle its consent level from Private to Family. Judges understand immediately: this is not a database. This is a mind, made navigable. The D3 force graph animation alone takes 3 seconds to render and generates an audible reaction in every test audience.

#### Wow Factor 03 — The Family Conversation Moment
**Ask her a question she's no longer alive to answer**

This is the demo's emotional climax. The presenter — playing the role of a granddaughter — speaks into the mic: *"Grandma, did you ever regret not traveling more?"* After 2 seconds, Echo responds in a warm voice, drawing on a memory fragment from the session: a story about a trip to Portugal she almost took in 1974. The response is in her rhythm, her vocabulary. Below it, a "Sources" accordion expands showing the exact memory fragment and the session timestamp. The judge does not see a chatbot. They see a grandmother answering from across time. The demo ends there. No features list. No roadmap slide. Just silence.

#### Wow Factor 04 — The Ethical Boundary, Live
**Ask something Echo doesn't know — and watch it refuse to fabricate**

Immediately after the emotional moment, the presenter asks: *"Grandma, what do you think about my husband?"* — a question the subject never addressed. Echo responds: *"I don't have a memory of your husband — I wish I could tell you. But I'd love to hear about him from you."* This single moment differentiates Echo from every ghost AI competitor and pre-empts the judges' ethical concern before they can raise it. The technical constraint becomes the emotional feature.

#### Wow Factor 05 — The Pre-Seeded Demo Fallback
**A fully populated demo subject ensures the demo never fails**

The `seed_demo.py` script populates a demo subject ("Eleanor, 74") with 87 pre-built memory fragments spanning 6 sessions, a completed fine-tune job, and a full memory graph. If any live component fails during the demo, the presenter switches to Eleanor's pre-built Echo in 10 seconds. The family conversation still works identically. Judges never see a loading spinner. This is the most important engineering decision for a live demo under pressure.

---

### 5.2 The 3-Minute Demo Script

| Time | Beat | Action |
|------|------|--------|
| 0:00 – 0:20 | **The hook** | *"67% of adults say they regret not asking a deceased parent more questions. Echo solves this — before it's too late."* |
| 0:20 – 1:15 | **Live interview** | Show Gemini Live conducting a real 55-second interview with transcript streaming. |
| 1:15 – 1:40 | **Memory graph** | *"Here's what 3 sessions produces."* Show the D3 constellation. Click one node. Read the memory. Show consent toggle. |
| 1:40 – 2:30 | **The family conversation** | Ask the emotional question. Play Echo's response with voice. Expand the sources accordion. Let the silence sit. |
| 2:30 – 2:50 | **The ethical boundary** | Ask the unknowable question. Show Echo's graceful refusal. *"This is what makes Echo trustworthy, not just powerful."* |
| 2:50 – 3:00 | **Close** | *"Echo is live at echo.app. The person you're thinking of right now — there's still time."* Cut. |

---

## 6. Personalised Voice Fingerprint Engine (Future Roadmap)

> **The Vision:** Echo listens to how a person speaks — their pitch, bass, treble, loudness, depth, tone, rhythm, pauses, and the words they reach for most — and synthesises every future response in that exact acoustic identity. Not a generic voice preset. Not a rough clone. A mathematically precise replica of how someone sounds when they are most themselves.

---

### 6.1 The Six Acoustic Dimensions Echo Will Capture

Current TTS systems reproduce *what* a voice sounds like in a neutral state. The Voice Fingerprint Engine goes six layers deeper, treating each dimension as a separately extractable and separately reproducible signal:

| # | Dimension | Tech | Description |
|---|-----------|------|-------------|
| 🎚️ | **Spectral Profile** | librosa · MFCCs · Mel filterbank | The physical shape of the voice — bass resonance, treble brightness, mid-range warmth. Captured as 40-coefficient MFCC vectors averaged across all session audio. This is the "colour" of someone's voice that makes them instantly recognisable. |
| 🎵 | **Pitch Contour** | CREPE · PYIN · F0 tracking | How pitch rises and falls across sentences — the melody of speech. Does the voice rise at the end of statements (uptalk)? Drop when being emphatic? CREPE tracks fundamental frequency (F0) frame-by-frame at 10ms resolution. |
| 🫁 | **Paralinguistic Texture** | Pyannote · spectral flatness | Breathiness, vocal fry, nasality, and the sound of thinking — the micro-textures that make a voice feel human rather than synthesised. Captured via spectral flatness and harmonic-to-noise ratio analysis per utterance. |
| ⏱️ | **Temporal Dynamics** | WebRTC VAD · silence detection | Speech rate, pause duration before emotional responses, how long silences last when someone is thinking, acceleration when excited. These rhythms are as identifying as a fingerprint and almost entirely absent from current voice clones. |
| 📢 | **Loudness & Dynamics** | RMS energy · dynamic range | How loud someone naturally speaks, how much they vary their volume, whether they get quieter when saying something vulnerable or louder when telling a story. Captured as per-utterance RMS energy distributions with emotional context tags. |
| 🗣️ | **Lexical & Prosodic Habits** | Groq Llama · word frequency analysis | Which words are overused ("you know," "sort of," "exactly"), characteristic sentence openers, filler patterns, and where stress falls — the verbal fingerprint that exists in the language model layer but must sync with the audio layer to feel real. |

---

### 6.2 The Technical Pipeline — End to End

```
1. Audio Accumulation      →  Sessions stored in Supabase Storage
2. Speaker Diarization     →  Pyannote isolates subject-only audio segments
3. Feature Extraction      →  librosa + CREPE → voice profile JSON
4. Profile Aggregation     →  Average across sessions → stable fingerprint
5. Voice Model Training    →  ElevenLabs Pro Clone → conditioned TTS
6. Conditioned Synthesis   →  Persona model text + voice fingerprint → audio
```

---

### 6.3 Step-by-Step Technical Detail

**Step 1 — Diarization: Isolating the Subject's Voice**

Raw session audio contains both the AI interviewer (Gemini Live output) and the subject. Before any analysis, Pyannote Audio's speaker diarization model (`pyannote/speaker-diarization-3.1`) segments the audio by speaker. Only segments attributed to the subject are forwarded to the feature extraction pipeline. This ensures the voice profile is built purely from the human, not contaminated by AI audio.

**Step 2 — MFCC Extraction: The Spectral Fingerprint**

Each subject audio segment is loaded via `librosa.load()` at 22,050 Hz. Mel-frequency cepstral coefficients are extracted with `librosa.feature.mfcc(y, sr, n_mfcc=40)`. The 40-coefficient MFCC matrix captures the spectral envelope — bass depth, treble brightness, nasal resonance, chest versus head voice ratio. These are averaged across all frames to produce a stable 40-dim spectral fingerprint vector stored in the `voice_profiles` table. After 3+ sessions (~90 minutes of subject audio), this vector becomes highly stable and reliable.

**Step 3 — Pitch Tracking with CREPE**

CREPE (Convolutional REPresentation for Pitch Estimation) runs on each segment to extract frame-level fundamental frequency (F0) at 10ms hop size. The output is a time-series of pitch values with confidence scores. From this series, the system computes:
- Mean F0 (the subject's natural speaking pitch)
- F0 standard deviation (how much they vary pitch — monotone vs. expressive)
- Pitch range (minimum to maximum across emotional moments)
- Characteristic pitch contour patterns at sentence boundaries (does it rise, fall, or stay flat?)

These statistics form the prosodic fingerprint.

**Step 4 — Temporal & Dynamic Analysis**

WebRTC VAD (Voice Activity Detection) timestamps are used to compute speech rate (syllables per second, estimated via zero-crossing rate), mean pause duration, and pause frequency. RMS energy analysis produces per-utterance loudness distributions. Crucially, utterances are tagged with their emotional context from the memory extraction pipeline — allowing the system to learn that this subject gets *quieter* when discussing grief and *faster* when excited, and to reproduce that emotional modulation during synthesis.

**Step 5 — ElevenLabs Professional Voice Clone Training**

Once 30+ minutes of clean subject audio is accumulated (typically after 2–3 sessions), it is submitted to ElevenLabs' Professional Voice Clone endpoint (`POST /v1/voices/add` with `files[]` containing the cleaned audio segments). The Professional Clone — distinct from the Instant Clone — trains a speaker-conditioned neural TTS model that captures not just the spectral shape but also prosodic tendencies and vocal texture. The resulting `voice_id` is stored in `echo_profiles.elevenlabs_voice_id`. All future TTS synthesis for this subject routes through this voice ID rather than a generic preset.

**Step 6 — Emotion-Conditioned Synthesis at Response Time**

When a future external voice-cloning integration generates a response from the Groq persona model, it must apply voice settings derived from the fingerprint. For ElevenLabs this means setting:
- `stability` — inverse of the subject's measured F0 standard deviation (more variable speakers get lower stability)
- `similarity_boost` — set to 0.85+ for the professional clone
- `style` — derived from the emotional tag on the retrieved memory (grief responses get higher style for slower delivery, humor responses get lower for faster)

The result is not just the right voice — it is the right voice in the right emotional register for what is being said.

**Step 7 — Phase 3: Full Neural Conditioning (12–18 Month Target)**

The long-term target replaces the ElevenLabs dependency with a fully in-house neural TTS model that jointly conditions on both the text (from the fine-tuned persona model) and the complete acoustic fingerprint vector (MFCC + F0 statistics + temporal dynamics). The architecture follows the VALL-E / VoiceBox paradigm: a neural codec language model that takes a 3-second acoustic prompt plus the fingerprint vector as conditioning signals and generates audio that is both acoustically identical to the subject and prosodically appropriate for the semantic content.

---

### 6.4 The Three-Phase Voice Roadmap

| Phase | Timeline | Approach | Cost |
|-------|----------|----------|------|
| **Phase 1 — Live Interview Voice** | Available at launch | Gemini Live provides native session audio through a constrained ephemeral token. No audio analysis is required. | Provider free/developer tier subject to quota |
| **Phase 2 — ElevenLabs Professional Voice Clone** | 3–6 months | Spectral + prosodic fingerprint extraction via librosa + CREPE. ElevenLabs Pro Clone trained on clean session audio. Emotion-conditioned synthesis settings per response. Subject must provide explicit voice clone consent separate from memory consent. | ~$5/subject training cost (after 30+ min of audio) |
| **Phase 3 — Full Acoustic Fingerprint Neural TTS** | 12–18 months | All 6 acoustic dimensions captured and stored as fingerprint vector. VALL-E / VoiceBox-style neural codec model conditioned on fingerprint. Emotional register modulation. Characteristic filler words and hesitation sounds reproduced. Full local model — no third-party voice API dependency. | After 90+ min of audio |

---

### 6.5 New Files & Services Required for Voice

```
apps/api/app/
├── services/
│   ├── voice_fingerprint.py       # Core: librosa MFCC extraction + CREPE F0 tracking
│   ├── diarization_service.py     # Pyannote: isolate subject audio from AI audio
│   ├── voice_clone_service.py     # ElevenLabs Pro Clone: train, store voice_id, synthesise
│   └── emotion_tts_mapper.py      # Map emotion tags → ElevenLabs stability/style params
│
├── workers/
│   └── build_voice_profile.py     # Celery task: runs after each session, updates fingerprint
│
└── db/migrations/
    ├── 007_voice_profiles.sql     # mfcc_vector, f0_mean, f0_std, speech_rate, pause_duration
    └── 008_voice_consent.sql      # Separate consent flag: voice_clone_consented (boolean)

apps/web/components/
└── voice/
    ├── VoiceConsentModal.tsx      # Explicit, separate consent UI for voice cloning
    ├── VoiceProfileCard.tsx       # Subject dashboard: show voice fingerprint dimensions
    └── VoicePreview.tsx           # Let subject hear a sample in their cloned voice before approving
```

---

### 6.6 New Tech Stack Additions for Voice

| Layer | Technology | Specific Reason for Choice |
|-------|------------|---------------------------|
| Diarization | Pyannote Audio 3.1 | State-of-the-art speaker diarization in Python. Pre-trained on thousands of hours of conversational audio. Accurately separates the subject's voice from the AI's TTS output even when voices overlap. Available via Hugging Face Hub with a one-time licence acceptance. |
| Spectral Analysis | librosa 0.10 | The canonical Python audio analysis library. Provides MFCC extraction, spectral centroid, zero-crossing rate, RMS energy, and harmonic-percussive separation in a single `pip install`. No GPU required — runs efficiently on CPU workers for post-session processing. |
| Pitch Tracking | CREPE (TensorFlow) | CREPE outperforms classical pitch trackers (YIN, PYIN) on real-world speech by ~30% in voiced/unvoiced accuracy. Its confidence output enables the system to discard unreliable pitch frames (whispers, glottalization) and build a cleaner F0 profile. Available as `pip install crepe`. |
| Phase 2 Voice Clone | ElevenLabs Professional Voice Clone API | The only commercially available voice clone that captures prosodic texture (not just spectral shape) from 30+ minutes of audio. The Professional tier trains a speaker-adaptive model rather than just conditioning on a 3-second prompt, resulting in significantly more natural long-form speech. Voice ID is persistent and reusable across all future synthesis calls. |
| Phase 3 Neural TTS | VALL-E / VoiceBox (Meta, open weights) | VALL-E's neural codec language model architecture enables conditioning on arbitrary acoustic prompts plus learned speaker embeddings. In Phase 3, the acoustic fingerprint vector replaces the 3-second prompt, enabling synthesis from accumulated statistical knowledge rather than a single audio clip. Requires GPU inference (A10G minimum) but eliminates all third-party API dependency. |
| Emotion Mapping | Custom `emotion_tts_mapper.py` | A lightweight lookup service that maps the emotion tags from retrieved memory fragments to ElevenLabs voice parameter ranges. Grief → stability 0.8, style 0.3 (slower, quieter). Humor → stability 0.4, style 0.7 (faster, more variable). Pride → stability 0.6, style 0.5. These ranges are seeded with defaults and refined per-subject based on family feedback. |

---

### 6.7 The Consent Architecture for Voice Cloning

> **Critical ethical distinction:** Voice cloning consent is handled entirely separately from memory consent. A subject may share all their memories with family but explicitly opt out of having their voice cloned. In this case, Echo uses the Phase 1 voice preset for all synthesis. The voice clone is never activated without an explicit, standalone consent action — a separate modal with plain-language explanation, a typed confirmation, and a recorded timestamp stored in `voice_profiles.clone_consented_at`.

**Subject consent at activation:** After 30+ minutes of audio is accumulated, the subject receives a notification: *"Echo can now learn your voice. This means future responses will sound more like you. You can turn this off at any time."* They must tap "I consent to voice learning" in a dedicated modal — not a checkbox buried in settings.

**Voice preview before approval:** The `VoicePreview.tsx` component generates a 15-second sample in the cloned voice using a neutral test sentence. The subject hears it before approving. If it sounds wrong or unsettling, they can decline and remain on the voice preset.

**Family member disclosure:** Every Echo conversation page shows a persistent label: *"Responses synthesised by AI in Eleanor's voice — not original recordings."* Family members cannot be confused about whether they are hearing a real recording or a synthesis.

**Revocation:** The subject or their designated estate contact can revoke voice clone consent at any time. Revocation triggers immediate deletion of the ElevenLabs voice model via `DELETE /v1/voices/{voice_id}` and sets `voice_profiles.clone_revoked_at`. All future responses fall back to the Phase 1 preset within seconds.

**Database enforcement:** The `008_voice_consent.sql` migration adds a check constraint:
```sql
CHECK (elevenlabs_voice_id IS NULL OR clone_consented_at IS NOT NULL)
```
This makes it structurally impossible to store a voice ID without a consent timestamp — the consent is not just a UI gate, it is a database-level invariant.

---

*Echo — Full Product Blueprint · Built for OpenAI Hackathon · All systems: Next.js 14 · FastAPI · Supabase · Pinecone · Gemini Live · Groq Llama · Gemini embeddings · librosa · CREPE · ElevenLabs Pro Clone · Pyannote*

---

## 7. Deployment Instructions

Echo is designed to be deployed with zero code changes using Railway for the backend and Vercel for the frontend.

### 7.1 Backend (Railway)
The FastAPI backend and Celery workers are containerised using Nixpacks.
1. Connect your GitHub repository to Railway.
2. Railway will automatically detect the `apps/api/railway.toml` and configure the Web and Worker services.
3. Configure the following environment variables in Railway:
   - `GEMINI_API_KEY`, `GROQ_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX`
   - `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`
   - `DATABASE_URL` (Auto-provisioned if using Railway PostgreSQL, or use Supabase pooling URL)
   - `REDIS_URL` (Auto-provisioned if using Railway Redis)
   - `CORS_ORIGINS` (Set to your Vercel frontend URL, e.g., `https://echo-web.vercel.app`)
4. Migrations will automatically run on startup via the configured `startCommand` in `railway.toml`.

### 7.2 Frontend (Vercel)
The Next.js 14 frontend is pre-configured for Vercel deployment.
1. Connect your GitHub repository to Vercel.
2. Select the `apps/web` directory as the Root Directory, or let Vercel auto-detect the monorepo structure using `vercel.json`.
3. Configure the following environment variable in Vercel:
   - `NEXT_PUBLIC_API_BASE_URL` (Set to your Railway backend URL, e.g., `https://echo-api.up.railway.app`)
   - `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` (the public Supabase browser configuration)
4. Vercel will automatically build and deploy using `pnpm`.
