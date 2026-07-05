"""WorkloadPlan provisioning tools: declare a plan and read its status."""

from pathlib import Path

from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime
from langgraph.types import Command
from pydantic import ValidationError

from agentic_patterns.infra_agent.state import Environment
from agentic_patterns.infra_agent.tools.clients import apply_cr, dynamic_client_for, get_cr_status
from agentic_patterns.infra_agent.tools.models import PlanModel, build_workload_plan
from agentic_patterns.infra_agent.tools.prompts import DECLARE_PLAN_DESCRIPTION, GET_PLAN_STATUS_DESCRIPTION
from agentic_patterns.shared.helper import tool_reply
from agentic_patterns.shared.skill_registry import TOOLS_BY_NAME


def _target_env(tool_runtime: ToolRuntime, name: str) -> Environment | None:
    """Return the named kubernetes environment from context, or None."""
    environments = getattr(tool_runtime.context, "environments", None) or []
    for env in environments:
        if env.name == name and env.kind == "kubernetes":
            return env
    return None


def _workspace(tool_runtime: ToolRuntime) -> Path:
    """Return the workspace path from context, defaulting to the current directory."""
    return Path(str(getattr(tool_runtime.context, "workspace", None) or "."))


def _format_children(children: list[dict]) -> str:
    """Render the per-child status breakdown for the model."""
    if not children:
        return "  (none reported yet)"
    lines = []
    for child in children:
        state = "ready" if child.get("ready") else "failed" if child.get("failed") else "pending"
        note = f" — {child['note']}" if child.get("note") else ""
        lines.append(f"  {child.get('name')} ({child.get('kind')}) {state}{note}")
    return "\n".join(lines)


def _format_attention(conditions: list[dict]) -> str:
    """Surface a NeedsAttention condition as a single line, or empty when absent."""
    for condition in conditions:
        if condition.get("type") == "NeedsAttention":
            return f"NeedsAttention: {condition.get('message', '')}"
    return ""


@tool(name_or_callable="declare_plan", description=DECLARE_PLAN_DESCRIPTION)
def declare_plan(
    name: str,
    intent: str,
    components: list[dict],
    target: str,
    tool_runtime: ToolRuntime,
) -> Command:
    """Validate a plan at Gate 1, translate it to a WorkloadPlan, and apply it to the target."""
    env = _target_env(tool_runtime, target)
    if env is None:
        return tool_reply(tool_runtime, "declare_plan_no_target", target=target)

    try:
        plan = PlanModel.model_validate({"intent": intent, "components": components})
    except ValidationError as exc:
        return tool_reply(tool_runtime, "declare_plan_invalid", errors=str(exc))

    cr = build_workload_plan(plan, name=name)
    try:
        client = dynamic_client_for(env, _workspace(tool_runtime))
        apply_cr(client, cr, env.namespace)
    except Exception as exc:
        return tool_reply(tool_runtime, "declare_plan_apply_error", name=name, error=str(exc))

    return tool_reply(
        tool_runtime,
        "declare_plan_ok",
        state_update={"plan_name": name},
        name=name,
        count=len(plan.components),
        target=target,
    )


@tool(name_or_callable="get_plan_status", description=GET_PLAN_STATUS_DESCRIPTION)
def get_plan_status(name: str, target: str, tool_runtime: ToolRuntime) -> Command:
    """Read a WorkloadPlan's status from the target cluster and render it for the model."""
    env = _target_env(tool_runtime, target)
    if env is None:
        return tool_reply(tool_runtime, "declare_plan_no_target", target=target)

    try:
        client = dynamic_client_for(env, _workspace(tool_runtime))
        status = get_cr_status(client, name, env.namespace)
    except Exception as exc:
        return tool_reply(tool_runtime, "get_plan_status_error", name=name, error=str(exc))

    if status is None:
        return tool_reply(tool_runtime, "get_plan_status_missing", name=name, target=target)

    return tool_reply(
        tool_runtime,
        "get_plan_status_ok",
        name=name,
        target=target,
        phase=status.get("phase", "Pending"),
        ready=status.get("readyCount", 0),
        children=_format_children(status.get("children", [])),
        attention=_format_attention(status.get("conditions", [])),
    )


for _tool in (declare_plan, get_plan_status):
    TOOLS_BY_NAME[_tool.name] = _tool
