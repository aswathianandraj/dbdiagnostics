from tools.diagnostic_tools import (
    inspect_query_plan,
    get_database_metrics
)


class modelbasedagent:

    def diagnose(self, scenario):

        plan = inspect_query_plan(scenario)
        metrics = get_database_metrics(scenario)

        if (
            plan == "Full Table Scan"
            and metrics["cpu"] < 70
        ):

            bottleneck = "Inefficient query execution"

            recommendation = (
                "Review indexing opportunities and query filters."
            )

        elif (
            metrics["connections"]
            >= scenario["connection_pool_max"]
        ):

            bottleneck = "Connection bottleneck"

            recommendation = (
                "Analyze connection usage and pool behaviour."
            )

        elif metrics["cpu"] > 85:

            bottleneck = "Resource saturation"

            recommendation = (
                "Investigate peak workload and CPU utilization."
            )

        else:

            bottleneck = "Unknown performance issue"

            recommendation = (
                "Collect additional diagnostic information."
            )

        return {
            "agent": "Model Based",
            "bottleneck": bottleneck,
            "recommendation": recommendation
        }