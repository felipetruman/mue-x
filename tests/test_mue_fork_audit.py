"""Reproducible, read-only MUE-X audit tests.
These checks demonstrate unsafe or misleading behavior; a green result
means the specific defect was reproduced, not that MUE-X is production-ready.
All file mutations are restricted to temporary directories.
"""
import ast
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from mue.evo.dna.genome import Genome
from mue.evo.dna.mutator import ExploitInjector
from mue.evo.dna.sandbox import GeneSandbox
from mue.evo.self_modification.pipeline import PipelineResult, SelfModificationPipeline


class MueProofTests(unittest.TestCase):
    def test_01_smoke_import(self):
        from mue.evo.core import MueAgent
        self.assertTrue(callable(MueAgent))
        print("AUDIT: core import OK")

    def test_02_kernel_integrity_empty_seal(self):
        actual_root = Path(__file__).resolve().parents[1] / "mue"
        self.assertTrue((actual_root / "evo" / "dna" / "genome.py").is_file())
        genome = Genome(actual_root)
        sealed = genome.seal_kernel()
        intact, violations = genome.verify_kernel()
        self.assertEqual(sealed, {}, "Integrity seal unexpectedly contained protected module hashes")
        self.assertTrue(intact, "Empty seal was unexpectedly rejected")
        self.assertEqual(violations, [])
        print("AUDIT: CONFIRMED: kernel declared intact despite zero protected hashes")

    def test_03_import_stage_only_compiles(self):
        with tempfile.TemporaryDirectory() as td:
            pipeline = SelfModificationPipeline(Path(td))
            mutation = PipelineResult(
                gene_name="demo",
                source_after="import __mue_package_that_does_not_exist_20261110\n",
            )
            stage = pipeline._stage_import_test(mutation)
            self.assertTrue(stage.passed, f"Import stage rejected missing dependency: {stage.error}")
            print("AUDIT: CONFIRMED: missing dependency passes claimed import check")

    def test_04_failed_tests_still_applied(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gene = root / "demo.py"
            before = "def baseline():\n    return 1\n"
            broken = "def test_broken():\n    raise AssertionError('intentional audit failure')\n"
            gene.write_text(before, encoding="utf-8")
            pipeline = SelfModificationPipeline(root)
            result = pipeline.run(
                "demo", before,
                llm_call=lambda **kwargs: {
                    "modified_source": broken,
                    "reasoning": "audit fixture",
                    "confidence": 1.0,
                },
            )
            execution = [s for s in result.stages if s.name == "execute_test"]
            self.assertEqual(len(execution), 1)
            self.assertFalse(execution[0].passed, "Broken fixture should fail test gate")
            self.assertTrue(result.success, "Main run unexpectedly rejected a failing test")
            self.assertEqual(gene.read_text(encoding="utf-8"), broken)
            print("AUDIT: CONFIRMED: failing tests still result in successful code replacement")

    def test_05_gene_sandbox_reports_runtime_error_as_success(self):
        result = GeneSandbox(timeout=2).test_gene(
            "audit_runtime",
            "def failing_function():\n    raise RuntimeError('intentional audit failure')\n",
        )
        self.assertIn("SANDBOX_RUNTIME_ERROR", result.stderr)
        self.assertTrue(result.success, "GeneSandbox rejected the runtime error")
        print("AUDIT: CONFIRMED: runtime exception logged but subprocess marked successful")

    def test_06_ast_repr_changes_semantics(self):
        code = ("class Sample:\n"
                "    value: int\n"
                "    def __init__(self, value):\n"
                "        self.value = value\n")
        original = {}
        exec(code, original)
        self.assertIn("Sample", repr(original["Sample"](3)))
        tree = ast.parse(code)
        transformer = ExploitInjector()
        updated = transformer.visit(tree)
        ast.fix_missing_locations(updated)
        namespace = {}
        exec(compile(updated, "<mue-exploit>", "exec"), namespace)
        self.assertTrue(transformer.changes_made)
        with self.assertRaises(NameError):
            repr(namespace["Sample"](3))
        print("AUDIT: CONFIRMED: exploit AST mutation produces a broken __repr__")

    def test_07_evolve_command_does_not_force_tick(self):
        from mue.evo.core import MueAgent
        with tempfile.TemporaryDirectory() as td:
            agent = MueAgent(td)
            agent.detector.get_evolution_pressure = lambda: 0.0
            agent.evolution.tick = Mock(return_value={"mutations_applied": 0})
            response = agent.chat("/mue evolve")
            agent.evolution.tick.assert_not_called()
            self.assertFalse(response["evolved"])
        print("AUDIT: CONFIRMED: /mue evolve does not force evolution if pressure is low")


if __name__ == "__main__":
    unittest.main(verbosity=2)
