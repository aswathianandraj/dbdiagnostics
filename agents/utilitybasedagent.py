"""Utility-Based Agent.

Mechanism: score EVERY candidate action and pick the highest expected utility:

    EU = P(cause | evidence) x benefit - 0.05 x cost - 0.5 x risk - 10 (if it is a schema change)

Unlike the goal-based agent (which asks "which sequence REACHES the SLA?"), this agent asks
"which single action is the best trade-off under uncertainty?". The unsafe
"Create Index Now" is scored too, so the table shows WHY it loses.
"""
from agents.common import ACTIONS, UNKNOWN, make_result, score_evidence

COST_WEIGHT = 0.05
RISK_WEIGHT = 0.5
UNSAFE_PENALTY = 10.0
DIAGNOSTIC_VALUE = 0.15


class utilitybasedagent:

    @staticmethod
    def benefit(action):
        return action.reduction if action.kind == "optimization" else DIAGNOSTIC_VALUE

    def expected_utility(self, action, probs):
        eu = probs.get(action.addresses, 0.0) * self.benefit(action)
        eu -= COST_WEIGHT * action.cost + RISK_WEIGHT * action.risk
        if not action.safe:
            eu -= UNSAFE_PENALTY
        return eu

    def diagnose(self, scenario):

        scores, why = score_evidence(scenario)
        total = sum(scores.values())
        probs = {b: round(v / total, 3) for b, v in scores.items()}

        table = sorted(
            ({"action": a.name, "addresses": a.addresses, "safe": a.safe, "P(cause)": probs[a.addresses],
              "benefit": self.benefit(a), "cost": a.cost, "risk": a.risk,
              "EU": round(self.expected_utility(a, probs), 3)} for a in ACTIONS),
            key=lambda r: r["EU"], reverse=True)

        best = next(a for a in ACTIONS if a.name == table[0]["action"])
        bottleneck = best.addresses
        chosen = [best] + [a for r in table[1:] for a in ACTIONS
                           if a.name == r["action"] and a.addresses == bottleneck and a.safe and r["EU"] > 0]
        unsafe = next(r for r in table if not r["safe"])

        evidence = list(why[bottleneck] or ["no strong signal for any known cause"])
        evidence.append("P(cause): " + ", ".join(f"{b} {p:.2f}" for b, p in
                                                sorted(probs.items(), key=lambda kv: -kv[1]) if p > 0))
        return make_result(
            "Utility Based", scenario, bottleneck, evidence,
            [f"{a.description} (EU {self.expected_utility(a, probs):+.3f})" for a in chosen],
            best.verification_metric,
            f"Scored all {len(ACTIONS)} actions; best is '{best.name}' (EU {table[0]['EU']:+.3f}). "
            f"The unsafe '{unsafe['action']}' scores {unsafe['EU']:+.2f} because of the schema-change penalty.",
            0.3 if bottleneck == UNKNOWN else probs[bottleneck],
            {"probabilities": probs, "utility_table": table},
        )
