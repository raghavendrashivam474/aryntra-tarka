# Changelog

All notable changes to Aryntra Tarka are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

---

## [1.0.0] - Sprint 3.11 - Release Candidate

### Added
- Responsive layout with mobile drawer sidebar
- TopBar with hamburger menu on mobile
- EmptyState with sample prompts
- Settings page with theme, data management, and about section
- AboutDialog with version metadata
- VersionFooter in sidebar
- Sidebar extracted as standalone component with event-based communication
- useConversations hook for Settings page
- Version constants (version.ts)
- Backend version endpoint (GET /api/version)
- react-router-dom routing (/, /settings)
- CHANGELOG, CONTRIBUTING, LICENSE, ROADMAP
- Deployment config: vercel.json, render.yaml
- Environment variable documentation (.env.example)
- docs/ARCHITECTURE.md
- docs/DEPLOYMENT.md
- docs/ROADMAP.md
- docs/DEMO_SCRIPT.md
- docs/FEATURE_CHECKLIST.md
- Sprint 3.11 regression suite

### Fixed
- App version bumped to 1.0.0 across all files
- Vite dev server port corrected to 5173
- ChatWindow inline sidebar replaced by Layout component

---

## [0.10.0] - Sprint 3.10 - Transparency

### Added
- Execution metadata on every response
- Tool badges displayed on assistant messages
- Duration (ms) shown alongside tool badges
- ExecutionMetadata schema in chat.py

---

## [0.9.0] - Sprint 3.9 - Persistence

### Added
- SQLite conversation storage via ConversationPersistence
- Session restore on page reload
- GET /api/chat/history/{session_id}
- GET /api/chat/sessions
- DELETE /api/chat/sessions/{session_id}
- Session-scoped memory isolation (Sprint 3.9.2)

---

## [0.8.0] - Sprint 3.8 - Streaming

### Added
- POST /api/chat/stream SSE endpoint
- Token-by-token streaming display in frontend
- generate_stream() on OllamaLLMProvider
- Streaming status indicators

---

## [0.6.0] - Sprint 3.6 - Multi-Tool Planning

### Added
- Planner collects ALL matching rules (not just first)
- ExecutionPlanStep for per-tool parameters
- Multi-tool prompt builder in Runtime
- Parallel tool badge display

---

## [0.5.0] - Sprint 3.5 - Memory

### Added
- ConversationMemory with configurable message cap
- History injected into planner prompts
- Memory pruning (oldest messages dropped first)

---

## [0.2.0] - Sprint 3.2 - Planner

### Added
- Rule-based Planner
- ExecutionPlan schema
- Tool routing by intent pattern
- Calculator and DateTime tool matching

---

## [0.1.0] - Foundation

### Added
- FastAPI backend
- React + TypeScript + Vite frontend
- Ollama LLM provider
- Basic chat interface
- Tool registry and base tool interface
- SQLite database layer
