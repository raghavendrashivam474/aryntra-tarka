<div align="center">

<img src="docs/assets/logo.png" alt="Aryntra Tarka" width="80" />

# Aryntra Tarka

**Autonomous Multi-Tool AI Agent**

[![Version](https://img.shields.io/badge/version-1.0.0-6366f1?style=flat-square)](CHANGELOG.md)
[![Sprint](https://img.shields.io/badge/sprint-3.11-22c55e?style=flat-square)](docs/sprints/)
[![License](https://img.shields.io/badge/license-MIT-white?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-3b82f6?style=flat-square)](https://python.org)
[![React](https://img.shields.io/badge/react-18-61dafb?style=flat-square)](https://react.dev)

[Demo](#demo) · [Quick Start](#quick-start) · [Architecture](docs/ARCHITECTURE.md) · [Contributing](CONTRIBUTING.md)

<img src="docs/assets/screenshot-conversation.png" alt="Tarka Screenshot" />

</div>

---

# What is Tarka?

Tarka is a production-ready autonomous AI agent that can **plan**, **reason**, and **execute multi-tool tasks** through a clean, responsive chat interface.

Ask a question. Tarka plans the approach, selects the appropriate tools, executes them in sequence, and streams back a coherent response while transparently showing how the answer was produced.

---

# Features

| Capability | Status |
|------------|--------|
| Multi-tool Planning | ✅ |
| Streaming Responses | ✅ |
| Persistent Conversations | ✅ |
| Execution Transparency | ✅ |
| Tool Execution Badges | ✅ |
| Syntax Highlighting | ✅ |
| Session History Sidebar | ✅ |
| Responsive Interface | ✅ |
| Copy & Regenerate | ✅ |
| SQLite Persistence | ✅ |

---

# Demo

Example interaction

```text
You:
Calculate 125 × 48 and save the result to notes.

Tarka:
✓ Calculator
✓ Filesystem

125 × 48 = 6000

The calculation has been completed and the result has been saved successfully.
```

---

# Quick Start

## Prerequisites

- Python 3.11+
- Node.js 18+
- OpenAI or Anthropic API Key

---

## 1. Clone Repository

```bash
git clone https://github.com/aryntra/tarka.git
cd tarka
```

---

## 2. Backend Setup

```bash
cd backend

python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

cp ../.env.example .env
```

Edit `.env`

```env
OPENAI_API_KEY=your_api_key
```

Run backend

```bash
uvicorn main:app --reload --port 8000
```

---

## 3. Frontend Setup

Open another terminal

```bash
cd frontend

npm install

cp .env.example .env
```

Edit `.env`

```env
VITE_API_URL=http://localhost:8000
```

Run frontend

```bash
npm run dev
```

---

## 4. Open in Browser

```
http://localhost:5173
```

---

# Screenshots

| View | Asset |
|------|-------|
| Home / Empty State | `docs/assets/home.png` |
| Conversation | `docs/assets/conversation.png` |
| Tool Badges | `docs/assets/tool-badges.png` |
| Code Rendering | `docs/assets/code-rendering.png` |
| Sidebar | `docs/assets/sidebar.png` |

---

# Architecture

```text
                     Browser
               (React + Vite)
                      │
             HTTP / REST / SSE
                      │
                      ▼
          FastAPI Application Server
                      │
      ┌───────────────┴───────────────┐
      │                               │
   Planner                      Conversation Memory
      │                               │
      └───────────────┬───────────────┘
                      ▼
                 Agent Runtime
                      │
               Tool Registry
      ┌─────────┼─────────┬─────────┐
      │         │         │         │
 Calculator  DateTime  Filesystem  Future Tools
                      │
                  SQLite Storage
```

For additional details see:

- `docs/ARCHITECTURE.md`

---

# Deployment

## Frontend (Vercel)

```bash
cd frontend
npx vercel --prod
```

Configure

```env
VITE_API_URL=https://your-backend.onrender.com
```

---

## Backend (Render)

1. Connect GitHub repository.
2. Render automatically detects `render.yaml`.
3. Configure environment variables.

```env
OPENAI_API_KEY=your_api_key
ALLOWED_ORIGINS=https://your-frontend.vercel.app
```

Complete deployment guide:

```
docs/DEPLOYMENT.md
```

---

# Project Structure

```text
tarka/
│
├── backend/
│   ├── main.py
│   ├── planner/
│   ├── runtime/
│   ├── tools/
│   ├── memory/
│   ├── persistence/
│   ├── api/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── constants/
│   │   └── App.tsx
│   ├── package.json
│   └── vercel.json
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DEPLOYMENT.md
│   ├── CHANGELOG.md
│   ├── ROADMAP.md
│   ├── sprints/
│   └── assets/
│
├── .env.example
├── render.yaml
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

---

# Technology Stack

| Layer | Technology |
|--------|------------|
| Backend | FastAPI |
| Frontend | React + TypeScript + Vite |
| AI Providers | OpenAI / Anthropic |
| Database | SQLite |
| Streaming | Server-Sent Events (SSE) |
| Styling | Tailwind CSS |
| Markdown | react-markdown |
| Syntax Highlighting | react-syntax-highlighter |

---

# Roadmap

## Version 1.0

- ✅ Multi-tool Planning
- ✅ Streaming Responses
- ✅ Persistent Memory
- ✅ SQLite Persistence
- ✅ Transparent Tool Execution
- ✅ Modern Chat UI
- ✅ Responsive Interface

## Future (Version 2)

- File Understanding
- Web Search
- Retrieval-Augmented Generation (RAG)
- Plugin Ecosystem
- Authentication
- Voice Interface
- Image Understanding

---

# Contributing

Contributions are welcome.

Please read:

```
CONTRIBUTING.md
```

before submitting a pull request.

---

# License

MIT License

See:

```
LICENSE
```

---

<div align="center">

### Aryntra Tarka

**Version 1.0.0**

Autonomous Multi-Tool AI Agent

Built with ❤️ using FastAPI, React, TypeScript, and SQLite.

</div>