"""Tool descriptions for the infrastructure agent tools."""

DECLARE_PLAN_DESCRIPTION = """Declare a set of components as a single WorkloadPlan on a target kubernetes environment.

Pass a plan name, the intent (migrate or provision), the list of components, and the name of the target
environment to apply to. Each component is an object with a unique 'name' and a 'manifest' (a complete
kubernetes object with apiVersion, kind and metadata.name). For a migration a component may also carry
'source_ref' (where it came from) and 'accepted_losses' (declared lossy mappings).

The plan is validated in process before anything reaches the cluster. On a validation error nothing is
applied and you are told exactly what to fix. On success an operator reconciles the plan into owned child
resources; call get_plan_status to watch it converge."""

GET_PLAN_STATUS_DESCRIPTION = """Read the status of a WorkloadPlan you declared, and dig into why when it is stuck.

Pass the plan name and the target environment name. Returns the phase (Pending, Ready or Failed), how many
children are ready, and a per-child breakdown with any failure notes.

When the plan is not converging — it has failed, the operator is behind on reconciling it, or a plan or child
has raised warnings — it also returns the conditions, the reconcile progress, and the recent Warning events
that explain the cause (a forbidden operation, an image that will not pull, a pod that will not schedule). A
stuck result is a signal to act on that cause (fix and update_plan, or escalate to the user), not to keep
polling; a Pending plan with no warnings is still converging, so poll again."""

UPDATE_PLAN_DESCRIPTION = """Update an existing WorkloadPlan on a target kubernetes environment, in one of two modes.

Pass the plan name, the target environment, and mode. With mode 'component' pass a single 'component' object
to add or replace by name, leaving every other component untouched: this is how you change one workload, such
as raising an app's resource requests. With mode 'plan' pass the full 'components' list, and optionally a new
intent, to replace the whole plan.

The plan must already exist; use declare_plan to create one. The resulting plan is validated in process before
anything reaches the cluster, so a bad edit is rejected with nothing applied. On success the operator
reconciles the change; call get_plan_status to watch it converge."""

DELETE_PLAN_DESCRIPTION = """Delete a WorkloadPlan, or one of its components, on a target kubernetes environment.

Pass the plan name, the target environment, and mode. With mode 'component' pass 'component_name' to remove
just that component; the operator deletes its child resource and leaves the rest of the plan running. With
mode 'plan' the whole plan is deleted and every child it owns is removed.

Removing the last component is refused, since a plan needs at least one; delete the whole plan instead."""

LIST_PLANS_DESCRIPTION = """List WorkloadPlans on a target kubernetes environment, or drill into one.

Pass the target environment. Without a name you get every plan with its intent, phase, ready count and number
of components. Pass a name to drill into that plan and see each component with its kind and current child
status."""

CHECK_ESCALATIONS_DESCRIPTION = """Check whether any WorkloadPlan needs a human.

Takes no arguments. It scans every kubernetes environment you can reach and reports any plan whose status
carries a NeedsAttention escalation, which the operator sets when a plan has failed. Use it to poll for
problems without naming a specific plan; an empty result means nothing needs attention right now."""
