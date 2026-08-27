#!/usr/bin/env python3
"""Validate, assess, create, and index Houdini workflow experience records."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_ROOT = SKILL_ROOT / "references"
SCHEMA_ROOT = REFERENCE_ROOT / "schemas"
RECORD_ROOT = REFERENCE_ROOT / "records"
SCHEMAS = {
    "case": SCHEMA_ROOT / "case.schema.json",
    "recipe": SCHEMA_ROOT / "recipe.schema.json",
    "experience": SCHEMA_ROOT / "experience.schema.json",
    "template_manifest": SCHEMA_ROOT / "template-manifest.schema.json",
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=False)
        handle.write("\n")


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def validate_instance(value: Any, schema: dict[str, Any], location: str = "$") -> list[str]:
    errors: list[str] = []
    expected = schema.get("type")
    if expected and not _matches_type(value, expected):
        return [f"{location}: expected {expected}, got {type(value).__name__}"]

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{location}: {value!r} is not one of {schema['enum']!r}")

    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{location}: missing required property {key!r}")

        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, child in value.items():
            child_location = f"{location}.{key}"
            if key in properties:
                errors.extend(validate_instance(child, properties[key], child_location))
            elif additional is False:
                errors.append(f"{child_location}: unexpected property")
            elif isinstance(additional, dict):
                errors.extend(validate_instance(child, additional, child_location))

    if isinstance(value, list):
        minimum = schema.get("minItems")
        if minimum is not None and len(value) < minimum:
            errors.append(f"{location}: expected at least {minimum} items")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, child in enumerate(value):
                errors.extend(validate_instance(child, item_schema, f"{location}[{index}]"))

    return errors


def schema_for(record: dict[str, Any]) -> dict[str, Any]:
    record_type = record.get("record_type")
    schema_path = SCHEMAS.get(record_type)
    if schema_path is None:
        raise ValueError(f"unsupported record_type: {record_type!r}")
    return load_json(schema_path)


def discover_record_paths() -> list[Path]:
    paths = [path for path in RECORD_ROOT.rglob("*.json") if path.name != "index.json"]
    paths.extend(SKILL_ROOT.glob("assets/**/*.manifest.json"))
    return sorted(set(paths))


def validate_paths(paths: list[Path]) -> tuple[int, list[dict[str, Any]]]:
    reports: list[dict[str, Any]] = []
    failures = 0
    for path in paths:
        try:
            record = load_json(path)
            errors = validate_instance(record, schema_for(record))
        except Exception as exc:  # Keep batch validation useful after one malformed file.
            errors = [str(exc)]
        if errors:
            failures += 1
        reports.append({"path": str(path), "valid": not errors, "errors": errors})
    return failures, reports


def assessment(record: dict[str, Any]) -> dict[str, Any]:
    missing: list[str] = []
    record_type = record.get("record_type")
    status = record.get("status", "candidate")

    if record_type == "case":
        acceptance = record.get("acceptance", {})
        environment = record.get("environment", {})
        if not record.get("source", {}).get("fingerprint"):
            missing.append("source fingerprint")
        if not environment.get("houdini_versions"):
            missing.append("verified Houdini version")
        if not acceptance.get("verified"):
            missing.append("reproducible acceptance run")
        if not acceptance.get("evidence"):
            missing.append("acceptance evidence")
    elif record_type == "recipe":
        evidence = record.get("evidence", {})
        if len(evidence.get("case_ids", [])) < 2:
            missing.append("at least two independent cases")
        if not evidence.get("experience_ids"):
            missing.append("at least one execution record")
        if not evidence.get("last_verified"):
            missing.append("last_verified date")
    elif record_type == "experience":
        acceptance = record.get("acceptance", {})
        if acceptance.get("failed"):
            missing.append("resolve failed acceptance checks")
        if acceptance.get("skipped"):
            missing.append("run or justify skipped acceptance checks")
        if not acceptance.get("passed"):
            missing.append("at least one passing acceptance check")
    elif record_type == "template_manifest":
        if not record.get("safe_on_load"):
            missing.append("safe_on_load must be true")

    suggested = status
    if status == "candidate" and not missing:
        suggested = "validated"
    if status == "validated" and not missing and record_type == "recipe":
        suggested = "canonical"
    return {
        "id": record.get("id") or record.get("template_id"),
        "record_type": record_type,
        "current_status": status,
        "suggested_status": suggested,
        "missing_evidence": missing,
    }


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "experience"


def new_experience(args: argparse.Namespace) -> Path:
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    identifier = args.id or f"exp-{now.strftime('%Y%m%d-%H%M%S')}-{slugify(args.workflow)}"
    record = {
        "schema_version": 1,
        "record_type": "experience",
        "id": identifier,
        "status": "candidate",
        "workflow": args.workflow,
        "goal": args.goal,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "environment": {
            "houdini": args.houdini,
            "sidefx_labs": args.sidefx_labs,
            "engine": args.engine,
            "project": args.project,
            "hip": args.hip,
        },
        "inputs": [],
        "decisions": [],
        "operations": [],
        "corrections": [],
        "outputs": [],
        "acceptance": {"passed": [], "failed": [], "skipped": [], "metrics": {}},
        "provenance": {
            "recipe_id": args.recipe_id,
            "case_ids": args.case_id,
            "created_by": "experience_cli.py",
            "supersedes": "",
        },
        "tags": args.tag,
    }
    errors = validate_instance(record, schema_for(record))
    if errors:
        raise ValueError("generated invalid record: " + "; ".join(errors))
    path = RECORD_ROOT / "experiences" / f"{identifier}.json"
    if path.exists() and not args.overwrite:
        raise FileExistsError(f"record exists: {path}")
    dump_json(path, record)
    return path


def rebuild_index() -> Path:
    entries: list[dict[str, Any]] = []
    for path in discover_record_paths():
        record = load_json(path)
        entries.append(
            {
                "id": record.get("id") or record.get("template_id"),
                "record_type": record.get("record_type"),
                "status": record.get("status", "n/a"),
                "workflow": record.get("workflow", ""),
                "path": path.relative_to(REFERENCE_ROOT).as_posix()
                if path.is_relative_to(REFERENCE_ROOT)
                else path.relative_to(SKILL_ROOT).as_posix(),
            }
        )
    index = {
        "schema_version": 1,
        "records": sorted(entries, key=lambda item: (item["record_type"], item["id"] or "")),
    }
    path = RECORD_ROOT / "index.json"
    dump_json(path, index)
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate records against their schemas")
    validate.add_argument("paths", nargs="*", type=Path)

    assess = subparsers.add_parser("assess", help="report evidence missing for promotion")
    assess.add_argument("paths", nargs="*", type=Path)

    subparsers.add_parser("reindex", help="rebuild the deterministic record index")

    create = subparsers.add_parser("new-experience", help="create a candidate execution record")
    create.add_argument("--goal", required=True)
    create.add_argument("--workflow", required=True)
    create.add_argument("--id")
    create.add_argument("--houdini", default="")
    create.add_argument("--sidefx-labs", default="")
    create.add_argument("--engine", default="")
    create.add_argument("--project", default="")
    create.add_argument("--hip", default="")
    create.add_argument("--recipe-id", default="")
    create.add_argument("--case-id", action="append", default=[])
    create.add_argument("--tag", action="append", default=[])
    create.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "validate":
        paths = args.paths or discover_record_paths()
        failures, reports = validate_paths(paths)
        print(json.dumps({"valid": failures == 0, "reports": reports}, ensure_ascii=False, indent=2))
        return 1 if failures else 0
    if args.command == "assess":
        paths = args.paths or discover_record_paths()
        reports = [assessment(load_json(path)) for path in paths]
        print(json.dumps(reports, ensure_ascii=False, indent=2))
        return 0
    if args.command == "reindex":
        print(rebuild_index())
        return 0
    if args.command == "new-experience":
        print(new_experience(args))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
