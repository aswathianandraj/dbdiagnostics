from ollama import chat

from tools.diagnostic_tools import (
    get_database_metrics,
    inspect_query_plan,
    search_database_logs,
    get_index_metadata
)


class llmagent:

    def diagnose(self, scenario):

        metrics = get_database_metrics(scenario)

        plan = inspect_query_plan(scenario)

        logs = search_database_logs(scenario)

        indexes = get_index_metadata(scenario)

        prompt = f"""
You are a database performance diagnosis assistant.

Analyze the following evidence.

Metrics:
{metrics}

Query Plan:
{plan}

Logs:
{logs}

Index Metadata:
{indexes}

Provide:

1. Symptom Summary
2. Evidence
3. Likely Bottleneck
4. Recommended Diagnostic Steps
5. Verification Metric

Do not suggest schema changes.
"""

        print("Metrics:", metrics)
        print("Plan:", plan)
        print("Calling Qwen3...")

        response = chat(
            model="qwen3",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        print("Completed")

       


        return {
            "agent": "LLM Agent",
            "bottleneck": "LLM Analysis",
            "recommendation": response.message.content
        }