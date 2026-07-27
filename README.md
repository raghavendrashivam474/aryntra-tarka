<div align="center">

<img src="docs/assets/logo.png" alt="Aryntra Tarka" width="96"/>

# Aryntra Tarka

### Transparent Local-First AI Agent

Build AI applications that **plan**, **reason**, **invoke tools**, and **stream responses** with complete execution transparency.

Built with **FastAPI**, **React**, **TypeScript**, **SQLite**, and **Ollama**.

**Version:** v1.0.0 • **Status:** Stable

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-Latest-009688?style=flat-square)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)

**[Quick Start](#quick-start) • [Architecture](docs/ARCHITECTURE.md) • [Documentation](#documentation)**

<img src="docs/assets/screenshot-conversation.png" width="900"/>

</div>

---

# What is Tarka?

Aryntra Tarka is a **local-first autonomous AI agent** that converts natural language requests into structured execution plans.

Instead of forwarding prompts directly to a language model, Tarka:

- Understands the user's intent
- Builds an execution plan
- Invokes the required tools
- Collects execution results
- Streams the final response
- Persists conversation history

The architecture is modular, transparent, and designed for long-term extensibility.

---

# Features

- 🧠 Autonomous multi-step planning
- 🛠 Transparent tool execution
- ⚡ Real-time streaming responses (SSE)
- 💾 Persistent conversation history
- 🤖 Local AI powered by Ollama
- 📦 Modular layered architecture
- 🔌 Provider abstraction
- 🚀 Extensible tool registry

---

# Architecture Overview

```text
User
   │
   ▼
Planner
   │
   ▼
Runtime
   │
   ├── Tool Registry
   ├── Memory
   └── LLM Provider
          │
          ▼
      Final Response
```

The complete architecture, execution flow, and design decisions are documented in:

**docs/ARCHITECTURE.md**

---

# Built-in Tools

| Tool | Purpose |
|------|---------|
| Calculator | Mathematical calculations |
| Date & Time | Current date and time |
| Filesystem | File and directory operations |

The Tool Registry is fully extensible, allowing additional tools to be added without modifying the Runtime.

---

# Screenshots

### Home

![Home](docs/assets/home.png)

### Conversation

![Conversation](docs/assets/conversation.png)

### Tool Execution

![Tool Execution](docs/assets/tool-badges.png)

### Settings

![Settings](docs/assets/settings.png)

---

# Technology Stack

| Layer | Technology |
|--------|------------|
| Backend | FastAPI |
| Frontend | React + TypeScript + Vite |
| AI Provider | Ollama |
| Database | SQLite |
| Streaming | Server-Sent Events |
| Styling | Tailwind CSS |

---

# Quick Start

## Prerequisites

- Python 3.11+
- Node.js 18+
- Git
- Ollama

## Clone

```bash
git clone https://github.com/<username>/aryntra-tarka.git
cd aryntra-tarka
```

## Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

## Ollama

```bash
ollama pull llama3.2
ollama serve
```

Open:

```
http://localhost:5173
```

---

# Documentation

Detailed documentation is available inside the `docs/` directory.

| Document | Purpose |
|----------|---------|
| `docs/ARCHITECTURE.md` | System architecture |
| `docs/DEPLOYMENT.md` | Deployment guide |
| `docs/ROADMAP.md` | Future plans |
| `CONTRIBUTING.md` | Contribution guide |
| `CHANGELOG.md` | Release history |

---

# Roadmap

## Completed

- ✅ Autonomous planning
- ✅ Local-first AI
- ✅ Tool execution
- ✅ SQLite persistence
- ✅ Streaming responses

## Planned

- 🚧 Web Search
- 🚧 Retrieval-Augmented Generation (RAG)
- 🚧 File Understanding
- 🚧 Plugin System
- 🚧 Multi-provider Support
- 🚧 Voice Interaction

---

# Contributing

Contributions are welcome.

You can help by:

- Reporting bugs
- Improving documentation
- Adding new tools
- Suggesting features
- Opening pull requests

Please read `CONTRIBUTING.md` before contributing.

---

# License

Released under the **MIT License**.

See the `LICENSE` file for details.

---

# About the Developer

**Raghavendra Singh**

Computer Science student passionate about AI systems, backend engineering, developer tools, and privacy-first software.

Building the **Aryntra** ecosystem—modular, local-first software designed for transparency and long-term maintainability.

### Connect

- GitHub: https://github.com/raghavendrashivam474
- LinkedIn: https://www.linkedin.com/in/raghavendra-singh-2335292ab/
- Portfolio: https://evolution-portfolio.vercel.app

---

<div align="center">

**Transparent AI. Local First. Built for Developers.**

Made with ❤️ by **Raghavendra Singh**

</div>
