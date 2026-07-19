"""Integration coverage for catalog-only capabilities and SideFX discovery."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import houdini_mcp_server as bridge


PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 19878
CONTAINER = "/obj/MCP_CATALOG_TEST"
bridge._houdini_port = PORT
bridge._houdini_connection = None


def call(name, arguments=None, allow_unsafe=False, expect_error=False):
    response = bridge.tool_registry.invoke(name, arguments or {}, allow_unsafe=allow_unsafe)
    if expect_error:
        assert response["status"] == "error", response
    else:
        assert response["status"] == "success", response
    return response


conn = bridge.get_houdini_connection()
conn.send_command("delete_node", {"path": CONTAINER})

environment = conn.send_command("get_environment_info")
assert environment["status"] == "success", environment
assert environment["result"]["version"], environment
assert environment["result"]["hfs"], environment
print("  PASS  portable Houdini environment info")

invalid = call(
    "create_node", {"node_type": "box", "parent_path": "/obj", "name": "invalid_box"},
    expect_error=True,
)
assert "category" in invalid["message"].lower(), invalid
assert invalid["official_docs"], invalid
print("  PASS  live node category validation + SideFX error docs")

geo = call("create_node", {"node_type": "geo", "parent_path": "/obj", "name": "MCP_CATALOG_TEST"})
geo_path = geo["result"]["path"]
box = call("create_node", {"node_type": "box", "parent_path": geo_path, "name": "box1"})
box_path = box["result"]["path"]

found = call("find_nodes", {"root_path": geo_path, "type_pattern": "box"})
assert found["result"]["total"] == 1, found
info = call("get_node_info", {"path": box_path})
assert info["result"]["type"] == "box", info
print("  PASS  catalog node search + detail")

modified = call(
    "modify_node",
    {"path": box_path, "position": [2, 3], "parameters": {"size": [2, 3, 4], "sze": 9}},
)
assert modified["result"]["changed"], modified
assert modified["result"]["failed"] and "Did you mean" in modified["result"]["failed"][0]["error"], modified
print("  PASS  modify_node changed/failed reporting")

material = call("set_material", {"node_path": geo_path, "name": "mcp_catalog_material"})
assert material["result"]["material_node"], material
assert material["result"]["material_type"], material
print("  PASS  live material type resolution + assignment")

hip_info = call("get_hip_info")
assert "has_unsaved_changes" in hip_info["result"], hip_info
with tempfile.TemporaryDirectory() as temp_dir:
    existing = os.path.join(temp_dir, "existing.hip")
    with open(existing, "wb") as handle:
        handle.write(b"not a hip")
    protected = call("save_hip", {"path": existing}, expect_error=True)
    assert "overwrite" in protected["message"].lower(), protected
    destination = os.path.join(temp_dir, "catalog_test.hip")
    saved = call("save_hip", {"path": destination})
    assert os.path.isfile(destination), saved
print("  PASS  HIP info + overwrite-protected save")

bridge._docs_provider = None
search = bridge.search_tools(None, "box", limit=5)
assert search["docs_status"] == "available", search
assert any(item["local_ref"] == "nodes.zip:sop/box.txt" for item in search["official_docs"]), search
schema = bridge.get_tool_schema(None, "create_node")
assert schema["status"] == "success" and schema["result"]["official_docs"], schema
print("  PASS  joint tool + bundled SideFX document search")

call("delete_node", {"path": geo_path})
bridge._houdini_connection.disconnect()
bridge._houdini_connection = None
print("\nALL CATALOG INTEGRATION TESTS PASSED")
