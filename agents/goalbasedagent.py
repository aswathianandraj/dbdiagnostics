from tools.diagnostic_tools import (
    inspect_query_plan,
    get_database_metrics
)


class goalbasedagent:

    def diagnose(self, scenario):

        metrics = get_database_metrics(scenario)
        plan = inspect_query_plan(scenario)

        if plan == "Full Table Scan":

            bottleneck = "Query inefficiency"

            recommendation = (
                "Reduce latency by reviewing indexing strategy."
            )

        elif (
            metrics["connections"]
            >= scenario["connection_pool_max"]
        ):

            bottleneck = "Connection pool saturation"

            recommendation = (
                "Reduce waiting time by investigating pool exhaustion."
            )

        else:

            bottleneck = "High system load"

            recommendation = (
                "Reduce resource utilization during peak traffic."
            )

        return {
            "agent": "Goal Based",
            "bottleneck": bottleneck,
            "recommendation": recommendation
        }