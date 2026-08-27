#!/usr/bin/env python3
"""Inspect a HIP or HDA under Hython and emit a non-cooking candidate case record."""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_INDEX = SKILL_ROOT / "references" / "workflow-index.json"
EXPENSIVE_OR_OUTPUT = re.compile(
    r"(cache|filecache|render|export|rop|output|vellum|pyro|rbd|bullet|vat|vertex.animation|pivotpainter|fbx)",
    re.IGNORECASE,
)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "houdini-case"


def fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def bounded_text(value: Any, limit: int = 500) -> str:
    return " ".join(str(value).split())[:limit]


def portable_locator(path: Path, source_root: Path | None) -> str:
    if source_root:
        try:
            return path.resolve().relative_to(source_root.resolve()).as_posix()
        except ValueError:
            pass
    return path.name


def workflow_routes(corpus: str) -> list[str]:
    with WORKFLOW_INDEX.open("r", encoding="utf-8") as handle:
        index = json.load(handle)
    lowered = corpus.lower()
    scores: list[tuple[int, str]] = []
    for workflow in index["workflows"]:
        score = sum(lowered.count(signal.lower()) for signal in workflow["signals"])
        scores.append((score, workflow["id"]))
    scores.sort(reverse=True)
    selected = [workflow for score, workflow in scores if score > 0]
    return selected[:2] or ["unclassified"]


def license_name(hou: Any) -> str:
    try:
        return hou.licenseCategory().name()
    except Exception:
        return "unknown"


def node_summary(nodes: list[Any]) -> dict[str, Any]:
    type_counts = collections.Counter(node.type().name() for node in nodes)
    top_nodes: list[str] = []
    notes: list[str] = []
    semantic: list[str] = []
    outputs: list[dict[str, Any]] = []

    for node in nodes:
        depth = node.path().count("/")
        if depth <= 3 and len(top_nodes) < 100:
            top_nodes.append(f"{node.path()}:{node.type().name()}")
        label = f"{node.path()} {node.type().name()}"
        if EXPENSIVE_OR_OUTPUT.search(label) and len(semantic) < 100:
            semantic.append(f"{node.path()}:{node.type().name()}")
        if node.type().name() == "output" or re.match(r"^(OUT|EXPORT|CACHE)_", node.name(), re.IGNORECASE):
            if len(outputs) < 80:
                outputs.append(
                    {"product": "houdini_output_node", "path_contract": node.path(), "attributes": []}
                )
        try:
            for note in node.stickyNotes():
                text = bounded_text(note.text())
                if text and text not in notes and len(notes) < 100:
                    notes.append(text)
        except Exception:
            pass

    return {
        "node_count": len(nodes),
        "node_type_counts": dict(type_counts.most_common(100)),
        "top_nodes": top_nodes,
        "sticky_notes": notes,
        "semantic": semantic,
        "outputs": outputs,
    }


def external_references(hou: Any) -> list[str]:
    references: list[str] = []
    try:
        pairs = hou.fileReferences()
    except Exception:
        return references
    for _parm, value in pairs:
        text = str(value)
        if not text or "\n" in text or len(text) > 500:
            continue
        if text not in references:
            references.append(text)
        if len(references) >= 120:
            break
    return references


def inspect_hip(hou: Any, path: Path) -> dict[str, Any]:
    hou.hipFile.load(str(path), suppress_save_prompt=True, ignore_load_warnings=True)
    nodes = list(hou.node("/").allSubChildren())
    summary = node_summary(nodes)
    return {
        **summary,
        "inputs": [],
        "contracts": [
            f"frame_range={hou.playbar.frameRange()}",
            f"fps={hou.fps()}",
        ],
        "references": external_references(hou),
    }


def inspect_hda(hou: Any, path: Path) -> dict[str, Any]:
    hou.hda.installFile(str(path))
    definitions = hou.hda.definitionsInFile(str(path))
    all_nodes: list[Any] = []
    inputs: list[dict[str, str]] = []
    contracts: list[str] = []
    limitations: list[str] = []

    for index, definition in enumerate(definitions):
        contracts.append(
            f"definition={definition.nodeTypeName()} inputs={definition.minNumInputs()}..{definition.maxNumInputs()}"
        )
        category = definition.nodeType().category().name()
        try:
            if category == "Sop":
                host = hou.node("/obj").createNode("geo", f"case_inspect_{index}")
                asset = host.createNode(definition.nodeTypeName())
            elif category == "Object":
                asset = hou.node("/obj").createNode(definition.nodeTypeName())
            elif category == "Lop":
                asset = hou.node("/stage").createNode(definition.nodeTypeName())
            else:
                limitations.append(f"internal graph not instantiated for category {category}")
                continue
            inputs.append(
                {
                    "name": definition.nodeTypeName(),
                    "domain": category,
                    "contract": f"{definition.minNumInputs()}..{definition.maxNumInputs()} node inputs",
                }
            )
            for parm in asset.parms():
                try:
                    parm_type = parm.parmTemplate().type().name()
                except Exception:
                    continue
                if parm.isHidden() or parm_type in {"Folder", "FolderSet", "Separator", "Label"}:
                    continue
                contracts.append(f"interface:{parm.name()}:{parm.description()}:{parm_type}")
                if len(contracts) >= 120:
                    break
            try:
                asset.allowEditingOfContents()
            except Exception:
                limitations.append(f"contents remained locked for {definition.nodeTypeName()}")
            all_nodes.extend([asset, *asset.allSubChildren()])
        except Exception as exc:
            limitations.append(f"could not instantiate {definition.nodeTypeName()}: {bounded_text(exc)}")

    summary = node_summary(all_nodes)
    return {
        **summary,
        "inputs": inputs,
        "contracts": contracts,
        "references": external_references(hou),
        "limitations": limitations,
    }


def make_record(hou: Any, source: Path, source_root: Path | None) -> dict[str, Any]:
    suffix = source.suffix.lower()
    if suffix == ".hip":
        inspected = inspect_hip(hou, source)
        source_kind = "hip"
    elif suffix in {".hda", ".otl", ".hdalc", ".hdanc"}:
        inspected = inspect_hda(hou, source)
        source_kind = "hda"
    else:
        raise ValueError(f"unsupported Houdini case file: {source.suffix}")

    corpus = " ".join(
        [
            source.name,
            *inspected["top_nodes"],
            *inspected["semantic"],
            *inspected["sticky_notes"],
            *inspected["contracts"],
        ]
    )
    routes = workflow_routes(corpus)
    limitations = list(inspected.get("limitations", []))
    limitations.append("Automatically inspected in manual update mode without cooking or acceptance validation.")

    return {
        "schema_version": 1,
        "record_type": "case",
        "id": f"case-auto-{slugify(source.stem)}",
        "title": source.stem,
        "status": "candidate",
        "summary": f"Automatically generated bounded inspection of {source.name}.",
        "source": {
            "kind": source_kind,
            "locator": portable_locator(source, source_root),
            "fingerprint": fingerprint(source),
            "notes": "Generated without saving, cooking expensive branches, caching, or exporting.",
        },
        "environment": {
            "houdini_versions": [hou.applicationVersionString()],
            "sidefx_labs_versions": [],
            "engines": [],
            "license_modes": [license_name(hou)],
        },
        "scope": {"workflows": routes, "domains": ["houdini"], "projects": []},
        "inputs": inspected["inputs"],
        "observations": {
            "node_count": inspected["node_count"],
            "node_type_counts": inspected["node_type_counts"],
            "top_nodes": inspected["top_nodes"],
            "external_references": inspected["references"],
            "sticky_notes": inspected["sticky_notes"],
            "stages": inspected["semantic"],
            "contracts": inspected["contracts"],
            "limitations": limitations,
        },
        "outputs": inspected["outputs"],
        "acceptance": {"verified": False, "checks": [], "evidence": []},
        "provenance": {
            "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "created_by": "inspect_houdini_case.py",
            "supersedes": "",
        },
        "tags": ["auto-inspected", source_kind],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source = args.source.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)

    import hou  # type: ignore[import-not-found]

    try:
        hou.setUpdateMode(hou.updateMode.Manual)
    except Exception:
        pass
    record = make_record(hou, source, args.source_root)
    encoded = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = args.output.resolve()
        if output.exists() and not args.overwrite:
            raise FileExistsError(f"output exists: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8", newline="\n")
        print(output)
    else:
        sys.stdout.write(encoded)
    return 0


if __name__ == "__main__":
    sys.exit(main())
