"""Simple Reflex Agent.

Mechanism: IF-THEN rules on the CURRENT snapshot only. No memory, no goal, no scores:
the first rule that fires wins (fixed priority order). That is why it can't tell a
brief blip from a trend, which the model-based agent can.
"""
from tools.diagnostic_tools import (
    inspect_query_plan,
    get_database_metrics,
    get_index_metadata
)

from agents.common import INDEX, POOL, LOAD, HEALTHY, UNKNOWN, actions_for, make_result


class reflexagent:

    def diagnose(self, scenario):

        plan = inspect_query_plan(scenario)
        metrics = get_database_metrics(scenario)
        index = get_index_metadata(scenario)

        if plan == "Full Table Scan" and not index["indexes_present"]:
            rule, bottleneck = "R1 full table scan without index", INDEX
            evidence = [f"plan = {plan}", "no index on the filtered column"]
        elif metrics["connections"] >= metrics["pool_max"] and metrics["waiting_requests"] > 0:
            rule, bottleneck = "R2 pool exhausted", POOL
            evidence = [f"pool {metrics['connections']}/{metrics['pool_max']}",
                        f"{metrics['waiting_requests']} requests waiting"]
        elif metrics["cpu"] > 85:
            rule, bottleneck = "R3 CPU high", LOAD
            evidence = [f"CPU {metrics['cpu']}% > 85%"]
        elif metrics["latency"] <= metrics["sla"]:
            rule, bottleneck = "R4 within SLA", HEALTHY
            evidence = [f"latency {metrics['latency']} ms <= SLA {metrics['sla']} ms"]
        else:
            rule, bottleneck = "R5 no rule matched", UNKNOWN
            evidence = [f"latency {metrics['latency']} ms above SLA, but no rule matched a known cause"]

        actions = actions_for(bottleneck)
        return make_result(
            "Reflex", scenario, bottleneck, evidence,
            [a.description for a in actions],
            actions[-1].verification_metric,
            f"Rule '{rule}' fired on the current snapshot. Rules are checked in a fixed order; "
            "no history, goals or costs are considered.",
            0.4 if bottleneck == UNKNOWN else 0.7,
            {"rule_fired": rule},
        )
