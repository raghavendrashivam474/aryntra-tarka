# Tarka Engineering Backlog

**Document Version:** 1.0  
**Created:** Sprint 3.1  
**Status:** Active  
**Owner:** Tarka Development Team

---

# Purpose

The Engineering Backlog serves as the single source of truth for all confirmed bugs,
technical debt, usability improvements, and future enhancements identified during
the development of Tarka.

This document ensures that:

- Every confirmed issue is documented before implementation begins.
- Developers work from an organized engineering backlog rather than memory.
- Future work remains traceable across sprints.
- Bug fixes and enhancements are prioritized consistently.
- No known issue is lost between releases.

This document is maintained throughout the lifetime of the project.

---

# Scope

This backlog includes:

- Confirmed software defects
- Planner improvements
- Prompt engineering improvements
- CLI usability improvements
- Technical debt
- Future architectural enhancements
- Long-term engineering tasks

This backlog does **not** include:

- Product roadmap
- Sprint reports
- Architecture documentation
- Feature specifications
- User documentation

---

# Development Workflow

Every engineering task should follow the workflow below.

```text
Issue Discovered
        │
        ▼
Document in BACKLOG.md
        │
        ▼
Assign Priority
        │
        ▼
Assign Sprint
        │
        ▼
Implementation
        │
        ▼
Regression Testing
        │
        ▼
Documentation Update
        │
        ▼
Resolved
```

No issue should be implemented before being documented.

---

# How to Use This Backlog

- Every sprint begins by selecting work from this backlog.
- Every newly discovered issue must first be documented here.
- Update the issue status whenever work begins or completes.
- Do not delete resolved issues.
- Preserve engineering history for future reference.

---

# Priority Definitions

| Priority | Meaning |
|----------|----------|
| High | Blocks usability or produces incorrect behaviour |
| Medium | Degrades user experience but does not block functionality |
| Low | Minor issue that can be fixed later |
| Future Enhancement | Planned capability rather than a software defect |

---

# Status Definitions

| Status | Meaning |
|---------|----------|
| Open | Confirmed but not yet started |
| In Progress | Currently being implemented |
| Resolved | Fix completed and verified |
| Deferred | Intentionally postponed |

---

# Issue Template

Every issue should follow the structure below.

```text
ISSUE-ID

Title

Priority

Category

Status

Owner

Description

Current Behaviour

Expected Behaviour

Reproduction Steps

Examples

Notes
```

---

# Engineering Backlog

---

# Section 1 — High Priority Bugs

---

## ISSUE-001

### Title

Planner fails to detect short DateTime requests

**Priority:** High

**Category:** Planner

**Status:** Open

**Owner:** Unassigned

---

### Description

The planner does not recognise short or casual DateTime requests.

When users submit inputs such as

- Time?
- Date and time
- What time is it

the planner fails to route the request to the DateTime Tool.

Instead, the request falls back to the LLM, which attempts to answer using its own knowledge.

This may result in stale or incorrect time information.

---

### Current Behaviour

Planner fails to invoke the DateTime Tool.

The LLM produces the response.

---

### Expected Behaviour

Any request asking for the current date, time, day, or related information should invoke the DateTime Tool regardless of wording.

---

### Reproduction Steps

1. Launch REPL or FastAPI.
2. Send:

```
Time?
```

3. Observe planner behaviour.
4. Notice DateTime Tool is not invoked.

---

### Example Inputs

```
Time?
Date and time
Current time
What time is it
```

---

### Notes

Planner keyword matching requires broader DateTime intent coverage.

---

## ISSUE-002

### Title

REPL commands are processed by the LLM instead of a local dispatcher

**Priority:** High

**Category:** CLI

**Status:** Open

**Owner:** Unassigned

---

### Description

Commands intended for controlling the REPL are currently treated as conversational input.

Instead of being handled locally, they are passed into the planner and eventually the LLM.

Examples include

```
clear
cls
help
exit
quit
version
```

---

### Current Behaviour

Planner receives REPL commands.

LLM attempts to respond conversationally.

---

### Expected Behaviour

A dedicated command dispatcher should intercept supported REPL commands before planner execution.

---

### Reproduction Steps

1. Launch REPL.
2. Enter

```
clear
```

3. Observe planner activity.

---

### Notes

Command Dispatcher should become the first stage of REPL processing.

---

# Section 2 — Medium Priority Bugs

---

## ISSUE-003

### Title

LLM expresses uncertainty after successful tool execution

**Priority:** Medium

**Category:** Prompt Engineering

**Status:** Open

**Owner:** Unassigned

---

### Description

After a successful tool execution, the LLM occasionally behaves as though an error occurred.

Examples include

> Let me try again.

> I think I made a mistake.

even when the tool returned the correct result.

---

### Current Behaviour

Tool succeeds.

LLM expresses unnecessary uncertainty.

---

### Expected Behaviour

Successful tool executions should produce confident responses.

Uncertainty should only appear after genuine execution failures.

---

### Reproduction Steps

1. Execute

```
Multiply 14 by 17
```

2. Observe calculator result.

3. Observe generated response.

---

### Notes

Likely requires prompt refinement and explicit success signalling.

---

# Section 3 — Low Priority Bugs

No low-priority issues have been identified.

This section will expand as testing continues.

---

# Section 4 — Future Enhancements

---

## ISSUE-004

### Title

Conversation context is not retained between requests

**Priority:** Future Enhancement

**Category:** Memory

**Status:** Deferred

**Owner:** Unassigned

---

### Description

Tarka currently processes every request independently.

No conversation memory exists.

As a result, follow-up questions cannot reference earlier interactions.

---

### Current Behaviour

```
Multiply 14 by 17

↓

Please double check.
```

Second request loses previous context.

---

### Expected Behaviour

Session memory enables follow-up references to previous interactions.

---

### Notes

Requires dedicated Memory Layer.

Should not be solved through planner modifications.

---

## ISSUE-005

### Title

Planner cannot execute multiple tools within a single request

**Priority:** Future Enhancement

**Category:** Planner

**Status:** Deferred

**Owner:** Unassigned

---

### Description

Current planner selects a single tool.

Compound requests requiring multiple tools are only partially completed.

---

### Example

```
What's today's date and calculate 25 × 8
```

Current

Only one tool executes.

Future

DateTime Tool executes.

Calculator Tool executes.

Results are merged into a unified response.

---

### Notes

Requires orchestration layer above the current planner.

---

# Planned Sprint Allocation

| Sprint | Planned Work |
|---------|--------------|
| Sprint 3.2 | Planner improvements |
| Sprint 3.3 | CLI command dispatcher |
| Sprint 3.4 | Prompt engineering improvements |
| Sprint 3.x | Session memory |
| Future | Multi-tool orchestration |

---

# Regression Policy

Every resolved issue must satisfy the following requirements:

- Original issue reproduced successfully
- Fix verified manually
- Regression test added
- Documentation updated
- Changelog updated
- Issue status changed to **Resolved**

No issue should be closed without verification.

---

# Definition of Done

An issue is considered complete only when:

- Implementation finished
- Manual testing passed
- Regression testing passed
- Documentation updated
- Changelog updated
- Issue marked **Resolved**

---

# Backlog Summary

| ID | Title | Priority | Category | Status |
|----|--------|----------|----------|--------|
| ISSUE-001 | Planner fails to detect short DateTime requests | High | Planner | Open |
| ISSUE-002 | REPL commands processed by the LLM | High | CLI | Open |
| ISSUE-003 | LLM expresses uncertainty after successful tool execution | Medium | Prompt Engineering | Open |
| ISSUE-004 | Conversation context not retained between requests | Future Enhancement | Memory | Deferred |
| ISSUE-005 | Planner cannot execute multiple tools | Future Enhancement | Planner | Deferred |

---

# Revision History

## Version 1.0 — Sprint 3.1

- Initial Engineering Backlog created.
- Added confirmed Sprint 2 testing issues.
- Added future enhancement tracking.
- Established engineering workflow.
- Defined issue lifecycle.
- Added regression policy.
- Added Definition of Done.

---