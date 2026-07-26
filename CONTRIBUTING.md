# Contributing to Aryntra Tarka

Thank you for your interest in contributing to **Aryntra Tarka**.

Whether you're fixing a bug, improving documentation, or implementing a new feature, your contributions are greatly appreciated.

---

# Before You Start

Before contributing, please:

- Search existing issues before creating a new one.
- For significant changes, open an issue first to discuss the proposed approach.
- Respect the existing project architecture and coding standards.
- Keep pull requests focused on a single feature or fix.

---

# Development Setup

## Clone the Repository

```bash
git clone https://github.com/aryntra/tarka.git
cd tarka
```

---

## Backend Setup

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r backend/requirements.txt
```

---

## Frontend Setup

```bash
cd frontend

npm install
```

---

# Running the Application

## Backend

From the project root:

```bash
uvicorn backend.main:app --reload --port 8000
```

---

## Frontend

```bash
cd frontend

npm run dev
```

The application will be available at:

```
http://localhost:5173
```

---

# Running Tests

## Backend

```bash
pytest tests/ -v
```

---

## Frontend

```bash
npm run lint
```

Before submitting a pull request, ensure that all backend tests and frontend checks pass successfully.

---

# Pull Request Guidelines

Please follow these guidelines when contributing:

1. Fork the repository.
2. Create a feature branch.

```bash
git checkout -b feat/your-feature
```

3. Keep commits small and focused.
4. Write meaningful commit messages.
5. Update documentation whenever behavior changes.
6. Ensure all tests pass.
7. Open a Pull Request targeting the `main` branch.

---

# Commit Message Convention

Examples:

```text
feat: add weather tool

fix: correct streaming disconnect handling

docs: update architecture diagram

refactor: simplify planner rule matching

test: add memory pruning edge case
```

Use clear, concise commit messages describing **what changed**, not how long it took.

---

# Code Style

## Python

- Follow **PEP 8**
- Use type annotations for all public functions
- Write docstrings for public classes and methods
- Prefer small, focused functions
- Keep business logic separate from API routes

---

## TypeScript / React

- Functional components only
- Explicit prop interfaces
- Avoid `any`
- Prefer composition over duplication
- Keep components reusable and focused

---

# Architecture Boundaries

Every contribution should respect the existing architecture.

| Layer | Responsibility |
|--------|----------------|
| API Routes | HTTP handling only (no business logic) |
| Agent Services | High-level orchestration |
| Planner | Intent analysis and execution planning |
| Runtime | Tool execution pipeline |
| Tools | One capability per tool |
| Providers | LLM communication only |
| Persistence | Conversation storage |
| Frontend | User interface and interaction |

Do **not** bypass architectural layers when implementing new features.

---

# Version 1 Scope

The following areas are considered complete for **Version 1**:

- Multi-tool planning
- Streaming responses
- Persistent conversations
- SQLite persistence
- Execution transparency
- Responsive interface
- Session management

Bug fixes and documentation improvements are always welcome.

---

# Version 2 Ideas

The following features are intentionally **out of scope** for Version 1:

- File upload and document understanding
- Web search
- Retrieval-Augmented Generation (RAG)
- Authentication
- Cloud synchronization
- Voice interface
- Plugin ecosystem
- Image understanding

Please discuss these ideas before beginning implementation.

---

# Reporting Bugs

When reporting a bug, please include:

- Operating System
- Python version
- Node.js version
- Browser (if applicable)
- Steps to reproduce
- Expected behavior
- Actual behavior
- Relevant logs or screenshots

Providing detailed reports helps resolve issues more quickly.

---

# Feature Requests

Feature requests should include:

- Problem being solved
- Proposed solution
- Alternative approaches considered
- Potential architectural impact

Large features should be discussed through an issue before implementation.

---

# License

By contributing to this project, you agree that your contributions will be licensed under the **MIT License**.

---

<div align="center">

Thank you for helping improve **Aryntra Tarka**.

Every contribution—whether code, documentation, testing, or feedback—helps make the project better.

</div>