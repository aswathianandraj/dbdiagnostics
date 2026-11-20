# tools/diagnostic_tools.py
"""The four READ-ONLY diagnostic tools from the brief.

They only read the scenario dict (our simulated database). None of them can
change anything, which is how "no schema changes are executed" is guaranteed.
The LLM agent wraps these same functions as LangChain tools.
"""


def get_database_metrics(scenario):
    return {
        "latency": scenario["query_latency_ms"],
        "baseline_latency": scenario.get("baseline_latency_ms"),
        "sla": scenario["expected_sla_ms"],
        "qps": scenario["query_frequency_per_min"],
        "cpu": scenario["cpu_usage"],
        "memory": scenario["memory_usage"],
        "connections": scenario["connection_pool_used"],
        "pool_max": scenario["connection_pool_max"],
        "waiting_requests": scenario["waiting_requests"],
        "history": scenario.get("history", []),
    }


def inspect_query_plan(scenario):
    return scenario["query_plan"]


def search_database_logs(scenario, pattern=""):
    return [line for line in scenario["logs"] if pattern.lower() in line.lower()]


def get_index_metadata(scenario):
    return {
        "indexes_present": scenario["indexes_present"],
        "rows_examined": scenario.get("rows_examined"),
        "rows_returned": scenario.get("rows_returned"),
    }
