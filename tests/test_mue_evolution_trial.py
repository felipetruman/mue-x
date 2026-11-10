"""Controlled end-to-end evolution trial (10 cycles, ephemeral filesystem).

The purpose is to measure whether the real evolution loop executes and
changes source files. This is NOT evidence of improved task quality.
No mining, network requests, external LLMs or Git commits are allowed.
"""
import hashlib
import json
import random
import tempfile
import unittest
from pathlib import Path

from mue.evo.core import MueAgent
from mue.evo.evolution.signals import Signal


class MueEvolutionTrial(unittest.TestCase):
    def test_08_ten_actual_evolution_cycles(self):
        random.seed(20261110)
        with tempfile.TemporaryDirectory(prefix="mue_proof_") as td:
            agent = MueAgent(td)
            evo = agent.evolution
            # Retain the real AST mutator, code validation, backup and scoring.
            # Disable external integrations and unrelated background behavior.
            evo.miner = None
            evo.autonomous = None
            evo.swarm = None
            evo.auto_corrector = None
            evo.specializer = None
            evo.task_runner = None
            evo.cycle_adapter = None
            evo.curiosity = None
            evo.knowledge_transfer = None
            evo.resources = None
            evo.solidifier.git_enabled = False

            base = {n: hashlib.sha256(g.source_path.read_bytes()).hexdigest()
                    for n, g in agent.genome.genes.items()}
            initial_fitness = agent.genome.stats["avg_fitness"]
            reports = []
            for index in range(10):
                evo.detector.signals = [Signal(
                    type="quality",
                    source="controlled_audit",
                    message=f"Traceback: code performance slow optimize audit_{index}",
                    severity=0.8,
                )]
                result = evo.tick()
                reports.append({
                    "cycle": index + 1,
                    "proposed": result["mutations_proposed"],
                    "applied": result["mutations_applied"],
                    "duration_ms": round(result.get("cycle_time_ms", 0), 2),
                })

            end = {n: hashlib.sha256(g.source_path.read_bytes()).hexdigest()
                   for n, g in agent.genome.genes.items()}
            changed = [n for n in base if n in end and base[n] != end[n]]
            print("AUDIT_EVOLUTION_TRIAL=" + json.dumps({
                "actual_cycles": evo.cycle_count,
                "proposed": sum(r["proposed"] for r in reports),
                "applied": sum(r["applied"] for r in reports),
                "changed_gene_files": changed,
                "initial_avg_fitness": initial_fitness,
                "final_avg_fitness": agent.genome.stats["avg_fitness"],
                "external_quality_benchmark": "not measured",
                "network_mining": "disabled",
                "git_commit": "disabled",
                "per_cycle": reports,
            }, sort_keys=True))
            self.assertEqual(evo.cycle_count, 10)
            self.assertEqual(len(reports), 10)
            self.assertGreater(sum(r["proposed"] for r in reports), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
