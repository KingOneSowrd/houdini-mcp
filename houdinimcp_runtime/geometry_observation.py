"""Bounded geometry observations and detached snapshot comparison.

No hou dependency at import time: comparison/storage are unit-testable.
Snapshots contain JSON values, never live Geometry references.
"""
from collections import OrderedDict
from itertools import islice
import copy
import hashlib
import json
import math
import uuid

OWNERS = {"points": ("pointAttribs", "pointcount"),
          "primitives": ("primAttribs", "primitivecount"),
          "vertices": ("vertexAttribs", "vertexcount"),
          "detail": ("globalAttribs", None)}


def bounded_value(value, max_items=128, max_string=2048, depth=0):
    """JSON-safe values; report truncation and encode nonfinite floats explicitly."""
    if isinstance(value, float) and not math.isfinite(value):
        return {"__nonfinite__": str(value)}, False
    if value is None or isinstance(value, (bool, int, float)):
        return value, False
    if isinstance(value, str):
        return value[:max_string], len(value) > max_string
    if depth >= 8:
        return "<depth limit>", True
    if isinstance(value, dict):
        result, truncated = {}, len(value) > max_items
        for key, item in islice(value.items(), max_items):
            child, cut = bounded_value(item, max_items, max_string, depth + 1)
            result[str(key)] = child
            truncated |= cut
        return result, truncated
    if isinstance(value, (tuple, list)):
        result, truncated = [], len(value) > max_items
        for item in value[:max_items]:
            child, cut = bounded_value(item, max_items, max_string, depth + 1)
            result.append(child)
            truncated |= cut
        return result, truncated
    return str(value)[:max_string], True


def schema(geo, owner):
    return [{"name": a.name(), "type": a.dataType().name(), "size": a.size(),
             "array": a.isArrayType()} for a in getattr(geo, OWNERS[owner][0])()]


def elements(geo, owner):
    if owner == "points":
        return geo.iterPoints()
    if owner == "primitives":
        return geo.iterPrims()
    if owner == "vertices":
        # Traversal order is primitive/local-vertex order, not linear vertex id.
        return (v for p in geo.iterPrims() for v in p.vertices())
    return iter([geo])


def read_rows(geo, owner, attributes, start, limit, max_bytes=262144,
              max_value_items=128, max_string_length=2048):
    if owner not in OWNERS:
        raise ValueError("element must be points, primitives, vertices or detail")
    if not 1 <= max_value_items <= 1024 or not 1 <= max_string_length <= 8192:
        raise ValueError("Value bounds out of range")
    available = {a.name(): a for a in getattr(geo, OWNERS[owner][0])()}
    names = list(dict.fromkeys(attributes)) if attributes is not None else (
        ["P"] if owner == "points" and "P" in available else list(available) if owner in {"vertices", "detail"} else [])
    if len(names) > 64:
        raise ValueError("Select at most 64 attributes")
    missing = [name for name in names if name not in available]
    if missing:
        raise ValueError("Attributes not found on %s: %s; available: %s" % (owner, missing, sorted(available)))
    total = int(geo.intrinsicValue(OWNERS[owner][1])) if owner != "detail" else 1
    rows, used, value_cuts = [], 0, 0
    for item in islice(elements(geo, owner), start, start + limit):
        row = {"number": 0 if owner == "detail" else item.linearNumber() if owner == "vertices" else item.number(),
               "attributes": {}, "truncated_attributes": []}
        if owner == "vertices":
            row.update(primitive_number=item.prim().number(), vertex_index=item.number(), point_number=item.point().number())
        if owner == "primitives":
            row["type"] = item.type().name()
        for name in names:
            value, cut = bounded_value(item.attribValue(available[name]), max_value_items, max_string_length)
            row["attributes"][name] = value
            if cut:
                row["truncated_attributes"].append(name)
        size = len(json.dumps(row, ensure_ascii=True, allow_nan=False).encode("utf-8")) + 2
        if used + size > max_bytes:
            if not rows:
                raise ValueError("First row exceeds max_bytes; select fewer attributes or smaller value limits")
            break
        used += size
        value_cuts += len(row["truncated_attributes"])
        rows.append(row)
    end = start + len(rows)
    return {"element": owner, "total": total, "start": start, "count": len(rows),
            "selected_attributes": names, "data": rows,
            "next_start": end if end < total else None,
            "rows_complete": start == 0 and end >= total,
            "truncated_values": value_cuts, "data_bytes": used,
            "ordering": "primitive/local-vertex" if owner == "vertices" else "element-index"}


def topology(geo, limit=100000):
    counts = {key: int(geo.intrinsicValue(key + "count")) for key in ("point", "primitive", "vertex")}
    if max(counts.values()) > limit:
        return {"counts": counts, "hash": None, "complete": False,
                "reason": "topology scan limit exceeded"}
    digest = hashlib.sha256()
    for prim in geo.iterPrims():
        item = [prim.type().name(), [v.point().number() for v in prim.vertices()]]
        digest.update(json.dumps(item, separators=(",", ":")).encode())
    return {"counts": counts, "hash": digest.hexdigest(), "complete": True,
            "scope": "primitive types and ordered vertex-to-point connectivity; not point identity or primitive intrinsics"}


class SnapshotStore:
    def __init__(self, max_count=8, max_bytes=16777216):
        self.items = OrderedDict()
        self.max_count, self.max_bytes = max_count, max_bytes

    def add(self, snapshot):
        encoded = json.dumps(snapshot, ensure_ascii=True, allow_nan=False)
        size = len(encoded.encode())
        if size > self.max_bytes:
            raise ValueError("Snapshot exceeds session storage budget")
        evicted = []
        while self.items and (len(self.items) >= self.max_count or sum(v[1] for v in self.items.values()) + size > self.max_bytes):
            key, _ = self.items.popitem(last=False)
            evicted.append(key)
        key = uuid.uuid4().hex
        self.items[key] = (json.loads(encoded), size)
        return key, evicted

    def get(self, key):
        if key not in self.items:
            raise ValueError("Snapshot unavailable (unknown, released, evicted, or server restarted): " + key)
        return copy.deepcopy(self.items[key][0])

    def release(self, key):
        self.get(key)
        del self.items[key]
        return {"released": key}


def numeric_diff(a, b, atol, rtol):
    """Return changed, absolute numeric deltas, nonfinite component count."""
    if (isinstance(a, dict) and "__nonfinite__" in a) or (isinstance(b, dict) and "__nonfinite__" in b):
        return True, [], 1
    if isinstance(a, (int, float)) and not isinstance(a, bool) and isinstance(b, (int, float)) and not isinstance(b, bool):
        delta = abs(a - b)
        if not math.isfinite(delta):
            return True, [], 1
        return not math.isclose(a, b, abs_tol=atol, rel_tol=rtol), [delta], 0
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        parts = [numeric_diff(x, y, atol, rtol) for x, y in zip(a, b)]
        return any(x[0] for x in parts), [v for x in parts for v in x[1]], sum(x[2] for x in parts)
    if isinstance(a, dict) and isinstance(b, dict) and a.keys() == b.keys():
        parts = [numeric_diff(a[k], b[k], atol, rtol) for k in a]
        return any(x[0] for x in parts), [v for x in parts for v in x[1]], sum(x[2] for x in parts)
    return a != b, [], 0


def compare(before, after, key_attribute=None, assume_index_correspondence=False,
            absolute_tolerance=1e-6, relative_tolerance=1e-6, max_examples=5):
    if not all(math.isfinite(v) and v >= 0 for v in (absolute_tolerance, relative_tolerance)):
        raise ValueError("Tolerances must be finite and nonnegative")
    if before["element"] != after["element"]:
        raise ValueError("Snapshots must have the same attribute owner")
    a_schema = {(o, a["name"]): a for o, attrs in before["schema"].items() for a in attrs}
    b_schema = {(o, a["name"]): a for o, attrs in after["schema"].items() for a in attrs}
    result = {"before": before["node"], "after": after["node"], "element": before["element"],
              "counts_before": before["topology"]["counts"], "counts_after": after["topology"]["counts"],
              "schema_added": [b_schema[k] | {"owner": k[0]} for k in sorted(b_schema.keys() - a_schema.keys())],
              "schema_removed": [a_schema[k] | {"owner": k[0]} for k in sorted(a_schema.keys() - b_schema.keys())],
              "schema_changed": [{"owner": k[0], "name": k[1], "before": a_schema[k], "after": b_schema[k]} for k in sorted(a_schema.keys() & b_schema.keys()) if a_schema[k] != b_schema[k]],
              "comparable": False, "attributes": [], "absolute_tolerance": absolute_tolerance,
              "relative_tolerance": relative_tolerance, "scope": "selected attributes and captured rows only"}
    at, bt = before["topology"], after["topology"]
    same_topology = bool(at["complete"] and bt["complete"] and at["hash"] == bt["hash"] and at["counts"] == bt["counts"])
    result["topology_equal"] = same_topology if at["complete"] and bt["complete"] else None
    def keyed(snapshot):
        rows = snapshot["data"]
        if not key_attribute:
            return {row["number"]: row for row in rows}
        mapping = {}
        for row in rows:
            key = row["attributes"].get(key_attribute)
            if key_attribute in row["truncated_attributes"] or isinstance(key, bool) or not isinstance(key, (str, int)):
                raise ValueError("Matching key must be a captured, untruncated scalar integer or string")
            token = (type(key).__name__, key)
            if token in mapping:
                raise ValueError("Duplicate matching key: " + str(key))
            mapping[token] = row
        return mapping
    if before["element"] != "detail" and not key_attribute and not (assume_index_correspondence and same_topology):
        result["reason"] = "Provide a unique key_attribute, or explicitly assert index correspondence with complete equal topology; equal counts alone do not establish identity"
        return result
    left, right = keyed(before), keyed(after)
    matched = left.keys() & right.keys()
    result.update(comparable=True, matched_rows=len(matched), unmatched_before=len(left.keys()-right.keys()),
                  unmatched_after=len(right.keys()-left.keys()),
                  matching="attribute:" + key_attribute if key_attribute else "detail" if before["element"] == "detail" else "asserted-index",
                  rows_complete=before["rows_complete"] and after["rows_complete"])
    selected_a, selected_b = set(before["selected_attributes"]), set(after["selected_attributes"])
    result["selected_only_before"], result["selected_only_after"] = sorted(selected_a-selected_b), sorted(selected_b-selected_a)
    for name in sorted(selected_a & selected_b):
        owner_key = (before["element"], name)
        if a_schema.get(owner_key) != b_schema.get(owner_key):
            result["attributes"].append({"name": name, "comparable": False, "reason": "attribute schema changed"})
            continue
        changed, cuts, nonfinite, count, maximum, squares, examples = 0, 0, 0, 0, 0., 0., []
        for key in sorted(matched, key=repr):
            a, b = left[key], right[key]
            if name in a["truncated_attributes"] or name in b["truncated_attributes"]:
                cuts += 1
                continue
            different, deltas, invalid = numeric_diff(a["attributes"][name], b["attributes"][name], absolute_tolerance, relative_tolerance)
            changed += int(different)
            nonfinite += invalid
            for delta in deltas:
                count += 1
                maximum = max(maximum, delta)
                # Stable online RMS avoids squaring huge values.
                squares = math.hypot(squares * math.sqrt((count - 1) / count), delta / math.sqrt(count))
            if different and len(examples) < max_examples:
                examples.append({"before_number": a["number"], "after_number": b["number"],
                                 "before": a["attributes"][name], "after": b["attributes"][name]})
        result["attributes"].append({"name": name, "comparable": True, "compared_rows": len(matched)-cuts,
            "changed_rows": changed, "changed_fraction": changed/(len(matched)-cuts) if len(matched)>cuts else None,
            "truncated_rows_skipped": cuts, "nonfinite_components": nonfinite,
            "max_absolute_delta": maximum if count else None,
            "rms_component_delta": squares if count else None, "examples": examples})
    result["equal_selected_values"] = bool(selected_a and result["rows_complete"] and not result["unmatched_before"] and not result["unmatched_after"]
        and selected_a == selected_b and all(x.get("comparable") and x["changed_rows"] == 0 and x["truncated_rows_skipped"] == 0 for x in result["attributes"]))
    return result
