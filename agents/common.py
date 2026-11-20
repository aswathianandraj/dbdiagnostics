"""Shared pieces every agent uses, so their outputs are comparable.

* Fixed bottleneck labels
* A library of candidate ACTIONS (all recommendations; nothing is executed)
* symptom_summary(): one factual line describing the symptoms
* score_evidence(): scores each possible cause from the signals
  (used by the goal-based, utility-based and learning agents, which then
  DECIDE differently; the two reflex agents use their own rules)
* make_result(): the common output with the 5 parts the brief asks for:
  symptom summary, evidence, likely bottleneck, recommended steps, verification metric
"""
from dataclasses import dataclass

INDEX = "Missing index / full table scan"
POOL = "Connection pool saturation"
LOAD = "Peak load / capacity"
HEALTHY = "Healthy"
UNKNOWN = "Insufficient evidence"
BOTTLENECKS = (INDEX, POOL, LOAD, HEALTHY, UNKNOWN)


@dataclass(frozen=True)
class Action:
    name: str
    description: str
    addresses: str          # which bottleneck it helps
    kind: str               # "diagnostic" or "optimization"
    safe: bool              # False = schema change on production -> never recommended
    cost: int               # effort 0 (none) .. 5 (high)
    risk: float             # 0 .. 1 chance of side effects
    reduction: float        # predicted share of the regression (latency - baseline) removed
    verification_metric: str


ACTIONS = [
    Action("Query Plan Check", "Run EXPLAIN ANALYZE on the slow query in staging to confirm the full scan",
           INDEX, "diagnostic", True, 1, 0.02, 0.0, "rows examined vs rows returned"),
    Action("Index Review", "Propose an index on the filtered column for DBA review; test it in staging first",
           INDEX, "optimization", True, 2, 0.10, 0.99, "query latency + rows examined"),
    Action("Create Index Now", "Run CREATE INDEX directly on production",
           INDEX, "optimization", False, 2, 0.60, 0.99, "query latency"),
    Action("Pool Analysis", "List long-held / idle-in-transaction connections and the jobs that own them",
           POOL, "diagnostic", True, 1, 0.02, 0.0, "connections held longer than 30 s"),
    Action("Fix Connection Leak", "Release leaked connections in the app; set idle and checkout timeouts",
           POOL, "optimization", True, 3, 0.15, 0.99, "pool wait time + waiting requests"),
    Action("Raise Pool Size", "Raise the pool size moderately, staying within the DB's max_connections",
           POOL, "optimization", True, 1, 0.30, 0.40, "pool wait time + DB CPU"),
    Action("Capacity Review", "Identify the top queries by CPU/time during the peak window",
           LOAD, "diagnostic", True, 1, 0.02, 0.0, "CPU share per query"),
    Action("Cache Hot Reads", "Cache hot read queries with a short TTL",
           LOAD, "optimization", True, 3, 0.20, 0.50, "latency at peak QPS + CPU"),
    Action("Read Replica", "Route read-only traffic to a read replica",
           LOAD, "optimization", True, 4, 0.25, 0.45, "primary CPU + latency at peak"),
    Action("Rate Limit Non-critical", "Rate-limit or defer non-critical traffic during peaks",
           LOAD, "optimization", True, 2, 0.20, 0.30, "latency of critical endpoints at peak"),
    Action("Keep Monitoring", "No change needed; keep monitoring latency against the SLA",
           HEALTHY, "diagnostic", True, 0, 0.0, 0.0, "latency vs SLA"),
    Action("Collect More Data", "Collect the missing evidence: enable the slow-query log, capture query plans, "
           "gather more metric windows", UNKNOWN, "diagnostic", True, 1, 0.02, 0.0,
           "evidence completeness (plans, logs, >= 3 windows)"),
]
BY_NAME = {a.name: a for a in ACTIONS}


def actions_for(bottleneck, safe_only=True):
    return [a for a in ACTIONS if a.addresses == bottleneck and (a.safe or not safe_only)]


def symptom_summary(s):
    return (f"Latency {s['query_latency_ms']} ms vs SLA {s['expected_sla_ms']} ms "
            f"(baseline {s.get('baseline_latency_ms', '?')} ms); pool {s['connection_pool_used']}/"
            f"{s['connection_pool_max']} with {s['waiting_requests']} waiting; CPU {s['cpu_usage']}%; "
            f"{s['query_frequency_per_min']} queries/min")


def score_evidence(s):
    """Returns ({bottleneck: score}, {bottleneck: [evidence lines]})."""
    logs = " ".join(s.get("logs") or []).lower()
    history = s.get("history") or []
    scores = {INDEX: 0, POOL: 0, LOAD: 0, HEALTHY: 0, UNKNOWN: 1}  # small prior: "I might not know"
    why = {b: [] for b in scores}

    if s.get("query_plan") == "Full Table Scan" and not s.get("indexes_present"):
        scores[INDEX] += 3
        why[INDEX].append("query plan is a Full Table Scan and no index covers the filter")
        if s.get("rows_examined") and s.get("rows_returned"):
            if s["rows_examined"] / s["rows_returned"] > 1000:
                scores[INDEX] += 1
                why[INDEX].append(f"{s['rows_examined']:,} rows examined to return {s['rows_returned']}")
        if "slow query" in logs or "rows scanned" in logs:
            scores[INDEX] += 1
            why[INDEX].append("logs report repeated slow queries / high rows scanned")

    if s["connection_pool_used"] >= s["connection_pool_max"] and s["waiting_requests"] > 0:
        scores[POOL] += 3
        why[POOL].append(f"pool {s['connection_pool_used']}/{s['connection_pool_max']} "
                         f"with {s['waiting_requests']} requests waiting")
        if s["waiting_requests"] > 20:
            scores[POOL] += 1
            why[POOL].append("large queue of waiting requests")
    if "acquisition timeout" in logs or "maximum pool size" in logs:
        scores[POOL] += 1
        why[POOL].append("logs show connection-acquisition timeouts / max pool size reached")

    if s["cpu_usage"] > 85:
        scores[LOAD] += 2
        why[LOAD].append(f"CPU {s['cpu_usage']}% at {s['query_frequency_per_min']} queries/min")
        if len(history) >= 2 and history[-1]["qps"] > 1.5 * history[0]["qps"]:
            scores[LOAD] += 1
            why[LOAD].append(f"traffic grew from {history[0]['qps']} to {history[-1]['qps']} queries/min")
    if "traffic spike" in logs or "cpu utilization" in logs:
        scores[LOAD] += 1
        why[LOAD].append("logs report a traffic spike / high CPU")

    if s["query_latency_ms"] <= s["expected_sla_ms"]:
        scores[HEALTHY] += 4
        why[HEALTHY].append(f"latency {s['query_latency_ms']} ms is within the {s['expected_sla_ms']} ms SLA")

    if s.get("query_plan") is None:
        scores[UNKNOWN] += 1
        why[UNKNOWN].append("query plan unavailable")
    if not s.get("logs"):
        scores[UNKNOWN] += 1
        why[UNKNOWN].append("no logs available")
    if len(history) < 2:
        scores[UNKNOWN] += 1
        why[UNKNOWN].append(f"only {len(history)} metric window(s), so no trend can be seen")

    return scores, why


def top_hypothesis(s):
    scores, why = score_evidence(s)
    best = max(scores, key=scores.get)
    return best, why[best] or ["no strong signal for any known cause"], scores


def make_result(agent, scenario, bottleneck, evidence, steps, verification_metric, reasoning,
                confidence, details=None):
    return {
        "agent": agent,
        "bottleneck": bottleneck,
        "symptom_summary": symptom_summary(scenario),
        "evidence": "; ".join(evidence),
        "recommendation": " | ".join(f"{i}. {s}" for i, s in enumerate(steps, 1)),
        "verification_metric": verification_metric,
        "confidence": round(float(confidence), 2),
        "reasoning": reasoning,
        "details": details or {},
    }
