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
            def run_smoke_checks():
                """Independent fixed-function checks; not part of the agent's fitness metric."""
                checks = {}
                def load(gene_name):
                    gene = agent.genome.genes[gene_name]
                    namespace = {"__name__": f"audit_{gene_name}"}
                    exec(compile(gene.source_path.read_text("utf-8"),
                                 str(gene.source_path), "exec"), namespace)
                    return namespace
                def attempt(name, fn):
                    try:
                        checks[name] = bool(fn())
                    except Exception as error:
                        checks[name] = False
                        print(f"AUDIT_SMOKE_ERROR {name}: {type(error).__name__}: {error}")
                reasoning = load("reasoning")
                communication = load("communication")
                planning = load("planning")
                persistence = load("persistence")
                attempt("strategy_failure", lambda: reasoning["select_strategy"](
                    {"recent_failures": 5}) == "careful")
                attempt("strategy_success", lambda: reasoning["select_strategy"](
                    {"recent_successes": 7, "resources": 0.8}) == "bold")
                attempt("evaluate_outcome", lambda: reasoning["evaluate_outcome"](
                    "task", "success", 1.0)["score"] > 0.5)
                attempt("format_response", lambda: communication["format_response"](
                    "hello world")["metadata"]["tokens"] == 2)
                attempt("sanitize_output", lambda: communication["sanitize_output"](
                    " a ") == "a")
                attempt("empty_summary", lambda: communication["generate_summary"](
                    []) == "No events to report.")
                def planning_case():
                    planner = planning["TaskPlanner"]()
                    planner.add_task("task", priority=0.9)
                    return planner.next()["description"] == "task"
                attempt("planning", planning_case)
                def persistence_case():
                    cache = persistence["StateCache"](cache_dir=str(
                        Path(td) / "audit_cache"))
                    cache.set("key", 27)
                    return cache.get("key") == 27
                attempt("persistence", persistence_case)
                return checks

            smoke_before = run_smoke_checks()
            start_cycle = evo.cycle_count
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

            smoke_after = run_smoke_checks()
            end = {n: hashlib.sha256(g.source_path.read_bytes()).hexdigest()
                   for n, g in agent.genome.genes.items()}
            changed = [n for n in base if n in end and base[n] != end[n]]
            print("AUDIT_EVOLUTION_TRIAL=" + json.dumps({
                "cycles_executed": evo.cycle_count - start_cycle,
                "prior_cycles": start_cycle,
                "proposed": sum(r["proposed"] for r in reports),
                "applied": sum(r["applied"] for r in reports),
                "changed_gene_files": changed,
                "initial_avg_fitness": initial_fitness,
                "final_avg_fitness": agent.genome.stats["avg_fitness"],
                "smoke_before": smoke_before,
                "smoke_after": smoke_after,
                "smoke_passed_before": sum(smoke_before.values()),
                "smoke_passed_after": sum(smoke_after.values()),
                "external_quality_benchmark": "8 fixed-function smoke checks; not a performance benchmark",
                "network_mining": "disabled",
                "git_commit": "disabled",
                "per_cycle": reports,
            }, sort_keys=True))
            self.assertEqual(evo.cycle_count - start_cycle, 10)
            self.assertEqual(len(reports), 10)
            self.assertGreater(sum(r["proposed"] for r in reports), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
