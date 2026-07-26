# Sprint 3.12 — Agent Execution Transparency

**Status:** 📋 Planned  
**Type:** UX + Observability  
**Scope:** Backend event emission, frontend execution timeline, streaming integration  
**Breaking Changes:** None  
**Backward Compatible:** Yes

---

# Objective

Transform Tarka from a conventional chat interface into a transparent **Agentic AI experience** by exposing the internal execution lifecycle of every user request.

Currently, users only see a generic **"Thinking..."** indicator while the backend processes a request.

Although Tarka already performs multiple execution stages internally—such as planning, tool selection, tool execution, and response generation—none of these stages are visible to users.

The goal of this sprint is to expose those stages in real time, allowing users to observe how the agent works.

This sprint introduces **no new AI capabilities, tools, or reasoning logic.**

Its sole purpose is to improve transparency and user experience.

---

# Current State

Current interaction flow:

```
User
    │
    ▼
Send Prompt
    │
    ▼
Thinking...
    │
    ▼
Assistant Response
```

Current limitations:

- Users cannot see what the agent is doing.
- Tool execution is hidden.
- Planning is hidden.
- Execution progress is hidden.
- The interaction feels identical to a traditional chatbot.

---

# Desired End State

The execution lifecycle should become visible.

Instead of:

```
Thinking...
```

Users should observe:

```
🧠 Understanding Request

↓

📋 Planning

↓

🔧 Selecting Tool

↓

⚡ Executing Tool

↓

💬 Generating Response

↓

✔ Completed
```

Every stage must correspond to a real backend operation.

No artificial delays.

No fake progress.

---

# Existing System

## Backend

The backend already contains:

- FastAPI Backend
- Planner
- Tool Registry
- Tool Executor
- Ollama Provider
- Conversation Runtime
- Streaming Responses

These systems already work correctly.

They should **not** be modified beyond emitting execution events.

---

## Frontend

Current behavior:

```
User Prompt

↓

Thinking...

↓

Streaming Response
```

The frontend has no awareness of backend execution.

---

# Sprint Goal

Expose backend execution stages to the frontend.

Replace the generic loading indicator with a live execution timeline.

The timeline should update dynamically as execution progresses.

---

# Functional Requirements

## 1. Execution State Model

Introduce a shared execution state model.

Suggested stages:

```
UNDERSTANDING

PLANNING

SELECTING_TOOL

EXECUTING_TOOL

GENERATING_RESPONSE

COMPLETED
```

These represent execution progress only.

They must never expose model reasoning or chain-of-thought.

---

## 2. Backend Event Emission

The backend should emit execution events whenever the runtime reaches a new stage.

Example:

```
Receive Request

↓

UNDERSTANDING

↓

PLANNING

↓

SELECTING_TOOL

↓

EXECUTING_TOOL

↓

GENERATING_RESPONSE

↓

COMPLETED
```

Each event should correspond to an actual backend operation.

---

## 3. Tool Awareness

When a tool is selected, emit the tool name.

Examples:

```
Calculator

Date Tool

File System

Weather
```

If no tool is required, skip tool-related stages entirely.

Example:

```
Understanding

↓

Planning

↓

Generating Response
```

---

## 4. Frontend Timeline

Replace the current "Thinking..." indicator with an execution timeline.

Example:

```
🧠 Agent Activity

✔ Understanding Request

✔ Planning

✔ Selected Calculator

✔ Executing Calculator

⏳ Generating Response
```

The timeline should update live as events arrive.

---

## 5. Streaming Compatibility

Execution updates must integrate with the existing streaming architecture.

Expected execution flow:

```
Understanding

↓

Planning

↓

Selecting Tool

↓

Executing Tool

↓

Generating Response

↓

Streaming Begins

↓

Streaming Continues

↓

Completed
```

Streaming should continue functioning exactly as it does today.

---

# Backend Responsibilities

The backend is responsible for:

- Determining execution stage
- Emitting execution events
- Providing selected tool name
- Signaling completion

The backend should not contain UI logic.

---

# Frontend Responsibilities

The frontend is responsible for:

- Receiving execution events
- Rendering the execution timeline
- Updating completed stages
- Highlighting the active stage
- Clearing or collapsing the timeline after completion

---

# Example Execution Flow

User asks:

```
Calculate 25 / 39
```

Backend:

```
Receive Request

↓

UNDERSTANDING

↓

PLANNING

↓

SELECTING_TOOL
Calculator

↓

EXECUTING_TOOL
Calculator

↓

GENERATING_RESPONSE

↓

STREAM RESPONSE

↓

COMPLETED
```

Frontend:

```
🧠 Agent Activity

✔ Understanding Request

✔ Planning

✔ Selected Calculator

✔ Executing Calculator

⏳ Generating Response
```

After streaming completes:

```
🧠 Agent Activity

✔ Understanding Request

✔ Planning

✔ Selected Calculator

✔ Executing Calculator

✔ Response Generated
```

---

# Technical Constraints

- Do not modify planner logic.
- Do not modify tool execution behavior.
- Do not change LLM generation.
- Do not introduce artificial delays.
- Do not expose chain-of-thought.
- Every stage must represent a real backend event.

---

# Future Compatibility

The architecture should support future execution stages without redesign.

Examples:

```
MEMORY_RETRIEVAL

RAG_RETRIEVAL

WEB_SEARCH

FILE_ANALYSIS

MULTI_AGENT_ROUTING

VERIFICATION

REFLECTION

CACHE_LOOKUP

TASK_DELEGATION

TOOL_FAILED
```

Adding a new stage should only require:

1. Backend event emission.
2. Frontend rendering.

No architectural changes.

---

# Out of Scope

This sprint does **not** include:

- New Tools
- New LLM Providers
- Multi-Agent Collaboration
- Memory Improvements
- RAG
- Web Search
- Authentication
- Deployment
- UI Redesign beyond the execution timeline

---

# Definition of Done

Sprint 3.12 is complete when:

- [ ] Generic "Thinking..." indicator removed.
- [ ] Backend emits execution stage events.
- [ ] Frontend displays a live execution timeline.
- [ ] Tool selection is visible.
- [ ] Tool execution is visible.
- [ ] Streaming continues without regression.
- [ ] No artificial progress is introduced.
- [ ] Timeline accurately reflects backend execution.
- [ ] Existing chat functionality remains unchanged.

---

# Success Criteria

After this sprint, a first-time user should immediately recognize that Tarka behaves as an **autonomous AI agent** rather than a conventional chatbot.

The interface should communicate *what the agent is doing* throughout the request lifecycle, improving transparency, trust, and showcasing Tarka's agentic architecture.