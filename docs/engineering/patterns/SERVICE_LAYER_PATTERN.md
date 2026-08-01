# Service Layer Pattern

> **Project:** Aryntra Tarka
>
> **Version:** 1.0
>
> **Status:** Active
>
> **Category:** Engineering Pattern

---

# Purpose

This document defines the Service Layer Pattern used throughout the Aryntra Tarka ecosystem.

The Service Layer isolates business logic and external system communication from plugins, allowing capabilities to evolve independently while preserving runtime stability.

Every plugin interacting with external systems should implement a dedicated service layer.

---

# Motivation

A plugin should coordinate execution—not perform business logic or communicate directly with external systems.

Without a service layer, responsibilities become mixed, resulting in:

- Tight coupling
- Difficult testing
- Poor maintainability
- Provider lock-in
- Runtime instability

The Service Layer addresses these problems by separating execution from implementation.

---

# Responsibilities

The Service Layer is responsible for:

- Business logic
- External API communication
- Request construction
- Response parsing
- Retry logic
- Timeout handling
- Provider-specific processing
- Data normalization

The Service Layer is **not** responsible for:

- Runtime orchestration
- Planning
- User interaction
- Plugin registration
- Response formatting

---

# Architecture

```
Plugin

↓

Service Layer

↓

Provider Adapter (optional)

↓

External Provider
```

The plugin delegates execution to the service layer.

The service layer owns implementation details.

---

# Why This Pattern Exists

Plugins should remain stable.

Business logic changes frequently.

External providers change even more frequently.

Separating these responsibilities minimizes the impact of future changes.

---

# Example Evolution

## Initial Implementation

```
Plugin

↓

Open-Meteo
```

Simple, but tightly coupled.

---

## Improved Architecture

```
Plugin

↓

Weather Service

↓

Open-Meteo
```

The plugin becomes independent of provider details.

---

## Future Architecture

```
Plugin

↓

Weather Service

↓

Weather Provider

↓

Open-Meteo
```

or

```
Plugin

↓

Weather Service

↓

Weather Provider

↓

Tomorrow.io
```

Only the provider implementation changes.

---

# Design Principles

A Service Layer should:

- Expose a simple interface
- Hide implementation details
- Return structured models
- Translate provider errors
- Avoid leaking provider-specific schemas

It should behave as a stable abstraction over external systems.

---

# Communication Rules

Plugins communicate **only** with services.

Services communicate **only** with providers or external systems.

Providers never communicate directly with plugins.

This keeps dependency flow unidirectional.

```
Plugin

↓

Service

↓

Provider

↓

External API
```

---

# Error Handling

The Service Layer owns provider failures.

Examples include:

- Network errors
- API failures
- Authentication failures
- Timeouts
- Invalid responses

These should be translated into structured internal errors before returning to the plugin.

Raw provider exceptions should never cross architectural boundaries.

---

# Data Transformation

External APIs rarely expose the schema required by the runtime.

The Service Layer should:

- Parse provider responses
- Validate required fields
- Normalize values
- Remove provider-specific details
- Return platform-standard models

The runtime should never depend on external API formats.

---

# Configuration

Service Layers should obtain configuration through the project's configuration system.

Examples include:

- API keys
- Base URLs
- Request timeouts
- Retry policies

Configuration should never be hardcoded.

---

# Testing

The Service Layer should be independently testable.

Recommended tests include:

- Successful execution
- Timeout handling
- Invalid responses
- Provider failures
- Data transformation
- Retry behaviour

Business logic should not require the plugin layer to be tested.

---

# Benefits

Using a Service Layer provides:

- Clear separation of concerns
- Easier maintenance
- Independent testing
- Provider flexibility
- Reduced plugin complexity
- Improved long-term scalability

---

# Common Mistakes

Avoid:

❌ HTTP requests inside `tool.py`

❌ Provider-specific parsing inside plugins

❌ Returning raw provider responses

❌ Embedding API configuration inside plugin code

❌ Mixing orchestration with business logic

---

# Real-World Validation

This pattern has been validated through the Weather Plugin.

Key observations:

- Moving HTTP communication into the Service Layer simplified the plugin.
- Upgrading from a demo implementation to live weather required changes only inside the service implementation.
- Future provider replacements can be localized without affecting the runtime.

These results demonstrate the effectiveness of the Service Layer Pattern.

---

# Future Applications

This pattern should be reused across future capabilities, including:

- Maps
- GitHub
- Docker
- Email
- Calendar
- Browser
- Search
- Memory
- Travel

Each capability should isolate external communication behind its own dedicated service layer.

---

# Closing Statement

The Service Layer Pattern is a foundational architectural pattern within Aryntra Tarka.

By separating business logic and provider communication from plugin orchestration, the platform remains modular, maintainable, and capable of evolving through isolated changes rather than widespread architectural modifications.