# Space Fractions

Web-based, interactive learning tool to improve fraction-solving skills for
sixth-grade students. Implemented as a set of microservices per the
architecture specification.

## Overview

| Component | Responsibilities | Owns |
|-----------|------------------|------|
| `GameComponent` | game logic, user interaction | game state data |
| `QuestionComponent` | question management, data persistence | question data |
| `UserComponent` | user authentication, authorization | user data |

The system flow is: introductory movie → main menu → fraction questions →
ending scene with feedback.

## Stack

- **Language**: Node.js 18
- **Framework**: Express.js 4
- **Database**: PostgreSQL 14
- **Cache**: Redis 6
- **Messaging**: RabbitMQ 3
- **Search**: Elasticsearch 7
- **Auth**: OAuth2
- **Observability**: Prometheus 2
- **CI**: Jenkins 2
- **Containers**: Docker 20
- **Infra**: Terraform 1

## Project layout

```
output/
├── package.json              # dependency manifest + scripts
├── openapi.yaml              # FR-1 artifact (GET /play)
├── proto/internal.proto      # NFR-1 artifact (GameService.Play gRPC)
├── sql/
│   ├── games_ddl.sql         # games table (exact data model from spec)
│   ├── question_ddl.sql      # ASR-1 artifact (questions table)
│   └── users_ddl.sql         # users table
├── src/
│   ├── shared/               # config + cache/messaging/search/metrics wrappers
│   ├── game-component/       # GameService, GameState, HTTP app, server
│   ├── question-component/   # QuestionService, stores, HTTP app, server
│   └── user-component/       # AuthService (OAuth2), HTTP app, server
├── tests/                    # Jest + Supertest suites
├── docker-compose.yml        # local service + data-service orchestration
├── Dockerfile                # multi-service Node 18 image
├── Jenkinsfile               # CI pipeline
└── terraform/                # Terraform 1 cloud infra (illustrative)
```

## Running

Install dependencies and run tests:

```sh
npm install
npm test
```

Start a single service:

```sh
node src/game-component/server.js
node src/question-component/server.js
node src/user-component/server.js
```

Or run the full stack with Docker Compose:

```sh
docker compose up --build
```

## APIs

- `GET /play` → `200 { "gameId": <int32> }` (creates/continues a game session)
- `GameService.Play` gRPC (`proto/internal.proto`), request/response
  `{ gameId: int32 }`
- Additional HTTP endpoints: `/game/:gameId/score`, `/game/:gameId/pause`,
  `/game/:gameId/resume`, `/game/:gameId/gameover`, `GET|POST|PUT|DELETE /questions`,
  `POST /questions/:id/check`, `GET /login`, `GET /oauth/callback`, `GET /me`.

Each service exposes `/healthz` and `/metrics` (Prometheus).

## Data models

The architecture's `data_models` section defines exactly one table:

```sql
CREATE TABLE games (
  id SERIAL PRIMARY KEY,
  game_state JSONB NOT NULL
);
```

This is reproduced verbatim in `sql/games_ddl.sql`.

## Notes on specification gaps / decisions

The following items are **not** fully specified by the architecture document and
are either left as stubs or derived from the diagrams, as noted:

1. **`questions` and `users` tables** — The `data_models` section only defines
   the `games` table, but requirement `ASR-1` references `sql/question_ddl.sql`
   and `QuestionComponent` owns "question data". `sql/question_ddl.sql` and
   `sql/users_ddl.sql` derive their columns (`id`, `prompt`, `options` and
   `id`, `username`) from the `ClassDiagram` classes `Question` and `User` so
   persistence responsibilities can be fulfilled. No other column definitions
   exist in the spec.
2. **Answer correctness** — The `Question` class exposes only `id`, `prompt`,
   and `options`; the spec does not define a "correct answer" field. The
   `checkAnswer` method therefore only validates that a submitted option index
   is within bounds. Correct/incorrect evaluation is intentionally undefined.
3. **OAuth2** — Auth wiring is a stub. `AuthService` provides the
   authorization-code flow entry points and a bearer-token middleware with an
   injectable token verifier; the default verifier (`user:<id>`) is for local
   development/tests only and must be replaced with real OAuth2 token
   introspection in production.
4. **External dependencies** — Redis/RabbitMQ/Elasticsearch/PostgreSQL clients
   are wired through lazily-initialized wrappers in `src/shared/`. Services run
   with in-memory stores by default so they start and test without those
   services; production wiring (PostgreSQL store, cache, messaging) is provided
   and enabled via `docker-compose.yml`/environment.
5. **Input gaps flagged in the spec** remain unaddressed here: the empty test
   matrix, the traceability map covering only 3 requirements, and the Object
   diagram using sequence-diagram syntax. The diagrams are not embedded in this
   repository (they are represented by the code they describe).
6. **Open questions** (user growth rate, expected session length) are not
   encoded anywhere; the stated assumptions (1000 concurrent users, 1-hour
   sessions) were not used to change any implementation behaviour.

## Requirements traceability (from the spec)

| ID | Text | Diagram | Component | Artifact |
|----|------|---------|-----------|----------|
| FR-1 | Play game | UseCaseDiagram | GameComponent | openapi.yaml |
| NFR-1 | Performance | SequenceDiagram1 | GameComponent | internal.proto |
| ASR-1 | Data durability | DeploymentDiagram | QuestionComponent | sql/question_ddl.sql |

## Use cases → endpoints

| Use case (from the diagrams) | Endpoint | Status |
|---|---|---|
| Play Game | `GET /play` | Implemented — defined in the spec |
| View Score | `GET /game/:gameId/score` | Implemented — designed from the diagrams |
| Update Questions | `POST /questions`, `PUT /questions/:id`, `DELETE /questions/:id` | Implemented — designed from the diagrams |
| View Help | — | Not implemented: the diagrams name this use case, but the documents define no help content or route for it |

## Generation record

This project was generated by a simplified Code Agent built for this task,
from `Architecture_Documentation.md` and `Architecture_View.md`.
Model: deepseek-v4-pro (DeepSeek official API), thinking mode disabled.
Generation run: 24 turns; 528,905 prompt tokens (520,832 cached) and
25,283 completion tokens. Real measured cost from server-reported usage:
**$0.1337** (the agent's budget cap was $0.90; the task limit is $1).
Verified after generation: `npm install` clean, 29 Jest tests pass, and the
services run end to end (add question → check answer → play → score →
game over).
