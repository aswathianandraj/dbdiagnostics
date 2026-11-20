import json


class learningagent:

    def diagnose(self, scenario):

        with open(
            "data/experience.json",
            "r"
        ) as file:

            history = json.load(file)

        scores = {}

        for action, stats in history.items():

            total = (
                stats["success"]
                + stats["failure"]
            )

            scores[action] = (
                stats["success"] / total
            )

        best_action = max(
            scores,
            key=scores.get
        )

        return {
            "agent": "Learning Agent",
            "bottleneck": best_action,
            "recommendation": (
                f"Historical success rate favors "
                f"{best_action} ({scores[best_action]:.2%})."
            )
        }