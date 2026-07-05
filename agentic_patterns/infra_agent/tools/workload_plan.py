"""WorkloadPlan provisioning tools: declare a plan and read its status."""

import json
from pathlib import Path
from typing import Literal

from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime
from langgraph.types import Command
from pydantic import ValidationError

from agentic_patterns.infra_agent.state import Environment
from agentic_patterns.infra_agent.tools.clients import (
    apply_cr,
    delete_cr,
    dynamic_client_for,
    get_cr,
    get_cr_status,
    list_crs,
)
from agentic_patterns.infra_agent.tools.models import Component, PlanModel, build_workload_plan
from agentic_patterns.infra_agent.tools.prompts import (
    DECLARE_PLAN_DESCRIPTION,
    DELETE_PLAN_DESCRIPTION,
    GET_PLAN_STATUS_DESCRIPTION,
    LIST_PLANS_DESCRIPTION,
    UPDATE_PLAN_DESCRIPTION,
)
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


def _as_components(components: list[Component] | str) -> list:
    """Coerce components to a list, tolerating a JSON string from the model.

    The typed schema guides the model to send a real array, but some still wrap it
    in a JSON string; parse that back so Gate 1 validation sees the real structure.
    """
    if isinstance(components, str):
        components = json.loads(components)
    if not isinstance(components, list):
        raise ValueError("components must be a JSON array of component objects")
    return components


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
    components: list[Component] | str,
    target: str,
    tool_runtime: ToolRuntime,
) -> Command:
    """Validate a plan at Gate 1, translate it to a WorkloadPlan, and apply it to the target."""
    env = _target_env(tool_runtime, target)
    if env is None:
        return tool_reply(tool_runtime, "declare_plan_no_target", target=target)

    try:
        plan = PlanModel.model_validate({"intent": intent, "components": _as_components(components)})
    except (ValueError, ValidationError) as exc:
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
    print(f"====> [get_plan_status] name {name} target {target}")
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


def _component_dict(component: Component | dict | str) -> dict:
    """Normalize an incoming component to a plain dict, tolerating a JSON string."""
    if isinstance(component, str):
        component = json.loads(component)
    if isinstance(component, Component):
        return component.model_dump()
    if isinstance(component, dict):
        return component
    raise ValueError("component must be an object with a name and manifest")


def _format_plans(crs: list[dict]) -> str:
    """Render a one-line overview per plan for the list view."""
    lines = []
    for cr in crs:
        meta = cr.get("metadata") or {}
        spec = cr.get("spec") or {}
        status = cr.get("status") or {}
        components = spec.get("components") or []
        lines.append(
            f"  {meta.get('name')} — intent={spec.get('intent')}, phase={status.get('phase', 'Pending')}, "
            f"ready={status.get('readyCount', 0)}, components={len(components)}"
        )
    return "\n".join(lines)


def _format_plan_components(cr: dict) -> str:
    """Render each declared component with its kind and current child status."""
    spec = cr.get("spec") or {}
    status = cr.get("status") or {}
    child_by_name = {child.get("name"): child for child in (status.get("children") or [])}
    lines = []
    for component in spec.get("components") or []:
        cname = component.get("name")
        kind = (component.get("manifest") or {}).get("kind")
        child = child_by_name.get(cname) or {}
        state = "ready" if child.get("ready") else "failed" if child.get("failed") else "pending"
        note = f" — {child['note']}" if child.get("note") else ""
        lines.append(f"  {cname} ({kind}) {state}{note}")
    return "\n".join(lines) or "  (no components)"


@tool(name_or_callable="update_plan", description=UPDATE_PLAN_DESCRIPTION)
def update_plan(
    name: str,
    target: str,
    mode: Literal["component", "plan"],
    tool_runtime: ToolRuntime,
    component: Component | str | None = None,
    components: list[Component] | str | None = None,
    intent: str | None = None,
) -> Command:
    """Read the current plan, apply a component or whole-plan edit, revalidate, and reapply."""
    env = _target_env(tool_runtime, target)
    if env is None:
        return tool_reply(tool_runtime, "declare_plan_no_target", target=target)
    if mode not in ("component", "plan"):
        return tool_reply(tool_runtime, "update_plan_bad_mode", mode=mode)

    try:
        client = dynamic_client_for(env, _workspace(tool_runtime))
        current = get_cr(client, name, env.namespace)
    except Exception as exc:
        return tool_reply(tool_runtime, "update_plan_apply_error", name=name, error=str(exc))
    if current is None:
        return tool_reply(tool_runtime, "plan_missing", name=name, target=target)

    spec = current.get("spec") or {}
    existing = spec.get("components") or []
    existing_names = ", ".join(str(component.get("name")) for component in existing)

    if mode == "component":
        if component is None:
            return tool_reply(tool_runtime, "update_plan_no_component")
        try:
            comp = _component_dict(component)
        except (ValueError, TypeError) as exc:
            return tool_reply(tool_runtime, "update_plan_invalid", existing=existing_names, errors=str(exc))
        merged = [c for c in existing if c.get("name") != comp.get("name")] + [comp]
        change = f"component '{comp.get('name')}'"
    else:
        if components is None:
            return tool_reply(tool_runtime, "update_plan_no_components")
        try:
            merged = _as_components(components)
        except ValueError as exc:
            return tool_reply(tool_runtime, "update_plan_invalid", existing=existing_names, errors=str(exc))
        change = "whole plan"

    try:
        plan = PlanModel.model_validate({"intent": intent or spec.get("intent"), "components": merged})
    except (ValueError, ValidationError) as exc:
        return tool_reply(tool_runtime, "update_plan_invalid", existing=existing_names, errors=str(exc))

    cr = build_workload_plan(plan, name=name)
    try:
        apply_cr(client, cr, env.namespace)
    except Exception as exc:
        return tool_reply(tool_runtime, "update_plan_apply_error", name=name, error=str(exc))

    return tool_reply(
        tool_runtime,
        "update_plan_ok",
        state_update={"plan_name": name},
        name=name,
        target=target,
        change=change,
        count=len(plan.components),
    )


@tool(name_or_callable="delete_plan", description=DELETE_PLAN_DESCRIPTION)
def delete_plan(
    name: str,
    target: str,
    mode: Literal["component", "plan"],
    tool_runtime: ToolRuntime,
    component_name: str | None = None,
) -> Command:
    """Delete a whole plan, or remove one component and let the operator prune its child."""
    env = _target_env(tool_runtime, target)
    if env is None:
        return tool_reply(tool_runtime, "declare_plan_no_target", target=target)
    if mode not in ("component", "plan"):
        return tool_reply(tool_runtime, "delete_plan_bad_mode", mode=mode)

    try:
        client = dynamic_client_for(env, _workspace(tool_runtime))
        current = get_cr(client, name, env.namespace)
    except Exception as exc:
        return tool_reply(tool_runtime, "delete_plan_error", name=name, error=str(exc))
    if current is None:
        return tool_reply(tool_runtime, "plan_missing", name=name, target=target)

    if mode == "plan":
        try:
            delete_cr(client, name, env.namespace)
        except Exception as exc:
            return tool_reply(tool_runtime, "delete_plan_error", name=name, error=str(exc))
        return tool_reply(tool_runtime, "delete_plan_ok", name=name, target=target)

    if component_name is None:
        return tool_reply(tool_runtime, "delete_plan_no_component_name")

    spec = current.get("spec") or {}
    existing = spec.get("components") or []
    names = [component.get("name") for component in existing]
    if component_name not in names:
        return tool_reply(
            tool_runtime,
            "delete_plan_component_missing",
            name=name,
            component_name=component_name,
            existing=", ".join(str(n) for n in names),
        )
    if len(existing) <= 1:
        return tool_reply(tool_runtime, "delete_plan_last_component", name=name, component_name=component_name)

    remaining = [component for component in existing if component.get("name") != component_name]
    try:
        plan = PlanModel.model_validate({"intent": spec.get("intent"), "components": remaining})
        cr = build_workload_plan(plan, name=name)
        apply_cr(client, cr, env.namespace)
    except Exception as exc:
        return tool_reply(tool_runtime, "delete_plan_error", name=name, error=str(exc))

    return tool_reply(
        tool_runtime,
        "delete_plan_component_ok",
        name=name,
        target=target,
        component_name=component_name,
        count=len(remaining),
    )


@tool(name_or_callable="list_plans", description=LIST_PLANS_DESCRIPTION)
def list_plans(target: str, tool_runtime: ToolRuntime, name: str | None = None) -> Command:
    """List every plan on the target, or drill into one plan's components and their status."""
    env = _target_env(tool_runtime, target)
    if env is None:
        return tool_reply(tool_runtime, "declare_plan_no_target", target=target)

    try:
        client = dynamic_client_for(env, _workspace(tool_runtime))
        if name is None:
            crs = list_crs(client, env.namespace)
        else:
            cr = get_cr(client, name, env.namespace)
    except Exception as exc:
        return tool_reply(tool_runtime, "list_plans_error", target=target, error=str(exc))

    if name is None:
        if not crs:
            return tool_reply(tool_runtime, "list_plans_empty", target=target)
        return tool_reply(tool_runtime, "list_plans_ok", target=target, plans=_format_plans(crs))

    if cr is None:
        return tool_reply(tool_runtime, "plan_missing", name=name, target=target)
    spec = cr.get("spec") or {}
    status = cr.get("status") or {}
    return tool_reply(
        tool_runtime,
        "list_plans_detail",
        name=name,
        target=target,
        intent=spec.get("intent"),
        phase=status.get("phase", "Pending"),
        components=_format_plan_components(cr),
    )


for _tool in (declare_plan, get_plan_status, update_plan, delete_plan, list_plans):
    TOOLS_BY_NAME[_tool.name] = _tool
