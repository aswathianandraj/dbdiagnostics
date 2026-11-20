"""LLM Agent: local Ollama model (Qwen3) through LangChain, with real tool calling.

How it works:
  1. The four read-only diagnostic tools are given to the model as LangChain tools.
  2. Tool loop: the MODEL decides which tools to call; our code runs them and returns the results.
     If it answers after fewer than 2 distinct tools, it is told to gather more evidence.
  3. The final answer is forced into a Pydantic schema (the 5 required outputs + confidence).
  4. Evidence check: every number the model cites must appear in some tool output.
     Unverified claims cap the confidence at 0.4.

Safety: tools are read-only, and the system prompt forbids executing schema changes.
"""
import json
import re
from typing import Literal

from pydantic import BaseModel, Field

from agents.common import BOTTLENECKS, UNKNOWN, make_result
from tools import diagnostic_tools as dt

MODEL = "qwen3"
MAX_STEPS = 6

SYSTEM_PROMPT = f"""You are a database performance diagnosis assistant.
Rules:
- Use the tools to gather evidence. Call AT LEAST TWO different tools before answering.
- Base every claim on numbers the tools returned, and quote those numbers.
- NEVER execute or recommend executing schema changes directly (no CREATE/ALTER/DROP on production).
  Recommend safe diagnostics, or changes for DBA review tested in staging first.
- If the evidence is weak or missing, say "{UNKNOWN}" with low confidence. Do not invent a cause.
- The bottleneck must be exactly one of: {list(BOTTLENECKS)}.
"""


class LLMDiagnosis(BaseModel):
    symptom_summary: str
    evidence: list[str] = Field(description="Facts quoting numbers returned by the tools")
    bottleneck: Literal[BOTTLENECKS]  # type: ignore[valid-type]
    recommended_steps: list[str]
    verification_metric: str
    confidence: float = Field(ge=0, le=1)


def build_tools(scenario):
    from langchain_core.tools import tool

    @tool
    def get_database_metrics() -> str:
        """Current latency, SLA, baseline, queries/min, CPU, memory, connection pool usage, waiting requests and recent history windows."""
        return json.dumps(dt.get_database_metrics(scenario))

    @tool
    def inspect_query_plan() -> str:
        """The query plan type of the main query (e.g. Full Table Scan, Index Scan), or null if unavailable."""
        return json.dumps(dt.inspect_query_plan(scenario))

    @tool
    def search_database_logs(pattern: str = "") -> str:
        """Search the database logs (case-insensitive). An empty pattern returns all lines."""
        return json.dumps(dt.search_database_logs(scenario, pattern))

    @tool
    def get_index_metadata() -> str:
        """Whether an index exists for the filtered column, plus rows examined vs rows returned."""
        return json.dumps(dt.get_index_metadata(scenario))

    return [get_database_metrics, inspect_query_plan, search_database_logs, get_index_metadata]


_NUM = re.compile(r"-?\d[\d,]*\.?\d*")


def _numbers(text):
    out = set()
    for n in _NUM.findall(text):
        try:
            f = float(n.replace(",", "").rstrip("."))
            out.add(str(int(f)) if f.is_integer() else str(f))
        except ValueError:
            pass
    return out


def check_evidence(evidence, tool_log):
    """Every number in an evidence line must appear in some tool output."""
    tool_numbers = set().union(*(_numbers(t["output"]) for t in tool_log)) if tool_log else set()
    verified, unverified = [], []
    for item in evidence:
        nums = _numbers(item)
        (verified if nums and nums <= tool_numbers else unverified).append(item)
    tools_used = sorted({t["tool"] for t in tool_log})
    return {"verified": verified, "unverified": unverified, "tools_used": tools_used,
            "enough_tools": len(tools_used) >= 2}


class llmagent:

    def __init__(self, model=MODEL):
        self.model = model

    def run(self, scenario):
        from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
        from langchain_ollama import ChatOllama

        tools = build_tools(scenario)
        by_name = {t.name: t for t in tools}
        llm = ChatOllama(model=self.model, temperature=0)
        llm_tools = llm.bind_tools(tools)

        messages = [SystemMessage(SYSTEM_PROMPT),
                    HumanMessage(f"The application is slow. Diagnose this situation: {scenario['name']}")]
        tool_log = []
        for _ in range(MAX_STEPS):  # hard cap on loop iterations
            ai = llm_tools.invoke(messages)
            messages.append(ai)
            if ai.tool_calls:
                for call in ai.tool_calls:
                    t = by_name.get(call["name"])
                    output = t.invoke(call["args"]) if t else json.dumps({"error": f"unknown tool {call['name']}"})
                    tool_log.append({"tool": call["name"], "args": call["args"], "output": output})
                    messages.append(ToolMessage(content=output, tool_call_id=call["id"]))
                continue
            if len({t["tool"] for t in tool_log}) < 2:
                messages.append(HumanMessage("You have used fewer than two different tools. "
                                             "Call more tools to gather evidence before answering."))
                continue
            break

        messages.append(HumanMessage("Now give your final diagnosis using only the evidence above."))
        diagnosis = llm.with_structured_output(LLMDiagnosis).invoke(messages)
        return diagnosis, tool_log

    def diagnose(self, scenario):
        try:
            diagnosis, tool_log = self.run(scenario)
        except Exception as e:  # Ollama not running, model missing, invalid output...
            return make_result(
                "LLM Agent", scenario, UNKNOWN, [f"LLM unavailable: {type(e).__name__}: {e}"],
                ["Start Ollama (`ollama serve`) and pull the model (`ollama pull qwen3`)"],
                "-", "The LLM agent could not run, so it makes no claim.", 0.0,
                {"error": str(e)},
            )

        check = check_evidence(diagnosis.evidence, tool_log)
        confidence = diagnosis.confidence
        if check["unverified"] or not check["enough_tools"]:
            confidence = min(confidence, 0.4)  # don't trust what we could not verify
        return make_result(
            "LLM Agent", scenario, diagnosis.bottleneck, diagnosis.evidence,
            diagnosis.recommended_steps, diagnosis.verification_metric,
            f"Qwen3 called {len(tool_log)} tool(s) ({', '.join(check['tools_used']) or 'none'}). "
            f"Evidence check: {len(check['verified'])} verified, {len(check['unverified'])} unverified.",
            confidence,
            {"evidence_check": check, "tool_log": tool_log, "symptom_summary_llm": diagnosis.symptom_summary},
        )
