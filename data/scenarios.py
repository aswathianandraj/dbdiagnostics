"""Shared scenarios: every agent receives exactly the same dict.

Scenarios A, B, C are the three failure cases from the brief.
N (healthy) and E (edge / ambiguous) are added so the test set covers
normal, critical and edge cases.

`history` holds recent metric windows (oldest first). Only the model-based
agent uses it, which is what makes it different from the simple reflex agent.
`expected_bottleneck` is the answer key: tests read it, agents must NOT
(app.py and the tests pass `agent_view(scenario)`, which strips it).
"""

SCENARIOS = {
    "Scenario A": {
        "name": "Frequent Slow Query with Full Table Scan",
        "query_latency_ms": 1200,
        "baseline_latency_ms": 150,
        "query_frequency_per_min": 500,
        "connection_pool_used": 35,
        "connection_pool_max": 100,
        "waiting_requests": 2,
        "cpu_usage": 42,
        "memory_usage": 58,
        "query_plan": "Full Table Scan",
        "rows_examined": 4800000,
        "rows_returned": 12,
        "indexes_present": False,
        "logs": [
            "Repeated slow query warning",
            "Query execution exceeded threshold of 1000ms",
            "High rows scanned"
        ],
        "history": [
            {"window": "09:00", "latency_ms": 1100, "qps": 490, "cpu": 40, "pool_used": 33, "waiting": 1},
            {"window": "09:05", "latency_ms": 1150, "qps": 495, "cpu": 41, "pool_used": 34, "waiting": 2},
            {"window": "09:10", "latency_ms": 1200, "qps": 500, "cpu": 42, "pool_used": 35, "waiting": 2}
        ],
        "expected_sla_ms": 300,
        "expected_bottleneck": "Missing index / full table scan"
    },

    "Scenario B": {
        "name": "Connection Pool Saturation",
        "query_latency_ms": 850,
        "baseline_latency_ms": 150,
        "query_frequency_per_min": 300,
        "connection_pool_used": 100,
        "connection_pool_max": 100,
        "waiting_requests": 75,
        "cpu_usage": 38,
        "memory_usage": 52,
        "query_plan": "Index Scan",
        "rows_examined": 1,
        "rows_returned": 1,
        "indexes_present": True,
        "logs": [
            "Connection acquisition timeout",
            "Maximum pool size reached",
            "Request waiting for database connection"
        ],
        "history": [
            {"window": "09:00", "latency_ms": 300, "qps": 295, "cpu": 37, "pool_used": 88, "waiting": 5},
            {"window": "09:05", "latency_ms": 600, "qps": 298, "cpu": 38, "pool_used": 100, "waiting": 40},
            {"window": "09:10", "latency_ms": 850, "qps": 300, "cpu": 38, "pool_used": 100, "waiting": 75}
        ],
        "expected_sla_ms": 300,
        "expected_bottleneck": "Connection pool saturation"
    },

    "Scenario C": {
        "name": "Peak Traffic Resource Saturation",
        "query_latency_ms": 700,
        "baseline_latency_ms": 150,
        "query_frequency_per_min": 1200,
        "connection_pool_used": 95,
        "connection_pool_max": 100,
        "waiting_requests": 40,
        "cpu_usage": 92,
        "memory_usage": 85,
        "query_plan": "Index Scan",
        "rows_examined": 52000,
        "rows_returned": 6,
        "indexes_present": True,
        "logs": [
            "Traffic spike detected",
            "CPU utilization exceeded 90%",
            "Connection usage approaching pool limit"
        ],
        "history": [
            {"window": "19:00", "latency_ms": 220, "qps": 400, "cpu": 48, "pool_used": 40, "waiting": 0},
            {"window": "19:05", "latency_ms": 450, "qps": 800, "cpu": 75, "pool_used": 70, "waiting": 10},
            {"window": "19:10", "latency_ms": 700, "qps": 1200, "cpu": 92, "pool_used": 95, "waiting": 40}
        ],
        "expected_sla_ms": 300,
        "expected_bottleneck": "Peak load / capacity"
    },

    "Scenario N": {
        "name": "Normal Traffic, All Within SLA",
        "query_latency_ms": 160,
        "baseline_latency_ms": 150,
        "query_frequency_per_min": 450,
        "connection_pool_used": 30,
        "connection_pool_max": 100,
        "waiting_requests": 0,
        "cpu_usage": 40,
        "memory_usage": 50,
        "query_plan": "Index Scan",
        "rows_examined": 1,
        "rows_returned": 1,
        "indexes_present": True,
        "logs": [
            "Checkpoint complete"
        ],
        "history": [
            {"window": "10:00", "latency_ms": 155, "qps": 440, "cpu": 39, "pool_used": 29, "waiting": 0},
            {"window": "10:05", "latency_ms": 158, "qps": 445, "cpu": 40, "pool_used": 30, "waiting": 0},
            {"window": "10:10", "latency_ms": 160, "qps": 450, "cpu": 40, "pool_used": 30, "waiting": 0}
        ],
        "expected_sla_ms": 300,
        "expected_bottleneck": "Healthy"
    },

    "Scenario E": {
        "name": "Edge Case: Weak Mixed Signals, Missing Data",
        "query_latency_ms": 340,
        "baseline_latency_ms": 150,
        "query_frequency_per_min": 460,
        "connection_pool_used": 80,
        "connection_pool_max": 100,
        "waiting_requests": 0,
        "cpu_usage": 68,
        "memory_usage": 60,
        "query_plan": None,
        "rows_examined": None,
        "rows_returned": None,
        "indexes_present": True,
        "logs": [],
        "history": [
            {"window": "14:10", "latency_ms": 340, "qps": 460, "cpu": 68, "pool_used": 80, "waiting": 0}
        ],
        "expected_sla_ms": 300,
        "expected_bottleneck": "Insufficient evidence"
    }
}


def agent_view(scenario):
    """The scenario without the answer key. Always pass this to agents."""
    return {k: v for k, v in scenario.items() if k != "expected_bottleneck"}
