from tools.diagnostic_tools import (
    inspect_query_plan,
    get_database_metrics
)


class utilitybasedagent:

    def diagnose(self, scenario):

        metrics = get_database_metrics(scenario)
        plan = inspect_query_plan(scenario)

        utility_scores = {
            "Index Review": 0,
            "Pool Analysis": 0,
            "Capacity Review": 0
        }

        if plan == "Full Table Scan":
            utility_scores["Index Review"] = 95

        if (
            metrics["connections"]
            >= scenario["connection_pool_max"]
        ):
            utility_scores["Pool Analysis"] = 90

        if metrics["cpu"] > 85:
            utility_scores["Capacity Review"] = 92

        best_action = max(
            utility_scores,
            key=utility_scores.get
        )

        return {
            "agent": "Utility Based",
            "bottleneck": best_action,
            "recommendation": (
                f"Prioritize {best_action} because it provides "
                "the highest estimated performance improvement."
            )
        }