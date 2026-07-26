# Tarka Architecture

---

# Overview

Aryntra Tarka is a layered, autonomous AI agent designed around the principles of separation of concerns, extensibility, and predictable execution.

Rather than relying on a single monolithic AI call, Tarka decomposes each user request into distinct architectural layers. A planner determines the required actions, the runtime orchestrates execution, tools perform specialized capabilities, providers generate natural language responses, and persistence maintains conversation history.

Each subsystem owns a single responsibility and communicates only through well-defined interfaces. This architecture allows new tools, providers, and platform capabilities to be added with minimal impact on existing components.

Version 1 focuses on providing a robust foundation for autonomous multi-tool execution. Future versions extend this architecture through additional tools and integrations without requiring architectural rewrites.

---

# Design Principles

The architecture is guided by a small set of principles that shape every subsystem and future enhancement.

## Layered Architecture

The system is organized into independent layers, each responsible for a specific part of the application. Layers communicate only through well-defined interfaces, reducing coupling and improving maintainability.

## Separation of Concerns

Each component has a single responsibility.

- The Planner decides **what** should happen.
- The Runtime decides **how** it happens.
- Tools perform specialized tasks.
- Providers communicate with language models.
- Persistence manages long-term storage.
- The Frontend presents information to the user.

## Stateless API

The FastAPI application remains stateless between requests. Conversation context is reconstructed from persistent storage for every request, allowing reliable session handling and easier horizontal scaling.

## Session Isolation

Each conversation is isolated using a unique session identifier. Messages from one session never influence another, ensuring predictable and secure conversation management.

## Tool Independence

Every tool is implemented as an independent module with a consistent interface. Tools remain unaware of each other and can be added, removed, or replaced without affecting the runtime.

## Provider Abstraction

Language model providers are accessed through a common abstraction layer. Switching between providers requires implementing the provider interface without modifying the planner or runtime.

## Streaming First

Responses are streamed to the client using Server-Sent Events (SSE), providing immediate feedback and improving the user experience during long-running operations.

## Extensible by Design

The architecture is designed to grow through extension rather than modification. New capabilities should integrate with existing interfaces instead of requiring changes to established architectural layers.

---

# High-Level Architecture

```text
                           Browser
                  (React + Vite + TypeScript)
                               │
                        HTTP / REST / SSE
                               │
                               ▼
                    FastAPI Application Server
                               │
            ┌──────────────────┴──────────────────┐
            │                                     │
      Conversation Memory                  Planner
            │                                     │
            └──────────────────┬──────────────────┘
                               ▼
                         Agent Runtime
                               │
                        Tool Registry
         ┌──────────────┼──────────────┬──────────────┐
         │              │              │              │
    Calculator      DateTime      Filesystem     Future Tools
                               │
                               ▼
                    LLM Provider Interface
                               │
                               ▼
                     Ollama (Current Provider)
                               │
                               ▼
                            SQLite
```

## Architectural Layers

The system is divided into six logical layers:

| Layer | Responsibility |
|--------|----------------|
| Frontend | Presents the user interface and streams responses |
| API | Accepts requests and exposes HTTP endpoints |
| Planning | Determines how a user request should be executed |
| Runtime | Orchestrates tool execution and response generation |
| Integration | Provides tools and language model providers |
| Persistence | Stores conversations and application state |

---

# Project Structure

The repository is organized into independent modules that mirror the architectural layers of the system.

```text
backend/
├── api/             # HTTP routes and request handling
├── planner/         # Rule-based planning engine
├── runtime/         # Execution orchestration
├── providers/       # LLM provider implementations
├── persistence/     # SQLite data access
├── memory/          # Conversation memory management
├── tools/           # Tool implementations
├── services/        # Shared business services
└── main.py          # Application entry point

frontend/
├── components/      # Reusable UI components
├── pages/           # Application pages
├── hooks/           # Custom React hooks
├── services/        # API communication
├── constants/       # Shared constants
├── assets/          # Static assets
└── App.tsx          # Frontend entry point
```

## Directory Responsibilities

### `api/`

Exposes HTTP endpoints, validates requests, and delegates execution to the runtime. This layer contains no business logic.

### `planner/`

Analyzes user requests and produces an ordered `ExecutionPlan` describing which tools should be executed and in what sequence.

### `runtime/`

Acts as the orchestration layer. It executes plans, invokes tools, communicates with language model providers, streams responses, and collects execution metadata.

### `providers/`

Contains implementations of language model providers. Every provider follows the `BaseLLMProvider` interface, allowing providers to be replaced without affecting other layers.

### `persistence/`

Responsible for storing and retrieving conversation history using SQLite. This layer is the only component that directly interacts with the database.

### `memory/`

Reconstructs conversation context from persistent storage and prepares prompt-ready conversation history for the runtime.

### `tools/`

Contains self-contained tool implementations such as Calculator, DateTime, and Filesystem. Each tool performs one specialized capability and remains independent of other tools.

### `services/`

Contains reusable business logic shared across multiple modules while avoiding duplication.

### Frontend

The frontend is responsible only for presentation. It renders streamed responses, displays execution metadata, manages navigation, and communicates with the backend through the API.

---

# Layer Responsibilities

Each architectural layer has a clearly defined responsibility. A layer should focus exclusively on its own concern and communicate with other layers only through well-defined interfaces.

## Frontend

**Responsibilities**

- Provides the user interface
- Sends requests to the backend
- Streams responses using Server-Sent Events (SSE)
- Displays execution metadata
- Manages application state and navigation

**Does Not**

- Execute tools
- Contain business logic
- Communicate directly with language model providers

---

## API Layer

**Responsibilities**

- Exposes REST endpoints
- Validates incoming requests
- Delegates execution to the runtime
- Returns streaming responses

**Does Not**

- Plan user requests
- Execute tools
- Access the database directly

---

## Planner

**Responsibilities**

- Analyzes user intent
- Determines whether tools are required
- Produces an ordered `ExecutionPlan`
- Defines execution sequence for multiple tools

**Does Not**

- Execute tools
- Generate language model responses
- Store conversation history

---

## Runtime

**Responsibilities**

- Executes the `ExecutionPlan`
- Invokes tools
- Builds prompts
- Communicates with language model providers
- Streams responses
- Collects execution metadata

**Does Not**

- Decide which tools should be used
- Implement tool-specific logic

---

## Tool Layer

**Responsibilities**

- Performs specialized capabilities
- Accepts structured input
- Returns structured output
- Remains independent of other tools

Examples include:

- Calculator
- DateTime
- Filesystem

**Does Not**

- Access the user interface
- Generate final responses
- Communicate directly with language models

---

## Provider Layer

**Responsibilities**

- Communicates with language model providers
- Supports streaming and non-streaming generation
- Implements a common provider interface

**Does Not**

- Perform planning
- Execute tools
- Manage persistence

---

## Persistence Layer

**Responsibilities**

- Stores conversation history
- Retrieves previous conversations
- Maintains session isolation
- Persists assistant and user messages

**Does Not**

- Generate prompts
- Execute application logic
- Interact with the user interface

---

# Layer Dependencies

Dependencies always flow downward through the architecture. Each layer communicates only with the layer directly beneath it, preventing tight coupling and preserving clear separation of concerns.

```text
                    Frontend
                        │
                        ▼
                    API Layer
                        │
                        ▼
                     Runtime
                        │
          ┌─────────────┴─────────────┐
          ▼                           ▼
      Planner                  Conversation Memory
          │                           │
          └─────────────┬─────────────┘
                        ▼
                 Tool Registry
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
    Calculator      DateTime      Filesystem
                        │
                        ▼
                 LLM Providers
                        │
                        ▼
                   Persistence
```

## Dependency Rules

### Frontend

May communicate with:

- API Layer

Must never communicate directly with:

- Runtime
- Planner
- Tools
- Providers
- Database

---

### API Layer

May communicate with:

- Runtime

Must never communicate directly with:

- Planner
- Individual Tools
- Providers
- Persistence

---

### Planner

May communicate with:

- Runtime (through shared models)
- Tool Registry (for tool discovery)

Must never:

- Execute tools
- Access the database
- Generate LLM responses

---

### Runtime

May communicate with:

- Planner
- Tool Registry
- Providers
- Memory
- Persistence

Acts as the central orchestration layer for the entire system.

---

### Tools

May communicate with:

- Runtime

Must never communicate with:

- Other tools
- API Layer
- Frontend
- Database

Each tool should remain completely independent.

---

### Providers

May communicate with:

- Runtime
- External LLM services

Must never communicate directly with:

- Planner
- Tools
- Frontend
- Database

---

### Persistence

May communicate with:

- Runtime
- Conversation Memory

Must never communicate with:

- Frontend
- Planner
- Providers
- Tools

---

# Request Lifecycle

Every user request follows a deterministic execution pipeline. The runtime orchestrates each stage, ensuring that planning, tool execution, language generation, and persistence remain independent responsibilities.

```text
User
 │
 ▼
React Frontend
 │
 ▼
POST /api/chat/stream
 │
 ▼
FastAPI API Layer
 │
 ▼
Runtime
 │
 ├── Load conversation from SQLite
 ├── Rebuild Conversation Memory
 ├── Persist user message
 │
 ▼
Planner
 │
 └── Generate ExecutionPlan
 │
 ▼
Runtime
 │
 ├── Execute tool steps
 ├── Collect tool results
 ├── Build LLM prompt
 │
 ▼
LLM Provider
 │
 └── Stream response tokens
 │
 ▼
Runtime
 │
 ├── Persist assistant response
 ├── Generate execution metadata
 │
 ▼
FastAPI (SSE)
 │
 ▼
React Frontend
 │
 ▼
User
```

## Step-by-Step Execution

### 1. User Request

The user submits a message through the frontend. The request is sent to the backend using the streaming chat endpoint.

---

### 2. Session Restoration

Before processing the request, the runtime restores the conversation history from SQLite and rebuilds the in-memory conversation context for the current session.

---

### 3. Message Persistence

The user's message is immediately stored in persistent storage, ensuring the conversation remains recoverable even if execution is interrupted.

---

### 4. Planning

The planner analyzes the request and determines whether any tools are required.

The output of this stage is an `ExecutionPlan`, which defines:

- Which tools should be executed
- The order of execution
- Whether the request can be answered directly by the language model

---

### 5. Tool Execution

The runtime executes each step defined in the execution plan.

Tool outputs are collected as structured data and made available for prompt construction.

---

### 6. Prompt Construction

The runtime combines:

- Conversation history
- User request
- Tool outputs
- System instructions

into a single prompt for the language model provider.

---

### 7. Response Generation

The configured language model provider generates the response and streams tokens back to the runtime using Server-Sent Events (SSE).

---

### 8. Response Persistence

Once generation completes, the assistant's response is stored in SQLite alongside the user message.

Execution metadata, such as tools used and execution duration, is also prepared.

---

### 9. Streaming to the Client

The backend continuously streams generated tokens to the frontend.

The frontend renders the response incrementally, providing immediate feedback while generation is still in progress.

---

## Execution Characteristics

Every request follows the same lifecycle regardless of complexity.

Whether the request requires:

- No tools
- A single tool
- Multiple tools

the runtime executes the same architectural pipeline, ensuring predictable behavior and consistent execution across the application.

---

# Data Flow

As a request moves through the system, its data is progressively enriched rather than replaced. Each architectural layer transforms the input into a more complete representation before passing it to the next layer.

```text
User Message
      │
      ▼
Raw Request
      │
      ▼
Execution Plan
      │
      ▼
Tool Results
      │
      ▼
Conversation Context
      │
      ▼
LLM Prompt
      │
      ▼
Generated Response
      │
      ▼
Execution Metadata
      │
      ▼
Persistent Storage
      │
      ▼
Frontend Rendering
```

## Data Transformation Stages

### 1. Raw Request

The frontend submits the user's message along with the active session identifier.

Example:

```json
{
  "session_id": "...",
  "message": "What time is it and how many minutes until midnight?"
}
```

---

### 2. Execution Plan

The planner analyzes the request and converts it into an internal execution plan.

Example:

```text
ExecutionPlan

Step 1 → DateTime
Step 2 → Calculator
```

The execution plan contains only execution logic and never includes natural-language responses.

---

### 3. Tool Results

Each tool produces structured output.

Example

```json
{
  "current_time": "21:35",
  "minutes_until_midnight": 145
}
```

Tool outputs remain machine-readable and independent of presentation.

---

### 4. Conversation Context

The runtime reconstructs the complete conversation for the current session by combining:

- Previous messages
- Current user message
- Tool outputs
- System instructions

This context forms the foundation for prompt generation.

---

### 5. LLM Prompt

The runtime constructs a single prompt containing all information required by the language model.

The provider receives:

- System instructions
- Conversation history
- Tool outputs
- Current user request

The provider remains unaware of how these inputs were produced.

---

### 6. Generated Response

The language model generates a natural-language response.

During streaming, the response exists as a sequence of tokens before becoming a complete assistant message.

---

### 7. Execution Metadata

Alongside the assistant response, the runtime produces metadata describing how the response was generated.

Typical metadata includes:

- Tools executed
- Number of tool invocations
- Execution duration
- Provider information

This metadata improves transparency without affecting the generated response.

---

### 8. Persistence

After generation completes, both the conversation and execution metadata are stored in SQLite.

Persistent storage ensures that conversations can be restored across application restarts.

---

### 9. Frontend Rendering

The frontend receives streamed tokens and execution metadata independently.

It is responsible for:

- Rendering Markdown
- Displaying syntax-highlighted code
- Showing tool badges
- Displaying execution duration
- Updating conversation history

---

# Persistence Architecture

Tarka separates **conversation memory** from **persistent storage** to provide reliable session management while keeping the runtime stateless.

## Persistence Overview

```text
              User Request
                    │
                    ▼
          Load Conversation History
                    │
                    ▼
        SQLite (Persistent Storage)
                    │
                    ▼
      Conversation Memory (In-Memory)
                    │
                    ▼
           Runtime Processing
                    │
                    ▼
        Generate Assistant Response
                    │
                    ▼
        Persist Updated Conversation
                    │
                    ▼
                 SQLite
```

The database acts as the source of truth, while the in-memory conversation exists only for the lifetime of a single request.

---

## Conversation Memory

The `ConversationMemory` component maintains the working context required during request execution.

Responsibilities include:

- Rebuilding conversation history
- Preparing prompt-ready messages
- Maintaining message ordering
- Limiting context size when necessary

Conversation memory is recreated for every request and discarded after the response is generated.

---

## Persistent Storage

SQLite stores all long-term conversation data.

Current Version 1 schema:

```text
messages
├── id
├── session_id
├── role
├── content
└── created_at
```

Each message belongs to exactly one session.

The database enables:

- Conversation restoration
- Sidebar history
- Session switching
- Conversation deletion
- Long-term persistence across application restarts

---

## Session Management

Every conversation is identified using a unique `session_id`.

```text
Session A
├── User
├── Assistant
├── User
└── Assistant

Session B
├── User
└── Assistant
```

Messages are never shared between sessions.

This guarantees complete isolation between independent conversations.

---

## Memory Reconstruction

Instead of keeping all conversations permanently in memory, Tarka reconstructs the working context for every incoming request.

Execution flow:

```text
Request
    │
    ▼
Load Messages
    │
    ▼
Rebuild Conversation Memory
    │
    ▼
Generate Prompt
    │
    ▼
Execute Request
```

This approach ensures that the application remains stateless while preserving complete conversation history.

---

## Why SQLite?

SQLite was selected for Version 1 because it provides:

- Zero external dependencies
- Lightweight deployment
- Reliable ACID transactions
- Fast local storage
- Simple backups
- Minimal operational overhead

As the architecture evolves, the persistence layer can be extended to support databases such as PostgreSQL without affecting higher-level components.

---

## Design Rationale

Separating memory from persistence provides several advantages:

- Runtime components remain stateless.
- Conversation history survives application restarts.
- Session isolation is guaranteed.
- Memory usage remains predictable.
- The persistence layer can evolve independently of the runtime.

This design keeps the execution pipeline simple while providing a reliable foundation for future platform capabilities such as cloud synchronization, authentication, and collaborative workspaces.

---

# Technology Decisions

The technologies used in Tarka were selected to prioritize simplicity, maintainability, extensibility, and developer experience while providing a solid foundation for future growth.

| Technology | Purpose | Reason for Selection |
|------------|---------|----------------------|
| **FastAPI** | Backend API Framework | Asynchronous by default, excellent performance, automatic OpenAPI documentation, and native support for Server-Sent Events (SSE). |
| **React** | Frontend Framework | Component-based architecture with a mature ecosystem and strong community support. |
| **TypeScript** | Frontend Language | Improves maintainability through static typing and better developer tooling. |
| **Vite** | Frontend Build Tool | Extremely fast development server with optimized production builds. |
| **SQLite** | Persistent Storage | Lightweight, serverless database requiring zero external infrastructure while providing reliable ACID transactions. |
| **Ollama** | LLM Provider | Enables local language model execution with provider abstraction for future extensibility. |
| **Server-Sent Events (SSE)** | Response Streaming | Efficient one-way streaming from server to client, ideal for incremental AI response generation. |
| **Rule-Based Planner** | Task Planning | Deterministic, predictable, and easily extensible planning mechanism for Version 1. |
| **Markdown** | Response Rendering | Supports rich text, syntax-highlighted code blocks, tables, and structured AI responses. |

---

## Why a Layered Architecture?

A layered architecture was chosen to ensure that each subsystem has a clearly defined responsibility.

Benefits include:

- Easier maintenance
- Independent testing of components
- Reduced coupling
- Improved scalability
- Simpler debugging
- Clear extension points for future features

Each layer can evolve independently as long as it continues to honor its public interface.

---

## Why Rule-Based Planning?

Version 1 uses a deterministic planner instead of an AI-based planner.

This approach provides:

- Predictable behavior
- Easier debugging
- Faster execution
- Lower operational cost
- Transparent decision-making

As the platform evolves, more sophisticated planning strategies can be introduced without changing the runtime architecture.

---

## Why Server-Sent Events?

Streaming improves the user experience by displaying responses as they are generated instead of waiting for the complete response.

Compared with polling, SSE provides:

- Lower latency
- Reduced network overhead
- Simpler implementation
- Native browser support
- Efficient one-way communication

This makes SSE well suited for AI-powered conversational applications.

---

## Future Technology Evolution

The architecture intentionally isolates technology-specific implementations.

Future upgrades may include:

- PostgreSQL replacing SQLite
- Additional LLM providers
- Cloud-based model hosting
- Plugin-based tool loading
- Distributed persistence
- Authentication providers

These enhancements can be introduced without modifying the core architectural layers, preserving the stability of the overall system.

---

# Extension Points

Tarka is designed to evolve through extension rather than modification. New capabilities should integrate with existing architectural layers instead of introducing new execution paths.

## Adding a New Tool

Tools provide specialized capabilities that can be invoked by the runtime.

To add a new tool:

1. Create a new class extending `BaseTool`.
2. Implement the required interface:
   - `name`
   - `description`
   - `execute()`
3. Register the tool in the Tool Registry.
4. Add matching rules to the Planner.
5. Write unit tests for the tool.

Once registered, the tool becomes available to the planner and runtime without requiring changes to other architectural layers.

---

## Adding a New Language Model Provider

Language model providers implement a common interface, allowing the runtime to remain provider-agnostic.

To add a provider:

1. Create a class extending `BaseLLMProvider`.
2. Implement:
   - `generate()`
   - `generate_stream()`
   - `ping()`
3. Register the provider in the application configuration.
4. Configure any required environment variables.

The runtime communicates only with the provider interface, allowing providers to be swapped without affecting planning, tools, or persistence.

---

## Adding a New API Route

API routes expose new backend capabilities while keeping business logic inside the appropriate architectural layer.

To add a route:

1. Create a router inside `api/routes`.
2. Define request and response schemas.
3. Delegate execution to the appropriate service or runtime component.
4. Register the router with the FastAPI application.
5. Add integration tests.

Routes should remain thin and contain no business logic.

---

## Adding Persistent Data

When introducing new persistent entities:

1. Extend the persistence layer.
2. Define the required database schema.
3. Add repository methods.
4. Keep database access isolated within the persistence module.

Higher-level components should never interact directly with the database.

---

## Adding Frontend Features

Frontend features should focus on presentation and user interaction.

New UI functionality should:

- Consume backend APIs
- Display streamed responses
- Render execution metadata
- Avoid implementing backend business logic

The frontend should remain independent of runtime implementation details.

---

## Architectural Guidelines

When extending Tarka, contributors should follow these principles:

- Prefer extending existing interfaces over modifying them.
- Keep components focused on a single responsibility.
- Maintain clear boundaries between layers.
- Avoid introducing circular dependencies.
- Ensure new features remain testable and modular.
- Preserve backward compatibility whenever practical.

Following these guidelines allows the architecture to scale while remaining predictable, maintainable, and easy to understand.

---

# Architectural Philosophy

The architecture of Tarka is built around a simple principle:

> **Every component should do one thing well, and every new capability should extend the existing architecture rather than replace it.**

The system intentionally separates planning, execution, language model integration, persistence, and presentation into independent layers. This separation allows each subsystem to evolve without introducing unnecessary complexity or tight coupling.

Version 1 establishes a stable architectural foundation focused on deterministic planning, transparent tool execution, persistent conversations, and a responsive user experience. Future versions will expand the platform through additional tools, providers, and intelligent capabilities while preserving the same architectural principles.

As the project grows, contributors are encouraged to:

- Respect the responsibility of each architectural layer.
- Prefer extension over modification.
- Keep interfaces simple and well-defined.
- Design components to be modular and independently testable.
- Maintain clear boundaries between planning, execution, persistence, and presentation.

A well-designed architecture should make future development easier, not more difficult. Every design decision in Tarka aims to improve maintainability, scalability, and developer experience while providing a reliable foundation for long-term evolution.

---

## Document Information

| Property | Value |
|----------|-------|
| Project | Aryntra Tarka |
| Document | Architecture Specification |
| Version | 1.0.0 |
| Status | Stable |
| Last Updated | July 2026 |