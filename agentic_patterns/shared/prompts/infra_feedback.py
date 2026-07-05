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
}
