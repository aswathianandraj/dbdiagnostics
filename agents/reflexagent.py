from tools.diagnostic_tools import (
    inspect_query_plan,
    get_database_metrics
)

class reflexagent:

    def diagnose(self, scenario):

        plan = inspect_query_plan(scenario)

        if plan == "Full Table Scan":

            bottleneck = "Query execution issue"

            recommendation = (
                "Investigate missing indexes."
            )

        else:

            metrics = get_database_metrics(scenario)

            if metrics["connections"] >= scenario["connection_pool_max"]:

                bottleneck = "Connection pool saturation"

                recommendation = (
                    "Review pool configuration."
                )

            else:

                bottleneck = "Resource contention"

                recommendation = (
                    "Investigate peak traffic."
                )

        return {
            "agent": "Reflex",
            "bottleneck": bottleneck,
            "recommendation": recommendation
        }