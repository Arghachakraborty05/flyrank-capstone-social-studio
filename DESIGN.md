 # Social Media Studio - Design

## 1. Problem & Scope

### Problem

Social Media Studio turns one blog post into a multiplatform social media campaign.

A user provides a blog post either as a URL or as pasted Markdown. The system stores the source post and treats the stored copy as the single source of truth. Platform-specific variants are generated only from the stored post.

Each variant is validated against the rules of its target platform before it can enter the review workflow. A person can approve, edit, or reject a variant. Only an approved variant can be scheduled.

Approved variants are published at their scheduled time through a common `SocialPublisher` interface. Platform-specific adapters handle the details of communicating with each target platform, while the application business logic depends on the interface rather than a specific platform.

The system records publish attempts and uses an idempotency key for each variant and schedule slot so that repeated processing of the same scheduled publication can be detected and safely ignored.

### Initial Platforms

The initial implementation uses three target platforms:

- **Telegram** - real free publishing target using a Telegram bot.
- **X** - mock adapter only; it records what would be published locally.
- **LinkedIn** - mock adapter only; it records what would be published locally.

X and LinkedIn are not connected to real accounts. The mock adapters demonstrate that the application can support additional platforms without changing the publishing business logic.

### Core Flow

```text
        Blog Post
     (URL / Markdown)
            |
            v
      Ingest + Store
            |
            v
  Stored Source of Truth
            |
            v
    Variant Generation
            |
            v
   Constraint Validation
            |
            v
          Review
(draft -> approved / rejected)
            |
            v
 Schedule Approved Variant
            |
            v
     Durable Scheduler
            |
            v
 SocialPublisher Interface
            |
            +--> TelegramPublisher (real)
            +--> MockXPublisher
            +--> MockLinkedInPublisher
            |
            v
      Publish History
```

### Reliability Goals

The design prioritizes the main reliability requirements of the capstone:

1. An unapproved variant must never be scheduled.
2. Platform constraints must be enforced by application code.
3. Scheduled work must persist so that a worker restart does not lose pending jobs.
4. Publishing must be idempotent for a variant and schedule slot.
5. Publish attempts and their results must be visible in publish history.
6. Publisher implementations must be replaceable without changing business logic.

---

## 2. Platform Constraint Profiles

Each platform has a constraint profile. The application validates a generated or edited variant against the profile before allowing it to continue through the workflow.

The initial profiles are:

| Platform |  Maximum Length |     Tone     | Maximum Hashtags |
|----------|-----------------|--------------|------------------|
| Telegram | 4096 characters |  Informative |         5        |
|    X     | 280 characters  |    Concise   |         3        |
| LinkedIn | 3000 characters | Professional |         5        |

### Enforcement Rules

The following rules are enforced by application code:

1. **Maximum length** - the variant must not exceed the configured maximum character limit.
2. **Hashtag count** - the number of hashtags matching the application's hashtag pattern must not exceed the configured maximum.
3. **Tone structure** - generated variants use platform-specific templates and deterministic structural checks appropriate to the configured tone.

The system does not claim to perform perfect human-level tone classification. Instead, tone is represented through controlled generation structures and simple rules that can be tested and demonstrated.

The initial tone approach is:

- **Telegram:** informative structure with an explanatory body.
- **X:** concise structure with a short body and strict length enforcement.
- **LinkedIn:** professional structure using a clear explanatory format and rejecting configured informal patterns.

Validation occurs before review. If a variant violates a constraint, validation fails and the response identifies the broken rule.

A rule-breaking variant therefore cannot proceed to the review workflow until it passes validation.

---

## 3. SocialPublisher Interface

The application uses one common publisher interface for all target platforms.

The business logic knows only about `SocialPublisher`. It does not directly depend on Telegram, X, or LinkedIn implementations.

The conceptual interface is:

```python
class SocialPublisher(ABC):

    @abstractmethod
    def publish(self, content: str, idempotency_key: str) -> dict:
        raise NotImplementedError
```

### Interface Responsibilities

The `publish` method receives:

- `content` - the already validated social media variant.
- `idempotency_key` - the unique key representing the variant and schedule slot.

The method returns a structured result containing the publication status and, when available, an external publication identifier or preview information.

### Implementations

The interface has at least three implementations:

```text
SocialPublisher
       |
       +-- TelegramPublisher
       |
       +-- MockXPublisher
       |
       +-- MockLinkedInPublisher
```

`TelegramPublisher` sends the message to the configured real Telegram target.

`MockXPublisher` records what would have been published and provides a local preview.

`MockLinkedInPublisher` records what would have been published and provides a local preview.

Adding or replacing a publisher should require changing adapter configuration or adapter registration rather than rewriting campaign, review, scheduling, or business logic.

### Adapter Seam

The publisher interface is intentionally kept separate from:

- post ingestion
- variant generation
- constraint validation
- review
- scheduling
- publish history

The scheduling worker calls the interface and does not contain platform-specific publishing code.

This provides the adapter seam required by the capstone and makes the adapter-swap acceptance probe possible.

---

## 4. Data Model

The system uses SQLite through SQLAlchemy for persistent application data.

### Post

Stores the original blog post.

|       Field       |                Purpose                |
|-------------------|---------------------------------------|
|       `id`        |         Unique post identifier        |
|   `source_type`   |          `url` or `markdown`          |
|   `source_url`    | Original URL when the source is a URL |
| `source_markdown` |         Stored source content         |
|   `created_at`    |          Creation timestamp           |

The stored post is the single source of truth for generation.

### Variant

Stores one platform-specific version of a post.

|     Field    |                     Purpose                     |
|--------------|-------------------------------------------------|
|     `id`     |             Unique variant identifier           |
|   `post_id`  |               Source post reference             |
|  `platform`  |                 Target platform                 |
|   `content`  |                   Variant text                  |
|   `status`   | `draft`, `approved`, `rejected`, or `published` |
| `created_at` |                 Creation timestamp              |
| `updated_at` |            Last modification timestamp          |

A variant belongs to one stored source post and one target platform.

### ScheduleSlot

Represents a scheduled publication.

|       Field       |                   Purpose                    |
|-------------------|----------------------------------------------|
|        `id`       |          Unique schedule identifier          |
|    `variant_id`   |            Variant being scheduled           |
|   `scheduled_at`  |                Publication time              |
| `idempotency_key` | Unique key for the variant and schedule slot |
|     `status`      |         Scheduling/publication state         |
|    `created_at`   |              Creation timestamp              |
|    `updated_at`   |          Last state update timestamp         |

The schedule status will represent states such as `scheduled`, `processing`, `published`, or `failed`.

### PublishAttempt

Records each publication attempt and its result.

|       Field        |                    Purpose                     |
|--------------------|------------------------------------------------|
|        `id`        |           Unique attempt identifier            |
|    `variant_id`    |               Published variant                |
| `schedule_slot_id` |                Related schedule                |
|     `platform`     |                Target platform                 |
|  `idempotency_key` |              Idempotency key used              |
|   `attempted_at`   |               Attempt timestamp                |
|      `status`      |           Success or failure state             |
|    `external_id`   | Platform publication identifier when available |
|   `error_message`  |    Error information when publication fails    |

Publish history provides visible evidence of what the worker attempted and what happened.

### Relationships

```text
 Post
  |
  +----< Variant
            |
            +----< ScheduleSlot
            |           |
            |           +----< PublishAttempt
            |
            +----< PublishAttempt
```

A post can have multiple platform variants.

A variant can have scheduled publication information and associated publish history.

### Persistence and Uniqueness

The implementation should use database constraints where appropriate to protect logical identities.

In particular:

- `ScheduleSlot.idempotency_key` should be unique.
- A successful publication for a logical variant/slot should be uniquely identifiable.
- Publish attempts remain separate records so retry history is not lost.

These constraints complement, rather than replace, application-level idempotency checks.

---

## 5. Review Workflow

Each variant follows a controlled review lifecycle.

```text
             +------------+
             |    draft   |
             +-----+------+
                   |
          +--------+--------+
          |                 |
          v                 v
     +----------+      +----------+
     | approved |      | rejected |
     +----+-----+      +----------+
          |
          v
      scheduled
          |
          v
      published
```

### Allowed Review Actions

A person can:

- approve a draft variant;
- edit a variant;
- reject a variant.

When a variant is edited, the updated content must pass constraint validation before it can be approved.

Only an `approved` variant can be scheduled.

A scheduling request for a `draft` or `rejected` variant must return a 4xx response with a clear error message.

After successful publication, the variant can be marked `published`.

### Review Rules

The review workflow enforces these rules:

1. A generated variant starts as `draft`.
2. Invalid variants never enter review.
3. Editing a variant triggers validation again.
4. Only a valid `draft` can be approved.
5. A rejected variant cannot be scheduled.
6. A draft variant cannot be scheduled.
7. Only an approved variant can be scheduled.
8. Successful publication changes the variant to `published`.
9. Publish history is recorded separately from the variant status.

---

## 6. Scheduling and Idempotency Design

The scheduler is responsible for publishing approved variants at their scheduled time.

The Python implementation will use:

- FastAPI
- APScheduler
- APScheduler persistent job store
- SQLAlchemy
- SQLite

The scheduler must not depend only on in-memory jobs. Scheduled work must be persisted so that a process restart can recover pending jobs.

### Time Handling

The application will use one consistent timestamp convention internally, preferably UTC.

When a schedule is received with a timezone-aware datetime, it will be normalized before storage and before idempotency-key creation.

The API will document the expected datetime format and timezone behavior.

This avoids mixing naive local timestamps with UTC timestamps.

### Idempotency Key

Each schedule slot receives a unique idempotency key based on the variant and normalized scheduled slot.

Conceptually:

```text
variant-{variant_id}-slot-{normalized_scheduled_time}
```

The same variant scheduled for the same logical slot must resolve to the same idempotency key.

Before publishing, the worker checks persistent schedule and publish state using the idempotency key.

If the same logical publication has already completed successfully, the worker must not publish it again.

### Worker Flow

```text
    Find due scheduled slots
               |
               v
      Check variant status
               |
               +---- not approved ----> record/return clear failure
               |
               v
Check idempotency / publish history
               |
               +---- already successful ----> skip duplicate publish
               |
               v
 Claim / mark work as processing
               |
               v
 Get publisher through registry
               |
               v
            Publish
               |
          +----+----+
          |         |
        success   failure
          |         |
          v         v
      published    failed
          |         |
          +----+----+
               |
               v
     Record publish history
```

The worker must be safe to run repeatedly.

### Retry and Crash Handling

The implementation will persist schedule state and publish history so the worker can resume after a process restart.

The acceptance test will intentionally interrupt processing and restart the worker. The expected evidence is:

- the schedule remains persisted;
- the worker can resume;
- no duplicate successful publication is created for the same logical variant and slot;
- publish history remains available;
- failed attempts are visible.

### External Provider Limitation

The application can guarantee its own database-level idempotency and protect against duplicate work that the application can observe.

However, an external provider call and a local SQLite transaction are not one distributed atomic transaction.

For example, Telegram may accept a message and the application may stop before recording the successful result locally. A basic Telegram `sendMessage` operation does not provide a universal exactly-once transaction spanning Telegram and the local database.

Therefore, the project will not falsely claim distributed exactly-once delivery. The README and EVIDENCE will document this limitation honestly.

The acceptance demonstration will focus on the application's persistent idempotency behavior and the strongest retry safety supported by the chosen architecture.

---

## 7. API Surface

The API is implemented with FastAPI.

The initial API surface is:

### Posts

```text
POST /api/posts
```

Create and store a blog post from a URL or pasted Markdown.

The ingestion layer stores the source before generation.

```text
GET /api/posts
```

List stored posts.

```text
GET /api/posts/{post_id}
```

Retrieve one stored source post.

### Variant Generation

```text
POST /api/posts/{post_id}/generate
```

Generate platform-specific variants from the stored source post.

Generation reads only from the stored post and does not use a fresh request payload as an alternate source of truth.

```text
GET /api/posts/{post_id}/variants
```

List variants belonging to a post.

```text
GET /api/variants/{variant_id}
```

Retrieve one variant.

### Review

```text
PUT /api/variants/{variant_id}
```

Edit a variant and validate the updated content.

```text
POST /api/variants/{variant_id}/approve
```

Approve a valid draft variant.

```text
POST /api/variants/{variant_id}/reject
```

Reject a variant.

### Scheduling

```text
POST /api/variants/{variant_id}/schedule
```

Schedule an approved variant for publication.

```text
GET /api/schedules
```

List schedule slots and their current states.

### Publishing History

```text
GET /api/publish-history
```

View publication attempts and their results.

### Supporting Endpoints

The final implementation may add small supporting endpoints required by the demonstration UI, such as:

- health/status
- publisher configuration display
- mock publication preview

Such endpoints will not replace or weaken the core API responsibilities above.

---

## 8. Adapter Registry

Publisher implementations are selected through a registry.

Conceptually:

```text
       Configured Platform
               |
               v
       Publisher Registry
               |
               v
  SocialPublisher implementation
               |
   +-----------+--------------+
   |           |              |
Telegram     Mock X     Mock LinkedIn
```

The registry keeps platform selection separate from campaign and scheduling logic.

For example, changing the configured publisher from `telegram` to `mock_x` should allow the same approved campaign and scheduling workflow to use the mock publisher without changing the business logic.

### Adapter Contract

Each adapter must:

1. implement the `SocialPublisher` interface;
2. accept already validated content;
3. receive the schedule-specific idempotency key;
4. return a structured result;
5. avoid owning review or scheduling decisions.

### Mock Adapter Behavior

Mock X and Mock LinkedIn do not contact the real platforms.

They record:

- platform
- content
- idempotency key
- timestamp
- mock external ID
- simulated result

This gives the project a visible preview/history for those platforms while respecting the capstone rule that X and LinkedIn must remain mock adapters.

---

## 9. Technology Choices

The project uses the Python lane of the capstone.

|       Area      |             Choice             |
|-----------------|--------------------------------|
|    Language     |           Python 3.12          |
|  API framework  |             FastAPI            |
|     Database    |             SQLite             |
|       ORM       |           SQLAlchemy           |
|    Scheduler    |           APScheduler          | 
|   HTTP client   |            Requests            |
|  Configuration  | `.env` / environment variables |
|     Frontend    |  HTML, CSS, vanilla JavaScript |
|  Real publisher |        Telegram Bot API        |
| Mock publishers | Local database-backed adapters |

The project intentionally avoids unnecessary infrastructure such as PostgreSQL, Redis, Kafka, Kubernetes, or microservices.

The goal is a small standalone system that clearly demonstrates correctness, resilience, adapter architecture, review workflow, durable scheduling, idempotency, and publish history.

---

## 10. Security and Secrets

Platform credentials are configuration rather than source code.

Real Telegram credentials will be stored in `.env`.

The repository will contain `.env.example` with safe placeholder values.

The real `.env` file must never be committed.

The application will read credentials from environment variables rather than hard-coding them into Python files.

### Secret Handling Rules

The project must ensure that:

- `.env` is ignored by Git;
- `.env.example` contains placeholders only;
- bot tokens are never committed;
- secrets are not placed in README examples;
- screenshots used for evidence do not expose credentials;
- error responses do not unnecessarily expose secret values.

---

## 11. Explicit Non-Goals

The following are intentionally outside the scope of this capstone:

- Real Instagram publishing
- Real X publishing
- Real LinkedIn publishing
- Image generation
- Social media analytics
- Engagement tracking
- Follower management
- Multi-tenant account management
- Billing or payments
- Complex authentication and authorization
- Distributed microservices
- Large-scale production infrastructure

The project focuses on the core capstone problem:

```text
ingest
  -> store
  -> generate
  -> validate
  -> review
  -> approve
  -> schedule
  -> publish
  -> record history
```

---

## 12. Phase 1 Design Gate

The Phase 1 design gate requires a one-page design covering:

- the problem;
- constraint profiles for each platform;
- the `SocialPublisher` interface signature;
- the data model;
- the API surface;
- at least one explicit non-goal.

This design goes beyond the minimum gate by also documenting the review workflow, scheduler/idempotency approach, adapter registry, technology choices, and secret handling.

### Phase 1 Baseline

The implementation will be built from this design as the baseline.

If implementation discoveries require a design change, the change will be documented in Git rather than silently diverging from the design.

The following implementation phases will map to the capstone brief:

|              Capstone Phase               |                            Implementation Focus                           |
|-------------------------------------------|---------------------------------------------------------------------------|
| Phase 1 - Design                          |                     This document and repository setup                    |
| Phase 2 - Ingestion and generation        |         Stored post, two+ platform variants, constraint validation        |
| Phase 3 - Review                          |           Draft/approved/rejected workflow and scheduling guard           |
| Phase 4 - Adapters and idempotent publish |            Telegram real adapter, X/LinkedIn mocks, idempotency           |
| Phase 5 - Scheduling, history, hardening  | Durable worker, restart/retry proof, publish history, final documentation |

### Acceptance Evidence Mapping

The design anticipates the required acceptance probes:

1. **Ingest and generate**
   - One stored post produces variants for each configured platform.
   - Variants pass their platform constraints.

2. **Bad variant blocked**
   - A deliberately invalid variant is rejected by validation.
   - The response identifies the broken rule.

3. **Unapproved scheduling blocked**
   - A draft/rejected variant receives a 4xx scheduling response.
   - The error clearly states that approval is required.

4. **Approved scheduled publication**
   - An approved Telegram variant is scheduled.
   - The worker publishes it to the real Telegram target.
   - Publish history records the result and external message ID when available.

5. **Retry/restart protection**
   - Worker processing is interrupted and restarted.
   - The same logical schedule is not successfully published twice by the application.
   - Publish history shows the relevant attempt/result records.

6. **Adapter swap**
   - The configured publisher is changed from Telegram to a mock adapter.
   - The same campaign/scheduling flow uses the mock publisher.
   - No business-logic code is changed.

This design therefore provides the architectural baseline for implementing and evidencing all required capstone areas without adding features that are explicitly out of scope.