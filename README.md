# Aryntra Tarka

A clean, modular AI backend framework built for local LLM interaction.

---

## Vision

Before writing any code, it is important to understand **why** this project exists.

A previous repository named **AI System** was created as a proof of concept to validate two fundamental ideas:

- Local Large Language Model (LLM) interaction
- Retrieval-Augmented Generation (RAG)

Those experiments successfully demonstrated that both concepts were technically feasible. However, the implementation remained tightly coupled to the prototype's objectives and was intentionally limited in scope.

**Aryntra Tarka is not a continuation of that repository.**

Instead, it is a **clean architectural reimplementation** inspired by the lessons learned during those experiments.

The objective is to build a modular AI backend where every major subsystem is isolated behind well-defined interfaces. Components such as providers, retrieval, reasoning, memory, planning, and tools should evolve independently without forcing changes throughout the rest of the application.

The architecture should remain maintainable, testable, and extensible as the system grows.

Sprint 0 is therefore **not about AI intelligence**.

Sprint 0 exists solely to establish the architectural foundation upon which every future capability will be built.

---

## Design Principles

The architecture is guided by the following principles:

- Separation of concerns
- Modularity by default
- Replaceable implementations
- Centralized configuration
- Unified logging
- Interface-first design
- Clean, maintainable code
- Incremental development through small milestones

Every implementation decision throughout Sprint 0 should reinforce these principles.

---

## Architectural Vision

```text
                Aryntra Tarka

                      │
                      ▼

            FastAPI Application Layer

                      │
                      ▼

              Provider Abstraction Layer

                      │
          ┌───────────┴───────────┐
          ▼                       ▼

    LLM Providers         Embedding Providers

                      │
                      ▼

           Future Architecture (Later Sprints)

      Retrieval → Planning → Reasoning → Memory
                    ↓
                 Tool Execution
                    ↓
               Intelligent Response

This layered architecture allows each subsystem to evolve independently while preserving a clean separation of responsibilities.

## Sprint 0 Philosophy

Sprint 0 focuses exclusively on establishing infrastructure.

It intentionally avoids implementing:

- Retrieval
- Vector search
- Reasoning
- Planning
- Memory
- Agents
- Tool execution
- Prompt engineering

Those capabilities belong to future milestones.

The goal of Sprint 0 is simple:

Build a backend that future engineers can confidently extend without redesigning its architecture.

The architectural vision is now established.

The next milestone focuses on creating the repository structure that will support this architecture for years to come.
---

# Repository Foundation

With the architectural vision established, the next step is to create a repository structure capable of supporting that vision.

The objective of this milestone is **not** to implement AI functionality. Instead, it is to establish a clean, scalable repository layout that encourages separation of concerns from the very beginning.

Every directory has a clearly defined responsibility. Future contributors should be able to locate functionality intuitively without navigating unrelated modules.

---

## Repository Structure

```text
aryntra-tarka/
│
├── backend/
│   ├── api/                 FastAPI routers and route definitions
│   ├── core/                Core application logic
│   ├── providers/
│   │   ├── llm/             Language model providers
│   │   └── embeddings/      Embedding providers
│   ├── reasoning/           Reasoning engine (future)
│   ├── retrieval/           Retrieval pipeline (future)
│   ├── tools/               Tool execution (future)
│   ├── models/              Shared data models
│   ├── config/              Application configuration
│   ├── utils/               Shared utilities
│   └── main.py              FastAPI entry point
│
├── docs/                    Project documentation
├── tests/                   Test suite
├── scripts/                 Development utilities
├── configs/                 Configuration assets
├── knowledge/               Knowledge sources
│
├── requirements.txt
├── README.md
├── .gitignore
├── .env
└── .gitattributes

## Why This Structure?

The repository is intentionally organized around architectural boundaries rather than implementation details.

Each package owns a single responsibility.

For example:

api exposes HTTP endpoints.
providers communicates with external AI services.
reasoning will contain decision-making logic.
retrieval will manage knowledge retrieval.
config centralizes application configuration.
utils contains reusable infrastructure.

This organization minimizes coupling and allows teams to develop independent modules without interfering with one another.

## Repository Principles

Every new file added to the project should follow these rules:

A directory should own one responsibility.
Business logic should never live inside the API layer.
Infrastructure should remain reusable.
External services should always be accessed through abstractions.
Future components should integrate into the existing structure rather than creating parallel architectures.

Consistency is significantly more valuable than cleverness.

## Foundation Complete

At this point, the repository has a clear architectural layout and is ready to host executable code.

The next milestone brings the project to life by creating the first running FastAPI application and exposing the initial API endpoints.

---

# FastAPI Application Foundation

With the repository structure established, the next objective is to create a running backend application.

This milestone intentionally keeps the application minimal. The purpose is not to implement AI functionality, but to verify that the project's foundation is operational.

A successful backend should be able to start, expose a small API surface, and provide a stable platform for every future subsystem.

---

## Objectives

The application should:

- Start successfully without errors
- Expose a root endpoint
- Expose a health endpoint
- Generate OpenAPI documentation automatically
- Serve Swagger UI for API exploration

At this stage, no AI functionality should exist.

---

## Application Responsibilities

The FastAPI application is responsible only for:

- Creating the application instance
- Registering API routers
- Defining application metadata
- Bootstrapping the backend

Business logic should never be implemented inside the application entry point.

Keeping `backend/main.py` lightweight ensures that future features can be added without turning it into a monolithic file.

---

## Available Endpoints

### Root Endpoint

```text
GET /
```

Returns basic application metadata indicating that the backend is operational.

Example:

```json
{
    "name": "Aryntra Tarka",
    "version": "0.1.0",
    "status": "running"
}
```

---

### Health Endpoint

```text
GET /health
```

Returns the health status of the backend.

Example:

```json
{
    "status": "healthy"
}
```

The health endpoint should remain intentionally simple during Sprint 0.

Dependency checks, provider validation, database connectivity, and external service monitoring will be introduced in later milestones.

---

## Automatic API Documentation

FastAPI automatically generates interactive documentation.

After starting the backend, the following resources should be available:

Swagger UI

```text
http://127.0.0.1:8000/docs
```

OpenAPI Specification

```text
http://127.0.0.1:8000/openapi.json
```

These endpoints provide immediate visibility into the API surface and greatly simplify future development and testing.

---

## Design Philosophy

The application layer should never contain business rules.

Instead, it serves as the entry point that delegates work to specialized modules.

As Aryntra Tarka evolves, additional responsibilities such as middleware, authentication, lifecycle management, and dependency injection will be added without disrupting this architectural principle.

---

## Foundation Complete

The backend can now start successfully and expose a minimal but production-oriented API.

With an executable application in place, the next milestone introduces two foundational infrastructure services that every future component will rely upon:

- Centralized configuration
- Unified logging

These services will become the backbone of the entire application.

---

# Configuration & Logging Infrastructure

A running application is only the beginning.

As software grows, two infrastructure services become essential:

- Configuration
- Logging

Rather than allowing every module to manage these independently, Aryntra Tarka centralizes both responsibilities from the very beginning.

This approach improves consistency, maintainability, and observability across the entire application.

---

## Centralized Configuration

Configuration should have a single source of truth.

Application settings such as environment, host, port, provider selection, and feature flags should never be scattered throughout the codebase.

Instead, all configuration is loaded once and exposed through a dedicated configuration layer.

This provides several benefits:

- Consistent configuration access
- Easier validation
- Simpler testing
- Cleaner dependency management
- Environment-specific customization

No module outside the configuration package should access environment variables directly.

Every component should receive configuration through this centralized layer.

---

## Unified Logging

Logging is one of the most valuable tools for understanding how a system behaves.

Instead of using `print()` statements throughout the project, Aryntra Tarka uses a centralized logging system.

Every module should rely on the same logger so that log output remains consistent regardless of which component generated it.

The logging infrastructure is responsible for recording:

- Application startup
- General information
- Warnings
- Errors
- Debug information (during development)

As the project grows, this logging system will become invaluable for debugging, monitoring, and production diagnostics.

---

## Separation of Responsibilities

The interaction between these foundational services can be visualized as follows:

```text
                FastAPI Application
                        │
          ┌─────────────┴─────────────┐
          ▼                           ▼
Configuration Service          Logging Service
          │                           │
          └─────────────┬─────────────┘
                        ▼
             Future Application Modules
```

Neither configuration nor logging should contain business logic.

Instead, they provide reusable infrastructure that every other subsystem can depend upon.

---

## Architectural Principles

The following rules apply throughout the project:

- Configuration is loaded once.
- Environment variables are never accessed directly outside the configuration layer.
- Logging is centralized.
- Application code should never rely on `print()` for operational messages.
- Infrastructure remains independent of business logic.

Following these principles ensures that every future subsystem behaves consistently.

---

## Foundation Complete

At this stage, Aryntra Tarka possesses the essential infrastructure expected from a modern backend application.

The project now has:

- A structured repository
- A running FastAPI application
- Centralized configuration
- Unified logging

The next milestone introduces provider abstractions that decouple the application from specific AI implementations while preserving the clean architecture established so far.

---

# Provider Abstraction Architecture

With the application's foundation established, the next objective is to introduce provider abstractions.

This milestone represents the first interaction with AI-related architecture, but **not** AI intelligence itself.

The goal is to ensure that the rest of the application never communicates directly with a specific provider such as Ollama or a particular embedding library.

Instead, every interaction passes through well-defined interfaces.

---

## Why Provider Abstractions?

Modern AI systems evolve rapidly.

Language models, embedding engines, and inference providers change frequently.

If the application communicates directly with a specific implementation, replacing that implementation later becomes difficult and error-prone.

By introducing abstraction layers, Aryntra Tarka remains flexible and future-proof.

The application depends on **capabilities**, not **technologies**.

---

## High-Level Architecture

```text
                Application Layer
                        │
                        ▼
             Provider Abstraction Layer
                        │
        ┌───────────────┴───────────────┐
        ▼                               ▼
   LLM Provider Interface      Embedding Provider Interface
        │                               │
        ▼                               ▼
 Ollama Provider          Local Embedding Provider
```

The application never communicates with Ollama directly.

Instead, it interacts only with provider interfaces.

Concrete implementations remain isolated behind the provider layer.

## Language Model Providers

Language model providers are responsible for interacting with conversational AI models.

Their responsibilities include:

Accepting prompts
Sending requests to the configured provider
Receiving responses
Returning standardized results

Business rules, reasoning logic, and prompt engineering do not belong inside provider implementations.

Providers are responsible only for communication.

## Embedding Providers

Embedding providers generate numerical vector representations of text.

These vectors will later support retrieval, semantic search, and knowledge indexing.

At this stage, providers expose only the capability to generate embeddings.

Vector databases, indexing, and retrieval pipelines remain outside their scope.

## Provider Factories

The application should never instantiate providers directly.

Instead, provider factories determine which implementation should be used.

This provides several advantages:

Provider implementations become interchangeable.
Configuration determines the active provider.
Future integrations require minimal code changes.
Testing becomes significantly easier.

As additional providers are introduced, only the factory requires awareness of the available implementations.

## Design Principles

Every provider implementation should follow these rules:

One provider, one responsibility.
No business logic.
No application-specific behavior.
Configuration-driven initialization.
Replaceable without affecting application code.

Following these principles ensures that the provider layer remains stable even as underlying AI technologies evolve.

## Architectural Benefits

By introducing provider abstractions early, Aryntra Tarka gains several long-term advantages:

Vendor independence
Improved maintainability
Cleaner testing
Reduced coupling
Easier future integrations
Consistent application architecture

These benefits become increasingly valuable as the project grows beyond a single provider.

## Foundation Complete

The architectural backbone of Aryntra Tarka is now complete.

The project contains:

A modular repository
A running FastAPI application
Centralized configuration
Unified logging
Provider abstraction architecture

The final milestone focuses on documentation, verification, and preparing the repository for future development.

---

# Sprint 0 Completion

Sprint 0 establishes the architectural foundation of Aryntra Tarka.

Unlike feature-focused development, this sprint intentionally concentrates on infrastructure, maintainability, and long-term scalability.

No advanced AI capabilities have been implemented yet.

Instead, the objective has been to build a backend that future engineers can confidently extend without redesigning its core architecture.

Every decision made during Sprint 0 has been guided by one principle:

> Build the foundation once. Build features on top of it forever.

---

## What Has Been Implemented

At the conclusion of Sprint 0, the project includes:

- A clean and modular repository structure
- A production-oriented FastAPI application
- Automatic OpenAPI specification generation
- Interactive Swagger documentation
- Centralized configuration management
- Unified application logging
- Language model provider abstractions
- Embedding provider abstractions
- Provider factory architecture
- Development environment configuration
- Comprehensive project documentation

These components collectively establish the foundation required for future AI capabilities.

---

## Verification Checklist

Sprint 0 is considered complete when the following conditions are satisfied:

- Repository clones successfully.
- Python dependencies install without errors.
- Virtual environment activates correctly.
- Configuration loads successfully.
- Logging initializes successfully.
- FastAPI starts without errors.
- Root endpoint responds correctly.
- Health endpoint responds correctly.
- Swagger documentation is accessible.
- OpenAPI specification is generated.
- Provider abstractions initialize correctly.
- Project structure remains modular and maintainable.

Meeting these requirements confirms that the project is ready for feature development.

---

## Current Architecture

```text
                    User Request
                         │
                         ▼
                FastAPI Application
                         │
                         ▼
                   API Router Layer
                         │
                         ▼
              Configuration & Logging
                         │
                         ▼
              Provider Abstraction Layer
              ┌────────────────────────┐
              │                        │
              ▼                        ▼
      LLM Provider             Embedding Provider
              │                        │
              └──────────────┬─────────┘
                             ▼
                    External AI Services
```

This architecture intentionally separates infrastructure from business logic.

Future modules will integrate into this structure rather than modifying it.

## Looking Ahead

With the architectural foundation complete, future sprints can focus entirely on intelligent capabilities.

Upcoming work includes:

Knowledge ingestion
Retrieval pipelines
Vector indexing
Semantic search
Prompt management
Reasoning engine
Planning engine
Memory systems
- Tool execution
Multi-step workflows

Each of these systems will integrate into the architecture established during Sprint 0 without requiring structural redesign.

## Project Philosophy

Aryntra Tarka is being developed with long-term maintainability as a primary objective.

The project emphasizes:

Clear architectural boundaries
Modular design
Interface-first development
Replaceable implementations
Incremental delivery
Comprehensive documentation
Clean engineering practices

Every future contribution should strengthen these principles rather than compromise them.

## Conclusion

Sprint 0 marks the completion of the project's foundation.

The repository now provides a stable, extensible, and maintainable backend architecture capable of supporting increasingly sophisticated AI functionality in future development phases.

The focus now shifts from building infrastructure to building intelligence.

Welcome to Sprint 1.
