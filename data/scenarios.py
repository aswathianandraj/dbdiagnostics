SCENARIOS = {
    "Scenario A": {
        "name": "Frequent Slow Query with Full Table Scan",
        "query_latency_ms": 1200,
        "query_frequency_per_min": 500,
        "connection_pool_used": 35,
        "connection_pool_max": 100,
        "waiting_requests": 2,
        "cpu_usage": 42,
        "memory_usage": 58,
        "query_plan": "Full Table Scan",
        "indexes_present": False,
        "logs": [
            "Repeated slow query warning",
            "Query execution exceeded threshold of 1000ms",
            "High rows scanned"
        ],
        "expected_sla_ms": 300
    },

    "Scenario B": {
        "name": "Connection Pool Saturation",
        "query_latency_ms": 850,
        "query_frequency_per_min": 300,
        "connection_pool_used": 100,
        "connection_pool_max": 100,
        "waiting_requests": 75,
        "cpu_usage": 38,
        "memory_usage": 52,
        "query_plan": "Index Scan",
        "indexes_present": True,
        "logs": [
            "Connection acquisition timeout",
            "Maximum pool size reached",
            "Request waiting for database connection"
        ],
        "expected_sla_ms": 300
    },

    "Scenario C": {
        "name": "Peak Traffic Resource Saturation",
        "query_latency_ms": 700,
        "query_frequency_per_min": 1200,
        "connection_pool_used": 95,
        "connection_pool_max": 100,
        "waiting_requests": 40,
        "cpu_usage": 92,
        "memory_usage": 85,
        "query_plan": "Index Scan",
        "indexes_present": True,
        "logs": [
            "Traffic spike detected",
            "CPU utilization exceeded 90%",
            "Connection usage approaching pool limit"
        ],
        "expected_sla_ms": 300
    }
}