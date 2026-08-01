Aryntra Tarka — v1.5.0 Milestone Report
To: Senior Engineering
From: Raghav
Date: 01 August 2026
Status: Ready for review · pending tag

Summary
v1.5.0 completes the Plugin SDK milestone.

Aryntra Tarka now supports dynamic extension without modifying runtime code. New capabilities can be added by dropping a plugin file into backend/plugins/ — no changes to the planner, runtime, registry, or API required.

The milestone was delivered in 6 logical commits with zero regressions in existing chat, streaming, memory, or Command Center functionality.

Objectives Achieved
Objective    Status
Plugin SDK core (base, registry, loader)    ✅
Bridge to existing agent tool system    ✅
Dynamic plugin discovery    ✅
Planner integration    ✅
REST API surface    ✅
Frontend runtime inspector    ✅
Live end-to-end verification    ✅
Zero regressions    ✅
Architecture Delivered
text

User
  ↓
Frontend  (Plugins page, Chat, Command Center)
  ↓
REST API  (/api/plugins, /api/chat, /api/runtime)
  ↓
AgentRuntime
  ↓
Planner  ── injected registry, plugin-aware routing
  ↓
PlanExecutor
  ↓
ToolRegistry
  ↓
   ┌───────────────┐
   │               │
BaseTool       PluginAdapter
(built-ins)    (wraps PluginBase)
                   ↓
              PluginBase
              (SDK contract)
Key architectural decision: the agent runtime speaks only BaseTool. The Plugin SDK speaks only PluginBase. A single adapter (PluginAdapter) bridges the two. Neither side needed modification.

Deliverables
Backend
text

backend/runtime/plugins/
    base.py         PluginBase abstract interface
    registry.py     Plugin storage + lookup
    loader.py       Dynamic filesystem discovery

backend/agent/tools/
    plugin_adapter.py     Bridges PluginBase → BaseTool
    plugin_bootstrap.py   Wires plugins into agent registry

backend/api/routes/
    plugins.py     REST endpoints (GET, POST)

backend/plugins/
    calculator/    Example (skipped: built-in wins)
    filesystem/    Example (skipped: built-in wins)
    weather/       Example (loaded successfully)
Frontend
text

frontend/src/
    pages/PluginsPage.tsx           Runtime Tools inspector
    types/plugins.ts                Plugin type definitions
    services/api.ts                 Plugin API client methods
    components/TopBar.tsx           Puzzle icon nav link
    constants/version.ts            Version bumped to 1.5.0
    components/VersionFooter.tsx    Cosmetic character fix
API Surface
Method    Path    Purpose
GET    /api/plugins/    List installed plugins
GET    /api/plugins/all    List all tools with built_in flag
POST    /api/plugins/execute    Execute any tool by name
The execute endpoint accepts both { tool, arguments } (future-proof) and { plugin, input } (backward-compatible) — chosen deliberately so the API is not coupled to the internal architecture.

Verification
Live end-to-end chat query:

User: current temperature of delhi
Runtime: planner → weather plugin → structured result → LLM composition
Response: "The current temperature in Delhi is 20 degrees Celsius."
Duration: 36.7s (Ollama local inference)

Planner routing (7/7 pass):

calculator, datetime, filesystem, weather, LLM-direct — all correctly routed
Weather intent detects natural phrasing ("Is it raining in New York?")
Location extraction from prepositions ("in Tokyo", "for London")
Plugin API smoke tests (5/5 pass):

List plugins, list all tools, execute weather (new naming), execute weather (backward-compat naming), execute built-in calculator via same endpoint
Regression check:

Chat streaming — verified working
Command Center live sync — verified working
Session persistence — verified working
Existing built-in tools — verified working
Commit Sequence
text

3358a62  refactor(runtime): Sprint 3.21.1 live sync polish       (leftover cleanup)
ab8f05f  feat(runtime):    add Plugin SDK core                   (foundation)
aff80d4  feat(agent):      bridge Plugin SDK into agent tool system  (integration)
de0efad  feat(planner):    plugin-aware routing with weather intent  (intelligence)
92f6315  feat(api):        plugin management endpoints           (transport)
f11a96d  feat(frontend):   Runtime Tools inspector + v1.5.0 polish  (visibility)
Each commit is self-contained and independently revertable.

Design Principles Applied
Single Responsibility — each module has one job
Open/Closed — runtime is closed to modification, open to plugins
Duck Typing over Inheritance — plugin discovery uses attribute presence, not issubclass() (necessary because dual import paths break identity checks)
Backward Compatibility — existing tools untouched; API accepts old and new naming
Fail Safe — missing plugin degrades to LLM response, never crashes
Zero Coupling — Plugin SDK has no dependency on the agent layer
Known Limitations
Weather plugin uses mock data — real API integration deferred (design intentional: proves SDK works before adding external dependencies)
Plugin hot-reload not supported — requires server restart
No plugin manifest validation — planned for v1.6
Tests are ad-hoc — no pytest suite for plugin flows yet (planned)
Recommended Next Steps
Before starting v2.0:

Tag v1.5.0 in git
Draft ARCHITECTURE.md capturing the current stable design
Freeze codebase for a short architecture review
Then begin v2.0 — the Context Engine
v2.0 Preview — Context Engine
v1.5 answered "How does the runtime execute?"
v2.0 answers "How does the runtime remember?"

The runtime loop evolves from:

text

Plan → Execute → Done
to:

text

Remember → Reason → Plan → Execute → Reflect → Learn → Remember
This is the point where Aryntra Tarka begins to feel like an intelligence runtime rather than an execution engine.

Verdict
v1.5.0 is the point where Aryntra Tarka graduates from a hackathon prototype into a real platform foundation. The architecture is now extensible without accumulating debt. Every subsequent milestone (memory, distributed execution, multi-agent workflows) can be added without breaking what already exists.

Ready for tag.

— Raghav

