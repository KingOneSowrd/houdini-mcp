import argparse
import base64
import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "houdini-production-workflows"
CLI_PATH = SKILL_ROOT / "scripts" / "experience_cli.py"
DASHBOARD_PATH = SKILL_ROOT / "scripts" / "build_dashboard.py"


def load_cli_module():
    spec = importlib.util.spec_from_file_location("houdini_experience_cli", CLI_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_dashboard_module():
    scripts_path = str(SKILL_ROOT / "scripts")
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)
    spec = importlib.util.spec_from_file_location("houdini_knowledge_dashboard", DASHBOARD_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ExperienceSystemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cli = load_cli_module()
        cls.dashboard = load_dashboard_module()

    def test_all_curated_records_validate(self):
        paths = self.cli.discover_record_paths()
        self.assertGreaterEqual(len(paths), 13)
        failures, reports = self.cli.validate_paths(paths)
        self.assertEqual(failures, 0, reports)

    def test_strict_schema_rejects_unknown_fields(self):
        record = self.cli.load_json(
            SKILL_ROOT / "references" / "records" / "recipes" / "curve-instancing-v1.json"
        )
        record["unexpected"] = True
        errors = self.cli.validate_instance(record, self.cli.schema_for(record))
        self.assertTrue(any("unexpected property" in error for error in errors))

    def test_candidate_recipe_reports_missing_promotion_evidence(self):
        record = self.cli.load_json(
            SKILL_ROOT / "references" / "records" / "recipes" / "curve-instancing-v1.json"
        )
        report = self.cli.assessment(record)
        self.assertEqual(report["suggested_status"], "candidate")
        self.assertIn("at least two independent cases", report["missing_evidence"])
        self.assertIn("at least one execution record", report["missing_evidence"])

    def test_new_experience_is_valid_and_candidate(self):
        with tempfile.TemporaryDirectory() as temporary:
            original_root = self.cli.RECORD_ROOT
            self.cli.RECORD_ROOT = Path(temporary)
            try:
                args = argparse.Namespace(
                    goal="Build a modular fence",
                    workflow="curve-instancing",
                    id="exp-test-fence",
                    houdini="21.0.440",
                    sidefx_labs="21.0",
                    engine="unreal",
                    project="test",
                    hip="test.hip",
                    recipe_id="curve-instancing-v1",
                    case_id=["project-titan-curve-modules"],
                    tag=["test"],
                    overwrite=False,
                )
                path = self.cli.new_experience(args)
                record = json.loads(path.read_text(encoding="utf-8"))
                errors = self.cli.validate_instance(record, self.cli.schema_for(record))
                self.assertEqual(errors, [])
                self.assertEqual(record["status"], "candidate")
            finally:
                self.cli.RECORD_ROOT = original_root

    def test_workflow_index_references_and_recipes_exist(self):
        index = json.loads(
            (SKILL_ROOT / "references" / "workflow-index.json").read_text(encoding="utf-8")
        )
        for workflow in index["workflows"]:
            self.assertTrue((SKILL_ROOT / "references" / workflow["reference"]).is_file())
            recipe = SKILL_ROOT / "references" / "records" / "recipes" / f"{workflow['id']}-v1.json"
            self.assertTrue(recipe.is_file(), workflow["id"])

    def test_record_index_matches_discovery(self):
        index = json.loads(
            (SKILL_ROOT / "references" / "records" / "index.json").read_text(encoding="utf-8")
        )
        discovered = {
            (self.cli.load_json(path).get("id") or self.cli.load_json(path).get("template_id"))
            for path in self.cli.discover_record_paths()
        }
        indexed = {entry["id"] for entry in index["records"]}
        self.assertEqual(indexed, discovered)

    def test_dashboard_model_has_valid_graph_and_real_counts(self):
        model = self.dashboard.build_model()
        node_ids = {node["data"]["id"] for node in model["nodes"]}
        workflows = self.cli.load_json(SKILL_ROOT / "references" / "workflow-index.json")["workflows"]
        records = [self.cli.load_json(path) for path in self.cli.discover_record_paths()]
        self.assertEqual(model["stats"]["workflows"], len(workflows))
        self.assertEqual(model["stats"]["records"], len(self.cli.discover_record_paths()))
        for kind, key in (("case", "cases"), ("recipe", "recipes"), ("experience", "experiences")):
            self.assertEqual(model["stats"][key], sum(record["record_type"] == kind for record in records))
        self.assertEqual(model["warnings"], [])
        self.assertGreater(model["stats"]["evidence_gaps"], 0)
        for edge in model["edges"]:
            self.assertIn(edge["data"]["source"], node_ids)
            self.assertIn(edge["data"]["target"], node_ids)
            self.assertIn(edge["data"]["tier"], {"spine", "evidence", "context"})
        spine_edges = [edge for edge in model["edges"] if edge["data"]["tier"] == "spine"]
        self.assertEqual(len(spine_edges), sum(record["record_type"] in {"recipe", "template_manifest"} for record in records))

    def test_successful_retrospective_is_linked_without_claiming_a_new_recipe_run(self):
        record_root = SKILL_ROOT / "references" / "records"
        experience = self.cli.load_json(record_root / "experiences" / "exp-hair-tangent-baker-2-11-success.json")
        recipe = self.cli.load_json(record_root / "recipes" / "hda-authoring-v1.json")
        case = self.cli.load_json(record_root / "cases" / "hair-tangent-baker-2-11-success.json")
        self.assertEqual(experience["acceptance"]["metrics"]["outcome"], "user_accepted_success")
        self.assertEqual(experience["provenance"]["case_ids"], [case["id"]])
        self.assertIn(experience["id"], recipe["evidence"]["experience_ids"])
        self.assertEqual(experience["provenance"]["recipe_id"], "")
        self.assertEqual(experience["operations"], [])
        self.assertFalse(case["acceptance"]["verified"])
        self.assertEqual(recipe["status"], "candidate")
        self.assertEqual(recipe["evidence"]["last_verified"], "")
        self.assertIn("at least two independent cases", self.cli.assessment(recipe)["missing_evidence"])

    def test_dashboard_render_is_self_contained(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "knowledge.html"
            rendered = self.dashboard.render_dashboard(output)
            content = rendered.read_text(encoding="utf-8")
            self.assertGreater(rendered.stat().st_size, 400_000)
            self.assertNotIn("__KNOWLEDGE_MODEL__", content)
            self.assertNotIn("/*__CYTOSCAPE_BUNDLE__*/", content)
            self.assertNotIn('src="http', content)
            self.assertNotIn("fetch(", content)
            self.assertIn("project-titan-curve-modules", content)
            self.assertIn("cytoscape", content)
            self.assertIn('id="relation-filter"', content)
            for relation_mode in ("spine", "evidence", "all"):
                self.assertIn(f'<option value="{relation_mode}">', content)

    def test_dashboard_cli_builds_requested_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "cli-dashboard.html"
            result = self.cli.main(["dashboard", "--output", str(output)])
            self.assertEqual(result, 0)
            self.assertTrue(output.is_file())

    def test_houdini_icons_are_embedded_from_a_local_archive(self):
        inkscape_svg = (
            '<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" '
            'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
            'xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd" '
            'viewBox="0 0 16 16" sodipodi:docname="x.svg">'
            '<sodipodi:namedview id="nv"><inkscape:page x="0" y="0"/></sodipodi:namedview>'
            '<metadata><rdf/></metadata><rect inkscape:label="r" width="8" height="8"/></svg>'
        )
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "icons.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("BUTTONS/recipe.svg", inkscape_svg)
                bundle.writestr("SOP/copytocurves.svg", inkscape_svg)
            found = self.dashboard.discover_icon_archive({"HOUDINI_MCP_ICON_ARCHIVE": str(archive)})
            self.assertEqual(found, archive)
            workflows = [{"id": "curve-instancing", "icon": "SOP/copytocurves"}, {"id": "no-icon"}]
            icons = self.dashboard.load_icons(workflows, found)

        self.assertTrue(icons["available"])
        self.assertEqual(set(icons["types"]), {"recipe"})
        self.assertEqual(set(icons["workflows"]), {"curve-instancing"})
        svg = base64.b64decode(icons["types"]["recipe"].split(",", 1)[1]).decode("utf-8")
        ElementTree.fromstring(svg)  # still well-formed after removing editor data
        for editor_data in ("namedview", "inkscape", "sodipodi", "metadata"):
            self.assertNotIn(editor_data, svg)
        self.assertIn("<rect", svg)

    def test_dashboard_degrades_without_houdini_icons(self):
        self.assertIsNone(self.dashboard.discover_icon_archive({}))
        self.assertIsNone(self.dashboard.discover_icon_archive({"HOUDINI_MCP_ICON_ARCHIVE": "missing/icons.zip"}))
        model = self.dashboard.build_model(icon_archive=None)
        self.assertFalse(model["icons"]["available"])
        with tempfile.TemporaryDirectory() as temporary:
            rendered = self.dashboard.render_dashboard(Path(temporary) / "plain.html", icon_archive=None)
            self.assertNotIn("data:image/svg+xml;base64", rendered.read_text(encoding="utf-8"))

    def test_template_ships_no_sidefx_assets(self):
        template = (SKILL_ROOT / "dashboard" / "index.template.html").read_text(encoding="utf-8")
        self.assertNotIn("data:image/svg+xml;base64", template)
        self.assertNotIn("icons.zip", template)


if __name__ == "__main__":
    unittest.main()
