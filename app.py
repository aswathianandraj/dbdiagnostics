import pandas as pd
import streamlit as st

from data.scenarios import SCENARIOS

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
st.markdown( """
    Compare how different AI agent architectures diagnose
    the same database performance problem.
    """
)

st.divider()

# ----------------------------
# SCENARIO SELECTION
# ----------------------------

scenario_name = st.selectbox(
    "Select Scenario",
    list(SCENARIOS.keys())
)

scenario = SCENARIOS[scenario_name]

# ----------------------------
# SCENARIO DETAILS
# ----------------------------

st.subheader("Scenario Details")

c1, c2, c3 = st.columns(3)

with c1:
    st.metric(
        "Latency (ms)",
        scenario["query_latency_ms"]
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

with st.expander("View Complete Scenario Data"):

    st.json(scenario)

st.divider()

# ----------------------------
# RUN AGENTS
# ----------------------------

if st.button("Run All Agents", use_container_width=True):

    agents = [
        reflexagent(),
        modelbasedagent(),
        goalbasedagent(),
        utilitybasedagent(),
        learningagent(),
        llmagent()
    ]

    results = []

    for agent in agents:

        result = agent.diagnose(scenario)

        results.append(result)

    # -----------------------------------
    # AGENT CARDS
    # -----------------------------------

    st.subheader("Agent Diagnoses")

    cols = st.columns(5)

    for col, result in zip(cols, results):

        with col:

            st.info(result["agent"])

            st.write(
                f"**Bottleneck**\n\n{result['bottleneck']}"
            )

            st.write(
                f"**Recommendation**\n\n{result['recommendation']}"
            )

    st.divider()

    # -----------------------------------
    # COMPARISON TABLE
    # -----------------------------------

    st.subheader("Agent Comparison")

    comparison_df = pd.DataFrame(results)

    st.dataframe(
        comparison_df,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # -----------------------------------
    # SUMMARY
    # -----------------------------------

    st.subheader("Decision Summary")

    for result in results:

        st.markdown(
            f"""
            **{result['agent']}**

            - Bottleneck: {result['bottleneck']}
            - Recommendation: {result['recommendation']}
            """
        )