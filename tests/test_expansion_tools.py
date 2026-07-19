"""Live integration coverage for discovery, snapshots, channels, graph patch and HDA MVP."""

import os
import sys
import tempfile
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import houdini_mcp_server as bridge


PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 19878
ROOT = "/obj/MCP_EXPANSION_TEST"
bridge._houdini_port = PORT
bridge._houdini_connection = None


def call(name, arguments=None, allow_unsafe=False, expect_error=False):
    response = bridge.tool_registry.invoke(name, arguments or {}, allow_unsafe=allow_unsafe)
    assert response["status"] == ("error" if expect_error else "success"), response
    return response


conn = bridge.get_houdini_connection()
conn.send_command("delete_node", {"path": ROOT})

geo = call("create_node", {"node_type": "geo", "parent_path": "/obj", "name": "MCP_EXPANSION_TEST"})["result"]
types = call("search_node_types", {"parent_path": ROOT, "query": "box"})["result"]
assert any(item["name"] == "box" for item in types["node_types"]), types
schema = call("get_node_type_schema", {"parent_path": ROOT, "node_type": "box", "pattern": "size"})["result"]
assert any(item["name"] == "size" for item in schema["parameters"]), schema
print("  PASS  live node discovery and type schema")

subnet = call("create_node", {"node_type": "subnet", "parent_path": ROOT, "name": "asset_subnet"})["result"]
operations = [
    {"op": "create", "id": "box", "parent_path": ROOT + "/asset_subnet", "node_type": "box", "name": "box1"},
    {"op": "create", "id": "xform", "parent_path": ROOT + "/asset_subnet", "node_type": "xform", "name": "xform1"},
    {"op": "create", "id": "normal", "parent_path": ROOT + "/asset_subnet", "node_type": "normal", "name": "normal1"},
    {"op": "connect", "from_path": "$box", "to_path": "$xform"},
    {"op": "connect", "from_path": "$xform", "to_path": "$normal"},
    {"op": "set_parameters", "path": "$box", "parameters": {"size": [2.0, 3.0, 4.0]}},
]
dry = call("apply_graph_patch", {"operations": operations, "dry_run": True})["result"]
assert dry["dry_run"] and conn.send_command("get_node_info", {"path": ROOT + "/asset_subnet/box1"}).get("status") == "error"
applied = call("apply_graph_patch", {"operations": operations, "dry_run": False, "idempotency_key": str(uuid.uuid4())})["result"]
assert len(applied["operations"]) == len(operations), applied
print("  PASS  graph patch dry-run, temporary ids and atomic apply")

snapshot1 = call("get_network_snapshot", {"path": ROOT + "/asset_subnet", "depth": 2, "include_parameters": True})["result"]
snapshot2 = call("get_network_snapshot", {"path": ROOT + "/asset_subnet", "depth": 2, "include_parameters": True})["result"]
assert snapshot1["snapshot_revision"] == snapshot2["snapshot_revision"] and snapshot1["count"] >= 4
print("  PASS  bounded stable network snapshot")

box_path = ROOT + "/asset_subnet/box1"
expr = conn.send_command("execute_code", {"code": "hou.node(%r).parm('sizex').setExpression('$F')" % box_path})
assert expr["status"] == "success", expr
protected = call("set_parameters", {"path": box_path, "parameters": {"size": [1, 1, 1]}}, expect_error=True)
assert "overwrite channel" in protected["message"].lower(), protected
call("set_parameters", {"path": box_path, "parameters": {"size": [1, 1, 1]}, "overwrite_channel": True})
print("  PASS  channel overwrite protection and explicit override")

with tempfile.TemporaryDirectory() as temp_dir:
    library_path = os.path.join(temp_dir, "mcp_verified_asset.hda")
    try:
        create_args = {
            "path": ROOT + "/asset_subnet",
            "type_name": "mcp::verified_asset::1.0",
            "label": "MCP Verified Asset",
            "library_path": library_path,
            "promotions": [{
                "source_node": box_path,
                "source_parameter": "size",
                "name": "box_size",
                "label": "Box Size",
            }],
        }
        analysis = call("analyze_hda_candidate", {"path": create_args["path"], "library_path": library_path, "type_name": create_args["type_name"]})["result"]
        assert analysis["can_create"], analysis
        plan = call("create_hda_from_subnetwork", create_args, allow_unsafe=True)["result"]
        apply_args = dict(create_args, dry_run=False, plan_id=plan["plan_id"], expected_revision=plan["candidate_revision"], idempotency_key=str(uuid.uuid4()))
        created = call("create_hda_from_subnetwork", apply_args, allow_unsafe=True)["result"]
        assert os.path.isfile(library_path) and created["library_sha256"], created
        validated = call("validate_hda", {"path": created["instance_path"]})["result"]
        assert validated["cook"]["cooked"] and validated["matches_current_definition"], validated
        info = call("get_hda_info", {"definition_id": created["definition_id"]})["result"]
        assert any(item["name"] == "box_size" for item in info["parameters"]), info
    finally:
        conn.send_command("delete_node", {"path": ROOT})
        if os.path.isfile(library_path):
            conn.send_command("execute_code", {"code": "hou.hda.uninstallFile(%r)" % library_path})
print("  PASS  planned HDA creation, promotion, cook, identity and validation")

bridge._houdini_connection.disconnect()
bridge._houdini_connection = None
print("\nALL EXPANSION INTEGRATION TESTS PASSED")
