import unittest
from typing import Optional

from tool_registry import DocRef, ToolArguments, ToolRegistry, ToolSpec
from houdini_catalog import build_registry as build_houdini_registry


class EchoArguments(ToolArguments):
    value: int
    label: Optional[str] = None


DOC = DocRef(
    kind="hom",
    archive="hom.zip",
    entry="hou/Node.txt",
    symbol="hou.Node",
    official_url="https://www.sidefx.com/docs/houdini/hom/hou/Node.html",
)


def build_registry(risk="low"):
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="node_echo",
            category="node",
            description="Echo a node-related value.",
            keywords=("inspect", "value"),
            arguments_model=EchoArguments,
            invoke=lambda args: {"value": args["value"], "label": args.get("label")},
            docs=[DOC],
            risk=risk,
        )
    )
    return registry


class ToolRegistryTests(unittest.TestCase):
    def test_registration_requires_docs(self):
        with self.assertRaisesRegex(ValueError, "SideFX"):
            ToolRegistry().register(
                ToolSpec(
                    name="invalid",
                    category="test",
                    description="Missing docs",
                    arguments_model=EchoArguments,
                    invoke=lambda args: args,
                    docs=[],
                )
            )

    def test_search_and_schema(self):
        registry = build_registry()
        result = registry.search("inspect")
        self.assertEqual([item["name"] for item in result], ["node_echo"])
        schema = registry.get("node_echo").schema("21.0.440")
        self.assertIn("value", schema["input_schema"]["properties"])
        self.assertEqual(schema["official_docs"][0]["houdini_version"], "21.0.440")

    def test_search_supports_multiple_words_and_pagination(self):
        registry = build_registry()
        self.assertEqual(registry.search("node inspect", offset=0, limit=1)[0]["name"], "node_echo")
        self.assertEqual(registry.search("node inspect", offset=1, limit=1), [])

    def test_validation_rejects_extra_fields(self):
        result = build_registry().invoke("node_echo", {"value": 1, "typo": True})
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["origin"], "validation")

    def test_high_risk_requires_opt_in(self):
        registry = build_registry(risk="high")
        denied = registry.invoke("node_echo", {"value": 2})
        self.assertEqual(denied["origin"], "risk_policy")
        allowed = registry.invoke("node_echo", {"value": 2}, allow_unsafe=True)
        self.assertEqual(allowed["status"], "success")
        self.assertEqual(allowed["result"]["value"], 2)

    def test_availability_is_reported(self):
        registry = ToolRegistry()
        registry.register(
            ToolSpec(
                name="offline",
                category="external",
                description="Unavailable external tool",
                arguments_model=EchoArguments,
                invoke=lambda args: args,
                docs=[DOC],
                availability=lambda: (False, "not configured"),
            )
        )
        summary = registry.search()[0]
        self.assertFalse(summary["available"])
        self.assertEqual(summary["unavailable_reason"], "not configured")

    def test_expansion_catalog_is_strict_and_catalog_only(self):
        registry = build_houdini_registry(lambda command, args: {"status": "success", "result": args})
        expected = {
            "search_node_types", "get_node_type_schema", "get_network_snapshot",
            "analyze_hda_candidate", "search_hda_definitions", "get_hda_info",
            "create_hda_from_subnetwork", "validate_hda", "apply_graph_patch",
        }
        self.assertTrue(expected.issubset(set(registry.names())))
        invalid = registry.invoke("get_network_snapshot", {"path": "/obj", "unknown": True})
        self.assertEqual(invalid["origin"], "validation")
        overwrite = registry.invoke(
            "create_hda_from_subnetwork",
            {"path": "/obj/subnet1", "type_name": "demo::asset::1.0", "label": "Demo", "library_path": "demo.hda", "overwrite": True},
            allow_unsafe=True,
        )
        self.assertEqual(overwrite["origin"], "validation")

    def test_hda_disk_write_requires_unsafe_opt_in(self):
        registry = build_houdini_registry(lambda command, args: {"status": "success", "result": args})
        denied = registry.invoke(
            "create_hda_from_subnetwork",
            {"path": "/obj/subnet1", "type_name": "demo::asset::1.0", "label": "Demo", "library_path": "demo.hda"},
        )
        self.assertEqual(denied["origin"], "risk_policy")


if __name__ == "__main__":
    unittest.main()
