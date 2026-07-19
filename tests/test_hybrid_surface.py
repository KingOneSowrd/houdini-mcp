import json
import os
import subprocess
import sys
import unittest

from houdini_catalog import build_registry


HYBRID_TOOLS = {
    "houdini_ping",
    "get_scene_info",
    "create_node",
    "connect_nodes",
    "set_parameters",
    "get_parameter_schema",
    "get_geometry_info",
    "execute_houdini_code",
    "search_tools",
    "get_tool_schema",
    "call_tool",
}

LEGACY_ORIGINALS = {
    "disconnect_node_input",
    "delete_node",
    "set_node_flags",
    "layout_network",
    "find_error_nodes",
    "cook_node",
    "create_wrangle",
    "set_wrangle_code",
    "get_geometry_data",
    "render_single_view",
    "render_quad_views",
    "render_specific_camera",
    "opus_get_model_names",
    "opus_get_model_params_schema",
    "opus_create_model",
    "opus_variate_model",
    "opus_check_job_status",
    "opus_import_model_url",
}


def exposed_names(mode):
    env = os.environ.copy()
    env["HOUDINI_MCP_TOOL_MODE"] = mode
    code = (
        "import json, houdini_mcp_server as b; "
        "print('TOOLS=' + json.dumps(sorted(b.mcp._tool_manager._tools)))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env, check=True
    )
    line = next(item for item in completed.stdout.splitlines() if item.startswith("TOOLS="))
    return set(json.loads(line[6:]))


class HybridSurfaceTests(unittest.TestCase):
    def test_hybrid_surface_is_exactly_eight_plus_three(self):
        self.assertEqual(exposed_names("hybrid"), HYBRID_TOOLS)

    def test_invalid_mode_falls_back_to_hybrid(self):
        self.assertEqual(exposed_names("unexpected"), HYBRID_TOOLS)

    def test_legacy_surface_preserves_original_tools(self):
        names = exposed_names("legacy")
        self.assertEqual(len(names), 29)
        self.assertTrue(HYBRID_TOOLS.issubset(names))
        self.assertTrue(LEGACY_ORIGINALS.issubset(names))

    def test_catalog_has_documented_specs(self):
        registry = build_registry(lambda command, args: {"status": "success", "result": {}})
        self.assertGreaterEqual(len(registry.names()), 31)
        for spec in registry.specs():
            self.assertTrue(spec.docs, spec.name)
            for ref in spec.docs:
                self.assertTrue(ref.archive.endswith(".zip"), spec.name)
                self.assertTrue(ref.entry.endswith(".txt"), spec.name)
                self.assertTrue(ref.official_url.startswith("https://www.sidefx.com/docs/houdini/"), spec.name)

    def test_catalog_validation_and_unsafe_gate(self):
        calls = []
        registry = build_registry(
            lambda command, args: calls.append((command, args)) or {"status": "success", "result": args}
        )
        invalid = registry.invoke("create_node", {"parent_path": "/obj"})
        self.assertEqual(invalid["origin"], "validation")
        denied = registry.invoke("execute_houdini_code", {"code": "print('x')"})
        self.assertEqual(denied["origin"], "risk_policy")
        allowed = registry.invoke(
            "execute_houdini_code", {"code": "print('x')"}, allow_unsafe=True
        )
        self.assertEqual(allowed["status"], "success")
        self.assertEqual(calls[-1][0], "execute_code")


if __name__ == "__main__":
    unittest.main()
