"""Model-Based Reflex Agent.

Mechanism: rules, like the reflex agent, but applied to an INTERNAL STATE built from the
metric `history`, not just the current snapshot:
  * pool_saturated_streak: consecutive latest windows with the pool full and requests waiting
  * latency_trend:         rising / flat / single_window
  * latency_tracks_load:   latency, traffic and CPU all rise together -> capacity problem
  * missing_data:          what evidence is absent

"Latency rises WITH traffic" (Scenario C) vs "latency high at FLAT traffic" (Scenario A)
can only be told apart from history; a single snapshot can't show it.
"""
from tools.diagnostic_tools import (
    inspect_query_plan,
    get_database_metrics,
    get_index_metadata
)

from agents.common import INDEX, POOL, LOAD, HEALTHY, UNKNOWN, actions_for, make_result


class modelbasedagent:

    def update_state(self, scenario):

        metrics = get_database_metrics(scenario)
        history = metrics["history"]

        streak = 0
        for w in reversed(history):
            if w["pool_used"] >= metrics["pool_max"] and w["waiting"] > 0:
                streak += 1
            else:
                break

        if len(history) < 2:
            trend, qps_change, cpu_change = "single_window", 0.0, 0.0
        else:
            first, last = history[0], history[-1]
            trend = "rising" if (last["latency_ms"] - first["latency_ms"]) / first["latency_ms"] > 0.2 else "flat"
            qps_change = (last["qps"] - first["qps"]) / first["qps"]
            cpu_change = last["cpu"] - first["cpu"]

        missing = []
        if inspect_query_plan(scenario) is None:
            missing.append("query plan")
        if not scenario.get("logs"):
            missing.append("logs")
        if len(history) < 2:
            missing.append("metric history")

        return {
            "windows_seen": len(history),
            "pool_saturated_streak": streak,
            "latency_trend": trend,
            "qps_change_pct": round(100 * qps_change, 1),
            "cpu_change_pts": cpu_change,
            "latency_tracks_load": trend == "rising" and qps_change > 0.3 and cpu_change > 15,
            "full_scan_without_index": (inspect_query_plan(scenario) == "Full Table Scan"
                                        and not get_index_metadata(scenario)["indexes_present"]),
            "within_sla": metrics["latency"] <= metrics["sla"],
            "missing_data": missing,
        }

    def diagnose(self, scenario):

        state = self.update_state(scenario)
        confidence = 0.8

        if state["within_sla"] and state["latency_trend"] != "rising":
            rule, bottleneck = "M1 within SLA and not trending up", HEALTHY
            evidence = [f"latency within SLA across {state['windows_seen']} windows, trend {state['latency_trend']}"]
        elif state["pool_saturated_streak"] >= 2:
            rule, bottleneck = "M2 pool saturated for >= 2 windows", POOL
            evidence = [f"pool full with requests waiting for {state['pool_saturated_streak']} consecutive windows",
                        f"CPU flat ({state['cpu_change_pts']:+} pts), so the DB itself is not overloaded"]
        elif state["latency_tracks_load"]:
            rule, bottleneck = "M3 latency rises with traffic and CPU", LOAD
            evidence = [f"traffic {state['qps_change_pct']:+}% and CPU {state['cpu_change_pts']:+} pts "
                        "across the windows while latency rose", "query plans use indexes"]
        elif state["full_scan_without_index"] and abs(state["qps_change_pct"]) < 10:
            rule, bottleneck = "M4 full scan at flat traffic", INDEX
            evidence = ["full table scan with no index",
                        f"latency high at FLAT traffic ({state['qps_change_pct']:+}%), so not a load problem"]
        else:
            rule, bottleneck = "M5 no pattern / missing data", UNKNOWN
            evidence = [f"missing: {', '.join(state['missing_data']) or 'nothing, but no pattern matched'}"]
            confidence = 0.3

        actions = actions_for(bottleneck)
        return make_result(
            "Model Based", scenario, bottleneck, evidence,
            [a.description for a in actions],
            actions[-1].verification_metric,
            f"Built an internal state from {state['windows_seen']} history window(s); "
            f"rule '{rule}' fired on that state.",
            confidence,
            {"state": state, "rule_fired": rule},
        )
