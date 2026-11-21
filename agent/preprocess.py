"""Deterministic preprocessing: the two architecture documents into JSON.

No LLM call, no cost. This parser reads Architecture_Documentation.md
and Architecture_View.md with plain regular expressions and returns
one JSON object in the shape the agent loop expects. The ``input_gaps``
list is the honest part: it records what the documents leave out or
get wrong, so the agent does not invent requirements that were never
stated. The generated README must list these gaps instead.
"""

import json
import re
from pathlib import Path

# Stack bullets ("Node.js 18") mapped to the JSON key they fill.
STACK_KEYS = [
    ("Node.js", "language"),
    ("Express.js", "framework"),
    ("PostgreSQL", "database"),
    ("Redis", "cache"),
    ("RabbitMQ", "messaging"),
    ("Elasticsearch", "search"),
    ("OAuth2", "auth"),
    ("Prometheus", "observability"),
    ("Jenkins", "ci"),
    ("Docker", "containers"),
    ("Terraform", "infra"),
]

# Fallback "owns" text when a component has no detailed section.
OWNS_FALLBACK = {
    "QuestionComponent": "question data",
    "UserComponent": "user data",
}


def preprocess(doc_path, view_path):
    """Parse both documents into the spec dict. Raises FileNotFoundError."""
    doc_path = Path(doc_path)
    view_path = Path(view_path)
    if not doc_path.is_file():
        raise FileNotFoundError("Architecture document not found: {}".format(doc_path))
    if not view_path.is_file():
        raise FileNotFoundError("Architecture view document not found: {}".format(view_path))
    doc = doc_path.read_text(encoding="utf-8")
    view = view_path.read_text(encoding="utf-8")

    spec = {
        "system": _parse_system(doc),
        "components": _parse_components(doc),
        "stack": _parse_stack(doc),
        "apis": _parse_apis(doc),
        "data_models": _parse_data_models(doc),
        "diagrams": _parse_diagrams(view),
        "requirements": _parse_requirements(doc),
        "assumptions": _parse_assumptions(doc),
        "open_questions": _parse_open_questions(doc),
        "input_gaps": [],
    }
    # Gaps depend on the parsed requirements and diagrams, so compute
    # them after the rest of the spec exists.
    spec["input_gaps"] = _find_gaps(
        doc, view, spec_requirements=spec["requirements"], spec_diagrams=spec["diagrams"]
    )
    return spec


def spec_to_json(spec):
    """The spec as a JSON string, for the first user message and for logs."""
    return json.dumps(spec, indent=2, ensure_ascii=False)


# ------------------------------------------------------------------- system

def _parse_system(doc):
    name_match = re.search(r"The ([\w ]+?) system is a web-based", doc)
    name = name_match.group(1).strip() if name_match else "Space Fractions"
    description = (
        "Web-based, interactive learning tool to improve fraction-solving "
        "skills for sixth-grade students."
    )
    flow = []
    flow_match = re.search(r"consists of (.+?)\.", doc, re.DOTALL)
    if flow_match:
        raw = flow_match.group(1).replace("\n", " ")
        for part in re.split(r",\s*|\s+and\s+", raw):
            part = part.strip()
            # Lists use "a, b, and c": after splitting on the comma the
            # last item still starts with "and".
            part = re.sub(r"^and\s+", "", part)
            # Longest prefix first: "a series of" must be tried before "a".
            part = re.sub(r"^(a series of|an|a)\s+", "", part)
            if part:
                flow.append(part)
    style_match = re.search(r"Chosen architectural style:\s*(.+)", doc)
    style = style_match.group(1).strip().lower() if style_match else ""
    deployment = "cloud"
    if "Cloud-based infrastructure" not in doc:
        deployment = ""
    return {
        "name": name,
        "description": description,
        "flow": flow,
        "style": style,
        "deployment": deployment,
    }


# --------------------------------------------------------------- components

def _parse_components(doc):
    components = []
    overview = re.search(
        r"# C\. Architecture Overview(.*?)(?=\n# D\.|\Z)", doc, re.DOTALL
    )
    text = overview.group(1) if overview else doc
    for match in re.finditer(r"\*\s*(\w+Component): responsible for (.+)", text):
        name = match.group(1)
        responsibilities = [
            item.strip()
            for item in re.split(r",\s*|\s+and\s+", match.group(2).strip())
            if item.strip()
        ]
        owns = _find_owns(doc, name)
        components.append(
            {"name": name, "responsibilities": responsibilities, "owns": owns}
        )
    return components


def _find_owns(doc, component):
    detailed = re.search(
        r"## {}\b(.*?)(?=\n## |\n# [A-Z]\.|\Z)".format(re.escape(component)),
        doc,
        re.DOTALL,
    )
    if detailed:
        owns_match = re.search(r"[Oo]wns the (.+?) data", detailed.group(1))
        if owns_match:
            return owns_match.group(1).strip() + " data"
    return OWNS_FALLBACK.get(component, "")


# -------------------------------------------------------------------- stack

def _parse_stack(doc):
    stack = {}
    block = re.search(
        r"### Recommended default stack(.*?)(?=\nJustification:|\Z)", doc, re.DOTALL
    )
    text = block.group(1) if block else ""
    for bullet in re.findall(r"^\*\s*(.+)$", text, re.MULTILINE):
        bullet = bullet.strip()
        for prefix, key in STACK_KEYS:
            if bullet.startswith(prefix):
                stack[key] = bullet
                break
    return stack


# --------------------------------------------------------------------- apis

def _parse_apis(doc):
    apis = []
    for fence in re.findall(r"```yml\n(.*?)```", doc, re.DOTALL):
        if "openapi:" not in fence:
            continue
        path_match = re.search(r"paths:\n\s+(/\S+):\n\s+(\w+):\n\s+summary:\s*(.+)", fence)
        if not path_match:
            continue
        prop_match = re.search(
            r"properties:\n\s+(\w+):\n\s+type:\s*(\w+)", fence
        )
        response = {}
        if prop_match:
            response = {prop_match.group(1): prop_match.group(2)}
        apis.append(
            {
                "method": path_match.group(2).upper(),
                "path": path_match.group(1),
                "summary": path_match.group(3).strip(),
                "response": response,
            }
        )
        break
    for fence in re.findall(r"```proto\n(.*?)```", doc, re.DOTALL):
        service = re.search(r"service\s+(\w+)\s*\{", fence)
        rpc = re.search(r"rpc\s+(\w+)\((\w+)\)\s+returns\s*\((\w+)\)", fence)
        if not service or not rpc:
            continue
        messages = {}
        for msg in re.finditer(
            r"message\s+(\w+)\s*\{(.*?)\}", fence, re.DOTALL
        ):
            fields = {}
            for field in re.finditer(r"(\w+)\s+(\w+)\s*=\s*\d+;", msg.group(2)):
                fields[field.group(2)] = field.group(1)
            messages[msg.group(1)] = fields
        apis.append(
            {
                "service": service.group(1),
                "rpc": rpc.group(1),
                "request": messages.get(rpc.group(2), {}),
                "response": messages.get(rpc.group(3), {}),
            }
        )
        break
    return apis


# -------------------------------------------------------------- data models

def _parse_data_models(doc):
    models = []
    seen = set()
    for fence in re.findall(r"```sql\n(.*?)```", doc, re.DOTALL):
        for table in re.finditer(
            r"CREATE TABLE\s+(\w+)\s*\((.*?)\);", fence, re.DOTALL | re.IGNORECASE
        ):
            # The doc repeats the same DDL in two sections; keep one copy.
            if table.group(1) in seen:
                continue
            seen.add(table.group(1))
            columns = []
            for line in table.group(2).splitlines():
                line = line.strip().rstrip(",")
                if not line:
                    continue
                parts = line.split(None, 1)
                if len(parts) == 2:
                    columns.append({"name": parts[0], "type": parts[1].strip()})
            models.append({"table": table.group(1), "columns": columns})
    return models


# ----------------------------------------------------------------- diagrams

def _parse_diagrams(view):
    """One entry per numbered diagram; multi-block diagrams are joined."""
    diagrams = []
    heading = re.compile(
        r"^(\d+)\.\s+(.+?)\s+—\s+(.+?)\s+View:\s*(.+)$", re.MULTILINE
    )
    matches = list(heading.finditer(view))
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(view)
        section = view[start:end]
        blocks = re.findall(r"```plantuml\n(.*?)```", section, re.DOTALL)
        if not blocks:
            continue
        names = [
            re.search(r"@startuml\s+(\S+)", block).group(1)
            for block in blocks
            if re.search(r"@startuml\s+(\S+)", block)
        ]
        if len(names) == 1:
            name = names[0]
        else:
            # Sequence and Collaboration each have two blocks; keep the
            # shared base name and both blocks in full.
            base = re.sub(r"\d+$", "", names[0]) if names else match.group(2)
            name = base
        diagrams.append(
            {
                "name": name,
                "view": match.group(3).strip(),
                "plantuml": "\n".join(block.strip() for block in blocks),
            }
        )
    return diagrams


# ------------------------------------------------------------- requirements

def _parse_requirements(doc):
    requirements = []
    table = re.search(
        r"# B\. Traceability & Rationale(.*?)(?=\n# C\.|\Z)", doc, re.DOTALL
    )
    text = table.group(1) if table else ""
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or "---" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 5 or cells[0] in ("Requirement ID", ""):
            continue
        requirements.append(
            {
                "id": cells[0],
                "text": cells[1],
                "diagram": cells[2],
                "component": cells[3],
                "artifact": cells[4],
            }
        )
    return requirements


# ------------------------------------------- assumptions and open questions

def _parse_assumptions(doc):
    section = re.search(
        r"## Assumptions(.*?)(?=\n## |\n# [A-Z]\.|\Z)", doc, re.DOTALL
    )
    assumptions = []
    if section:
        for line in section.group(1).splitlines():
            match = re.match(r"A\d+:\s*(.+)", line.strip())
            if match:
                assumptions.append(match.group(1).strip())
    return assumptions


def _parse_open_questions(doc):
    section = re.search(
        r"## Unresolved stakeholder questions needing input(.*?)(?=\n# [A-Z]\.|\Z)",
        doc,
        re.DOTALL,
    )
    questions = []
    if section:
        for line in section.group(1).splitlines():
            line = line.strip()
            if line.startswith("*"):
                questions.append(line.lstrip("*").strip())
    return questions


# --------------------------------------------------------------------- gaps

def _find_gaps(doc, view, spec_requirements=None, spec_diagrams=None):
    gaps = []
    requirements = spec_requirements if spec_requirements is not None else []
    if len(requirements) <= 3:
        gaps.append(
            "Traceability maps only {} requirement(s); most of the doc's "
            "FR/NFR/ASR claims have no rows.".format(len(requirements))
        )
    testing = re.search(
        r"## Matrix mapping.*?(?=\n## |\n# [A-Z]\.|\Z)", doc, re.DOTALL
    )
    if testing:
        rows = [
            line
            for line in testing.group(0).splitlines()
            if line.strip().startswith("|") and "---" not in line
            and "Test Type" not in line
        ]
        if rows and all(
            not cell.strip()
            for line in rows
            for cell in line.strip("|").split("|")[1:]
        ):
            gaps.append("Test matrix in the doc is empty.")
    diagrams = spec_diagrams if spec_diagrams is not None else []
    for diagram in diagrams:
        if diagram["name"].startswith("Object") and "participant" in diagram["plantuml"]:
            gaps.append(
                "Object diagram uses sequence-diagram syntax (participant), "
                "not object syntax."
            )
            break
    meta = [name for name in ("Analysis Plan", "How to review") if name in doc]
    if meta:
        gaps.append(
            "Doc contains meta sections ({}) that are not architecture.".format(
                ", ".join(meta)
            )
        )
    return gaps
