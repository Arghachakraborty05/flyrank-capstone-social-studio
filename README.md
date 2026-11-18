# Social Media Studio

A backend-focused social media campaign system that turns one stored blog post into platform-specific social media variants, validates platform constraints, supports human review, schedules approved variants, and publishes through interchangeable social publisher adapters.

> **Implementation status:** Phase 1 (design and repository setup) and Phase 2 (database layer and core ORM models) are completed and committed. Application routes, variant generation, scheduling, and acceptance evidence are being implemented phase by phase. This README distinguishes planned behavior from behavior that has actually been implemented and verified.

## Project goals

The project demonstrates the core backend engineering requirements in the FlyRank Backend AI Engineering capstone:

- Source ingestion and persistence, with the stored post as the single source of truth.
- Platform-specific content variants and application-enforced constraints.
- Human review, including edit, approve, and reject actions.
- A common `SocialPublisher` interface with a real Telegram adapter and mock X/LinkedIn adapters.
- Idempotent scheduling and publication processing.
- Durable scheduling and recovery after a worker restart.
- Persistent publish-attempt history and evidence for the required acceptance probes.
- Safe handling of credentials and a clear record of AI assistance in `BUILDLOG.md`.

See [`DESIGN.md`](DESIGN.md) for the full architecture, data model, API surface, reliability approach, and acceptance mapping.

## End-to-end workflow

```text
      Blog post URL or pasted Markdown
                    |
                    v
             Ingest and store
                    |
                    v
            Stored source post
                    |
                    v
            Generate variants
                    |
                    v
           Validate constraints
                    |
                    v
               Human review
                /        \
            Approved    Rejected
               |
               v
        Durable scheduler
               |
               v
    SocialPublisher interface
       /       |         \
 Telegram    Mock X     Mock LinkedIn
  (real)  (local only)  (local only)
       \       |        /
               v
        Publish history
```

All generation must use the stored source post. Invalid content must be blocked before review. Only approved variants may be scheduled. Publisher-specific API calls belong in adapters, not in campaign or scheduling business logic.

## Initial platform constraint profiles

These are the initial design profiles. The application must enforce the configured rules in code; a table in documentation alone is not enforcement.

| Platform | Maximum content length | Intended tone | Maximum hashtags |                         Publishing mode                           |
|----------|------------------------|---------------|------------------|-------------------------------------------------------------------|
| Telegram |     4096 characters    |  Informative  |        5         | Real Telegram Bot API target owned/controlled by the project user |
|    X     |      280 characters    |    Concise    |        3         |                  Mock only; no real X publishing                  |
| LinkedIn |     3000 characters    |  Professional |        5         |               Mock only; no real LinkedIn publishing              |

The implementation uses deterministic templates and testable structural checks for tone. It does not claim perfect human-level tone classification. A failed validation must identify the specific rule that was broken, such as maximum length, hashtag count, or a configured tone-structure rule. Editing a variant must trigger validation again.

## Architecture and design

### Publisher contract

The shared publisher contract is designed around the following method:

```python
class SocialPublisher(ABC):
    @abstractmethod
    def publish(self, content: str, idempotency_key: str) -> dict:
        raise NotImplementedError
```

The application will call the interface through a publisher registry. `TelegramPublisher` performs real publishing to a configured Telegram target. `MockXPublisher` and `MockLinkedInPublisher` persist local mock results and previews without contacting those platforms. Switching the configured adapter should not require changing campaign, review, or scheduling business logic.

### Planned persistent records

|      Record      |                                            Purpose                                                |
|------------------|---------------------------------------------------------------------------------------------------|
|      `Post`      |     Stores source type, source URL when applicable, stored source content, and creation time.     |
|     `Variant`    |                  Stores platform-specific content and review/publication status.                  |
|  `ScheduleSlot`  |          Stores the scheduled time, state, and unique idempotency key for a variant/slot.         |
| `PublishAttempt` | Records attempts, outcome, error information, and external or mock publication ID when available. |

SQLite and SQLAlchemy will persist application data. APScheduler with a persistent job store will preserve scheduled work across restarts. Schedule timestamps will use a consistent UTC convention, and the normalized schedule time will be used when deriving an idempotency key.

### Review and scheduling rules

- A newly generated valid variant starts as `draft`.
- A person can edit, approve, or reject a variant.
- Edited content is validated again.
- Only a valid, approved variant can be scheduled.
- Scheduling a draft or rejected variant must return a 4xx response with a clear explanation.
- Successful publication updates the variant and creates persistent publication history.
- Reprocessing the same logical variant and schedule slot must not create a second successful publication within the application's observable state.

### Important delivery limitation

A Telegram API call and a local SQLite transaction cannot be committed as one distributed atomic operation. Telegram may accept a message immediately before the application stops, leaving the local process uncertain about the result. The project will document this boundary honestly and will not claim universal exactly-once delivery across Telegram and SQLite. Tests and evidence will describe the retry guarantees actually demonstrated by the implementation.

## Planned API surface

The API will be built with FastAPI. The following endpoints are the design baseline; they are **planned**, not claimed to be available in the current design-only repository.

| Method |                Endpoint               |                  Responsibility                   |
|--------|---------------------------------------|---------------------------------------------------|
| `POST` | `/api/posts`                          | Ingest and store a URL or pasted Markdown source. |
| `GET`  | `/api/posts`                          | List stored posts.                                |
| `GET`  | `/api/posts/{post_id}`                | Retrieve a stored source post.                    |
| `POST` | `/api/posts/{post_id}/generate`       | Generate variants from the stored source.         |
| `GET`  | `/api/posts/{post_id}/variants`       | List variants for a post.                         |
| `GET`  | `/api/variants/{variant_id}`          | Retrieve a variant.                               |
| `PUT`  | `/api/variants/{variant_id}`          | Edit content and revalidate it.                   |
| `POST` | `/api/variants/{variant_id}/approve`  | Approve a valid draft.                            |
| `POST` | `/api/variants/{variant_id}/reject`   | Reject a variant.                                 |
| `POST` | `/api/variants/{variant_id}/schedule` | Schedule an approved variant.                     |
| `GET`  | `/api/schedules`                      | List schedule slots and states.                   |
| `GET`  | `/api/publish-history`                | View publication attempts and results.            |

FastAPI's interactive API documentation is expected at `/docs` when the application is running. The actual run command and URL will be recorded here after the application entry point is implemented and verified.

## Technology stack

- Python 3.12
- FastAPI
- SQLite and SQLAlchemy
- APScheduler with a persistent SQLAlchemy job store
- Requests for HTTP calls
- Environment variables loaded from `.env`
- Telegram Bot API for real publishing
- Database-backed mock adapters for X and LinkedIn
- HTML, CSS, and vanilla JavaScript for a small demonstration interface

The project intentionally avoids PostgreSQL, Redis, Docker, React, microservices, billing, analytics, and other infrastructure that is not required for the capstone.

## Repository status and planned phases

|               Phase             |                                  Scope                                     |     Completion evidence     |
|---------------------------------|----------------------------------------------------------------------------|-----------------------------|
| 1 - Design and repository setup | Public repository, environment template, ignore rules, architecture design | `DESIGN.md` and Git history |
| 2 - Ingestion and generation    | Ingest URL/Markdown, persist source, generate at least two platform variants, enforce constraints | One stored post generates different variants; invalid content is blocked with a named rule |
| 3 - Review workflow             | Draft/approved/rejected states, edit/revalidate, approve/reject, scheduling guard | An unapproved variant cannot be scheduled; a valid approved variant can be scheduled |
| 4 - Adapters and idempotency    | `SocialPublisher`, real Telegram, mock X and LinkedIn, duplicate protection | Real Telegram message; repeated logical publication protection; adapter swap without business-logic changes |
| 5 - Scheduling, history, and hardening | Persistent scheduler, restart/retry behavior, history, final documentation | Worker restart evidence, no duplicate successful app-level publication, recorded attempts and outcomes |

The design stage, database layer and core ORM models are implemented and committed. Remaining application routes, automated tests, and the seed workflow are being implemented phase by phase. `EVIDENCE.md` tracks acceptance probes, and `BUILDLOG.md` records development progress and AI assistance. Planned functionality is not considered complete until fully implemented and verified.

## Setup and run

### Current repository state

The repository contains the design baseline, project configuration, and the core database layer (`app/database.py`, `app/models.py`). A fully runnable FastAPI application entry point and route modules are actively being added phase by phase. Therefore, there is not yet a verified application start command or sample-data seed command to give. Commands such as `uvicorn app.main:app --reload` or `python -m app.seed` must not be treated as working until the corresponding modules and seed workflow have been implemented and tested.

### Run instructions to be completed during implementation

Once the application and seed workflow exist, this section will contain exact, tested instructions for:

1. Python 3.12 setup and dependency installation.
2. Creating a local `.env` from `.env.example` and configuring Telegram credentials if real publishing is being tested.
3. Starting the application and opening `/docs`.
4. Seeding sample data with one explicit command.
5. Running automated tests and the acceptance probes.

The final capstone README will replace this note with the actual commands and expected outputs before submission. This avoids giving strangers commands that do not match code in the repository.

## Configuration and secrets

- Keep real credentials in a local `.env` file.
- Commit only `.env.example` with safe placeholder values.
- Ensure `.env` is ignored by Git.
- Never hard-code or commit bot tokens.
- Never include credentials in screenshots, test output, or evidence transcripts.
- Error responses and logs must not disclose secret values.

A real Telegram test requires a bot token and a Telegram destination that the bot is allowed to post to. The mock X and LinkedIn adapters require no real platform credentials.

## Testing and acceptance evidence

`EVIDENCE.md` will capture the actual test names, commands, outputs, API transcripts, and logs for each required probe. The evidence will cover:

1. Ingesting one source and generating valid variants for the configured platforms.
2. Blocking a deliberately invalid variant and naming its broken rule.
3. Returning a clear 4xx response when scheduling an unapproved variant.
4. Scheduling an approved Telegram variant and recording the live result and external ID when available.
5. Interrupting and restarting worker processing and checking persistent schedule/history state and duplicate protection.
6. Switching to `mock_x` and publishing through the same workflow without changing business logic.

Only results actually observed from the implementation will be recorded as passing. A test that has not run or an acceptance probe that has not been demonstrated will be marked pending or failed, not described as successful.

## AI-use and build log

`BUILDLOG.md` will record implementation progress, meaningful decisions, where AI assistance was used, mistakes or incorrect suggestions, and how those were checked or corrected. AI-generated code will be reviewed and tested; AI use will not be presented as proof that a feature works.

## Explicit non-goals

- Real publishing to X, LinkedIn, or Instagram.
- Image generation.
- Social analytics or engagement tracking.
- Follower management.
- Multi-tenant account management, billing, or payments.
- Complex authentication and authorization.
- Distributed microservices or large-scale production infrastructure.

## Documentation

- [`DESIGN.md`](DESIGN.md) - detailed architecture and phase/acceptance design.
- [`EVIDENCE.md`](EVIDENCE.md) - acceptance probes and their verification status.
- [`BUILDLOG.md`](BUILDLOG.md) - development progress, technical decisions, and AI assistance.

## License

No license has been selected yet. Unless a license is added to the repository, reuse and redistribution are not explicitly granted.
