# Database Performance Diagnosis Assistant

## Overview

This project implements six AI agents that diagnose performance issues in database-backed applications using simulated database telemetry and diagnostics.

The system compares:
- Simple Reflex Agent
- Model-Based Reflex Agent
- Goal-Based Agent
- Utility-Based Agent
- Learning Agent
- LLM-Based Agent (Ollama + Qwen3)

All agents receive the same scenario data to ensure fair comparison.

## Problem Statement

Diagnose slow database-backed applications using:
- Query latency
- Connection pool status
- Query plans
- Index metadata
- Database logs

Agents recommend safe diagnostics and optimizations without performing schema changes.

## Project Structure

dbdiagnostics/
├── app.py
├── agents/
├── llmagents/
├── tools/
├── data/
├── requirements.txt
└── README.md


## Scenarios

### Scenario A
Frequent query is slow and the query plan shows a full table scan.

### Scenario B
Requests wait for connections because the database pool is saturated.

### Scenario C
Query latency rises during peak traffic along with CPU and connection usage.

## Diagnostic Tools

- get_database_metrics()
- inspect_query_plan()
- search_database_logs()
- get_index_metadata()

## Agent Architectures

### Simple Reflex Agent
Uses condition-action rules based on current observations.

### Model-Based Agent
Uses an internal representation of system state.

### Goal-Based Agent
Selects actions that help achieve the SLA goal.

### Utility-Based Agent
Chooses actions with the highest estimated utility.

### Learning Agent
Uses historical success and failure data.

### LLM Agent
Uses Ollama Qwen3 with tool calling and evidence-based reasoning.

## Installation


python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt


## Run Application


streamlit run app.py


or


python -m streamlit run app.py


## Ollama Setup


ollama pull qwen3
ollama list


## Requirements


streamlit
pandas
numpy
ollama


## Submission Checklist

- Five Classical Agents
- One LLM Agent
- Tool Calling
- Streamlit UI
- Comparison Table
- Test Results
- Screenshots
- README

## Author

Aswathi Anandraj
