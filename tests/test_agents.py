"""Tests: every classical agent x every scenario (run: pytest -v).

The LLM agent is tested only where it doesn't need Ollama (the evidence checker).
"""
import copy

import pytest

from agents.common import BOTTLENECKS, UNKNOWN
from agents.goalbasedagent import goalbasedagent
from agents.learningagent import learningagent
from agents.llmagent import check_evidence
from agents.modelbasedagent import modelbasedagent
from agents.reflexagent import reflexagent
from agents.utilitybasedagent import utilitybasedagent
from data.scenarios import SCENARIOS, agent_view
from tools import diagnostic_tools as dt

AGENTS = [reflexagent(), modelbasedagent(), goalbasedagent(), utilitybasedagent(),
          learningagent(persist=False, seed=7)]
REQUIRED = ["agent", "bottleneck", "symptom_summary", "evidence", "recommendation",
            "verification_metric", "confidence", "reasoning"]


def test_scenarios_cover_normal_critical_edge():
    assert {"Scenario A", "Scenario B", "Scenario C", "Scenario N", "Scenario E"} <= set(SCENARIOS)


@pytest.mark.parametrize("name", list(SCENARIOS))
@pytest.mark.parametrize("agent", AGENTS, ids=lambda a: type(a).__name__)
def test_output_has_the_five_required_parts(agent, name):
    r = agent.diagnose(agent_view(SCENARIOS[name]))
    assert all(r[k] not in (None, "") for k in REQUIRED)
    assert r["bottleneck"] in BOTTLENECKS


@pytest.mark.parametrize("name", list(SCENARIOS))
@pytest.mark.parametrize("agent", AGENTS, ids=lambda a: type(a).__name__)
def test_expected_bottleneck(agent, name):
    s = SCENARIOS[name]
    r = agent.diagnose(agent_view(s))
    if s["expected_bottleneck"] == UNKNOWN:
        assert r["bottleneck"] == UNKNOWN or r["confidence"] <= 0.5, "over-confident on the edge case"
    else:
        assert r["bottleneck"] == s["expected_bottleneck"]


@pytest.mark.parametrize("agent", AGENTS, ids=lambda a: type(a).__name__)
def test_never_recommends_schema_change_on_production(agent):
    for s in SCENARIOS.values():
        assert "CREATE INDEX directly" not in agent.diagnose(agent_view(s))["recommendation"]


def test_agents_do_not_see_the_answer_key():
    assert all("expected_bottleneck" not in agent_view(s) for s in SCENARIOS.values())


def test_tools_are_read_only():
    s = copy.deepcopy(SCENARIOS["Scenario A"])
    dt.get_database_metrics(s); dt.inspect_query_plan(s); dt.search_database_logs(s, "slow"); dt.get_index_metadata(s)
    assert s == SCENARIOS["Scenario A"]


def test_model_based_uses_history():
    assert modelbasedagent().update_state(SCENARIOS["Scenario B"])["pool_saturated_streak"] >= 2
    assert modelbasedagent().update_state(SCENARIOS["Scenario C"])["latency_tracks_load"]


def test_goal_based_confirms_before_fixing_and_stays_safe():
    r = goalbasedagent().diagnose(agent_view(SCENARIOS["Scenario A"]))
    plan = [p["action"] for p in r["details"]["plan"]]
    assert plan == ["Query Plan Check", "Index Review"] and r["details"]["goal_reached"]


def test_utility_unsafe_action_loses():
    r = utilitybasedagent().diagnose(agent_view(SCENARIOS["Scenario A"]))
    table = r["details"]["utility_table"]
    assert table[0]["action"] == "Index Review"
    assert next(t for t in table if t["action"] == "Create Index Now")["EU"] < 0


def test_learning_updates_history(tmp_path):
    f = tmp_path / "exp.json"
    f.write_text('{"Missing index / full table scan": {"Index Review": {"success": 10, "failure": 2}}}')
    r = learningagent(experience_file=f, seed=1).diagnose(agent_view(SCENARIOS["Scenario A"]))
    assert sum(r["details"]["after"].values()) == sum(r["details"]["before"].values()) + 1


def test_evidence_checker():
    log = [{"tool": "get_database_metrics", "output": '{"latency": 1200, "cpu": 42}'},
           {"tool": "get_index_metadata", "output": '{"rows_examined": 4800000}'}]
    res = check_evidence(["latency is 1200 ms", "4,800,000 rows examined", "CPU is 99%"], log)
    assert res["unverified"] == ["CPU is 99%"] and res["enough_tools"]
