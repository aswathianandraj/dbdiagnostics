# Database Performance Diagnosis Assistant

Agentic AI (PCAM ZG519) · Mini Project 1 · Group 14

## Overview

This project implements six AI agents that diagnose performance issues in database-backed applications using simulated database telemetry and diagnostics.

All agents receive **the same scenario data** to ensure a fair comparison. Each agent outputs the five parts the brief asks for: **symptom summary, evidence, likely bottleneck, recommended diagnostic/optimisation steps, verification metric**, plus its reasoning and a confidence score.

**Safety:** the four diagnostic tools are read-only, and every recommendation is advisory (for DBA review, tested in staging first). No schema change is ever executed. The unsafe option "Create Index Now" exists only so the utility agent can show why it loses.

## Problem Statement

Diagnose slow database-backed applications using:
- Query latency
- Connection pool status
- Query plans
- Index metadata
- Database logs

## Project Structure

```
dbdiagnostics/
├── app.py                     # Streamlit UI: pick a scenario, run all agents, compare
├── agents/
│   ├── common.py              # bottleneck labels, action library, evidence scorer, common output
│   ├── reflexagent.py         # Simple reflex
│   ├── modelbasedagent.py     # Model-based reflex
│   ├── goalbasedagent.py      # Goal-based (BFS planner)
│   ├── utilitybasedagent.py   # Utility-based (expected utility)
│   ├── learningagent.py       # Learning (reads + updates experience.json)
│   └── llmagent.py            # LLM: Ollama Qwen3 via LangChain + tool calling
├── tools/diagnostic_tools.py  # the 4 read-only tools
├── data/
│   ├── scenarios.py           # shared scenarios A, B, C, N, E
│   └── experience.json        # learning agent's outcome history
├── tests/test_agents.py       # pytest
├── requirements.txt
└── README.md
```

## Scenarios

| ID | Type | Situation | Expected diagnosis |
|---|---|---|---|
| A | critical | Frequent query slow; plan is a Full Table Scan; no index | Missing index / full table scan |
| B | critical | Pool 100/100, 75 requests waiting; acquisition timeouts | Connection pool saturation |
| C | critical | Latency rises with traffic (400 → 1200 queries/min) and CPU (92%) | Peak load / capacity |
| N | normal | Everything within SLA | Healthy (no action) |
| E | edge | Slightly over SLA, no logs, query plan unavailable, one metric window | Insufficient evidence (low confidence) |

Each scenario also has a short `history` of metric windows (used by the model-based agent).

## Diagnostic Tools

- `get_database_metrics()`: latency, SLA, baseline, queries/min, CPU, memory, pool usage, waiting requests, history
- `inspect_query_plan()`: plan type (Full Table Scan / Index Scan / unavailable)
- `search_database_logs(pattern)`: case-insensitive log search
- `get_index_metadata()`: index present? rows examined vs returned

## Agent Architectures

| Agent | Decision mechanism |
|---|---|
| **Simple Reflex** | IF-THEN rules on the current snapshot only; the first matching rule wins. No memory. |
| **Model-Based** | Rules over an **internal state** built from history: pool-saturation streak, latency trend, whether latency rises *with* traffic and CPU. This is what separates C (load) from A (bad plan at flat traffic). |
| **Goal-Based** | Goal: latency ≤ SLA, safe actions only, cause confirmed first. **Breadth-first search** over actions with preconditions (optimise only after a diagnostic) and effects (predicted latency). Returns the shortest plan, e.g. A: Query Plan Check → Index Review (1200 → 160 ms). |
| **Utility-Based** | Scores every action: EU = P(cause \| evidence) × benefit − 0.05·cost − 0.5·risk − 10 if unsafe. Picks the maximum; the full table is shown in the UI. |
| **Learning** | Picks the action with the best Laplace-smoothed success rate (s+1)/(n+2) from `experience.json`, explores 10% of the time, then records the (simulated) outcome, so history changes the next decision. |
| **LLM** | Qwen3 on Ollama **via LangChain** (`ChatOllama.bind_tools`). The model calls the 4 tools itself (at least 2 are enforced), and the answer is forced into a Pydantic schema. **Evidence check:** every number it cites must appear in a tool output, otherwise confidence is capped at 0.4. |

## Installation

```
python -m venv venv
venv\Scripts\activate          (Linux / lab server: source venv/bin/activate)
pip install -r requirements.txt
```

## Ollama Setup

```
ollama pull qwen3
ollama list
```

## Run Application

```
streamlit run app.py
```

or

```
python -m streamlit run app.py
```

## Tests

```
pytest -v
```

63 tests: every classical agent × every scenario (correct bottleneck, all five output parts, never recommends a schema change on production; the edge case must not be answered with high confidence), plus mechanism tests (model-based uses history, goal plan confirms before fixing, unsafe action loses on utility, learning updates history) and the LLM evidence checker.

## Comparison: why decisions differ

All classical agents reach the right bottleneck on all five scenarios, but they **recommend differently**:
- **Reflex vs model-based:** same final label, but the model-based agent's evidence comes from trends (e.g. "pool saturated for 2 consecutive windows"), so it would not overreact to a one-window blip.
- **Goal-based vs utility-based:** in A, the goal agent insists on *Query Plan Check first* (precondition), while the utility agent ranks *Index Review* first (highest expected payoff). In C, the goal agent needs a 4-step plan (diagnose, cache, replica, rate limit) to predict latency under the SLA.
- **Learning:** its choice depends on history (e.g. in B it prefers *Fix Connection Leak* over *Pool Analysis* because it worked 5/6 times), and it changes as outcomes are recorded.
- **LLM:** gives the richest explanation, but its claims are only trusted after the evidence check.
- **Edge case E:** every agent reports *Insufficient evidence* with low confidence and recommends collecting more data instead of inventing a cause.

## Limitations

- Simulated data, not a live database; thresholds and the world model are hand-tuned.
- The utility weights and the predicted latency reductions are assumptions, not measured values.
- The learning agent's critic is simulated (an action "works" with 80% probability if it targets the diagnosed cause).
- The goal-based, utility-based and learning agents share one evidence scorer for the diagnosis; they differ in how they choose actions.
- Small local LLMs can skip tools or hallucinate numbers, which is mitigated (not eliminated) by the 2-tool rule, the Pydantic schema and the evidence check.

## Individual Contributions

| Member | Implemented |
|---|---|
| **Aswathi Anandraj** | Original project structure and Streamlit UI (scenario selector, metric cards, comparison table); scenarios A, B, C; the 4 diagnostic tools; first versions of all six agents; lab-server (Prayogshala) setup with Ollama + Qwen3; execution report and screenshots |
| **Kartikey Rana** | Distinct decision mechanisms for the 5 classical agents (model-based state from history, goal-based BFS planner, utility table, learning agent that updates its history); shared evidence scorer and action library; scenarios N and E plus metric history; LLM agent rewritten with LangChain tool calling, Pydantic output and evidence check; pytest suite; README sections |

## Authors

Aswathi Anandraj · Kartikey Rana
