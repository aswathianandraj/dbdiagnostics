"""Goal-Based Agent.

Mechanism: set a GOAL and SEARCH (breadth-first) for the shortest action sequence that a
simple world model predicts will reach it.

Goal: predicted latency <= SLA, safe actions only, cause confirmed before any optimisation.

Actions have PRECONDITIONS and EFFECTS:
  * diagnostic:   no precondition; effect = cause confirmed
  * optimisation: precondition = cause confirmed; effect = removes `reduction` of the
                  regression (latency - baseline)
  * unsafe (schema change on production): never part of any plan
"""
from collections import deque

from agents.common import UNKNOWN, actions_for, make_result, top_hypothesis

MAX_PLAN_LENGTH = 4


class goalbasedagent:

    @staticmethod
    def goal_reached(state):
        return state["confirmed"] and state["latency"] <= state["sla"]

    @staticmethod
    def applicable(state, action):
        return action.safe and (action.kind == "diagnostic" or state["confirmed"])

    @staticmethod
    def apply(state, action):
        new = dict(state)
        if action.kind == "diagnostic":
            new["confirmed"] = True
        else:
            regression = max(0.0, state["latency"] - state["baseline"])
            new["latency"] = round(state["latency"] - action.reduction * regression, 1)
        return new

    def search(self, start, bottleneck):
        """BFS: the first plan that reaches the goal is the shortest one."""
        candidates = actions_for(bottleneck)
        queue = deque([([], [start])])
        best = None
        while queue:
            plan, states = queue.popleft()
            state = states[-1]
            if self.goal_reached(state):
                return plan, states, True
            if state["confirmed"] and (best is None or state["latency"] < best[1][-1]["latency"]):
                best = (plan, states)
            if len(plan) >= MAX_PLAN_LENGTH:
                continue
            for a in candidates:
                if a not in plan and self.applicable(state, a):
                    queue.append((plan + [a], states + [self.apply(state, a)]))
        return (best[0], best[1], False) if best else ([], [start], False)

    def diagnose(self, scenario):

        bottleneck, evidence, _ = top_hypothesis(scenario)
        start = {"latency": float(scenario["query_latency_ms"]), "sla": float(scenario["expected_sla_ms"]),
                 "baseline": float(scenario.get("baseline_latency_ms") or 0), "confirmed": False}
        plan, states, reached = self.search(start, bottleneck)

        steps = [f"{a.description} (predicted latency after: {s['latency']:.0f} ms)"
                 for a, s in zip(plan, states[1:])]
        trace = [{"step": i + 1, "action": a.name, "predicted_latency_ms": s["latency"]}
                 for i, (a, s) in enumerate(zip(plan, states[1:]))]

        if bottleneck == UNKNOWN:
            reasoning = ("The cause is unknown, so no optimisation's precondition can be met. "
                         "The only valid plan is to collect the missing evidence first.")
            confidence = 0.3
        elif reached:
            reasoning = (f"BFS found the shortest safe plan ({len(plan)} step(s)) reaching the goal: "
                         f"latency {start['latency']:.0f} -> {states[-1]['latency']:.0f} ms "
                         f"(SLA {start['sla']:.0f} ms).")
            confidence = 0.8
        else:
            reasoning = (f"No safe plan of <= {MAX_PLAN_LENGTH} steps reaches the SLA; the best gets to "
                         f"{states[-1]['latency']:.0f} ms. Recommend it and escalate for capacity planning.")
            confidence = 0.6

        last = plan[-1] if plan else None
        return make_result(
            "Goal Based", scenario, bottleneck, evidence,
            steps or ["No action needed: the goal is already met"],
            last.verification_metric if last else "latency vs SLA",
            reasoning, confidence,
            {"goal": f"latency <= {start['sla']:.0f} ms, cause confirmed, safe actions only",
             "goal_reached": reached, "plan": trace},
        )
