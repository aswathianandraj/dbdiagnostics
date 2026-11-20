"""Learning Agent.

Mechanism (the four parts from the lectures):
  * performance element: picks the action with the best past success rate for the diagnosed cause
  * critic:              judges the outcome (simulated: did the verification metric improve?)
  * learning element:    updates data/experience.json (success / failure counts)
  * problem generator:   with probability EPSILON, tries the least-tried action (exploration)

Success rate uses Laplace smoothing, (s + 1) / (n + 2): an untried action starts at 0.5
and one lucky success doesn't look like 100%. Because every run updates the history,
the same scenario can get a different recommendation over time.
"""
import copy
import json
import random
from pathlib import Path

from agents.common import UNKNOWN, actions_for, make_result, top_hypothesis

EXPERIENCE_FILE = Path(__file__).resolve().parent.parent / "data" / "experience.json"
EPSILON = 0.1


class learningagent:

    def __init__(self, experience_file=EXPERIENCE_FILE, seed=42, persist=True):
        self.experience_file = Path(experience_file)
        self.rng = random.Random(seed)
        self.persist = persist  # tests use persist=False so they never change the real file

    def load(self):
        if self.experience_file.exists():
            return json.loads(self.experience_file.read_text(encoding="utf-8"))
        return {}

    def save(self, history):
        if self.persist:
            self.experience_file.write_text(json.dumps(history, indent=4), encoding="utf-8")

    @staticmethod
    def success_rate(stats):
        s, f = stats.get("success", 0), stats.get("failure", 0)
        return (s + 1) / (s + f + 2)

    def simulate_outcome(self, bottleneck, action):
        """Simulated critic: an action 'works' if it targets the diagnosed cause, with noise."""
        return self.rng.random() < (0.8 if action.addresses == bottleneck else 0.1)

    def diagnose(self, scenario):

        history = self.load()
        bottleneck, evidence, _ = top_hypothesis(scenario)
        past = history.get(bottleneck, {})

        ranked = sorted(((a, past.get(a.name, {"success": 0, "failure": 0})) for a in actions_for(bottleneck)),
                        key=lambda r: self.success_rate(r[1]), reverse=True)
        explored = len(ranked) > 1 and self.rng.random() < EPSILON
        action, before = (min(ranked, key=lambda r: sum(r[1].values())) if explored else ranked[0])
        before = copy.deepcopy(before)
        rate = self.success_rate(before)

        outcome = self.simulate_outcome(bottleneck, action)                       # critic
        stats = history.setdefault(bottleneck, {}).setdefault(action.name, {"success": 0, "failure": 0})
        stats["success" if outcome else "failure"] += 1                             # learning element
        self.save(history)

        record = [f"{a.name}: {s['success']}/{s['success'] + s['failure']} worked "
                  f"(rate {self.success_rate(s):.2f})" for a, s in ranked]
        why = ("explored the least-tried action (problem generator)" if explored else
               f"chose '{action.name}' because it has the best smoothed success rate ({rate:.2f})")
        return make_result(
            "Learning Agent", scenario, bottleneck,
            evidence + ["past outcomes: " + "; ".join(record)],
            [action.description] + [a.description for a, _ in ranked if a is not action],
            action.verification_metric,
            f"{why}. Simulated verification: {'SUCCESS' if outcome else 'FAILURE'}. History "
            f"{before['success']}/{sum(before.values())} -> {stats['success']}/{sum(stats.values())}.",
            min(rate, 0.3) if bottleneck == UNKNOWN else rate,
            {"chosen_action": action.name, "explored": explored, "before": before,
             "after": dict(stats), "persisted": self.persist},
        )
