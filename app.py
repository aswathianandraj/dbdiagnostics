import json

import pandas as pd
import streamlit as st

from data.scenarios import SCENARIOS, agent_view

from agents.reflexagent import reflexagent
from agents.modelbasedagent import modelbasedagent
from agents.goalbasedagent import goalbasedagent
from agents.utilitybasedagent import utilitybasedagent
from agents.learningagent import learningagent
from agents.llmagent import llmagent

st.set_page_config(
    page_title="Database Diagnosis Assistant",
    layout="wide"
)

st.title("Database Performance Diagnosis Assistant")
st.markdown(
    """
    Compare how different AI agent architectures diagnose
    the same database performance problem.
    All recommendations are advisory: **no schema changes are executed**.
    """
)

st.divider()

# ----------------------------
# SCENARIO SELECTION
# ----------------------------

scenario_name = st.selectbox(
    "Select Scenario",
    list(SCENARIOS.keys()),
    format_func=lambda k: f"{k}: {SCENARIOS[k]['name']}"
)

scenario = SCENARIOS[scenario_name]
view = agent_view(scenario)  # the answer key is never shown to agents

# ----------------------------
# SCENARIO DETAILS
# ----------------------------

st.subheader("Scenario Details")

c1, c2, c3 = st.columns(3)

with c1:
    st.metric(
        "Latency (ms)",
        scenario["query_latency_ms"],
        help=f"SLA {scenario['expected_sla_ms']} ms"
    )

    st.metric(
        "Query Frequency",
        scenario["query_frequency_per_min"]
    )

with c2:
    st.metric(
        "CPU Usage %",
        scenario["cpu_usage"]
    )

    st.metric(
        "Memory Usage %",
        scenario["memory_usage"]
    )

with c3:
    st.metric(
        "Connections",
        f"{scenario['connection_pool_used']}/{scenario['connection_pool_max']}"
    )

    st.metric(
        "Waiting Requests",
        scenario["waiting_requests"]
    )

with st.expander("View Complete Scenario Data (identical input for all agents)"):

    st.json(view)

st.divider()

use_llm = st.checkbox("Include LLM agent (needs Ollama running with qwen3)", value=True)

# ----------------------------
# RUN AGENTS
# ----------------------------

if st.button("Run All Agents", width="stretch"):

    agents = [
        reflexagent(),
        modelbasedagent(),
        goalbasedagent(),
        utilitybasedagent(),
        learningagent()
    ]

    if use_llm:
        agents.append(llmagent())

    results = []

    with st.spinner("Agents are diagnosing..."):

        for agent in agents:

            result = agent.diagnose(view)

            results.append(result)

    # -----------------------------------
    # AGENT CARDS (3 per row, so all six fit)
    # -----------------------------------

    st.subheader("Agent Diagnoses")

    for row_start in range(0, len(results), 3):

        cols = st.columns(3)

        for col, result in zip(cols, results[row_start:row_start + 3]):

            with col:

                st.info(result["agent"])

                st.write(
                    f"**Bottleneck**\n\n{result['bottleneck']} "
                    f"(confidence {result['confidence']:.2f})"
                )

                st.write(
                    f"**Recommendation**\n\n{result['recommendation']}"
                )

    st.divider()

    # -----------------------------------
    # COMPARISON TABLE
    # -----------------------------------

    st.subheader("Agent Comparison")

    comparison_df = pd.DataFrame(results)[
        ["agent", "bottleneck", "confidence", "recommendation", "verification_metric"]
    ]

    st.dataframe(
        comparison_df,
        width="stretch",
        hide_index=True
    )

    found = {r["bottleneck"] for r in results}
    if len(found) == 1:
        st.success(f"All agents agree: **{found.pop()}**")
    else:
        st.warning("Agents disagree: " + ", ".join(sorted(found)) +
                   ". See the reasoning below for why their mechanisms differ.")

    st.divider()

    # -----------------------------------
    # SUMMARY (the 5 required outputs per agent)
    # -----------------------------------

    st.subheader("Decision Summary")

    for result in results:

        with st.expander(f"{result['agent']}: {result['bottleneck']}"):

            st.markdown(
                f"""
                - **Symptom summary:** {result['symptom_summary']}
                - **Evidence:** {result['evidence']}
                - **Likely bottleneck:** {result['bottleneck']}
                - **Recommended steps:** {result['recommendation']}
                - **Verification metric:** {result['verification_metric']}
                - **Reasoning:** {result['reasoning']}
                """
            )

            if result["details"]:
                st.markdown("**Agent internals** (state / plan / utility table / learning history / tool log):")
                st.code(json.dumps(result["details"], indent=2, default=str), language="json")

    with st.expander("Answer key (for testing only; never passed to agents)"):

        st.write(scenario["expected_bottleneck"])
