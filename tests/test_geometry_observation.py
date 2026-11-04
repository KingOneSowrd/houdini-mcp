import copy
import unittest

import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location("geometry_observation", Path(__file__).resolve().parents[1] / "houdinimcp_runtime" / "geometry_observation.py")
observation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observation)
SnapshotStore, bounded_value, compare = observation.SnapshotStore, observation.bounded_value, observation.compare
from houdini_mcp_bridge.catalog import build_registry


def snapshot(values, element="points", ids=None):
    attrs = [{"name": "P", "type": "Float", "size": 3, "array": False}]
    if ids is not None:
        attrs.append({"name": "id", "type": "Int", "size": 1, "array": False})
    rows = []
    for i, value in enumerate(values):
        data = {"P": value}
        if ids is not None:
            data["id"] = ids[i]
        rows.append({"number": i, "attributes": data, "truncated_attributes": []})
    return {"node": "/obj/test", "element": element, "schema": {element: attrs},
            "topology": {"counts": {"point": len(values)}, "hash": "same", "complete": True},
            "selected_attributes": [a["name"] for a in attrs], "data": rows, "rows_complete": True}


class GeometryObservationTests(unittest.TestCase):
    def test_index_identity_is_not_inferred_from_equal_counts_or_topology(self):
        a = snapshot([[0, 0, 0], [1, 0, 0]])
        b = snapshot([[1, 0, 0], [0, 0, 0]])
        self.assertFalse(compare(a, b)["comparable"])
        b["topology"]["hash"] = "different"
        self.assertFalse(compare(a, b, assume_index_correspondence=True)["comparable"])

    def test_key_matching_survives_reordering_and_reports_unmatched(self):
        a = snapshot([[0, 0, 0], [1, 0, 0]], ids=[10, 20])
        b = snapshot([[1, 0, 0], [0, 0, 0]], ids=[20, 10])
        self.assertTrue(compare(a, b, key_attribute="id")["equal_selected_values"])
        b["data"][0]["attributes"]["id"] = 30
        result = compare(a, b, key_attribute="id")
        self.assertEqual(result["unmatched_before"], 1)
        self.assertFalse(result["equal_selected_values"])

    def test_duplicate_and_missing_keys_rejected(self):
        a = snapshot([0, 1], ids=[1, 1])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            compare(a, a, key_attribute="id")
        with self.assertRaisesRegex(ValueError, "captured"):
            compare(a, a, key_attribute="missing")

    def test_tolerance_nonfinite_and_partial_results(self):
        a, b = snapshot([[1., 0, 0]]), snapshot([[1.0000001, 0, 0]])
        result = compare(a, b, assume_index_correspondence=True)
        self.assertTrue(result["equal_selected_values"])
        b["rows_complete"] = False
        self.assertFalse(compare(a, b, assume_index_correspondence=True)["equal_selected_values"])
        b["data"][0]["attributes"]["P"] = [{"__nonfinite__": "nan"}, 0, 0]
        result = compare(a, b, assume_index_correspondence=True)
        self.assertEqual(result["attributes"][0]["nonfinite_components"], 1)
        b["data"][0]["truncated_attributes"] = ["P"]
        self.assertEqual(compare(a, b, assume_index_correspondence=True)["attributes"][0]["truncated_rows_skipped"], 1)

    def test_schema_owner_and_type_changes_visible_even_without_identity(self):
        a, b = snapshot([0]), snapshot([0])
        b["schema"]["vertices"] = b["schema"].pop("points")
        result = compare(a, b)
        self.assertEqual(result["schema_added"][0]["owner"], "vertices")
        self.assertEqual(result["schema_removed"][0]["owner"], "points")
        b = copy.deepcopy(a)
        b["schema"]["points"][0]["size"] = 1
        self.assertFalse(compare(a, b, assume_index_correspondence=True)["attributes"][0]["comparable"])

    def test_detached_store_eviction_and_release(self):
        store = SnapshotStore(max_count=1)
        source = snapshot([1])
        first, _ = store.add(source)
        source["data"].clear()
        self.assertEqual(len(store.get(first)["data"]), 1)
        second, evicted = store.add(source)
        self.assertEqual(evicted, [first])
        with self.assertRaisesRegex(ValueError, "unavailable"):
            store.get(first)
        store.release(second)
        with self.assertRaises(ValueError):
            store.get(second)

    def test_bounded_nested_values_and_detail(self):
        value, truncated = bounded_value({"array": [1, 2, 3], "text": "abcdef"}, 2, 3)
        self.assertTrue(truncated)
        self.assertEqual(value, {"array": [1, 2], "text": "abc"})
        value, _ = bounded_value(float("inf"))
        self.assertEqual(value, {"__nonfinite__": "inf"})
        a = snapshot([{"nested": [1, "text"]}], element="detail")
        self.assertTrue(compare(a, a)["equal_selected_values"])

    def test_catalog_rejects_invalid_bounds_before_relay(self):
        calls = []
        registry = build_registry(lambda name, args: calls.append((name, args)) or {"status": "success", "result": args})
        for name, args in [
            ("get_geometry_data", {"path": "/obj/x", "element": "edges"}),
            ("get_geometry_data", {"path": "/obj/x", "frame": float("nan")}),
            ("capture_geometry_snapshot", {"path": "/obj/x", "max_elements": 100001}),
            ("capture_geometry_snapshot", {"path": "/obj/x", "unexpected": True}),
            ("compare_geometry_snapshots", {"before_id": "a", "after_id": "b", "absolute_tolerance": -1}),
            ("compare_geometry_snapshots", {"before_id": "a", "after_id": "b", "relative_tolerance": float("inf")}),
        ]:
            self.assertEqual(registry.invoke(name, args)["origin"], "validation")
        self.assertEqual(calls, [])
        response = registry.invoke("get_geometry_data", {"path": "/obj/x", "element": "vertices"})
        self.assertEqual(response["status"], "success")
        self.assertTrue(registry.get("capture_geometry_snapshot").docs)


if __name__ == "__main__":
    unittest.main()
