#!/usr/bin/env python3
"""Build a self-contained knowledge dashboard from validated workflow records."""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from collections import Counter
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_ROOT.parent
REFERENCE_ROOT = SKILL_ROOT / "references"
WORKFLOW_INDEX = REFERENCE_ROOT / "workflow-index.json"
TEMPLATE_PATH = SKILL_ROOT / "dashboard" / "index.template.html"
CYTOSCAPE_PATH = SKILL_ROOT / "dashboard" / "vendor" / "cytoscape-3.34.2.min.js"
DEFAULT_OUTPUT = SKILL_ROOT / "dashboard" / "generated" / "houdini-knowledge-dashboard.html"

if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from experience_cli import (  # noqa: E402
    assessment,
    discover_record_paths,
    load_json,
    validate_paths,
)


TYPE_LABELS = {
    "workflow": "Workflow",
    "case": "Case",
    "recipe": "Recipe",
    "experience": "Experience",
    "template_manifest": "Template",
    "capability": "MCP capability",
}
STATUS_ORDER = ("candidate", "validated", "canonical", "deprecated")


def _humanize(identifier: str) -> str:
    return " ".join(part.capitalize() for part in identifier.replace("_", "-").split("-") if part)


def _record_identifier(record: dict[str, Any]) -> str:
    return str(record.get("id") or record.get("template_id") or "")


def _record_workflows(record: dict[str, Any]) -> list[str]:
    record_type = record.get("record_type")
    if record_type == "case":
        return list(record.get("scope", {}).get("workflows", []))
    workflow = record.get("workflow", "")
    return [workflow] if workflow else []


def _record_summary(record: dict[str, Any]) -> str:
    if record.get("summary"):
        return str(record["summary"])
    if record.get("goal"):
        return str(record["goal"])
    if record.get("hip_path"):
        return f"Template skeleton: {record['hip_path']}"
    return ""


def _record_title(record: dict[str, Any]) -> str:
    identifier = _record_identifier(record)
    return str(record.get("title") or record.get("goal") or _humanize(identifier))


def _record_acceptance(record: dict[str, Any]) -> list[str]:
    acceptance = record.get("acceptance", [])
    if isinstance(acceptance, list):
        return [str(item) for item in acceptance]
    if not isinstance(acceptance, dict):
        return []
    checks = acceptance.get("checks")
    if isinstance(checks, list):
        return [str(item) for item in checks]
    result: list[str] = []
    for key in ("passed", "failed", "skipped"):
        for item in acceptance.get(key, []):
            result.append(f"{key}: {item}")
    return result


def _record_environment(record: dict[str, Any]) -> list[str]:
    environment = record.get("environment", {})
    if not isinstance(environment, dict):
        return []
    values: list[str] = []
    for key, value in environment.items():
        if isinstance(value, list):
            rendered = ", ".join(str(item) for item in value if item)
        else:
            rendered = str(value) if value else ""
        if rendered:
            values.append(f"{key.replace('_', ' ')}: {rendered}")
    return values


def _node_id(record_type: str, identifier: str) -> str:
    return f"{record_type}:{identifier}"


def build_model() -> dict[str, Any]:
    """Return the dashboard projection; source records remain authoritative."""
    record_paths = discover_record_paths()
    failures, reports = validate_paths(record_paths)
    if failures:
        messages = [f"{item['path']}: {'; '.join(item['errors'])}" for item in reports if item["errors"]]
        raise ValueError("knowledge records are invalid:\n" + "\n".join(messages))

    workflow_document = load_json(WORKFLOW_INDEX)
    workflows = workflow_document["workflows"]
    records: list[tuple[Path, dict[str, Any]]] = [(path, load_json(path)) for path in record_paths]
    records_by_id = {_record_identifier(record): record for _, record in records}
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    edge_keys: set[tuple[str, str, str]] = set()
    warnings: list[str] = []

    def add_edge(source: str, target: str, relation: str) -> None:
        key = (source, target, relation)
        if source == target or key in edge_keys:
            return
        edge_keys.add(key)
        edges.append(
            {
                "data": {
                    "id": f"edge:{len(edges)}",
                    "source": source,
                    "target": target,
                    "relation": relation,
                    "label": relation.replace("_", " "),
                }
            }
        )

    workflow_ids = {item["id"] for item in workflows}
    for workflow in workflows:
        workflow_id = workflow["id"]
        nodes.append(
            {
                "data": {
                    "id": _node_id("workflow", workflow_id),
                    "record_id": workflow_id,
                    "type": "workflow",
                    "type_label": TYPE_LABELS["workflow"],
                    "label": _humanize(workflow_id),
                    "title": _humanize(workflow_id),
                    "status": "active",
                    "workflow": workflow_id,
                    "workflows": [workflow_id],
                    "summary": f"Routes signals to {workflow['reference']}",
                    "source_path": f"references/{workflow['reference']}",
                    "source_uri": (REFERENCE_ROOT / workflow["reference"]).resolve().as_uri(),
                    "tags": list(workflow.get("signals", [])),
                    "missing_evidence": [],
                    "acceptance": [],
                    "environment": [],
                }
            }
        )

    for path, record in records:
        record_type = record["record_type"]
        identifier = _record_identifier(record)
        workflows_for_record = _record_workflows(record)
        report = assessment(record)
        source_path = path.relative_to(SKILL_ROOT).as_posix()
        status = str(record.get("status", "active"))
        nodes.append(
            {
                "data": {
                    "id": _node_id(record_type, identifier),
                    "record_id": identifier,
                    "type": record_type,
                    "type_label": TYPE_LABELS[record_type],
                    "label": _record_title(record),
                    "title": _record_title(record),
                    "status": status,
                    "workflow": workflows_for_record[0] if workflows_for_record else "",
                    "workflows": workflows_for_record,
                    "summary": _record_summary(record),
                    "source_path": source_path,
                    "source_uri": path.resolve().as_uri(),
                    "tags": list(record.get("tags", [])),
                    "missing_evidence": list(report["missing_evidence"]),
                    "acceptance": _record_acceptance(record),
                    "environment": _record_environment(record),
                }
            }
        )
        for workflow_id in workflows_for_record:
            if workflow_id not in workflow_ids:
                warnings.append(f"{identifier} references unknown workflow {workflow_id}")
                continue
            relation = "scoped_to" if record_type == "case" else "belongs_to"
            add_edge(
                _node_id(record_type, identifier),
                _node_id("workflow", workflow_id),
                relation,
            )

        if record_type == "recipe":
            evidence = record.get("evidence", {})
            for case_id in evidence.get("case_ids", []):
                if case_id in records_by_id:
                    add_edge(_node_id("case", case_id), _node_id("recipe", identifier), "supports")
                else:
                    warnings.append(f"{identifier} references missing case {case_id}")
            for experience_id in evidence.get("experience_ids", []):
                if experience_id in records_by_id:
                    add_edge(
                        _node_id("experience", experience_id),
                        _node_id("recipe", identifier),
                        "verifies",
                    )
                else:
                    warnings.append(f"{identifier} references missing experience {experience_id}")
        elif record_type == "experience":
            provenance = record.get("provenance", {})
            recipe_id = provenance.get("recipe_id", "")
            if recipe_id:
                if recipe_id in records_by_id:
                    add_edge(
                        _node_id("experience", identifier),
                        _node_id("recipe", recipe_id),
                        "executes",
                    )
                else:
                    warnings.append(f"{identifier} references missing recipe {recipe_id}")
            for case_id in provenance.get("case_ids", []):
                if case_id in records_by_id:
                    add_edge(_node_id("case", case_id), _node_id("experience", identifier), "informed")
                else:
                    warnings.append(f"{identifier} references missing case {case_id}")

            for operation in record.get("operations", []):
                capability = str(operation.get("capability", "")).strip()
                if not capability:
                    continue
                capability_node = _node_id("capability", capability)
                if not any(node["data"]["id"] == capability_node for node in nodes):
                    nodes.append(
                        {
                            "data": {
                                "id": capability_node,
                                "record_id": capability,
                                "type": "capability",
                                "type_label": TYPE_LABELS["capability"],
                                "label": capability,
                                "title": capability,
                                "status": "observed",
                                "workflow": "",
                                "workflows": [],
                                "summary": "Observed in an Experience operation.",
                                "source_path": "",
                                "source_uri": "",
                                "tags": [],
                                "missing_evidence": [],
                                "acceptance": [],
                                "environment": [],
                            }
                        }
                    )
                add_edge(_node_id("experience", identifier), capability_node, "uses")

        supersedes = record.get("provenance", {}).get("supersedes", "")
        if supersedes:
            replaced = records_by_id.get(supersedes)
            if replaced:
                add_edge(
                    _node_id(record_type, identifier),
                    _node_id(replaced["record_type"], supersedes),
                    "supersedes",
                )
            else:
                warnings.append(f"{identifier} supersedes missing record {supersedes}")

    node_data = [node["data"] for node in nodes]
    workflow_rows: list[dict[str, Any]] = []
    for workflow in workflows:
        workflow_id = workflow["id"]
        related = [node for node in node_data if workflow_id in node.get("workflows", []) and node["type"] != "workflow"]
        type_counts = Counter(node["type"] for node in related)
        status_counts = Counter(node["status"] for node in related)
        workflow_rows.append(
            {
                "id": workflow_id,
                "label": _humanize(workflow_id),
                "reference": workflow["reference"],
                "records": len(related),
                "cases": type_counts["case"],
                "recipes": type_counts["recipe"],
                "experiences": type_counts["experience"],
                "templates": type_counts["template_manifest"],
                "candidate": status_counts["candidate"],
                "validated": status_counts["validated"],
                "canonical": status_counts["canonical"],
                "evidence_gaps": sum(len(node["missing_evidence"]) for node in related),
            }
        )

    recipe_rows: list[dict[str, Any]] = []
    for path, record in records:
        if record["record_type"] != "recipe":
            continue
        evidence = record["evidence"]
        recipe_rows.append(
            {
                "id": record["id"],
                "title": record["title"],
                "workflow": record["workflow"],
                "status": record["status"],
                "case_ids": list(evidence["case_ids"]),
                "experience_ids": list(evidence["experience_ids"]),
                "last_verified": evidence["last_verified"],
                "missing_evidence": assessment(record)["missing_evidence"],
                "source_uri": path.resolve().as_uri(),
            }
        )

    correction_counts: Counter[str] = Counter()
    correction_examples: dict[str, list[dict[str, str]]] = {}
    for _, record in records:
        if record["record_type"] != "experience":
            continue
        for correction in record.get("corrections", []):
            classification = correction["classification"]
            correction_counts[classification] += 1
            correction_examples.setdefault(classification, []).append(
                {
                    "experience_id": record["id"],
                    "request": correction["request"],
                    "resolution": correction["resolution"],
                    "outcome": correction["outcome"],
                }
            )

    type_counts = Counter(node["type"] for node in node_data)
    status_counts = Counter(node["status"] for node in node_data if node["type"] != "workflow")
    total_gaps = sum(len(node["missing_evidence"]) for node in node_data)
    return {
        "schema_version": 1,
        "nodes": nodes,
        "edges": edges,
        "workflow_rows": workflow_rows,
        "recipe_rows": sorted(recipe_rows, key=lambda item: item["workflow"]),
        "interventions": [
            {
                "classification": classification,
                "count": count,
                "examples": correction_examples[classification],
            }
            for classification, count in correction_counts.most_common()
        ],
        "stats": {
            "workflows": type_counts["workflow"],
            "records": sum(type_counts[key] for key in ("case", "recipe", "experience", "template_manifest")),
            "cases": type_counts["case"],
            "recipes": type_counts["recipe"],
            "experiences": type_counts["experience"],
            "templates": type_counts["template_manifest"],
            "capabilities": type_counts["capability"],
            "candidate": status_counts["candidate"],
            "validated": status_counts["validated"],
            "canonical": status_counts["canonical"],
            "evidence_gaps": total_gaps,
            "corrections": sum(correction_counts.values()),
        },
        "warnings": sorted(set(warnings)),
        "status_order": list(STATUS_ORDER),
    }


def _safe_script_text(value: str) -> str:
    return value.replace("</script", "<\\/script")


def render_dashboard(output: Path) -> Path:
    model = build_model()
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    cytoscape_bundle = CYTOSCAPE_PATH.read_text(encoding="utf-8")
    if template.count("/*__CYTOSCAPE_BUNDLE__*/") != 1:
        raise ValueError("dashboard template must contain one Cytoscape bundle marker")
    if template.count("__KNOWLEDGE_MODEL__") != 1:
        raise ValueError("dashboard template must contain one knowledge model marker")
    model_json = json.dumps(model, ensure_ascii=False, separators=(",", ":"))
    rendered = template.replace("/*__CYTOSCAPE_BUNDLE__*/", _safe_script_text(cytoscape_bundle))
    rendered = rendered.replace("__KNOWLEDGE_MODEL__", _safe_script_text(model_json))
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8", newline="\n")
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--open", action="store_true", dest="open_browser")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = render_dashboard(args.output)
    print(output)
    if args.open_browser:
        webbrowser.open(output.as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
