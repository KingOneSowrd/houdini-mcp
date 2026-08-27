import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from houdini_mcp_bridge.sidefx_docs import SideFXDocsProvider, discover_help_root, official_url
from houdini_mcp_bridge.catalog import build_registry
from houdini_mcp_bridge.registry import DocRef


def make_help_root(parent: Path, version: str = "") -> Path:
    root = parent / (f"hfs{version}" if version else "install") / "houdini" / "help"
    root.mkdir(parents=True)
    with zipfile.ZipFile(root / "hom.zip", "w") as archive:
        archive.writestr(
            "hou/Node.txt",
            "hou.Node\nThe base class for node-like objects in Houdini.\nUse hou.node to resolve paths.",
        )
        archive.writestr(
            "hou/hipFile.txt",
            "hou.hipFile\nFunctions for loading and saving Houdini scene files.",
        )
    with zipfile.ZipFile(root / "nodes.zip", "w") as archive:
        archive.writestr(
            "sop/box.txt",
            "Box\nCreates a cube or six-sided rectangular box.\nThe size parameter controls dimensions.",
        )
    return root


class SideFXDocsTests(unittest.TestCase):
    def test_override_has_highest_priority(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            override = make_help_root(base / "override")
            connected = make_help_root(base / "connected")
            found = discover_help_root(
                {"HOUDINI_MCP_DOC_ROOT": str(override)},
                {"hfs": str(connected.parent.parent)},
            )
            self.assertEqual(found, override.resolve())

    def test_connected_houdini_beats_process_environment(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            connected = make_help_root(base / "connected")
            inherited = make_help_root(base / "inherited")
            found = discover_help_root(
                {"HFS": str(inherited.parent.parent)},
                {"hfs": str(connected.parent.parent)},
            )
            self.assertEqual(found, connected.resolve())

    def test_platform_roots_are_portable_and_version_sorted(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            old = make_help_root(base, "20.5.100")
            new = make_help_root(base, "21.0.440")
            with mock.patch("houdini_mcp_bridge.sidefx_docs._windows_install_roots", return_value=[old.parent.parent, new.parent.parent]):
                found = discover_help_root({}, system_name="Windows")
            self.assertEqual(found, new.resolve())
            with mock.patch("houdini_mcp_bridge.sidefx_docs._mac_install_roots", return_value=[new.parent.parent]):
                self.assertEqual(discover_help_root({}, system_name="Darwin"), new.resolve())
            with mock.patch("houdini_mcp_bridge.sidefx_docs._linux_install_roots", return_value=[new.parent.parent]):
                self.assertEqual(discover_help_root({}, system_name="Linux"), new.resolve())

    def test_search_and_reference_resolution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = make_help_root(Path(temp))
            provider = SideFXDocsProvider(root, "21.0.440")
            result = provider.search("box")
            self.assertEqual(result[0]["local_ref"], "nodes.zip:sop/box.txt")
            self.assertEqual(result[0]["houdini_version"], "21.0.440")
            refs = provider.resolve_refs(
                [
                    DocRef(
                        kind="hom",
                        archive="hom.zip",
                        entry="hou/Node.txt",
                        symbol="hou.Node",
                        official_url=official_url("hom.zip", "hou/Node.txt"),
                    )
                ]
            )
            self.assertTrue(refs[0]["available_locally"])
            self.assertIn("node-like", refs[0]["summary"])

    def test_missing_docs_degrades_without_network(self):
        with mock.patch("houdini_mcp_bridge.sidefx_docs._windows_install_roots", return_value=[]), mock.patch(
            "houdini_mcp_bridge.sidefx_docs._mac_install_roots", return_value=[]
        ), mock.patch("houdini_mcp_bridge.sidefx_docs._linux_install_roots", return_value=[]):
            provider = SideFXDocsProvider(help_root=None, environment={}, houdini_info={})
            self.assertEqual(provider.status, "degraded")
            self.assertEqual(provider.search("box"), [])

    def test_official_urls_do_not_contain_machine_paths(self):
        self.assertEqual(
            official_url("nodes.zip", "sop/box.txt"),
            "https://www.sidefx.com/docs/houdini/nodes/sop/box.html",
        )
        self.assertEqual(
            official_url("hom.zip", "hou/hipFile.txt"),
            "https://www.sidefx.com/docs/houdini/hom/hou/hipFile.html",
        )

    def test_installed_sidefx_references_when_docs_are_available(self):
        provider = SideFXDocsProvider()
        if provider.status != "available":
            self.skipTest("No local SideFX help archives installed")
        registry = build_registry(lambda command, args: {"status": "success", "result": {}})
        missing = []
        for spec in registry.specs():
            for ref in spec.docs:
                if not provider.resolve_refs([ref])[0]["available_locally"]:
                    missing.append(f"{spec.name}:{ref.archive}:{ref.entry}")
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
