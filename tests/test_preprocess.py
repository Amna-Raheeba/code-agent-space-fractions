"""Tests for the preprocessor: synthetic docs plus the two real ones.

The real-document test skips when the documents are not present (in
CI the repo stands alone). Locally it runs against the actual
Architecture_Documentation.md and Architecture_View.md.
"""

import os
from pathlib import Path

import pytest

from agent.preprocess import preprocess

SYNTHETIC_DOC = """# A. Executive Summary
The Tiny Game system is a web-based, interactive learning tool designed to improve spelling skills for third-grade students. The system consists of an intro screen, a main menu, spelling questions, and a results screen.

Chosen architectural style: Monolith
Deployment topology: Cloud-based infrastructure

# B. Traceability & Rationale
| Requirement ID | Short Text | Diagram(s) | Component(s) | Artifact filename(s) | Rationale |
| --- | --- | --- | --- | --- | --- |
| FR-1 | Play game | UseCaseDiagram | GameComponent | openapi.yaml | Lets users play |

# C. Architecture Overview
* GameComponent: responsible for game logic and user interaction
* UserComponent: responsible for user authentication and authorization

# D. Detailed Technical Design
## GameComponent
### Responsibilities & data ownership
The GameComponent is responsible for game logic. It owns the game state data.

### Recommended default stack
* Node.js 18
* Express.js 4
* PostgreSQL 14
* Redis 6
* RabbitMQ 3
* Elasticsearch 7
* OAuth2
* Prometheus 2
* Jenkins 2
* Docker 20
* Terraform 1

Justification: Meets the requirements

### Interface design
#### External APIs
```yml
openapi: 3.0.0
info:
  title: Tiny Game API
  version: 1.0.0
paths:
  /play:
    get:
      summary: Play the game
      responses:
        200:
          description: Game started
          content:
            application/json:
              schema:
                type: object
                properties:
                  gameId:
                    type: integer
                    description: Game ID
```

#### Internal contracts
```proto
syntax = "proto3";
package tinygame;
service GameService {
  rpc Play(PlayRequest) returns (PlayResponse) {}
}
message PlayRequest {
  int32 gameId = 1;
}
message PlayResponse {
  int32 gameId = 1;
}
```

### Data model / schema
```sql
CREATE TABLE games (
  id SERIAL PRIMARY KEY,
  game_state JSONB NOT NULL
);
```

# H. Testing Strategy
## Matrix mapping Unit / Integration / Contract / E2E / Chaos tests to components
| Test Type | GameComponent |
| --- | --- |
| Unit testing | |
| Integration testing | |

# K. Open Questions & Assumptions
## Assumptions
A1: The game will be played by 10 users concurrently
A2: The game will be played for 30 minutes per session

## Unresolved stakeholder questions needing input
* What is the expected user growth rate?
"""

SYNTHETIC_VIEW = """## ScenarioView
1. UseCase — Scenario View: Use Case Diagram
```plantuml
@startuml UseCaseDiagram
actor EndUser as "End User"
usecase "Play Game" as (PlayGame)
EndUser -- (PlayGame)
@enduml
```

## LogicView
2. Object — Logic View: Object Diagram
```plantuml
@startuml ObjectDiagram
participant game1
participant user1
game1 --> user1
@enduml
```
"""


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_preprocess_synthetic_documents(tmp_path):
    doc = _write(tmp_path, "doc.md", SYNTHETIC_DOC)
    view = _write(tmp_path, "view.md", SYNTHETIC_VIEW)
    spec = preprocess(doc, view)

    assert spec["system"]["name"] == "Tiny Game"
    assert spec["system"]["style"] == "monolith"
    assert spec["system"]["deployment"] == "cloud"
    assert spec["system"]["flow"] == [
        "intro screen",
        "main menu",
        "spelling questions",
        "results screen",
    ]
    assert [c["name"] for c in spec["components"]] == [
        "GameComponent",
        "UserComponent",
    ]
    assert spec["components"][0]["owns"] == "game state data"
    assert spec["stack"]["language"] == "Node.js 18"
    assert spec["stack"]["database"] == "PostgreSQL 14"
    assert len(spec["stack"]) == 11
    assert spec["apis"][0] == {
        "method": "GET",
        "path": "/play",
        "summary": "Play the game",
        "response": {"gameId": "integer"},
    }
    assert spec["apis"][1]["service"] == "GameService"
    assert spec["apis"][1]["request"] == {"gameId": "int32"}
    assert spec["data_models"] == [
        {
            "table": "games",
            "columns": [
                {"name": "id", "type": "SERIAL PRIMARY KEY"},
                {"name": "game_state", "type": "JSONB NOT NULL"},
            ],
        }
    ]
    assert [d["name"] for d in spec["diagrams"]] == [
        "UseCaseDiagram",
        "ObjectDiagram",
    ]
    assert spec["requirements"][0]["id"] == "FR-1"
    assert len(spec["assumptions"]) == 2
    assert spec["open_questions"] == ["What is the expected user growth rate?"]
    gaps = spec["input_gaps"]
    assert any("Traceability maps only 1 requirement" in g for g in gaps)
    assert "Test matrix in the doc is empty." in gaps
    assert any("Object diagram uses sequence-diagram syntax" in g for g in gaps)


def test_preprocess_missing_file_raises(tmp_path):
    doc = _write(tmp_path, "doc.md", SYNTHETIC_DOC)
    with pytest.raises(FileNotFoundError):
        preprocess(doc, tmp_path / "missing.md")


def _real_docs_dir():
    candidates = []
    env_dir = os.environ.get("TASK1_DOCS_DIR")
    if env_dir:
        candidates.append(Path(env_dir))
    candidates.append(Path.home() / "workspace" / "goals" / "china-fully-funded-master-s-applications-fall-2027" / "hidden_files" / "task1")
    candidates.append(Path(__file__).resolve().parent.parent.parent)
    for candidate in candidates:
        if (candidate / "Architecture_Documentation.md").is_file() and (
            candidate / "Architecture_View.md"
        ).is_file():
            return candidate
    return None


def test_preprocess_real_documents():
    docs_dir = _real_docs_dir()
    if docs_dir is None:
        pytest.skip("Real architecture documents are not present here.")
    spec = preprocess(
        docs_dir / "Architecture_Documentation.md",
        docs_dir / "Architecture_View.md",
    )

    assert spec["system"]["name"] == "Space Fractions"
    assert spec["system"]["style"] == "microservices"
    assert spec["system"]["deployment"] == "cloud"
    assert len(spec["system"]["flow"]) == 4
    assert [c["name"] for c in spec["components"]] == [
        "GameComponent",
        "QuestionComponent",
        "UserComponent",
    ]
    assert len(spec["stack"]) == 11
    assert spec["stack"]["language"] == "Node.js 18"
    assert len(spec["apis"]) == 2
    assert spec["apis"][0]["method"] == "GET"
    assert spec["apis"][0]["path"] == "/play"
    assert spec["apis"][1]["service"] == "GameService"
    assert spec["apis"][1]["rpc"] == "Play"
    assert len(spec["data_models"]) == 1
    assert spec["data_models"][0]["table"] == "games"
    assert len(spec["data_models"][0]["columns"]) == 2
    assert len(spec["diagrams"]) == 11
    assert [d["name"] for d in spec["diagrams"]] == [
        "UseCaseDiagram",
        "ClassDiagram",
        "ObjectDiagram",
        "StateDiagram",
        "ActivityDiagram",
        "SequenceDiagram",
        "CollaborationDiagram",
        "PackageDiagram",
        "ComponentDiagram",
        "DeploymentDiagram",
        "ContainerDiagram",
    ]
    assert [r["id"] for r in spec["requirements"]] == ["FR-1", "NFR-1", "ASR-1"]
    assert len(spec["assumptions"]) == 2
    assert len(spec["open_questions"]) == 2
    gaps = spec["input_gaps"]
    assert len(gaps) == 4
    assert any("Traceability maps only 3 requirement" in g for g in gaps)
    assert "Test matrix in the doc is empty." in gaps
    assert any("Object diagram uses sequence-diagram syntax" in g for g in gaps)
    assert any("Analysis Plan" in g and "How to review" in g for g in gaps)
