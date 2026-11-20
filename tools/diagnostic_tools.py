# tools/database_tools.py

def get_database_metrics(scenario):
    return {
        "latency": scenario["query_latency_ms"],
        "cpu": scenario["cpu_usage"],
        "memory": scenario["memory_usage"],
        "connections": scenario["connection_pool_used"]
    }


def inspect_query_plan(scenario):
    return scenario["query_plan"]


def search_database_logs(scenario):
    return scenario["logs"]


def get_index_metadata(scenario):
    return {
        "indexes_present": scenario["indexes_present"]
    }