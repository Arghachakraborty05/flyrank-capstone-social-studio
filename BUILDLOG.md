# Build Log

This log records the development progress, key technical decisions, and use of AI assistance during the development of Social Media Studio.

## Phase 1 — Design and Repository Setup

**Status:** Completed and committed.

- Created the public GitHub repository and initial project configuration.
- Defined the system architecture, data model, API surface, platform constraints, publisher interface, and reliability considerations in `DESIGN.md`.
- Established the implementation roadmap and documented the intended system behavior in `README.md`.

## Phase 2 — Database Layer, Ingestion, and Generation

**Status:** Completed and committed.

- Pinned backend dependencies (`fastapi`, `uvicorn`, `SQLAlchemy`, `APScheduler`, `python-dotenv`, `requests`, `pytest`, `httpx`) in `requirements.txt`.
- Configured SQLite database engine with thread-safe session handling in `app/database.py`.
- Implemented normalized ORM models (`Post`, `Variant`, `ScheduleSlot`, `PublishAttempt`) in `app/models.py` establishing the single source of truth and database-level idempotency constraints.
- Added request/response schemas in `app/schemas.py`, multi-platform variant generation in `app/services/generator.py`, and platform constraint validation in `app/services/constraints.py`.
- Implemented `POST /api/posts` (Markdown and URL ingestion), `POST /api/posts/{post_id}/generate` (multi-platform `draft` variant generation from the stored post), and `POST /api/variants/validate-candidate` (returning HTTP `422` naming violated rules such as `max_hashtags` and `max_length`) in `app/routers/posts.py` and `app/main.py`.
- Added automated verification in `tests/test_phase2.py` confirming distinct platform variants and constraint-violation rejection (`max_hashtags` and `max_length`) via `pytest` in the `socialstudio` environment.

## AI Assistance

AI assistance was used for technical discussion, requirement analysis, implementation planning, design decision support, and documentation structuring. Core implementation, architectural decisions, and test verification were driven directly, with every suggested change reviewed and validated against real execution before committing:

- **Test structure verification:** Confirmed that Phase 2 automated tests should live in a dedicated `tests/` directory (`tests/test_phase2.py`) separate from `app/`, and verified behavior directly by executing `pytest`.
- **Documentation and evidence discipline:** Checked generated documentation wording against the actual codebase so that only implemented Phase 2 endpoints and models are described as complete, while Phases 3–5 and acceptance probes (`AP-01`–`AP-06` in `EVIDENCE.md`) remain explicitly marked pending until end-to-end execution.

## Development Progress

Design, repository setup, core database models, post ingestion, variant generation, constraint validation, and initial automated tests (`tests/test_phase2.py`) have been implemented, verified, and committed. Review workflows, publisher adapter integration, persistent scheduling, crash/restart recovery, and acceptance probe evidence (`AP-01`–`AP-06` in `EVIDENCE.md`) remain pending at this stage. Progress and significant technical decisions will be recorded as the corresponding work is completed.