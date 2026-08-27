import argparse
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


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
        self.assertEqual(model["stats"]["workflows"], 8)
        self.assertEqual(model["stats"]["records"], len(self.cli.discover_record_paths()))
        self.assertEqual(model["stats"]["cases"], 5)
        self.assertEqual(model["stats"]["recipes"], 8)
        self.assertGreater(model["stats"]["evidence_gaps"], 0)
        for edge in model["edges"]:
            self.assertIn(edge["data"]["source"], node_ids)
            self.assertIn(edge["data"]["target"], node_ids)
            self.assertIn(edge["data"]["tier"], {"spine", "evidence", "context"})
        spine_edges = [edge for edge in model["edges"] if edge["data"]["tier"] == "spine"]
        self.assertEqual(len(spine_edges), 8)

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
            self.assertIn('<option value="spine">只看主干</option>', content)

    def test_dashboard_cli_builds_requested_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "cli-dashboard.html"
            result = self.cli.main(["dashboard", "--output", str(output)])
            self.assertEqual(result, 0)
            self.assertTrue(output.is_file())


if __name__ == "__main__":
    unittest.main()
