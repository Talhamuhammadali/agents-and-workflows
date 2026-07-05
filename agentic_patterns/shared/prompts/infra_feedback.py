"""Feedback messages for the infrastructure agent tools."""

INFRA_FEEDBACK = {
    "declare_plan_no_target": (
        "{prefix} No kubernetes target named '{target}' is available. Check the environments "
        "you were given and pass one of their names."
    ),
    "declare_plan_invalid": (
        "{prefix} The plan failed validation and nothing was submitted to the cluster. Fix these "
        "and call declare_plan again:\n{errors}"
    ),
    "declare_plan_apply_error": (
        "{prefix} Plan '{name}' validated but could not be applied to the target cluster: {error}"
    ),
    "declare_plan_ok": (
        "{prefix} Declared plan '{name}' with {count} component(s) on target '{target}'. The operator "
        "is now reconciling it. Poll get_plan_status to watch it converge."
    ),
    "get_plan_status_error": "{prefix} Could not read status for plan '{name}': {error}",
    "get_plan_status_missing": "{prefix} No plan named '{name}' exists on target '{target}' yet.",
    "get_plan_status_ok": (
        "{prefix} Plan '{name}' on '{target}': phase={phase}, ready={ready}.\nChildren:\n{children}\n{attention}"
    ),
    "plan_missing": (
        "{prefix} No plan named '{name}' exists on target '{target}'. Use declare_plan to create it first."
    ),
    "update_plan_bad_mode": (
        "{prefix} Unknown mode '{mode}'. Use 'component' to change one component or 'plan' for the whole plan."
    ),
    "update_plan_no_component": "{prefix} mode 'component' needs a 'component' object with a name and manifest.",
    "update_plan_no_components": "{prefix} mode 'plan' needs the full 'components' list to replace the plan with.",
    "update_plan_invalid": (
        "{prefix} The edit was rejected and nothing changed on the cluster. Existing components: {existing}. "
        "Fix these and try again:\n{errors}"
    ),
    "update_plan_apply_error": "{prefix} Plan '{name}' validated but could not be applied: {error}",
    "update_plan_ok": (
        "{prefix} Updated plan '{name}' on '{target}' ({change}). It now has {count} component(s) and the "
        "operator is reconciling. Poll get_plan_status to watch it converge."
    ),
    "delete_plan_bad_mode": (
        "{prefix} Unknown mode '{mode}'. Use 'component' to remove one component or 'plan' to delete the whole plan."
    ),
    "delete_plan_no_component_name": "{prefix} mode 'component' needs 'component_name' naming the component to remove.",
    "delete_plan_component_missing": (
        "{prefix} Plan '{name}' has no component named '{component_name}'. Existing components: {existing}."
    ),
    "delete_plan_last_component": (
        "{prefix} '{component_name}' is the only component in plan '{name}'; a plan needs at least one. "
        "Delete the whole plan instead with mode 'plan'."
    ),
    "delete_plan_error": "{prefix} Could not delete from plan '{name}': {error}",
    "delete_plan_component_ok": (
        "{prefix} Removed component '{component_name}' from plan '{name}' on '{target}'. The operator is "
        "pruning its child; {count} component(s) remain."
    ),
    "delete_plan_ok": "{prefix} Deleted plan '{name}' on '{target}'. Its child resources are being removed.",
    "list_plans_error": "{prefix} Could not list plans on target '{target}': {error}",
    "list_plans_empty": "{prefix} No plans exist on target '{target}' yet.",
    "list_plans_ok": "{prefix} Plans on '{target}':\n{plans}",
    "list_plans_detail": (
        "{prefix} Plan '{name}' on '{target}': intent={intent}, phase={phase}.\nComponents:\n{components}"
    ),
}
